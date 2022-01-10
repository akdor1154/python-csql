from typing import *
from .input import strparsing
from .models.query import Query, Parameters, RenderedQuery
from .models.dialect import SQLDialect, DefaultDialect
from .models.overrides import Overrides
import warnings
from textwrap import dedent

if TYPE_CHECKING:
	import csql
	import csql.dialect

def Q(
	sql: str,
	dialect: 'csql.dialect.SQLDialect' = DefaultDialect,
	overrides: Optional['csql.Overrides'] = None
) -> 'csql.Query':
	"""
	Create a :class:`csql.Query`.

	Usage:

	>>> p = Parameters(created_on=date(2020,1,1))
	>>> q_cust  = Q(f'''select name, customer_type from customers where created_on > {p['created_on']}''')
	>>> q_count = Q(f'select customer_type, count(*) from {q_cust} group by rollup(type)')

	See: :ref:`basic_usage`

	:param sql: A string with a SQL query. The string is designed to be built with an ``f'f-string'``,
		so you can interpolate Parameters and other Queries inside in a natural way.

	:param dialect: A default :class:`dialect<csql.dialect.SQLDialect>` to use when building this Query.
	:param overrides: A default set of :class:`overrides<csql.Overrides>` to use when building this Query.

	"""
	if callable(sql):
		raise TypeError(
			dedent('''
				Passing a lambda to Q is no longer supported! You can now just pass an interpolated string directly:
					Q(f"select from {blah}")
			''').strip()
		)

	queryParts = strparsing.getQueryParts(sql)

	return Query(
		queryParts=queryParts,
		default_dialect=dialect,
		default_overrides=overrides,
		_extensions=frozenset()
	)