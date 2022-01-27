from csql import Q, RenderedQuery, Parameters
from csql.dialect import SQLDialect, DefaultDialect, ParamStyle
from textwrap import dedent
from pprint import pprint
import pytest

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

def test_dialect_propagation():
	import dataclasses
	p = Parameters(abc='abc', defg='defg')
	q1 = Q(
		f"select 1 where val = {p['abc']}",
		dialect=dataclasses.replace(DefaultDialect, paramstyle=ParamStyle.qmark)
	)

	q2 = Q(
		f"select count(*) from {q1} where val = {p['defg']}"
	)

	r = q2.build()

	assert r == RenderedQuery(
		sql='''\
with
_subQuery0 as (
	select 1 where val = ?
)
select count(*) from _subQuery0 where val = ?''',
		parameters=('abc', 'defg'),
		parameter_names=('abc', 'defg')
	)


def test_dialect_propagation_equivalence():
	import dataclasses
	p = Parameters(abc='abc', defg='defg')
	dialect1 = dataclasses.replace(DefaultDialect, paramstyle=ParamStyle.qmark)
	dialect2 = dataclasses.replace(DefaultDialect, paramstyle=ParamStyle.qmark)
	assert id(dialect1) != id(dialect2)
	q1 = Q(
		f"select 1 where val = {p['abc']}",
		dialect=dialect1
	)

	q2 = Q(
		f"select 2 where val = {p['defg']}",
		dialect=dialect2
	)

	q3 = Q(f'select * from {q1} join {q2}')

	r = q3.build()

	assert r == RenderedQuery(
		sql='''\
with
_subQuery0 as (
	select 1 where val = ?
),
_subQuery1 as (
	select 2 where val = ?
)
select * from _subQuery0 join _subQuery1''',
		parameters=('abc', 'defg'),
		parameter_names=('abc', 'defg')
	)


def test_dialect_propagation_error_on_ambiguity():
	import dataclasses
	p = Parameters(abc='abc', defg='defg')
	dialect1 = dataclasses.replace(DefaultDialect, paramstyle=ParamStyle.qmark)
	dialect2 = dataclasses.replace(DefaultDialect, paramstyle=ParamStyle.numeric)
	assert id(dialect1) != id(dialect2)
	q1 = Q(
		f"select 1 where val = {p['abc']}",
		dialect=dialect1
	)

	q2 = Q(
		f"select 2 where val = {p['defg']}",
		dialect=dialect2
	)

	with pytest.raises(Exception, match='.*Found multiple dialects.*'):
		q3 = Q(f'select * from {q1} join {q2}')


def test_overrides_propagation():
	import dataclasses
	import csql.overrides
	import csql.render.query
	class MySQLRenderer(csql.render.query.BoringSQLRenderer):
		def _render(self, query: csql.Query) -> RenderedQuery:
			rq = super()._render(query)
			return rq._replace(sql='-- yo yo --\n'+rq.sql)

	o = csql.overrides.Overrides(queryRenderer=MySQLRenderer)

	q1 = Q(
		f"select 1",
		overrides=o
	)

	q2 = Q(
		f"select count(*) from {q1}",
	)

	assert q2.build() == RenderedQuery(
		sql='''\
-- yo yo --
with
_subQuery0 as (
	select 1
)
select count(*) from _subQuery0''',
		parameters=(),
		parameter_names=()
	)