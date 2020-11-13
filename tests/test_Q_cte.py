from csql import Q, RenderedQuery, Parameters
from textwrap import dedent
from pprint import pprint


def test_basic_cte():
	q1 = Q(f"select 1")
	q2 = Q(f"select 2 join {q1}")

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1
		)
		select 2 join _subQuery0'''
	).strip()
	assert r.parameters == []

def test_multiple_cte():
	q1 = Q(f"select 1")
	q2 = Q(f"select 2 join {q1}")
	q3 = Q(f"select 3 join {q2}")

	r = q3.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1
		),
		_subQuery1 as (
			select 2 join _subQuery0
		)
		select 3 join _subQuery1'''
	).strip()
	assert r.parameters == []

def test_nonlinear_cte():
	q1 = Q(f"select 1")
	q2 = Q(f"select 2 join {q1}")
	q3 = Q(f"select 3 join {q1}")
	q4 = Q(f"select 4 join {q2} join {q3}")

	r = q4.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1
		),
		_subQuery1 as (
			select 2 join _subQuery0
		),
		_subQuery2 as (
			select 3 join _subQuery0
		)
		select 4 join _subQuery1 join _subQuery2'''
	).strip()
	assert r.parameters == []

def test_multi_root_cte():
	q1 = Q(f"select 1")
	q2 = Q(f"select 2 join {q1}")
	q3 = Q(f"select 3")
	q4 = Q(f"select 4 join {q2} join {q3}")

	r = q4.build()
	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1
		),
		_subQuery1 as (
			select 2 join _subQuery0
		),
		_subQuery2 as (
			select 3
		)
		select 4 join _subQuery1 join _subQuery2'''
	).strip()
	assert r.parameters == []