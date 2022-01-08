"""
``contrib.persist.snowflake`` contains cache implementations specifically
for the Snowflake database. For this file to import properly, you'll need
to make sure `snowflake-connector-python` is installed.
"""
from typing import *
from . import Cacher, Key
from csql import RenderedQuery, Query, Q
if TYPE_CHECKING:
    from snowflake.connector import Connection as SnowflakeConnection
import logging

logger = logging.getLogger(__name__)

class SnowflakeResultSetCacher(Cacher):
    def __init__(self, connection: 'SnowflakeConnection'):
        self._con = connection

    async def _persist(self, rq: RenderedQuery, key: Key, tag: Optional[str]) -> Query:

        sql, params = rq

        logger.debug(f'Executing persist SQL:\n{sql}\nwith params: {params}')
        c = self._con.cursor()
        try:
            c.execute(sql, params)
            qid = c.sfqid
        finally:
            c.close()

        retrieve_sql = Q(f'''select * from table(result_scan('{qid}')''')
        return retrieve_sql