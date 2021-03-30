from csql import Q, RenderedQuery, Parameters

p = Parameters(
	abc='abc',
	list=[1, 2, 3]
)
q = Q(f"select 1 where abc = {p['abc']} or def in {p['list']}", p)


def test_render_pd():
	assert q.pd() == {
		'sql':"select 1 where abc = :1 or def in ( :2,:3,:4 )",
		'params':['abc', 1, 2, 3]
	}

def test_render_db():
	assert q.db() == (
		"select 1 where abc = :1 or def in ( :2,:3,:4 )",
		['abc', 1, 2, 3]
	)