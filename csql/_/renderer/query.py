from typing import *
from textwrap import dedent, indent
from abc import ABCMeta

from ..utils import Collector
from ..models.query import Query, ParameterPlaceholder, RenderedQuery, ParameterList
from ..models.dialect import SQLDialect, ParamStyle
from .parameters import ParameterRenderer, ColonNumeric, DollarNumeric

__all__ = ['RendererdQuery', 'BoringSQLRenderer']

SQLBit = NewType('SQLBit', str)

DepNames = Dict[int, str] # dict of id(query) to query name

class BoringSQLRenderer:
	"""Render a Query. I'm crossing my fingers that I never have to handle sql dialects, but if they I do, they will be subclasses of this."""

	dialect: SQLDialect
	paramRenderer: ParameterRenderer
	# "pState" => state for the paramRenderer. atm this is always just an int to track which numeric param we are up to.
	def __init__(self, dialect: SQLDialect):
		self.dialect = dialect
		self.paramRenderer = ParameterRenderer.get(dialect)()

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

		return RenderedQuery(
			sql=fullSql,
			parameters=self.paramRenderer.renderedParams.render()
		)
