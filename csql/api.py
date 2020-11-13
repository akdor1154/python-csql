from typing import *
from types import FrameType
import inspect
from .input import asthackery, strparsing
from .models.query import Query, Parameters, RenderedQuery
from contextlib import contextmanager
import warnings
from textwrap import dedent

def _getCallerFrame(qframe: Optional[FrameType]) -> FrameType:
	assert qframe is not None, "CPython only! Go vote for PEP-501."
	parentFrame = qframe.f_back
	assert parentFrame is not None, "Couldn\'t get caller frame! Go whinge that PEP-501 never got implemented."
	return parentFrame

@contextmanager
def noisyWarnings():
	old_showwarning = warnings.showwarning
	with warnings.catch_warnings():
		warnings.simplefilter('always')
		warnings.showwarning = old_showwarning
		yield

def Q(sql: Union[str, Callable[[], str]], parameters: Optional[Parameters] = None) -> Query:
	if callable(sql):
		with noisyWarnings():
			warnings.warn(
				dedent('''
					Passing a lambda to Q is deprecated! You can now just pass an interpolated string directly:
						Q(f"select from {blah}")
				''').strip(),
				category=DeprecationWarning,
				stacklevel=2
			)
		callerFrame = _getCallerFrame(inspect.currentframe())
		queryParts = asthackery.getQueryParts(sql, callerFrame)
	else:
		queryParts = strparsing.getQueryParts(sql)

	return Query(
		queryParts=queryParts,
		parameters=parameters or Parameters()
	)