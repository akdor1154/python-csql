from csql import Q, Query, Parameters
from csql._.models.query import ParameterList, _replace_stuff
from textwrap import dedent

from csql._.cacher import TempTableCacher
from unittest.mock import Mock, MagicMock
import re
import sqlite3

def test_persist_simple():

	with sqlite3.connect(':memory:') as con:

		c = TempTableCacher(con)

		q1 = Q(f'''
			with t(a,b,c) as (
				values (1, 2, 3), (1, 2, 3)
			)
			select * from t
			''').persist(c)

		q1_built = q1.build() # should execute q1
		assert 'select * from "csql_cache' in q1_built.sql
		assert 'a, b, c' not in q1_built.sql

def test_persist_params():
	from csql._.cacher import TempTableCacher

	con = Mock()
	c = TempTableCacher(con)

	p = Parameters(v=1)
	q1 = Q(f'''select v where v = {p['v']}''').persist(c)

	q1r = q1.build()

	assert re.match(r'select \* from "csql_cache_.+"', q1r.sql)
	assert q1r.parameters == ParameterList()


def test_persist_reparameterize():
	from csql._.cacher import TempTableCacher

	with sqlite3.connect(':memory:') as con:

		c = TempTableCacher(con)
		p = Parameters(val=123)

		q1 = Q(f''' select {p['val']} as val ''').persist(c)
		q2 = Q(f''' select val*2 as v2 from {q1} ''')
		
		res2 = con.execute(*q2.db()).fetchall()
		assert res2 == [(246,)]

		res2_reparam = con.execute(
			*q2.db(newParams=dict(val=100))
		).fetchall()
		assert res2_reparam == [(200,)]


	con = Mock()
	c = TempTableCacher(con)

	p = Parameters(v=1)
	q1 = Q(f'''select v where v = {p['v']}''').persist(c)

	q1r = q1.build()

	assert re.match(r'select \* from "csql_cache_.+"', q1r.sql)
	assert q1r.parameters == ParameterList()
