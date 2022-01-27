"""
``contrib.persist.snowflake`` contains cache implementations specifically
for the Snowflake database. For this file to import properly, you'll need
to make sure `snowflake-connector-python` is installed.
"""

from __future__ import annotations
from typing import *
from . import Cacher, Key
from csql import RenderedQuery, Query, Q
if TYPE_CHECKING:
    import snowflake.connector
import logging

logger = logging.getLogger(__name__)

class SnowflakeResultSetCacher(Cacher):

    """
    Caches queries using the `RESULT_SCAN` functionality of snowflake. This is nice because it means you
    can kill your snowflake connection without losing temp tables, and the results are still cleaned up
    properly by Snowflake in 7 days.

    :type connection: `snowflake.connector.Connection <https://docs.snowflake.com/en/user-guide/python-connector-api.html#object-connection>`_
    """

    def __init__(self, connection: snowflake.connector.Connection):
        self._con = connection

    def _persist(self, rq: RenderedQuery, key: Key, tag: Optional[str]) -> Query:

        sql, params, _param_names = rq

        logger.debug(f'Executing persist SQL:\n{sql}\nwith params: {params}')
        c = self._con.cursor()
        try:
            c.execute(sql, params)
            qid = c.sfqid
        finally:
            c.close()

        retrieve_sql = Q(f'''select * from table(result_scan('{qid}')''')
        return retrieve_sql