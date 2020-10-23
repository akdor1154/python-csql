# csql - Composeable SQL

**csql** is a Python library to help you write more manageable SQL queries. You can write your queries as small, self-contained chunks, preview the results without pulling a whole result-set down from your database, then refer to them in future queries.

There are also useful features for handling database parameters properly.

The intended use-case is for data analysis and exploration. There's a particular hacky part of the current implementation that leads me to discourage using this in a productionized application: for that scenario you could still use this to generate your sql in a build step or something.

## Example:

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
q1 = Q(lambda: f"""
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
""", p)

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
q2 = Q(lambda: f"""
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
q3 = Q(lambda: f"""
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
	from {q1}
)
select
	ntile_100,
	min(sales),
	max(sales)
from {q2}
group by ntile_100
order by ntile_100
```

which is exactly the sort of unmaintainable and undebuggable monstrosity that this library is designed to help you avoid.

## Design Notes:

I am perhaps overly optimistic about this, but currently I think this should work with most SQL dialects. It doesn't attempt to parse your SQL, uses CTEs which are widely supported, and passes numeric style parameters.
It's also not actually tied to `pandas` at all - `.pd()` is just a convenience method to build a dict you can splat into pd.read_sql.

## TODO / Future Experiments:

 - Document the API (for now, just read the tests)
 - Implement other preview systems than `pandas` (input wanted! what would be useful for you?)
 - Finalize API to be as ergonomic as possible for interactive use (input wanted!)
 - Implement some way of actually storing previous results, e.g. into temp tables. (uh oh, this would need DB-specific awareness :( )
 - Consider other ways of nicely specifying dependent queries that don't rely on AST-parsing magic (e.g. maybe overloading __add__ and __radd__? `"select 1 from " + q1 + "where ..."`?)

## What was that 'particular hacky part of the current implementation'?

Glad you asked. Consider what goes on here:
```py
Q(lambda: f"""select 1 from {otherQuery}""")
```
We need to
 - get the SQL in a way that we can inject dependencies in to it
 - get the dependent queries
 - build the dependent queries into a CTE, and inject the names of previous clauses in this CTE into later ones as appropriate
 - not go down the rabbit hole of actually parsing SQL, this will certainly end in a headache and unsupported SQL dialects, which would be a big deal for the intended use case of interactive analytical queries against analytics DBs.

String interpolation is nearly adequate for this. Unfortunately, Python lacks the ability to "hook in" to string interpolation to the extent that would be required to. For example, in Javascript or Julia, it would be possible to define a string interpolation function or string macro like
```js
Q`select 1 from ${otherQuery}`
```
and it would satisfy all of the above.

However, Python lacks this ability, and the PEP to add it doesn't look likely to land any time soon, if ever (see: https://www.python.org/dev/peps/pep-0501/)

As a workaround, my current strategy is to require `Q` to be called with the fstring wrapped in a lambda, run getsource() to get the AST of the lambda, pull out the f-string AST node, and execute it myself, so I can pull out dependent queries and parameters properly. (I think e.g. pytest does similar hackery to get its magic `assert` diffs.)

This seems to work in most simple cases and the implementation is not complex. However it's still brittle and a bit shit. (in practice, the biggest drawback I've found is it won't work in the REPL.)