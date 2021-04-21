from typing import *
from .input import strparsing
from .models.query import Query, Parameters, RenderedQuery
from .models.dialect import SQLDialect, DefaultDialect
from .models.overrides import Overrides
import warnings
from textwrap import dedent

def Q(
	sql: Union[str, Callable[[], str]],
	parameters: Optional[Parameters] = None,
	dialect: SQLDialect = DefaultDialect,
	overrides: Optional[Overrides] = None
) -> Query:
	if callable(sql):
		warnings.warn(
			dedent('''
				Passing a lambda to Q is deprecated! You can now just pass an interpolated string directly:
					Q(f"select from {blah}")
			''').strip(),
			category=DeprecationWarning,
			stacklevel=2
		)
		queryParts = strparsing.getQueryParts(sql())
	else:
		queryParts = strparsing.getQueryParts(sql)

	if parameters is not None:
		warnings.warn(
			dedent('''
				Passing parameters to Q as a separate argument is no longer necessary! You can continue to just interpolate params:
					Q(f"select from {blah} where abc = {p['abc']}")
			'''),
			category=DeprecationWarning,
			stacklevel=2
		)

	return Query(
		queryParts=queryParts,
		default_dialect=dialect,
		default_overrides=overrides
	)