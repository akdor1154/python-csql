
# csql - Composeable SQL

<!-- (intro)= -->

**csql** is a Python library to help you write more manageable SQL queries. You can write your queries as small, self-contained chunks, preview the results without pulling a whole result-set down from your database, then refer to them in future queries.

There are also useful features for handling database parameters properly.

The intended use-case is for data analysis and exploration.

[![PyPI version](https://badge.fury.io/py/csql.svg)](https://pypi.org/project/csql/)

**Full documentation** is available at https://csql.readthedocs.io/en/latest/api.html .

## Example

```py
from csql import Q, Parameters
import pandas as pd
from datetime import date

con = your_database_connection()
```

Start with a straightforward query:
```py
p = Parameters(
	created_on = date(2020,1,1)
)
q1 = Q(f"""
select
	customers.id,
	first(customers.name) as name,
	first(created_on) as created_on,
	sum(sales.value) as sales
from
	customers
	join sales on customers.id = sales.customer_id
where created_on > {p['created_on']}}
group by customers.id
""")

print(q1.preview_pd(con))
```

|  | id | name | created_on | sales |
|--|----|------|------------|-------|
|1 |111 |John Smith | 2020-02-05 | 32.0 |
|2 |112 |Amy Zhang | 2020-05-01 | 101.5 |
|3 |115 |Tran Thanh | 2020-03-02 | 100000.0 |


The preview will pull down 10 rows to a) sanity-check the result of what you've just written, and b) validate your sql.

-----

Now, try building some new queries *that build on your previous queries*:
```py
q2 = Q(f"""
select
	ntile(100) over (order by sales)
		as ntile_100,
	name,
	sales
from {q1}
""")

print(q2.preview_pd(con))
```

|  | ntile_100 | name | sales |
|--|-----------|------|-------|
| 1|29| John Smith| 32.0 |
| 2|50|Amy Zhang | 101.5 |
| 3|99|Tran Thanh | 100000.0 |

-----

```py
q3 = Q(f"""
select
	ntile_100,
	min(sales),
	max(sales)
from {q2}
group by ntile_100
order by ntile_100
""")

# this time, we'll pull the whole result instead of just previewing:
result = pd.read_sql(**q3.pd(), con=con)
print(result)
```
|  | ntile_100 | min(sales) | max(sales) |
|--|-----------|----------|--------------|
| 28| 29 | 25 | 33.3 |
| 49| 50 | 98 | 120 |
| 98| 99 | 5004 | 100000.0 |

-----

## Cool! But, how does it work?

The basic idea is to turn your queries into a CTE by keeping track of what builds on top of what. For example, for the last query shown, `q3`, what actually gets sent to the database is:

```sql
with _subQuery0 as (
	select
		customers.id,
		first(customers.name) as name,
		first(created_on) as created_on,
		sum(sales.value) as sales
	from
		customers
		join sales on customers.id = sales.customer_id
	where created_on > :1
	group by customers.id
),
_subQuery1 as (
	select
		ntile(100) over (order by sales)
			as ntile_100,
		name,
		sales
	from _subQuery0
)
select
	ntile_100,
	min(sales),
	max(sales)
from _subQuery1
group by ntile_100
order by ntile_100
```

which is exactly the sort of unmaintainable and undebuggable monstrosity that this library is designed to help you avoid.


<!-- (end-intro)= -->

## Design Notes

I am perhaps overly optimistic about this, but currently I think this should work with most SQL dialects. It doesn't attempt to parse your SQL, uses CTEs which are widely supported, and passes numeric style parameters.
It's also not actually tied to `pandas` at all - `.pd()` is just a convenience method to build a dict you can splat into pd.read_sql.

## Easy Parameters

<!-- (params)= -->

Using proper SQL prepared statements is great to do, but can be annoying to maintain. Additionally, it can be incredibly
annoying when you are trying to use a list from Python:

```py
con = my_connection()
ids_i_want = [1, 2, 3]
with con.cursor() as c:
	# uh oh, you can't do this
	c.execute('select * from customers where id in :1', (ids_i_want,))

	# you need to do something like this instead
	c.execute('select * from customers where id in (:1, :2, :3), (ids_i_want[0], ids_i_want[1], ids_i_want[2],))
```

`csql` makes this much easier - you can embed your parameters naturally with string interpolation, and they will still be
sent as proper parameterized statements.

```py
p = Parameters(
	ids_i_want = [1, 2, 3],
	name = 'Jarrad'
)

get_customers = Q(f'''
	select * from customers
	where
		ids in {p['ids_i_want']}
		or name = {p['name']}
''')

with con.cursor() as c:
	c.execute(*get_customers.db)
```

That final statement is actually equivalent to:

```py
with con.cursor() as c:
	c.execute('''
		select * from customers
		where
			ids in (:1, :2, :3)
			or name = :4
	''', [1, 2, 3, 'Jarrad'])
```



<!-- (end-params)= -->


## Changing Parameter Values

<!-- (reparam)= -->

Parameters aren't super useful if they are set in stone, but `csql` wants you
to give values at the query definition time! How can you pass different values later?

This is achieved by passing `newParams` to {meth}`csql.Query.build`:

```py
p = Parameters(
  start=datetime.now() - timedelta(days=3),
  end=datetime.now()
)
q = Q(f'select count(*) from events where start <= date and date < end')
pd.read_sql(**q.pd, con=con)
# 42 # 3 days ago to now, as per `p`.
newParams = {'start': date(2010,1,1)}
pd.read_sql(**q.build(newParams=newParams).pd, con=con)
# 42000 # 2010 to now, with new value for `start` provided.
```

<!-- (end-reparam)= -->

## SQL Dialects

<!-- (sql-dialects)= -->

Different dialects can be specified at render time, or as the default dialect of your Queries. Currently the only things dialects control are parameter rendering and limits, but I expect to see some scope creep around here...
Dialects are instances of {class}`csql.dialect.SQLDialect` and can be found in {mod}`csql.dialect`. The default dialect is {class}`csql.dialect.DefaultDialect`, which uses a numeric parameter renderer. You can specify your own prefered dialect per-query:

```py
q = csql.Q(
	f"select 1 from thinger",
	dialect=csql.dialect.DuckDB
)
```

If you want to set a default, use `functools.partial` like so:

```py
import functools
Q = functools.partial(csql.Q, dialect=csql.dialect.DuckDB)
q = Q(f"select 1 from thinger")
```

### Inferred Dialects

If a query `q2` references a previous query `q1`, and `q1` has a dialect specified, then `q2` will use `q1`'s dialect by default.

```py
q1 = csql.Q('select 1 from thinger', dialect=csql.dialect.Snowflake)
q2 = csql.Q('select count(*) from {q1})
assert q2.default_dialect == csql.dialect.Snowflake
```

If you reference multiple queries with conflicting dialects, you'll get an error. Normally this is because you've actually
forgotten to specify something somewhere. If you're doing this on purpose, override by setting `dialect=` to `Q` manually.

### DIY Dialects 

You can construct your own dialects:

```py
import csql.dialect
MyDialect = csql.dialect.SQLDialect(
  paramstyle=csql.dialect.ParamStyle.qmark
)
```

There are presets for some common databases (see below), and I'm very happy to accept PRs for any
others.


<!-- (end-sql-dialects)= -->


How to use Caching
==================

<!-- (persist)= -->

Once you have a few queries chained together, you may
start to get annoyed by how long one or two big things at the start
take, and wonder if there's a way to stop them being executed each time.

For example,

```py
q1 = Q(f'select id, date, rank() over (partition by name order by date) as rank from customers')
q2 = Q(f'select date, count(*) from {q1}')
print(q2.preview_pd(con))
# takes 2 mins becuase q1 is so slow
print(q2.preview_pd(con))
# same thing again, also takes 2 mins
q3 = Q(f'select max(date) from {q2}')
print(q3.preview_pd(con))
# also takes 2 mins because q1 is so slow
```

The solution is to use {meth}`csql.Query.persist` on the slow query you want to re-use.
Above, we could either do this on `q1` or `q2`, depending on what works best with
our database. I'll demonstrate `q2`:

```py
q1 = Q(f'select id, date, rank() over (partition by name order by date) as rank from customers')
cache = TempTableCacher(con)
q2 = Q(f'select date, count(*) from {q1}').persist(cache) # <--- !!
print(q2.preview_pd(con))
# still takes 2 mins
print(q2.preview_pd(con))
# now this is fast!
q3 = Q(f'select max(date) from {q2}')
print(q3.preview_pd(con))
# now this is fast as well!
```

The only general builtin caching method is {class}`csql.contrib.persist.TempTableCacher`, however it's straightforward
to write your own. You may want to also see {mod}`csql.contrib.persist` as there is a Snowflake-specific example in there as well.

<!-- (end-persist)= -->
