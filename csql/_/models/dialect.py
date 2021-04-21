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

@dataclass
class SQLDialect:
	"""Represents settings of a SQL Dialect"""
	paramstyle: ParamStyle = ParamStyle.numeric
	limit: Limit = Limit.limit


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