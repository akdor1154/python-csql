from csql import Q, Query, Parameters
from csql._.models.query import ParameterList, _replace_stuff
from textwrap import dedent

from csql._.cacher import TempTableCacher
from unittest.mock import Mock, MagicMock
import re
import sqlite3
from typing import *

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

def test_persist_tag():

	with sqlite3.connect(':memory:') as con:

		c = TempTableCacher(con)

		q1 = Q(f'''
			with t(a,b,c) as (
				values (1, 2, 3), (1, 2, 3)
			)
			select * from t
			''').persist(c, 'q1')

		q1_built = q1.build() # should execute q1
		assert 'select * from "csql_cache_q1' in q1_built.sql
		assert 'a, b, c' not in q1_built.sql


def test_persist_chained():


	with sqlite3.connect(':memory:') as con:
		from csql import RenderedQuery

		hooked_saves = {}

		class HookedTempTableCacher(TempTableCacher):
			async def _persist(self, rq: RenderedQuery, key: int, tag: Optional[str]) -> Query:
				hooked_saves[tag] = rq
				return await super()._persist(rq, key, tag)
		c = HookedTempTableCacher(con)

		q1 = Q(f"select 'q1' as val").persist(c, 'q1')
		q2 = Q(f"select val || 'q2' as val from {q1}").persist(c, 'q2')
		q3 = Q(f"select val || 'q3' as val from {q2}").persist(c, 'q3')


		q3_built = q3.build() # should execute q1

		assert 'select * from "csql_cache_q3' in q3_built.sql
		assert 'q1' not in q3_built.sql

		from pprint import pprint
		pprint(hooked_saves)

		assert 'q1' not in hooked_saves['q3'].sql