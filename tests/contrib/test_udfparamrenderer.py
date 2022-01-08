from csql import Q, Query, RenderedQuery, Parameters, Overrides
from csql.contrib.render.param import UDFParameterRenderer

def test_contrib_param_render_udf() -> None:

	p = Parameters(
		abc='abcval'
	)
	q = Q(f"select 1 where abc = {p['abc']}", overrides=Overrides(paramRenderer=UDFParameterRenderer))

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = abc",
		parameters=('abcval',)
	)