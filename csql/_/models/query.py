from typing import *
from dataclasses import dataclass
from abc import ABCMeta, abstractmethod
from ..utils import unique
from textwrap import dedent
from ..input.strparsing import InstanceTracking
from weakref import WeakValueDictionary
from .dialect import SQLDialect
from collections.abc import Collection as CollectionABC
#from .persisted_query import PersistedQuery

import itertools

if TYPE_CHECKING:
	import pandas as pd
	from .overrides import Overrides
	from ..cacher.cacher import Cacher

import sys
if sys.version_info >= (3, 9):
	import collections.abc
	_Sequence = collections.abc.Sequence
else:
	import typing
	_Sequence = typing.Sequence

ScalarParameterValue = Any

class ParameterList(List[ScalarParameterValue]):
	"""This is designed to be returned and passed directly to your DB API. It acts like a list."""

	_params: List[ScalarParameterValue]
	_paramKeys: Dict[str, List[List[int]]]

	def __getitem__(self, i: Any) -> ScalarParameterValue:
		return self._params[i]

	def __iter__(self) -> Iterator[ScalarParameterValue]:
		return iter(self._params)

	def __len__(self) -> int:
		return len(self._params)

	def __init__(self, *params: ScalarParameterValue, keys: Dict[str, List[List[int]]] = {}) -> None:
		self._params = list(params)
		self._paramKeys = keys

	def __repr__(self) -> str:
		return f'Params {repr(self._params)}'

	def __eq__(self, other: Any) -> bool:
		if isinstance(other, ParameterList):
			return self._params == other._params
		elif isinstance(other, list): # mainly used so I didn't have to rewrite a bunch of tests.. this may be removed.
			return self._params == other
		else:
			return False

	def _reparameterize(self, replacements: Dict[str, Union[Collection[ScalarParameterValue], ScalarParameterValue]]) -> List[ScalarParameterValue]:

		newParams = self._params.copy()

		for key, paramValue in replacements.items():
			if key not in self._paramKeys:
				raise Exception(f'Replacement param {key} is not in the original query. You might mean one of {",".join(self._paramKeys)}')

			instances = self._paramKeys[key]

			for indices in instances:
				paramValue = replacements[key]
				if not isinstance(paramValue, CollectionABC) or isinstance(paramValue, str):
					paramValue = [paramValue]

				if len(paramValue) != len(indices):
					origValues = [
						self._params[i] for i in indices
					]
					raise ValueError(
						'Replacing collections is only OK if the replacement is the same length as the original.\n'
						f'You attempted to replace {repr(key)} = {repr(origValues)} (length {len(indices)}) with {repr(paramValue)} (length {len(paramValue)})'
					)
				for i, replacement in zip(indices, paramValue):
					newParams[i] = replacement

		return newParams

	def reparameterize(self, **replacements: ScalarParameterValue) -> 'ParameterList':
		return ParameterList(
			*self._reparameterize(replacements),
			keys=self._paramKeys
		)

class RenderedQuery(NamedTuple):
	sql: str
	parameters: ParameterList

	# utility properties for easy splatting
	@property
	def pd(self) -> Dict[str, Any]:
		return dict(
			sql=self.sql,
			params=self.parameters
		)

	@property
	def db(self) -> Tuple[str, ParameterList]:
		return (self.sql, self.parameters)

class QueryBit(metaclass=ABCMeta):
	pass

class PreBuild(Protocol):
	def __call__(newParams: Optional[Dict[str, ScalarParameterValue]]) -> None:
		pass

@dataclass
class Query(QueryBit, InstanceTracking):

	queryParts: List[Union[str, QueryBit]]
	default_dialect: SQLDialect
	default_overrides: Optional['Overrides']
	_pre_build: Optional[PreBuild] = lambda p: None

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	def _do_pre_build(self, newParams: Optional[Dict[str, ScalarParameterValue]]) -> None:
		# runs pre-build of me and all my deps.
		for dep in self._getDeps():
			if dep._pre_build is None:
				continue
			dep._pre_build(newParams)
		if self._pre_build is not None:
			self._pre_build(newParams)

	def build(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None,
	) -> RenderedQuery:
		dialect = dialect or self.default_dialect
		from ..renderer.query import BoringSQLRenderer, QueryRenderer
		from ..renderer.parameters import ParameterRenderer
		from .overrides import Overrides
		#from ..cacher.cacher import replacer as cache_replacer

		overrides = overrides or self.default_overrides or Overrides()

		ParamRenderer = (
			overrides.paramRenderer
			if overrides.paramRenderer is not None
			else ParameterRenderer.get(dialect)
		)
		if not issubclass(ParamRenderer, ParameterRenderer):
			raise ValueError(f'{ParamRenderer} needs to be a subclass of csql.ParameterRenderer')
		paramRenderer = ParamRenderer()

		QR: Type[QueryRenderer] = (
			overrides.queryRenderer # type: ignore # mypy bug
			if overrides.queryRenderer is not None
			else BoringSQLRenderer
		)
		if not issubclass(QR, QueryRenderer):
			raise ValueError(f'{QueryRenderer} needs to be a subclass of csql.SQLRenderer')
		queryRenderer = QR(paramRenderer, dialect=dialect)

		new_self = self
		if newParams is not None:
			new_self = _replace_stuff(_params_replacer(newParams), new_self)
		#new_self = _replace_stuff(cache_replacer(queryRenderer))
		new_self._do_pre_build(newParams)

		rendered = queryRenderer.render(new_self)

		return RenderedQuery(
			sql=rendered.sql,
			parameters=rendered.parameters
		)

	def persist(self, cacher: 'Cacher') -> 'Query':
		return cacher.persist(self)

	def preview_pd(
		self, con: Any, rows: int=10,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> "pd.DataFrame":
		import pandas as pd
		from csql import Q
		from ..utils import limit_query
		dialect = dialect or self.default_dialect
		previewQ = limit_query(self, rows, dialect)
		return pd.read_sql(**previewQ.pd(), con=con)

	def pd(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> Dict[str, Any]:
		return self.build(dialect=dialect, newParams=newParams).pd

	def db(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> Tuple[str, ParameterList]:
		return self.build(dialect=dialect, newParams=newParams).db

def _replace_stuff(fn: Callable[[QueryBit], QueryBit], q: Query):
	"""Replace every q in a tree with fn(q), beginning with the leaves."""
	import functools

	def cache_with(key):
		def decorator(fn):
			_cache = {}
			@functools.wraps(fn)
			def wrapped(arg):
				k = key(arg)
				if k not in _cache:
					_cache[k] = fn(arg)
				return _cache[k]
			return wrapped
		return decorator
		
	@cache_with(key=lambda q: id(q))
	def rewrite_query(q: Query) -> Query:

		def replacer(q: QueryBit) -> QueryBit:
			if isinstance(q, Query):
				return rewrite_query(q)
			else:
				return q

		new_q = _replace_parts(replacer, q)

		return fn(new_q)

	return rewrite_query(q)

def _replace_parts(fn: Callable[[QueryBit], QueryBit], q: Query):
	"""Replaces every bit in q with fn(bit). If the result is the same, q is returned unchanged."""
	new_parts = [fn(part) for part in q.queryParts]
	if new_parts == q.queryParts:
		return q
	else:
		return Query(
			queryParts=new_parts,
			default_dialect=q.default_dialect,
			default_overrides=q.default_overrides
		)

def _params_replacer(newParams):
	def part_replacer(p: QueryBit):
		if (isinstance(p, ParameterPlaceholder) and p.key in newParams):
			return ParameterPlaceholder(key=p.key, value=newParams[p.key], parameters=None)
		else:
			return p

	def query_replacer(q: Query) -> Query:
		return _replace_parts(part_replacer, q)

	return query_replacer

@dataclass
class ParameterPlaceholder(QueryBit, InstanceTracking):
	key: str
	value: Any
	parameters: 'Parameters'

NOVALUE = '_csql_novalue'

class Parameters:
	params: Dict[str, Any]

	def __init__(self, **kwargs: Any):
		self.params = kwargs

	def _add(self, key: str, val: Any) -> ParameterPlaceholder:
		if key in self.params:
			raise ValueError(f'Refusing to add {key}: it is already in this set of Parameters (with value {self.params[key]}).')
		self.params[key] = val
		return self[key]

	def add(self, _value: Optional[Any]=NOVALUE, **kwargs: Any) -> ParameterPlaceholder:
		'''
		Adds a single parameter into this Parameters, and returns it.
		Useful in loops.
		```
			p = Parameters()
			query = Q(f\'''
				select
					thing
				from table
				where
					val = {p.add('boo')}
					or val = {p.add('bah')}
			\''')
		```
		'''
		passed_arg = (_value is not NOVALUE)
		passed_kw = (len(kwargs) == 1)
		if not (passed_arg ^ passed_kw):
			raise ValueError('You need to call either add(val) or add(key=val)')
		if passed_arg:
			generate_keys = (f'_add_{i}' for i in itertools.count())
			key = next(k for k in generate_keys if k not in self.params)
			return self._add(key, _value)
		elif passed_kw:
			[(key, val)] = kwargs.items()
			return self._add(key, val)
		raise RuntimeError('Uh oh, csql bug. Please report.')


	def __getitem__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, parameters=self)

	def __getattr__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, parameters=self)
