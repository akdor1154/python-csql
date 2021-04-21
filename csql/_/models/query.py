from typing import *
from dataclasses import dataclass
from abc import ABCMeta
from ..utils import unique
from textwrap import dedent
from ..input.strparsing import InstanceTracking
from weakref import WeakValueDictionary
from .dialect import SQLDialect

if TYPE_CHECKING:
	import pandas as pd

import sys
if sys.version_info >= (3, 9):
	import collections.abc
	Sequence = collections.abc.Sequence
else:
	# imported from typing *
	pass

ScalarParameterValue = Any

class ParameterList(Sequence[ScalarParameterValue]):
	"""This is designed to be returned and passed directly to your DB API. It acts like a list."""

	_params: List[ScalarParameterValue]

	def __getitem__(self, i: Any) -> ScalarParameterValue:
		return self._params[i]

	def __iter__(self) -> Iterator[ScalarParameterValue]:
		return iter(self._params)

	def __len__(self) -> int:
		return len(self._params)

	def __init__(self, *params: ScalarParameterValue) -> None:
		self._params = list(params)

	def __repr__(self) -> str:
		return f'Params {repr(self._params)}'

	def __eq__(self, other: Any) -> bool:
		if isinstance(other, ParameterList):
			return self._params == other._params
		elif isinstance(other, list): # mainly used so I didn't have to rewrite a bunch of tests.. this may be removed.
			return self._params == other
		else:
			return False

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
	parameters: "Parameters"
	default_dialect: SQLDialect

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	def build(self, dialect: Optional[SQLDialect] = None) -> RenderedQuery:
		dialect = dialect or self.default_dialect
		from ..renderer.query import BoringSQLRenderer
		return BoringSQLRenderer(dialect).render(self)

	def preview_pd(self, con: Any, rows: int=10) -> "pd.DataFrame":
		import pandas as pd
		from csql import Q
		p = Parameters(rows=rows)
		previewQ = Q(lambda: f"""select * from {self} limit {p['rows']}""", p)
		return pd.read_sql(**previewQ.pd(), con=con)

	def pd(self) -> Dict[str, Any]:
		return self.build().pd

	def db(self) -> Tuple[str, ParameterList]:
		return self.build().db


@dataclass
class ParameterPlaceholder(QueryBit, InstanceTracking):
	key: str



class Parameters:
	params: Dict[str, Any]

	def __init__(self, **kwargs: Any):
		self.params = kwargs

	def __getitem__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key)

	def __getattr__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key)
