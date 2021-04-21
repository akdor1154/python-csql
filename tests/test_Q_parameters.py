from csql import Q, RenderedQuery, Parameters, ParameterList as PL
from csql.dialect import SQLDialect, ParamStyle
import pytest

def test_parameters():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=PL('abc')
	)

def test_parameters_list():
	p = Parameters(
		abc='abc',
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['abc']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1 or def in ( :2,:3,:4 )",
		parameters=PL('abc', 1, 2, 3)
	)

def test_parameters_reuse():
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = ( :1,:2,:3 ) or def in ( :1,:2,:3 )",
		parameters=PL(1, 2, 3)
	)

def test_parameters_getattr():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p.abc}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=PL('abc')
	)

def test_parameters_dialect_dollar_numeric():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric_dollar)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = $1",
		parameters=PL('abc')
	)

def test_parameters_dialect_qmark():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ?",
		parameters=PL('abc')
	)


def test_parameters_dialect_qmark_reuse():
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ( ?,?,? ) or def in ( ?,?,? )",
		parameters=PL(1, 2, 3, 1, 2, 3)
	)


def test_parameters_deprecation():
	with pytest.warns(DeprecationWarning):
		q = Q(lambda: "select 1", Parameters())
