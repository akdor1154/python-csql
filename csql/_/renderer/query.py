from __future__ import annotations
from typing import *
from textwrap import dedent, indent
import abc

from ..utils import Collector
from ..models.query import Query, ParameterPlaceholder, RenderedQuery, ParameterList
from ..models.dialect import SQLDialect, ParamStyle
from .parameters import ParameterRenderer, ColonNumeric, DollarNumeric

if TYPE_CHECKING:
	import csql
	import csql.render.param

SQLBit = NewType('SQLBit', str)

DepNames = Dict[int, str] # dict of id(query) to query name

class QueryRenderer(abc.ABC):
	ParamRenderer: Type[csql.render.param.ParameterRenderer]

	# mutable, replaced every render()
	paramRenderer: ParameterRenderer

	def __init__(self, ParamRenderer: Type[csql.render.param.ParameterRenderer], dialect: SQLDialect):
		# param renderer is stateful and should only be used once.
		# todo: refactor .render into a closure() or something.
		self.ParamRenderer = ParamRenderer

	def render(self, query: Query) -> RenderedQuery:

		# this guy is only good for a single use...
		self.paramRenderer = self.ParamRenderer()
		return self._render(query)

	@abc.abstractmethod
	def _render(self, query: Query) -> RenderedQuery:
		pass


class BoringSQLRenderer(QueryRenderer):
	"""Render a Query. Referenced other Queries are all assembled with this one into a CTE/with expression."""

	def __renderSingleQuery(self, query: Query, depNames: DepNames) -> Generator[SQLBit, None, None]:
		for part in query.queryParts:
			if isinstance(part, str):
				yield SQLBit(part)
			elif isinstance(part, Query):
				#isinstance(part, Query)
				depName = depNames[id(part)]
				yield SQLBit(depName)
			elif isinstance(part, ParameterPlaceholder):

				sql = self.paramRenderer.render(part)

				yield SQLBit(sql)

	class RenderedSingleQuery(NamedTuple):
		sql: str
		paramValues: List[Any]

	def _renderSingleQuery(self, query: Query, depNames: DepNames) -> SQLBit:
		queryBits = self.__renderSingleQuery(query, depNames)

		return SQLBit(
			"".join(queryBits)
		)

	def _render(self, query: csql.Query) -> csql.RenderedQuery:
		"""Renders a query and all its dependencies into a CTE expression."""

		cteParts = []
		depNames = {}
		i = 0
		for dep in query._getDeps():
			subName = f"_subQuery{i}"
			i += 1
			depNames[id(dep)] = subName
			cteParts.append((subName, dep))

		tab = '\t'
		depSqls: List[SQLBit] = []
		for (depName, dep) in cteParts:
			renderedDep = self._renderSingleQuery(dep, depNames)
			dedented = dedent(renderedDep).strip()
			depSql = SQLBit(
f'''\
{depName} as (
{indent(dedented, tab)}
)'''
)
			depSqls.append(depSql)

		cteString = "with\n" + ",\n".join(depSqls)

		renderedSelf = self._renderSingleQuery(query, depNames)

		fullSql = (
			f"{cteString}\n{dedent(renderedSelf).strip()}"
			if len(cteParts) >= 1
			else renderedSelf
		)

		paramValues, paramNames = self.paramRenderer.renderList()

		return RenderedQuery(
			sql=fullSql,
			parameters=paramValues,
			parameter_names=paramNames
		)
