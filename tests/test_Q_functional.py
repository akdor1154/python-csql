from csql import Q, RenderedQuery, Parameters
from textwrap import dedent
from pprint import pprint

def test_cte_params():
	p1 = Parameters(abc='abc')
	q1 = Q(f"select 1 where val = {p1['abc']}", p1)
	q2 = Q(f"select 2 join {q1}")

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0'''
	).strip()
	assert r.parameters == ['abc']


def test_cte_params_2():
	p1 = Parameters(abc='abc')
	q1 = Q(f"select 1 where val = {p1['abc']}", p1)
	p2 = Parameters(abc='def')
	q2 = Q(f"select 2 join {q1} where val = {p2['abc']}", p2)

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0 where val = :2'''
	).strip()
	assert r.parameters == ['abc', 'def']


def test_reused_params():
	p = Parameters(abc='abc', bcd='bcd')
	q1 = Q(f"select 1 where val = {p['abc']}", p)
	q2 = Q(f"select 2 join {q1} where val = {p['bcd']} or val = {p['abc']}", p)

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0 where val = :2 or val = :1'''
	).strip()
	assert r.parameters == ['abc', 'bcd']
