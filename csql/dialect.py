# mypy: implicit-reexport
# pyright: reportUnusedImport=false
# ruff: noqa: F401
from ._.models.dialect import (
	DefaultDialect,
	InferOrDefault,
	Limit,
	ParamStyle,
	SQLDialect,
)

DefaultDialect = DefaultDialect  # give sphinx a nudge  # noqa: PLW0127
"""The default dialect for ``csql``."""

Snowflake = SQLDialect(paramstyle=ParamStyle.numeric, limit=Limit.limit)
"""A dialect for Snowflake"""

DuckDB = SQLDialect(paramstyle=ParamStyle.numeric_dollar, limit=Limit.limit)
"""A dialect for DuckDB"""

MSSQL = SQLDialect(paramstyle=ParamStyle.numeric, limit=Limit.top_n)
"""A dialect for MS SQL Server"""
