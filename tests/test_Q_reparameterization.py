from csql import Q, RenderedQuery, Parameters, ParameterList as PL
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

	assert built.parameters == PL('ABC', 'def')


def test_parameters_reparameterization_numeric():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or def = {p['defkey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == PL('ABC', 'def')


def test_parameters_reparameterization_reuse_qmark():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or abc = {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == PL('ABC', 'ABC')


def test_parameters_reparameterization_reuse_numeric():
	p = Parameters(
		abckey='abc',
		defkey='def'
	)
	q = Q(f"select 1 where abc = {p['abckey']} or abc = {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': 'ABC'})

	assert built.parameters == PL('ABC')


def test_parameters_reparameterization_collection_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == PL('A','B','C')


def test_parameters_reparameterization_collection_numeric():
	p = Parameters(
		abckey=['a','b','c']
	)
	q = Q(f"select 1 where abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == PL('A','B','C')


def test_parameters_reparameterization_collection_resuse_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.qmark)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == PL('A','B','C', 'A', 'B', 'C')



def test_parameters_reparameterization_collection_reuse_qmark():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	built = q.build(dialect=dialect, newParams={'abckey': ['A','B','C']})

	assert built.parameters == PL('A','B','C')


def test_parameters_reparameterization_collection_bad_length():
	p = Parameters(
		abckey=['a','b','c'],
	)
	q = Q(f"select 1 where abc in {p['abckey']} or abc in {p['abckey']}")
	dialect = SQLDialect(paramstyle=ParamStyle.numeric)

	with pytest.raises(ValueError) as e:
		built = q.build(dialect=dialect, newParams={'abckey': ['A','B']})
	assert "You attempted to replace 'abckey' = ['a', 'b', 'c'] (length 3)" in str(e.value)
	assert "with ['A', 'B'] (length 2)" in str(e.value)