import dataclasses
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
	from ..cacher import Cacher

import sys
if sys.version_info >= (3, 9):
	import collections.abc
	_Sequence = collections.abc.Sequence
else:
	import typing
	_Sequence = typing.Sequence

ScalarParameterValue = Any

TParameterList = Sequence[ScalarParameterValue]
def ParameterList(*s: ScalarParameterValue) -> TParameterList:
	return list(s)

class RenderedQuery(NamedTuple):
	sql: str
	parameters: TParameterList

	# utility properties for easy splatting
	@property
	def pd(self) -> Dict[str, Any]:
		return dict(
			sql=self.sql,
			params=self.parameters
		)

	@property
	def db(self) -> Tuple[str, TParameterList]:
		return (self.sql, self.parameters)

class QueryBit(metaclass=ABCMeta):
	pass

class QueryExtension(metaclass=ABCMeta): pass

QE = TypeVar('QE', bound=QueryExtension) # should be bound=Intersection[QueryExtension, NamedTuple]

class PreBuildHook(Protocol):
	def __call__(self) -> Optional['Query']: ...

@dataclass(frozen=True)
class PreBuild(QueryExtension):
	hook: PreBuildHook

NOVALUE = '_csql_novalue'

@dataclass(frozen=True)
class Query(QueryBit, InstanceTracking):

	queryParts: Tuple[Union[str, QueryBit], ...]
	default_dialect: SQLDialect
	default_overrides: Optional['Overrides']
	_extensions: FrozenSet[QueryExtension]


	## deps

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	
	## extensions
	def _get_extension(self, t: Type[QE]) -> Optional[QE]:
		exts = {type(e): e for e in self._extensions} # could memoize this
		return cast(QE,
			exts.get(t)
		) # mypy sucks

	def _add_extensions(self, *e: QueryExtension) -> 'Query':
		return dataclasses.replace(self, 
			_extensions=self._extensions | set(e)
		)

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
		from ..cacher import _cache_replacer

		overrides = overrides or self.default_overrides or Overrides()

		ParamRenderer = (
			overrides.paramRenderer
			if overrides.paramRenderer is not None
			else ParameterRenderer.get(dialect)
		)
		if not issubclass(ParamRenderer, ParameterRenderer):
			raise ValueError(f'{ParamRenderer} needs to be a subclass of csql.ParameterRenderer')

		QR: Type[QueryRenderer] = (
			overrides.queryRenderer # type: ignore # mypy bug
			if overrides.queryRenderer is not None
			else BoringSQLRenderer
		)
		if not issubclass(QR, QueryRenderer):
			raise ValueError(f'{QueryRenderer} needs to be a subclass of csql.SQLRenderer')
		queryRenderer = QR(ParamRenderer, dialect=dialect)

		new_self = self
		new_self = _replace_stuff(_params_replacer(newParams), new_self)
		new_self = _replace_stuff(_cache_replacer(queryRenderer), new_self)
		new_self = _replace_stuff(_pre_build_replacer(), new_self)

		queryRenderer = QR(ParamRenderer, dialect=dialect)
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
		return pd.read_sql(
			**previewQ.pd(dialect=dialect, newParams=newParams, overrides=overrides),
			con=con
		)

	def pd(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> Dict[str, Any]:
		return self.build(dialect=dialect, newParams=newParams, overrides=overrides).pd

	def db(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> Tuple[str, TParameterList]:
		return self.build(dialect=dialect, newParams=newParams, overrides=overrides).db

PartReplacer = Callable[[Union[str, QueryBit]], Union[str, QueryBit]]
QueryReplacer = Callable[[Query], Query]

def _replace_stuff(fn: QueryReplacer, q: Query) -> Query:
	"""Replace every q in a tree with fn(q), beginning with the leaves."""
	import functools
		
	@functools.lru_cache(maxsize=None)
	def rewrite_query(q: Query) -> Query:

		def replacer(q: Union[str, QueryBit]) -> Union[str, QueryBit]:
			if isinstance(q, Query):
				return rewrite_query(q)
			else:
				return q

		new_q = _replace_parts(replacer, q)

		result = fn(new_q)

		if not isinstance(result, Query):
			raise TypeError(f'{fn} returned None! fn passed to QueryReplacer needs to always return a Query.')
		
		return result

	return rewrite_query(q)

def _replace_parts(fn: PartReplacer, q: Query) -> Query:
	"""Replaces every bit in q with fn(bit). If the result is the same, q is returned unchanged."""
	new_parts = tuple(fn(part) for part in q.queryParts)
	if new_parts == q.queryParts:
		return q
	else:
		return dataclasses.replace(q, queryParts=new_parts)

def _params_replacer(newParams: Optional[Dict[str, Any]]) -> QueryReplacer:
	if newParams is None:
		return lambda q: q
	
	def part_replacer(p: Union[str, QueryBit]) -> Union[str, QueryBit]:
		assert newParams is not None # make mypy happy
		_newParams = Parameters(**newParams) # checks if hashable.

		if (isinstance(p, ParameterPlaceholder) and p.key in _newParams):
			return _newParams[p.key]
		else:
			return p

	def query_replacer(q: Query) -> Query:
		return _replace_parts(part_replacer, q)

	return query_replacer

def _pre_build_replacer() -> QueryReplacer:
	def query_replacer(q: Query) -> Query:
		if (preBuild := q._get_extension(PreBuild)) is None:
			return q
		result = preBuild.hook()
		if result is None:
			return q
		elif isinstance(result, Query):
			return result
		else:
			raise Exception(f'prebuild needs to return None or a Query, it returned {repr(result)}!')
	return query_replacer

@dataclass(frozen=True)
class ParameterPlaceholder(QueryBit, InstanceTracking):
	key: str
	value: Hashable
	_key_context: Optional[int] # allow people to pass multiple distinct parameters with the same key into a Query.


class Parameters:
	params: Dict[str, Hashable]

	def __init__(self, **kwargs: Any):
		self.params = {k: self._check_hashable_value(k, v) for k, v in kwargs.items()}

	@staticmethod
	def _check_hashable_value(key: str, val: Any) -> Hashable:
		if isinstance(val, Collection) and not isinstance(val, str):
			val = tuple(val)
		try:
			h = hash(val)
			return cast(Hashable, val)
		except TypeError as e:
			raise ValueError(f'Refusing to add {key}:{val} - parameter values need to be hashable.') from e

	def _add(self, key: str, val: Any) -> ParameterPlaceholder:
		if key in self.params:
			raise ValueError(f'Refusing to add {key}: it is already in this set of Parameters (with value {self.params[key]}).')
		val = self._check_hashable_value(key, val)
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

	def __contains__(self, key: str) -> bool:
		return self.params.__contains__(key)

	def __getitem__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, _key_context=id(self))

	def __getattr__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, _key_context=id(self))
