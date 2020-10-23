import ast
import inspect
from typing import *
from types import FrameType
from dataclasses import dataclass
from abc import ABCMeta
import textwrap
import sys

try:
	from astpretty import pprint as astprint
except ImportError:
	from pprint import pprint
	astprint = pprint

if sys.version_info >= (3, 8):
	AST_CONSTANT_TYPES = (ast.Constant,)
elif sys.version_info >= (3, 6):
	AST_CONSTANT_TYPES = (ast.Str, ast.Constant)
else:
	raise Exception('Needs Python >= 3.6, sorry!')

from .models.query import Query, QueryBit, Parameters

ERRORMSG = textwrap.dedent("""
	Can only deal with simple code constructs, e.g.
		• Q(lambda: ...)
		• x = lambda: ...
		  Q(x)
		• r = Q(lambda: ...;)
	In particular, multiple lambdas on the same line are a no-no.
	Go get acceptance for and implement PEP-501."""
)

def getLambda(fn: Callable[[], str]) -> ast.Lambda:

	tree = ast.parse(inspect.getsource(fn).strip())
	lambdas = [
		node for node in ast.walk(tree)
		if isinstance(node, ast.Lambda)
	]

	if len(lambdas) == 1:
		return lambdas[0]
	else:
		astprint(tree)
		raise Exception(ERRORMSG)

def _getQueryPart(part: ast.expr, callerFrame: FrameType) -> Union[str, QueryBit]:
	if isinstance(part, ast.FormattedValue):
		expression = ast.Expression(part.value)
		compiled = compile(expression, filename='<HAX>', mode='eval')
		result = eval(compiled, callerFrame.f_globals, callerFrame.f_locals)
		if isinstance(result, QueryBit):
			return result
		else:
			return str(result)
	elif isinstance(part, AST_CONSTANT_TYPES):
		val = ast.literal_eval(part)
		return str(val)
	else:
		astprint(part)
		raise Exception("fstring had something (dumped above) that was not a Constant or a FormattedValue!")

def getQueryParts(f: Callable[[], str], callerFrame: FrameType) -> List[Union[str, QueryBit]]:
	lambdaAst = getLambda(f)

	if isinstance(lambdaAst.body, ast.JoinedStr):
		joinedStr = lambdaAst.body

		return [
			_getQueryPart(part, callerFrame)
			for part in joinedStr.values
		]
	elif isinstance(lambdaAst.body, AST_CONSTANT_TYPES):
		val = ast.literal_eval(lambdaAst.body)
		return [str(val)]
	else:
		astprint(lambdaAst)
		raise Exception(ERRORMSG)