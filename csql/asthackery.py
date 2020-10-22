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

ERRORMSG = "Can only deal with Q(lambda: ...), x = lambda: ...; Q(x), and r = Q(lambda: ...;). Go vote for PEP-501."

def getLambdaFromCall(call: ast.Call) -> ast.Lambda:
    args = call.args

    # it would be nice to check this but the simple form below will break e.g. import alias, import Q as S.
    #assert call.func.id == 'Q', ERRORMSG

    assert type(args[0]) == ast.Lambda, ERRORMSG
    return cast(ast.Lambda, args[0])

def getLambdaFromAssign(assign: ast.Assign) -> ast.Lambda:
    value = assign.value

    if isinstance(value, ast.Lambda):
        return value

    elif isinstance(value, ast.Call):
        return getLambdaFromCall(value)

    else:
        raise Exception(ERRORMSG)

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

    assert len(tree.body) == 1

    body = tree.body[0]

    if isinstance(body, ast.Assign):
        return getLambdaFromAssign(body)
    elif isinstance(body, ast.Expr) and isinstance(body.value, ast.Call):
        return getLambdaFromCall(body.value)
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