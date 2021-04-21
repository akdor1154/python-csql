from csql import Q, Query, RenderedQuery, Parameters, ParameterList as PL, SQLRenderer, ParameterRenderer, Overrides
from csql.dialect import SQLDialect, ParamStyle
import pytest

def test_renderer_override():
	class MySQLRenderer(SQLRenderer):
		def render(self, query: Query) -> RenderedQuery:
			return RenderedQuery(
				sql='hello hello',
				parameters=self.paramRenderer.renderList()
			)

	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}", overrides=Overrides(queryRenderer=MySQLRenderer))

	assert q.build() == RenderedQuery(
		sql="hello hello",
		parameters=PL()
	)