from typing import *
from textwrap import dedent, indent
from abc import ABCMeta

from ..utils import Collector
from ..models.query import Query, ParameterPlaceholder, RenderedQuery
from ..models.dialect import SQLDialect, ParamStyle
from .parameters import ParameterRenderer, ColonNumeric, DollarNumeric

__all__ = ['RendererdQuery', 'BoringSQLRenderer']


class QueryPartStr(NamedTuple):
	str: str
class QueryPartParam(NamedTuple):
	value: Any
QueryPart = Union[QueryPartStr, QueryPartParam]

DepNames = Dict[int, str] # dict of id(query) to query name

class BoringSQLRenderer:
	"""Render a Query. I'm crossing my fingers that I never have to handle sql dialects, but if they I do, they will be subclasses of this."""

	dialect: SQLDialect
	paramRenderer: ParameterRenderer
	# "pState" => state for the paramRenderer. atm this is always just an int to track which numeric param we are up to.
	def __init__(self, dialect: SQLDialect):
		self.dialect = dialect
		self.paramRenderer = ParameterRenderer.get(dialect)()

	def __renderSingleQuery(self, query: Query, depNames: DepNames) -> Generator[QueryPart, None, None]:
		for part in query.queryParts:
			if isinstance(part, str):
				yield QueryPartStr(
					part
				)
			elif isinstance(part, Query):
				#isinstance(part, Query)
				depName = depNames[id(part)]
				yield QueryPartStr(
					depName
				)
			elif isinstance(part, ParameterPlaceholder):
				# TODO
				paramKey = part.key

				sql, values = self.paramRenderer.render(paramKey, query.parameters)

				yield QueryPartStr(sql)
				yield from (QueryPartParam(value) for value in values)

	class RenderedSingleQuery(NamedTuple):
		sql: str
		paramValues: List[Any]

	def _renderSingleQuery(self, query: Query, depNames: DepNames) -> RenderedSingleQuery:
		queryBits = Collector(self.__renderSingleQuery(query, depNames))
		strBits: List[str] = []
		params: List[Any] = []
		for bit in queryBits:
			if isinstance(bit, QueryPartStr):
				strBits.append(bit.str)
			elif isinstance(bit, QueryPartParam):
				params.append(bit.value)

		return self.RenderedSingleQuery(
			sql="".join(strBits),
			paramValues=params
		)

	def render(self, query: Query) -> RenderedQuery:
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
		depSqls: List[str] = []
		paramValues: List[Any] = []
		for (depName, dep) in cteParts:
			renderedDep = self._renderSingleQuery(dep, depNames)
			dedented = dedent(renderedDep.sql).strip()
			depSql = (
f'''\
{depName} as (
{indent(dedented, tab)}
)'''
)
			depSqls.append(depSql)
			paramValues.extend(renderedDep.paramValues)

		cteString = "with\n" + ",\n".join(depSqls)

		renderedSelf = self._renderSingleQuery(query, depNames)
		paramValues.extend(renderedSelf.paramValues)

		fullSql = (
			f"{cteString}\n{dedent(renderedSelf.sql).strip()}"
			if len(cteParts) >= 1
			else renderedSelf.sql
		)

		return RenderedQuery(
			sql=fullSql,
			parameters=paramValues
		)
