#%%

from typing import NamedTuple
import pandas as pd
import duckdb
from typing import *
import csql
import csql.dialect
from csql import Parameters
from functools import partial
#%%
d = duckdb.connect()

#%%
Q = partial(csql.Q, dialect=csql.dialect.DuckDB)

#%%
class DPC(NamedTuple):
    c: duckdb.DuckDBPyConnection
    def close(self):
        pass
    def __getattr__(self, __name: str):
        return getattr(self.c, __name)
class DP(NamedTuple):
    d: duckdb.DuckDBPyConnection
    def cursor(self):
        return DPC(self.d)
    def __getattr__(self, __name: str):
        return getattr(self.d, __name)
dp = DP(d)
    
#%%
tab_df = pd.read_excel(
    'melbourne_crime.xlsx',
    sheet_name='Table 04',
    engine='openpyxl'
)
display(tab_df)
#%%
d.register('tab', tab_df)
# %%
qTab = Q(f'''
    select
        "Year" as year,
        "Local Government Area" as lga,
        "Location Division" as loc1,
        "Location Subdivision" as loc2,
        "Location Group" as loc3,
        "Offence Count" as offences
    from tab
''')
display(qTab.preview_pd(dp))

#%%
from csql._.persist import TempTableCacher
C = TempTableCacher(dp)
#%%
p = Parameters(year='2018')
#%%
qSlow = Q(f'''
    select
        lga, loc1, loc2,
        sum(offences) as offences,
        rank() over (
            partition by lga
            order by sum(offences) desc
        ) as location_rank_lga
    from {qTab} q
    where year >= {p['year']}
    group by 1,2,3
''').persist(C)
display(qSlow.preview_pd(dp))

# %%
qSlowQuick = Q(f'''
    select * from {qSlow}
    where location_rank_lga = 1
    order by lga
''')
display(qSlowQuick.preview_pd(dp))
display(qSlowQuick.build())
# %%
newParams = dict(year=2010)
display(qSlowQuick.preview_pd(dp, newParams=newParams))
display(qSlowQuick.build(newParams=newParams))
# %%
