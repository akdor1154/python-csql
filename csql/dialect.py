# mypy: implicit-reexport
from ._.models.dialect import (
	SQLDialect,

	ParamStyle,
	Limit,

	DefaultDialect,
	InferOrDefault
)

DefaultDialect = DefaultDialect # give sphinx a nudge
'''The default dialect for ``csql``.'''

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