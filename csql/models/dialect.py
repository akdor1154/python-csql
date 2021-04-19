import abc
import enum
from enum import auto
from typing import *

__all__ = [
	'ParamStyle',
	'SQLDialect',
	'Snowflake',
	'DuckDB'
]

class ParamStyle(enum.Enum):
	numeric = auto()
	numeric_dollar = auto()

class SQLDialect(NamedTuple):
	paramstyle: ParamStyle

Default = SQLDialect(
	paramstyle=ParamStyle.numeric
)

Snowflake = SQLDialect(
	paramstyle=ParamStyle.numeric
)

DuckDB = SQLDialect(
	paramstyle=ParamStyle.numeric_dollar
)
