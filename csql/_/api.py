from __future__ import annotations
from typing import *
from .input import strparsing
from .models.query import Query, Parameters, RenderedQuery
from .models import dialect as _dialect
from .models.dialect import SQLDialect, DefaultDialect
from .models import overrides as _overrides
from .models.overrides import Overrides
import warnings
from textwrap import dedent

if TYPE_CHECKING:
	import csql
	import csql.dialect
	import csql.overrides


def Q(
	sql: str,
	dialect: Union[csql.dialect.SQLDialect, csql.dialect.InferOrDefault] = _dialect.InferOrDefault(DefaultDialect),
	overrides: Union[Optional[csql.overrides.Overrides], csql.overrides.InferOrDefault] = _overrides.InferOrDefault(None)
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
		By default, if this Query references another Query, the references Query's dialects will be used.
	:param overrides: A default set of :class:`overrides<csql.overrides.Overrides>` to use when building this Query.
		By default, if this Query references another Query, the references Query's overrides will be used.

	"""
	if callable(sql):
		raise TypeError(
			dedent('''
				Passing a lambda to Q is no longer supported! You can now just pass an interpolated string directly:
					Q(f"select from {blah}")
			''').strip()
		)

	queryParts = strparsing.getQueryParts(sql)

	existing_dialects = {
		q.default_dialect
		for q in queryParts
		if isinstance(q, Query) and isinstance(q.default_dialect, SQLDialect)
	}

	existing_overrides = {
		q.default_overrides
		for q in queryParts
		if isinstance(q, Query)
	}

	if isinstance(dialect, _dialect.InferOrDefault):
		if len(existing_dialects) == 0:
			dialect = dialect
		elif len(existing_dialects) == 1:
			dialect = next(iter(existing_dialects))
		else:
			ds = ', '.join(str(d) for d in existing_dialects)
			raise Exception(dedent(f'''
				Found multiple dialects when inferring the default:
					{ds}.
				If this is intentional, please specify a dialect for this query explicitly, e.g.
					Q('select ...', dialect=csql.dialect.DefaultDialect)
			''').strip())

	if isinstance(overrides, _overrides.InferOrDefault):
		if len(existing_overrides) == 0:
			overrides = overrides
		elif len(existing_overrides) == 1:
			overrides = next(iter(existing_overrides))
		else:
			os = ', '.join(str(o) for o in existing_overrides)
			raise Exception(dedent(f'''
				Found multiple overrides when inferring the default:
					{os}.
				If this is intentional, please specify overrides for this query explicitly, e.g.
					Q('select ...', overrides=None)
			''').strip())


	return Query(
		queryParts=queryParts,
		default_dialect=dialect,
		default_overrides=overrides,
		_extensions=frozenset()
	)