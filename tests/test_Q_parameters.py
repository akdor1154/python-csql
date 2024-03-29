from csql import Q, RenderedQuery, Parameters
from csql.dialect import SQLDialect, ParamStyle
import pytest

def test_parameters():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=('abc',),
		parameter_names=('abc',)
	)

def test_parameters_list():
	p = Parameters(
		abc='abc',
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['abc']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1 or def in ( :2,:3,:4 )",
		parameters=('abc', 1, 2, 3),
		parameter_names=('abc', None, None, None)
	)

def test_parameters_reuse():
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = ( :1,:2,:3 ) or def in ( :1,:2,:3 )",
		parameters=(1, 2, 3),
		parameter_names=(None, None, None)
	)

def test_parameters_getattr():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p.abc}")

	assert q.build() == RenderedQuery(
		sql="select 1 where abc = :1",
		parameters=('abc',),
		parameter_names=('abc',)
	)

def test_parameters_dialect_dollar_numeric():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric_dollar)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = $1",
		parameters=('abc',),
		parameter_names=('abc',)
	)

def test_parameters_dialect_qmark():
	p = Parameters(
		abc='abc'
	)
	q = Q(f"select 1 where abc = {p['abc']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ?",
		parameters=('abc',),
		parameter_names=('abc',)
	)


def test_parameters_dialect_qmark_reuse():
	p = Parameters(
		list=[1, 2, 3]
	)
	q = Q(f"select 1 where abc = {p['list']} or def in {p['list']}")

	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql="select 1 where abc = ( ?,?,? ) or def in ( ?,?,? )",
		parameters=(1, 2, 3, 1, 2, 3),
		parameter_names=(None, None, None, None, None, None)
	)


def test_parameters_add_simple():
	p = Parameters()

	q = Q(f"select {p.add(1)}, {p.add(2)}")

	assert q.build() == RenderedQuery(
		sql = "select :1, :2",
		parameters=(1, 2),
		parameter_names=(None, None)
	)

def test_parameters_add_to_existing():
	p = Parameters(existing='abc')

	q = Q(f"select {p.add(1)}, {p.add(2)} where abc = {p['existing']}")

	assert q.build() == RenderedQuery(
		sql = "select :1, :2 where abc = :3",
		parameters=(1, 2, 'abc'),
		parameter_names=(None, None, 'existing')
	)

def test_parameters_add_to_existing_qmark():
	p = Parameters(existing='abc')

	q = Q(f"select {p.add(1)}, {p.add(2)} where abc = {p['existing']}")

	dialect = SQLDialect(paramstyle=ParamStyle.qmark)
	assert q.build(dialect=dialect) == RenderedQuery(
		sql = "select ?, ? where abc = ?",
		parameters=(1, 2, 'abc'),
		parameter_names=(None, None, 'existing')
	)

def test_parameters_add_key():
	p = Parameters(existing='abc')

	q = Q(f"select {p.add(one=1)}, {p.add(two=2)} where abc = {p['existing']}")

	assert q.build() == RenderedQuery(
		sql = "select :1, :2 where abc = :3",
		parameters=(1, 2, 'abc'),
		parameter_names=('one', 'two', 'existing')
	)

	assert q.build(newParams={'one': 'one'}) == RenderedQuery(
		sql = "select :1, :2 where abc = :3",
		parameters=('one', 2, 'abc'),
		parameter_names=('one', 'two', 'existing')
	)



def test_parameters_add_nothing():
	p = Parameters(existing='abc')

	with pytest.raises(ValueError):
		p.add()

def test_parameters_add_arg_and_kw():
	p = Parameters(existing='abc')

	with pytest.raises(ValueError):
		p.add(1, kw='hi')


def test_parameters_add_multiple_kw():
	p = Parameters(existing='abc')

	with pytest.raises(ValueError):
		p.add(kw1='hi', kw2='hi')
