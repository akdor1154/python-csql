import ast
import inspect
from pprint import pprint
from typing import *
from types import FrameType
from dataclasses import dataclass
from abc import ABCMeta
import textwrap

from astpretty import pprint as astprint

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
	'''
	tests:

	q1 = Q(lambda: f"""select a from b""")

	x = lambda: f"""select a from b2"""
	q2 = Q(x)

	Q(lambda: f""" select a from b3""")
	Q(x)
	'''

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
	if isinstance(part, ast.Constant):
		return cast(str, part.value)
	elif isinstance(part, ast.FormattedValue):
		# expression = ast.Expression(ast.Expr(
		#     lineno=part.lineno, end_lineno=part.end_lineno,
		#     col_offset=part.col_offset, end_col_offset=part.end_col_offset,
		#     value=part.value
		# ))
		expression = ast.Expression(part.value)
		compiled = compile(expression, filename='<HAX>', mode='eval')
		result = eval(compiled, callerFrame.f_globals, callerFrame.f_locals)
		pprint(result)
		if isinstance(result, QueryBit):
			return result
		else:
			return str(result)
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
	elif isinstance(lambdaAst.body, ast.Constant):
		return [lambdaAst.body.value]
	else:
		astprint(lambdaAst)
		raise Exception(ERRORMSG)