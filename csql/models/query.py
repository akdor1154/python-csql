from typing import *
from dataclasses import dataclass
from abc import ABCMeta
from ..utils import unique
from textwrap import dedent
from ..input.strparsing import InstanceTracking
from weakref import WeakValueDictionary

if TYPE_CHECKING:
	import pandas as pd

class RenderedQuery(NamedTuple):
	sql: str
	parameters: List[Any]

	# utility properties for easy splatting
	@property
	def pd(self) -> Dict[str, Any]:
		return dict(
			sql=self.sql,
			params=self.parameters
		)

	@property
	def db(self) -> Tuple[str, List[Any]]:
		return (self.sql, self.parameters)

class QueryBit(metaclass=ABCMeta):
	pass


@dataclass
class Query(QueryBit, InstanceTracking):

	queryParts: List[Union[str, QueryBit]]
	parameters: "Parameters"

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	def build(self) -> RenderedQuery:
		from ..renderer.query import BoringSQLRenderer
		return BoringSQLRenderer.render(self)

	def preview_pd(self, con: Any, rows: int=10) -> "pd.DataFrame":
		import pandas as pd
		from csql import Q
		p = Parameters(rows=rows)
		previewQ = Q(lambda: f"""select * from {self} limit {p['rows']}""", p)
		return pd.read_sql(**previewQ.pd(), con=con)

	def pd(self) -> Dict[str, Any]:
		return self.build().pd

	def db(self) -> Tuple[str, List[Any]]:
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
