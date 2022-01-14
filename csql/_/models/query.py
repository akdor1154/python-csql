from __future__ import annotations

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
import functools
#from .persisted_query import PersistedQuery

import itertools

if TYPE_CHECKING:
	import pandas as pd
	from .overrides import Overrides
	from ..persist import Cacher
	# import public interface so we can avoid internal ._....  appearing in
	# function signatures, doco, etc.
	import csql
	import csql.dialect
	import csql.persist
	import csql.overrides

import sys
if sys.version_info >= (3, 9):
	import collections.abc
	_Sequence = collections.abc.Sequence
else:
	import typing
	_Sequence = typing.Sequence

ScalarParameterValue = Hashable

ParameterList = Tuple[ScalarParameterValue, ...]

class RenderedQuery(NamedTuple):
	'''
	A :class:`RenderedQuery` is a pair of ``(sql, parameters)``, ready
	to be passed directly to a database.

	They are obtained by using :meth:`Query.build`.
	'''
	sql: str
	''' The rendered SQL, ready to be passed to a database. '''
	parameters: ParameterList
	''' A tuple of parameters, to go along with the SQL. '''
	parameter_names: Tuple[Optional[str], ...]
	''' A tuple of parameter names that the parameters were passed as. '''

	# utility properties for easy splatting
	@property
	def pd(self) -> Dict[str, Any]:
		"""
		Gives dict of ``{'sql':sql, 'params':params}``, for usage like:

		>>> con = my_connection()
		>>> q = Q('select 123')
		>>> pd.read_sql(**q.build().pd, con=con) # doctest: +IGNORE_RESULT

		"""
		return dict(
			sql=self.sql,
			params=self.parameters
		)

	@property
	def db(self) -> Tuple[str, ParameterList]:
		"""
		Returns a tuple of (sql, params), for usage like:

		>>> con = my_connection()
		>>> q = Q('select 123')
		>>> con.cursor().execute(*q.build().db) # doctest: +IGNORE_RESULT
		"""
		return (self.sql, self.parameters)

	def __repr__(self) -> str:
		return f'RenderedQuery({repr(self.sql)}, {repr(self.parameters)})'

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
	"""
	A Query is CSQL's structured concept of a SQL query. You should not create these directly,
	instead you should use :func:`csql.Q`.
	"""

	queryParts: Tuple[Union[str, QueryBit], ...]
	':meta private:'
	default_dialect: Union[csql.dialect.SQLDialect, csql.dialect.InferOrDefault]
	':meta private:'
	default_overrides: Optional[Union[Overrides, csql.overrides.InferOrDefault]]
	':meta private:'
	_extensions: FrozenSet[QueryExtension]
	':meta private:'


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
	
	def _default_dialect(self) -> SQLDialect:
		from .dialect import InferOrDefault
		d = self.default_dialect
		return d.dialect if isinstance(d, InferOrDefault) else d

	def _default_overrides(self) -> Optional[Overrides]:
		from .overrides import InferOrDefault
		o = self.default_overrides
		return o.overrides if isinstance(o, InferOrDefault) else o

	def preview_pd(
		self, con: Any, rows: int=10,
		dialect: Optional[csql.dialect.SQLDialect] = None,
		newParams: Optional[Dict[str, ParameterValue]] = None,
		overrides: Optional[csql.overrides.Overrides] = None
	) -> pd.DataFrame:
		"""
		Return a small dataframe to preview the results of this query.

		Usage:

		>>> c = my_connection()
		>>> q = Q(f'''select 123 as val''')
		>>> print(q.preview_pd(c))
		   val
		0  123


		:param con: A DBAPI-compliant connection, passed directly to ``con`` arg of :func:`pandas.read_sql`.
		:param rows: The number of rows to pull.
		:rtype: :class:`pandas.DataFrame`
		"""
		import pandas as pd
		from csql import Q
		from ..utils import limit_query
		dialect = dialect or self._default_dialect() #TODO - is this needed?
		previewQ = limit_query(self, rows, dialect)
		return pd.read_sql(
			**previewQ.build(dialect=dialect, newParams=newParams, overrides=overrides).pd,
			con=con
		)

	def build(
		self, *,
		dialect: Optional[csql.dialect.SQLDialect] = None,
		newParams: Optional[Dict[str, ParameterValue]] = None,
		overrides: Optional[csql.overrides.Overrides] = None,
	) -> csql.RenderedQuery:
		"""
		Build this :class:`csql.Query` into a :class:`csql.RenderedQuery`.

		While you can specify paramters to manually override how this Query is rendered, it's normally
		better to just supply these as defaults when you create your Queries in the first place. See: :ref:`sql-dialects`.

		:param dialect: An optional :class:`csql.dialect.SQLDialect` to render as. See :ref:`sql-dialects`.
		:param newParams: A dictionary of ``{'key': value}`` to override any parameters. See: :ref:`reparam`.
		:param overrides: An optional :class:`csql.overrides.Overrides` to override how rendering workd. See: :ref:`overrides`.
		"""
		dialect = dialect or self._default_dialect()
		from ..renderer.query import BoringSQLRenderer, QueryRenderer
		from ..renderer.parameters import ParameterRenderer
		from .overrides import Overrides
		from ..persist import cache_replacer
		from .query_replacers import replace_queries_in_tree, params_replacer, pre_build_replacer

		overrides = overrides or self._default_overrides() or Overrides()

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
		new_self = replace_queries_in_tree(params_replacer(newParams), new_self)
		new_self = replace_queries_in_tree(cache_replacer(queryRenderer), new_self)
		new_self = replace_queries_in_tree(pre_build_replacer(), new_self)

		queryRenderer = QR(ParamRenderer, dialect=dialect)
		return queryRenderer.render(new_self)

		# return RenderedQuery(
		# 	sql=rendered.sql,
		# 	parameters=rendered.parameters
		# 	parameter_names = rendered.parameter_names
		# )

	@property
	def pd(self) -> Dict[str, Any]:
		"""
		Convenience wrapper for Query.build().pd.

		Returns a dict of ``{'sql':sql, 'params':params}``, for usage like:

		>>> import pandas as pd
		>>> con = my_connection()
		>>> q = Q('select 123')
		>>> pd.read_sql(**q.pd, con=con)  # doctest: +IGNORE_RESULT

		"""
		return self.build().pd

	@property
	def db(self) -> Tuple[str, ParameterList]:
		"""
		Convenience wrapper for :meth:`Query.build().db<RenderedQuery.db>`.

		Returns a tuple of (sql, params), for usage like:

		>>> con = my_connection()
		>>> q = Q('select 123')
		>>> con.cursor().execute(*q.db) # doctest: +IGNORE_RESULT

		"""
		return self.build().db


	def persist(self, cacher: csql.persist.Cacher, tag: Optional[str] = None) -> csql.Query:
		"""
		Marks this query for persistance with the given :class:`csql.persist.Cacher`.

		See: :ref:`persist`

		Usage:

		>>> con = some_connection()
		>>> cache = csql.contrib.persist.TempTableCacher(con)
		>>> q = Q(f'select 123 from something_slow').persist(cache)
		>>> q.preview_pd(con) # slow # doctest: +IGNORE_RESULT
		>>> q.preview_pd(con) # fast # doctest: +IGNORE_RESULT
		>>> q2 = Q(f'select count(*) from {q}')
		>>> q2.preview_pd(con) # also fast # doctest: +IGNORE_RESULT
		"""
		return cacher.persist(self, tag)

ParameterValue = Union[Hashable, Collection[Hashable]]

@dataclass(frozen=True)
class ParameterPlaceholder(QueryBit, InstanceTracking):
	"""
	A ParameterPlaceholder is what you get when you get an individual parameter by
	name from a :class:`Parameters` object, like `p['param_you_want']`. The only thing
	you should need to do with it is interpolate it into a query:

	>>> p = Parameters(param_you_want=123)
	>>> q = Q(f'select {p["param_you_want"]}')
	>>> q.db
	('select :1', (123,))

	"""
	key: Union[str, AutoKey]
	':meta private:'
	value: csql.ParameterValue
	':meta private:'
	_key_context: Optional[int] # allow people to pass multiple distinct parameters with the same key into a Query.

@dataclass(frozen=True)
class AutoKey:
	"""
	A wrapper for a parameter key, indicating it was generated automatically by :meth:`csql.Parameters.add`.
	"""
	k: str

class Parameters:
	"""
	Parameters let you quickly initialize a bunch of params to pass into your queries.

	Once parameters have been added in the Parameters constructor or with :meth:`add`, they
	can be pulled out by their ``p['parameter name']``, for use in a :func:`Query<Q>`.

	Usage:

	>>> p = Parameters(
	...   start=date(2019,1,1),
	...   end=date(2020,1,1)
	... )
	>>> q = Q(f"select * from customers where {p['start']} <= date and date < {p['end']}")

	See: :ref:`reparam`
	"""

	params: Dict[Union[str, AutoKey], ParameterValue]
	':meta private:'

	def __init__(self, **kwargs: ParameterValue):
		self.params = {k: self._check_hashable_value(k, v) for k, v in kwargs.items()}

	@staticmethod
	def _check_hashable_value(key: Union[str, AutoKey], val: Any) -> Hashable:
		if isinstance(val, Collection) and not isinstance(val, str):
			val = tuple(val)
		try:
			h = hash(val)
			return cast(Hashable, val)
		except TypeError as e:
			raise ValueError(f'Refusing to add {key}:{val} - parameter values need to be hashable.') from e

	def _add(self, key: Union[str, AutoKey], val: Any) -> ParameterPlaceholder:
		if key in self.params:
			raise ValueError(f'Refusing to add {key}: it is already in this set of Parameters (with value {self.params[key]}).')
		val = self._check_hashable_value(key, val)
		self.params[key] = val
		return self[key]

	def add(self, value: csql.ParameterValue=NOVALUE, /, **kwargs: csql.ParameterValue) -> csql.ParameterPlaceholder:
		'''
		Adds a single parameter into this Parameters, and returns it.
		You don't normally need this (just add them directly when building :class:`Parameters`), but
		it can be useful in loops where you need to build a query based on an unknown number of params.

		Can be called as

		>>> p.add('value') # doctest: +IGNORE_RESULT
		... # which will add a single parameter with an autogenerated name.

		Can also be called as

		>>> p.add(key='value') # doctest: +IGNORE_RESULT
		... # which will add a named parameter.

		Useful in loops:

		>>> p = Parameters()
		>>> licence_cancellations = [
		...   ('Shazza', date(2019, 1,  1)),
		...   ('Bazza',  date(2019, 1, 26)),
		...   ('Azza',   date(2022, 1,  3))
		... ]
		>>> where_clause = ' or '.join(
		...   f'(name = {p.add(name)} and timestamp > {p.add(date)})'
		...  for name, date in licence_cancellations
		... )
		>>> query = Q(f'select * from frankston_traffic_log where {where_clause}')

		:param value: A single parameter to add: ``add(123)``. Cannot be used with ``kwargs``.
		:param kwargs: A single key and parameter to add: ``add(my_fav_number=123)``. Cannot be used with ``value``.

		'''
		passed_arg = (value is not NOVALUE)
		passed_kw = (len(kwargs) == 1)
		if not (passed_arg ^ passed_kw):
			raise ValueError('You need to call either add(val) or add(key=val)')
		if passed_arg:
			generate_keys = (AutoKey(f'_add_{i}') for i in itertools.count())
			auto_key = next(k for k in generate_keys if k not in self.params)
			return self._add(auto_key, value)
		elif passed_kw:
			[(key, val)] = kwargs.items()
			return self._add(key, val)
		raise RuntimeError('Uh oh, csql bug. Please report.')

	def __contains__(self, key: str) -> bool:
		return self.params.__contains__(key)

	def __getitem__(self, key: Union[str, AutoKey]) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, _key_context=id(self))

	def __getattr__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, _key_context=id(self))
