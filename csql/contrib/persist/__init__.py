"""
``contrib.persist`` contains some :class:`csql.persist.Cacher` implementations.
"""
from csql._.persist import (
    Cacher as Cacher,
    Key as Key
)
from typing import *
from csql import RenderedQuery, Query, Q
from logging import getLogger

logger = getLogger(__name__)

class TempTableCacher(Cacher):
    """
    The ``TempTableCacher`` persists a query in a ``create temporary table if not exists``
    statement. It needs to be given a DBAPI-compliant connector to work.

    >>> from csql.contrib.persist import TempTableCacher
    >>> con = my_connection()
    >>> cache = TempTableCacher(con)
    >>> q = Q('select * from slow_view').persist(cache)
    >>> q2 = Q(f'select count(*) from {q}') # does nothing
    >>> print(q2.build().sql) #doctest: +ELLIPSIS 
    with
    _subQuery0 as (...)
    select count(*) from _subQuery0

    """
    def __init__(self, connection: Any):
        self._con = connection

    def _persist(self, rq: RenderedQuery, key: Key, tag: Optional[str]) -> Query:
        table_name = f'"csql_cache_{tag}_{key}"'

        sql, params, _names = rq

        create_sql = RenderedQuery(
            sql=f'''
            create temporary table if not exists {table_name}
            as
            {sql}
            ''',
            parameters=params,
            parameter_names=_names
        )

        logger.debug(f'Executing persist SQL:\n{create_sql.sql}\nwith params: {create_sql.parameters}')
        c = self._con.cursor()
        try:
            c.execute(*create_sql.db)
        finally:
            c.close()

        retrieve_sql = Q(f'''select * from {table_name}''') # maybe copy overrides and stuff?
        return retrieve_sql