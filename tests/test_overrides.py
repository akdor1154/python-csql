from csql import Q, Query, RenderedQuery, Parameters
from csql.overrides import Overrides
from csql.render.param import ParameterRenderer
from csql.render.query import QueryRenderer

def test_renderer_override():
	class MySQLRenderer(QueryRenderer):
		def _render(self, query: Query) -> RenderedQuery:
			values, names = self.paramRenderer.renderList()
			return RenderedQuery(
				sql='hello hello',
				parameters=values,
				parameter_names=names
			)

	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}", overrides=Overrides(queryRenderer=MySQLRenderer))

	assert q.build() == RenderedQuery(
		sql="hello hello",
		parameters=(),
		parameter_names=(),
	)