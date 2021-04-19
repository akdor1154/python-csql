from typing import *
from textwrap import dedent, indent
from abc import ABCMeta

from ..utils import Collector
from ..models.query import Query, ParameterPlaceholder, RenderedQuery
from ..models.dialect import SQLDialect, ParamStyle
from .parameters import NumericParameterRenderer, RendererState, ColonNumeric, DollarNumeric

__all__ = ['RendererdQuery', 'BoringSQLRenderer']


class QueryPartStr(NamedTuple):
	str: str
class QueryPartParam(NamedTuple):
	value: Any
QueryPart = Union[QueryPartStr, QueryPartParam]

DepNames = Dict[int, str] # dict of id(query) to query name

PState = RendererState

class BoringSQLRenderer:
	"""Render a Query. I'm crossing my fingers that I never have to handle sql dialects, but if they I do, they will be subclasses of this."""

	dialect: SQLDialect
	paramRenderer = NumericParameterRenderer
	# "pState" => state for the paramRenderer. atm this is always just an int to track which numeric param we are up to.
	def __init__(self, dialect: SQLDialect):
		self.dialect = dialect
		if self.dialect.paramstyle == ParamStyle.numeric:
			self.paramRenderer = ColonNumeric
		elif self.dialect.paramstyle == ParamStyle.numeric_dollar:
			self.paramRenderer = DollarNumeric

	def __renderSingleQuery(self, query: Query, depNames: DepNames, pState: PState) -> Generator[QueryPart, None, PState]:
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

				((sql, values), newPState) = self.paramRenderer.render(paramKey, query.parameters, pState)
				pState = newPState

				yield QueryPartStr(sql)
				yield from (QueryPartParam(value) for value in values)
		return pState

	class RenderedSingleQuery(NamedTuple):
		sql: str
		paramValues: List[Any]
		nextPState: PState

	def _renderSingleQuery(self, query: Query, depNames: DepNames, pState: PState) -> RenderedSingleQuery:
		queryBits = Collector(self.__renderSingleQuery(query, depNames, pState))
		strBits: List[str] = []
		params: List[Any] = []
		for bit in queryBits:
			if isinstance(bit, QueryPartStr):
				strBits.append(bit.str)
			elif isinstance(bit, QueryPartParam):
				params.append(bit.value)

		return Self.RenderedSingleQuery(
			sql="".join(strBits),
			paramValues=params,
			nextPState=queryBits.returned
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
		pState = self.paramRenderer.initialState()
		depSqls: List[str] = []
		paramValues: List[Any] = []
		for (depName, dep) in cteParts:
			renderedDep = Self._renderSingleQuery(dep, depNames, pState)
			dedented = dedent(renderedDep.sql).strip()
			depSql = (
f'''\
{depName} as (
{indent(dedented, tab)}
)'''
)
			depSqls.append(depSql)
			paramValues.extend(renderedDep.paramValues)
			pState = renderedDep.nextPState

		cteString = "with\n" + ",\n".join(depSqls)

		renderedSelf = self._renderSingleQuery(query, depNames, pState)
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
