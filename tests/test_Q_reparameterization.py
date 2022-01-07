from csql import Q, RenderedQuery, Parameters
from csql.dialect import SQLDialect, ParamStyle
import pytest

def test_parameters_reparameterization_qmark():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or def = {p['defkey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == ('ABC', 'def')


def test_parameters_reparameterization_numeric():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or def = {p['defkey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == ('ABC', 'def')


def test_parameters_reparameterization_reuse_qmark():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or abc = {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == ('ABC', 'ABC')


def test_parameters_reparameterization_reuse_numeric():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or abc = {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == ('ABC',)


def test_parameters_reparameterization_collection_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == ('A','B','C')


def test_parameters_reparameterization_collection_numeric():
	p = Parameters(
		abckey=['a','b','c']
	)
	q = Q(f"select 1 where abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == ('A','B','C')


def test_parameters_reparameterization_collection_resuse_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == ('A','B','C', 'A', 'B', 'C')



def test_parameters_reparameterization_collection_reuse_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == ('A','B','C')


def test_parameters_reparameterization_collection_new_length():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B']})

	assert built.sql == 'select 1 where abc in ( :1,:2 ) or abc in ( :1,:2 )'
	assert built.parameters == ('A', 'B')