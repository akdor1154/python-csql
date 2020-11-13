from typing import *
from .input import strparsing
from .models.query import Query, Parameters, RenderedQuery
import warnings
from textwrap import dedent

def Q(sql: Union[str, Callable[[], str]], parameters: Optional[Parameters] = None) -> Query:
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

	return Query(
		queryParts=queryParts,
		parameters=parameters or Parameters()
	)