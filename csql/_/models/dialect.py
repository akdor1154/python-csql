import abc
import enum
from enum import auto
from typing import *

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

class SQLDialect(NamedTuple):
	"""Represents settings of a SQL Dialect"""
	paramstyle: ParamStyle

DefaultDialect = SQLDialect(
	paramstyle=ParamStyle.numeric
)

Snowflake = SQLDialect(
	paramstyle=ParamStyle.numeric
)

DuckDB = SQLDialect(
	paramstyle=ParamStyle.numeric_dollar
)
