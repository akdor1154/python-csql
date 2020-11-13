from csql import RenderedQuery, Parameters

def test_parameters(Q):
	p = Parameters(
		abc='abc'
	)
	q = Q(lambda: f"select 1 where abc = {p['abc']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=['abc']
	)

def test_parameters_list(Q):
	p = Parameters(
		abc='abc',
		list=[1, 2, 3]
	)
	q = Q(lambda: f"select 1 where abc = {p['abc']} or def in {p['list']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1 or def in ( :2,:3,:4 )",
		parameters=['abc', 1, 2, 3]
	)

def test_parameters_reuse(Q):
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(lambda: f"select 1 where abc = {p['list']} or def in {p['list']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = ( :1,:2,:3 ) or def in ( :1,:2,:3 )",
		parameters=[1, 2, 3]
	)

def test_parameters_getattr(Q):
	p = Parameters(
		abc='abc'
	)
	q = Q(lambda: f"select 1 where abc = {p.abc}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=['abc']
	)
