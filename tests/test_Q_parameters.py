from csql import Q, RenderedQuery, Parameters
from csql.dialect import SQLDialect, ParamStyle

def test_parameters():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=['abc']
	)

def test_parameters_list():
	p = Parameters(
		abc='abc',
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['abc']} or def in {p['list']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1 or def in ( :2,:3,:4 )",
		parameters=['abc', 1, 2, 3]
	)

def test_parameters_reuse():
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = ( :1,:2,:3 ) or def in ( :1,:2,:3 )",
		parameters=[1, 2, 3]
	)

def test_parameters_getattr():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p.abc}", p)

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=['abc']
	)

def test_parameters_dialect_dollar_numeric():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}", p)
	dialect = SQLDialect(paramstyle=ParamStyle.numeric_dollar)
	assert q.build(dialect) == RenderedQuery(
		sql="select 1 where abc = $1",
		parameters=['abc']
	)