import abc
import enum
from enum import auto
from typing import *
from dataclasses import dataclass

__all__ = [
	'ParamStyle',
	'SQLDialect',
	'DefaultDialect',
	'Snowflake',
	'DuckDB'
]

class ParamStyle(enum.Enum):
	numeric = auto()
	numeric_dollar = auto()
	qmark = auto()

class Limit(enum.Enum):
	limit = auto()
	top_n = auto()
	ansi = auto()

@dataclass(frozen=True)
class SQLDialect:
	"""
		Represents settings of a SQL Dialect

		.. :canonical: csql.dialect.SQLDialect
	"""
	paramstyle: ParamStyle = ParamStyle.numeric
	limit: Limit = Limit.limit

	# experiments for doc gen
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

Snowflake = SQLDialect(
	paramstyle=ParamStyle.numeric,
	limit=Limit.limit
)

DuckDB = SQLDialect(
	paramstyle=ParamStyle.numeric_dollar,
	limit=Limit.limit
)

MSSQL = SQLDialect(
	paramstyle=ParamStyle.numeric,
	limit=Limit.top_n
)