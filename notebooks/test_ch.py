# %%

# %load_ext autoreload
# %autoreload 2

# %%

import zoneinfo
from datetime import date, datetime
from functools import partial

import clickhouse_connect as chc
import polars as pl
from clickhouse_connect.driver.ddl import create_table_from_arrow_schema
from IPython.display import display

import csql
import csql.dialect
from csql import Parameters

# %%
ch = chc.create_client(password="asdf")
# chcon = chdb.dbapi.Connection()
# %%
Q = partial(csql.Q, dialect=csql.dialect.ClickHouse)


# %%
#
# class DPC(NamedTuple):
# 	c: duckdb.DuckDBPyConnection

# 	def close(self):
# 		pass

# 	def __getattr__(self, name: str):
# 		return getattr(self.c, name)


# class DP(NamedTuple):
# 	d: duckdb.DuckDBPyConnection

# 	def cursor(self):
# 		return DPC(self.d)

# 	def __getattr__(self, name: str):
# 		return getattr(self.d, name)


# dp = DP(d)

# %%
tab_df = pl.read_excel("melbourne_crime.xlsx", sheet_name="Table 04", engine="calamine")
display(tab_df)
# %%

ch.command(
	create_table_from_arrow_schema(
		"tab", tab_df.to_arrow().schema, "MergeTree", {"ORDER BY": "Year"}
	)
)
ch.insert_df_arrow("tab", tab_df)
# %%
#
# d.register("tab", tab_df)
# %%
qTab = Q("""
    select
        "Year" as year,
        "Local Government Area" as lga,
        "Location Division" as loc1,
        "Location Subdivision" as loc2,
        "Location Group" as loc3,
        "Offence Count" as offences
    from tab
""")
display(qTab.preview_pl(ch))
# %%
df = ch.query_df_arrow(**qTab.ch, dataframe_library="polars")
display(df)
# %%
# from csql.contrib.persist import TempTableCacher

# C = TempTableCacher(dp)
# %%
p = Parameters(year="2018")
# %%
qSlow = Q(f"""
    select
        lga, loc1, loc2,
        sum(offences) as sum_offences,
        rank() over (
            partition by lga
            order by sum(offences) desc
        ) as location_rank_lga
    from {qTab} q
    where year >= {p["year"]}
    group by 1,2,3
""")
# %%
display(qSlow.preview_pl(ch, dialect=csql.dialect.ClickHouse))

# %%
pp = Parameters(
	s="a string",
	i=123,
	f=123.0,
	d=date(2024, 1, 1),
	dtn=datetime(2024, 1, 1, 12, 00, 00, tzinfo=None),  # noqa: DTZ001
	dttz=datetime(
		2024, 1, 1, 12, 00, 00, tzinfo=zoneinfo.ZoneInfo("Australia/Melbourne")
	),
)
qp = Q(f"""
	select
		{pp.s} as s,
		{pp.i:Int32} as i,
		{pp.f} as f,
		{pp.d} as d,
		{pp.dtn} as dtn,
		{pp.dttz} as dttz
	""")
# %%
print(qp.build().sql)
print(qp.build().params_dict)
display(qp.preview_pl(ch, rows=None))
# %%
qp._default_dialect()

ch.query_df("select toTypeName(parseDateTime64OrZero(''))")
