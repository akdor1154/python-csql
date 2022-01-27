from __future__ import annotations
import abc
import enum
from enum import auto
from typing import *
from dataclasses import dataclass
if TYPE_CHECKING:
	import csql.dialect

__all__ = [
	'ParamStyle',
	'SQLDialect',
	'DefaultDialect',
	'Snowflake',
	'DuckDB'
]

class ParamStyle(enum.Enum):
	'''
	Enum to define how to render query parameter placeholders.
	'''

	numeric = auto()
	'''
	Use placeholders like ``:1``.

	:meta hide-value:
	'''
	numeric_dollar = auto()
	'''
	Use placeholders like ``$1``.

	:meta hide-value:
	'''
	qmark = auto()
	'''
	Use placeholders like ``?``.

	:meta hide-value:
	'''

	def __repr__(self) -> str:
		return 'ParamStyle.'+self.name

class Limit(enum.Enum):
	'''
	Enum to defines how to limit preview queries.
	'''
	limit = auto()
	'''
	Use a ``limit`` clause, e.g. ``select * from (query) limit 10``.

	:meta hide-value:
	'''
	top_n = auto()
	'''
	Use a ``top n`` clause, e.g. ``select top(10) * from (query)``.'

	:meta hide-value:
	'''
	ansi = auto()
	'''
	Use ANSI SQL ``fetch`` clause, e.g. ``select * from (query) fetch first 10 rows only``.

	:meta hide-value:
	'''

	def __repr__(self) -> str:
		return f'Limit.{self.name}'

@dataclass(frozen=True)
class SQLDialect:
	"""
	Represents settings of a SQL Dialect.

	
	>>> import functools
	>>> from csql.dialect import SQLDialect, ParamStyle
	>>> my_dialect=SQLDialect(paramstyle=ParamStyle.qmark)
	>>> p = Parameters(value=123)
	
	To use as a once-off, pass to :meth:`csql.Query.build`:

	>>> q = Q(f"select {p['value']}")
	>>> q.build() # builds normally
	RenderedQuery('select :1', (123,))
	>>> q.build(dialect=my_dialect) # builds with `my_dialect`
	RenderedQuery('select ?', (123,))

	To set as a default, use ``functools.partial``:

	>>> Q = functools.partial(csql.Q, dialect=my_dialect)
	>>> q = Q('select ...')	# builds with `my_dialect`

	"""
	paramstyle: csql.dialect.ParamStyle = ParamStyle.numeric
	limit: csql.dialect.Limit = Limit.limit

	# experiments for doc gen
Snowflake = SQLDialect(
	paramstyle=ParamStyle.numeric,
	limit=Limit.limit
)
'''A dialect for Snowflake'''

DuckDB = SQLDialect(
	paramstyle=ParamStyle.numeric_dollar,
	limit=Limit.limit
)
'''A dialect for DuckDB'''

MSSQL = SQLDialect(
	paramstyle=ParamStyle.numeric,
	limit=Limit.top_n
)
'''A dialect for MS SQL Server'''
	# def __repr__(self) -> str:
	# 	import inspect
	# 	mod = inspect.getmodule(self)
	# 	print('!!!')
	# 	if mod is None:
	# 		print('nomod')
	# 		return super().__repr__()
	# 	print('???')
	# 	name = next(
	# 		(
	# 			name
	# 			for name, obj in vars(mod).items()
	# 			if obj is self
	# 		),
	# 		None
	# 	)
	# 	print('!!!!')
	# 	if name is None:
	# 		print('nolocal')
	# 		return super().__repr__()
	# 	print(f'{name=}')
	# 	return name


DefaultDialect = SQLDialect(
	paramstyle=ParamStyle.numeric,
	limit=Limit.limit
)
'''The default dialect for CSQL.'''

import dataclasses
@dataclasses.dataclass(frozen=True)
class InferOrDefault:
	''' A wrapper to flag that this query should use a previous query\'s dialect if not otherwise specified. '''
	dialect: csql.dialect.SQLDialect