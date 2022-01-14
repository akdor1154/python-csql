from csql import Q, RenderedQuery, Parameters
from csql.dialect import SQLDialect, DefaultDialect, ParamStyle
from textwrap import dedent
from pprint import pprint

def test_cte_params():
	p1 = Parameters(abc='abc')
	q1 = Q(f"select 1 where val = {p1['abc']}")
	q2 = Q(f"select 2 join {q1}")

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0'''
	).strip()
	assert r.parameters == ('abc',)
	assert r.parameter_names == ('abc',)


def test_cte_params_2():
	p1 = Parameters(abc='abc')
	q1 = Q(f"select 1 where val = {p1['abc']}")
	p2 = Parameters(abc='def')
	q2 = Q(f"select 2 join {q1} where val = {p2['abc']}")

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0 where val = :2'''
	).strip()
	assert r.parameters == ('abc', 'def')
	assert r.parameter_names == ('abc', 'abc')

def test_reused_params():
	p = Parameters(abc='abc', bcd='bcd')
	q1 = Q(f"select 1 where val = {p['abc']}")
	q2 = Q(f"select 2 join {q1} where val = {p['bcd']} or val = {p['abc']}")

	r = q2.build()

	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 where val = :1
		)
		select 2 join _subQuery0 where val = :2 or val = :1'''
	).strip()
	assert r.parameters == ('abc', 'bcd')
	assert r.parameter_names == ('abc', 'bcd')

def test_indenting():
	q1 = Q(f"""
		select
			1
		from dummy
	""")

	q2 = Q(f"""
		select
			sum(1)
		from {q1}
		where 1 = 1
	""")

	r = q2.build()

	assert r.sql == '''\
with
_subQuery0 as (
	select
		1
	from dummy
)
select
	sum(1)
from _subQuery0
where 1 = 1\
'''


def test_default_dialect():
	import dataclasses

	p = Parameters(abc='abc')
	q1 = Q(
		f"select 1 where val = {p['abc']}",
		dialect=dataclasses.replace(
			DefaultDialect, paramstyle=ParamStyle.qmark
		)
	)

	r = q1.build()

	assert r.sql == 'select 1 where val = ?'
	assert r.parameters == ('abc',)
	assert r.parameter_names == ('abc',)

def test_preview_pd():
	import sqlite3
	con = sqlite3.connect(':memory:')

	base = Q("select 1 from ( values (1, 2, 3 ) )")
	assert base.preview_pd(con) is not None