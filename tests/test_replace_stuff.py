from csql import Q, Query
from csql._.models.query import ParameterPlaceholder, Parameters, QueryBit
from csql._.models.query_replacers import replace_queries_in_tree
from textwrap import dedent


def test_replace_identity():

	q1 = Q(f'select 1 from root')
	q2 = Q(f'select count(*) from {q1}')

	q2_built = q2.build()

	q2_2 = replace_queries_in_tree(lambda q: q, q2)
	
	assert q2_2 == q2
	assert q2_2 is q2

	q2_2_built = q2_2.build
	assert q2_2.build() == q2_built


def test_replace_simple():

	q1 = Q(f'select 1 from root')
	q2 = Q(f'select count(*) from {q1} as q1')
	q3 = Q(f'select * from {q2} q2 join {q1} q1')

	q2_built = q3.build()

	i = 0

	def replacer(q: Query) -> Query:
		nonlocal i
		i = i + 1
		return Query(
			queryParts=q.queryParts + (f'\n -- replaced {i}\n',),
			default_dialect=q.default_dialect,
			default_overrides=q.default_overrides,
			_extensions=q._extensions
		)

	replaced = replace_queries_in_tree(replacer, q3)
	r = replaced.build()
	
	assert r.sql == dedent('''
		with
		_subQuery0 as (
			select 1 from root
			 -- replaced 1
		),
		_subQuery1 as (
			select count(*) from _subQuery0 as q1
			 -- replaced 2
		)
		select * from _subQuery1 q2 join _subQuery0 q1
		 -- replaced 3
	''').strip()

def test_replace_modify_params():
	# todo:
	# test replacing all params with str injection works.
	from csql._.models.query_replacers import _replace_query_parts
	def replacer(q: Query) -> Query:
		def replace_params(p):
			if isinstance(p, ParameterPlaceholder):
				return f"'ZAP'"
			else:
				return p
		return _replace_query_parts(replace_params, q)
	
	p = Parameters(v=1)
	q1 = Q(f'select 1 from root where v = {p["v"]}')

	q1_replaced = replace_queries_in_tree(replacer, q1)

	q1r = q1.build()
	assert q1r.sql == 'select 1 from root where v = :1'
	assert q1r.parameters == (1,)

	q1rr = q1_replaced.build()
	assert q1rr.sql == "select 1 from root where v = 'ZAP'"
	assert q1rr.parameters == ()
