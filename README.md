# csql - Composeable SQL

**csql** is a Python library to help you write more manageable SQL queries. You can write your queries as small, self-contained chunks, preview the results without pulling a whole result-set down from your database, then refer to them in future queries.

There are also useful features for handling database parameters properly.

The intended use-case is for data analysis and exploration.

[![PyPI version](https://badge.fury.io/py/csql.svg)](https://pypi.org/project/csql/)

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

## Dialects (TODO: API DOCS INSTEAD OF MORE SHITTY README SECTIONS)

Different dialects can be specified at render time, or as the default dialect of your Queries. Currently the only thing dialects control is parameter rendering, but I expect to see some scope creep around here...
Dialects are instances of `SQLDialect` and can be found in `csql.dialect`. The default dialect is `DefaultDialect`, which uses a numeric parameter renderer. You can specify your own prefered dialect per-query:
```py
import csql
import csql.dialect

q = csql.Q(
	f"select 1 from thinger",
	dialect=csql.dialect.DuckDB
)
```

If you want to set a default, use `functools.partial` like so:
```py
import csql
import csql.dialect
import functools
Q = functools.partial(csql.Q, dialect=csql.dialect.DuckDB)
q = Q(f"select 1 from thinger")
```

You can also construct your own dialects:
```py
import csql.dialect
MyDialect = csql.dialect.SQLDialect(
	paramstyle=csql.dialect.ParamStyle.qmark
)
```

### Dialect Options:

#### paramstyle: csql.dialect.ParamStyle

`paramstyle` can be one of
 - `ParamStyle.numeric` (`where abc = :1`)
 - `ParamStyle.numeric_dollar` (`where abc = $1`)
 - `ParamStyle.qmark` (`where abc = ?`)

## TODO / Future Experiments:

 - Document the API (for now, just read the tests)
 - Implement other preview systems than `pandas` (input wanted! what would be useful for you?)
 - Finalize API to be as ergonomic as possible for interactive use (input wanted!)
 - Implement some way of actually storing previous results, e.g. into temp tables. (uh oh, this would need DB-specific awareness :( )
