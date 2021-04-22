from typing import *
from dataclasses import dataclass
from abc import ABCMeta
from ..utils import unique
from textwrap import dedent
from ..input.strparsing import InstanceTracking
from weakref import WeakValueDictionary
from .dialect import SQLDialect
from collections.abc import Collection as CollectionABC

if TYPE_CHECKING:
	import pandas as pd
	from .overrides import Overrides

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


@dataclass
class Query(QueryBit, InstanceTracking):

	queryParts: List[Union[str, QueryBit]]
	default_dialect: SQLDialect
	default_overrides: Optional['Overrides']

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	def build(
		self, *,
		dialect: Optional[SQLDialect] = None,
		newParams: Optional[Dict[str, ScalarParameterValue]] = None,
		overrides: Optional['Overrides'] = None
	) -> RenderedQuery:
		dialect = dialect or self.default_dialect
		from ..renderer.query import BoringSQLRenderer, QueryRenderer
		from ..renderer.parameters import ParameterRenderer
		from .overrides import Overrides
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
		rendered = queryRenderer.render(self)

		return RenderedQuery(
			sql=rendered.sql,
			parameters=rendered.parameters.reparameterize(**(newParams or {}))
		)

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


@dataclass
class ParameterPlaceholder(QueryBit, InstanceTracking):
	key: str
	value: Any
	parameters: 'Parameters'


class Parameters:
	params: Dict[str, Any]

	def __init__(self, **kwargs: Any):
		self.params = kwargs

	def __getitem__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, parameters=self)

	def __getattr__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key, value=paramVal, parameters=self)
