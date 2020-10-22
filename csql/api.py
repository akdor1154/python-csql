from typing import *
from types import FrameType
import inspect
from .asthackery import getQueryParts
from .models.query import Query, Parameters, RenderedQuery

def _getCallerFrame(qframe: Optional[FrameType]) -> FrameType:
	assert qframe is not None, "CPython only! Go vote for PEP-501."
	parentFrame = qframe.f_back
	assert parentFrame is not None, "Couldn\'t get caller frame! Go whinge that PEP-501 never got implemented."
	return parentFrame

def Q(sql: Union[str, Callable[[], str]], parameters: Optional[Parameters] = None) -> Query:
	if callable(sql):
		callerFrame = _getCallerFrame(inspect.currentframe())
		queryParts = getQueryParts(sql, callerFrame)
	else:
		queryParts = [sql]

	return Query(
		queryParts=queryParts,
		parameters=parameters or Parameters()
	)