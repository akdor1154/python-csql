import functools
from typing import TYPE_CHECKING
from ..models.query import PreBuild, Query, QueryBit, QueryExtension, QueryReplacer, RenderedQuery
from dataclasses import dataclass
from ..renderer.query import QueryRenderer
from csql import Q
from abc import ABC, abstractmethod
from typing import *
import threading
import asyncio
import uuid
import logging

logger = logging.getLogger(name=__name__)

@dataclass(frozen=True)
class Persistable(QueryExtension):
    """ Attached directly to a slow query. """
    cacher: 'Cacher'
    
    tag: Optional[str]
    'User-supplied tag, to potentially be used by Cacher to give readable names to things it caches.'

def  _cache_replacer(queryRenderer: QueryRenderer) -> QueryReplacer:
    def replacer(q: Query) -> Query:
        if (p := q._get_extension(Persistable)) is None:
            return q
    
        # q is persistable.
        save_fn = KL._make_save_fn(q, queryRenderer, p.cacher, p.tag)
        return q._add_extensions(PreBuild(save_fn))
    return replacer

class KeyLookup():

    saved: Dict[int, Awaitable[Query]] = {}
    lock = threading.Lock()

    def _get_key(self, rq: RenderedQuery, tag: Optional[str]) -> int:
        return hash((rq.sql, tag, *rq.parameters))

    def _make_save_fn(self, q: Query, qr: QueryRenderer, c: 'Cacher', tag: Optional[str]) -> Callable[[], Query]:
        rq = qr.render(q)
        key = self._get_key(rq, tag)

        # def wrapped_save_fn() -> Query:
        #     with self.lock:
        #         if key not in self.saved:
        #             logger.debug(f'Executing save function for rendered query {rq} with {tag=}')
        #             self.saved[key] = asyncio.run(c._persist(rq, key, tag))
        #         else:
        #             logger.debug(f'Using cached result for rendered query {rq} with {tag=}')
        #         result = self.saved[key]
            
        #     return result
            
        # return wrapped_save_fn
        
        async def wrapped_save_fn() -> Query:
            with self.lock:
                if key not in self.saved:
                    loop = asyncio.get_event_loop()
                    # we have to make our own future here so we can await it multiple times if necessary.
                    # if we were to put the task from _persist() into saved, we could only await it once.
                    future = loop.create_future()
                    self.saved[key] = future
                    asyncio \
                        .create_task(c._persist(rq, key, tag)) \
                        .add_done_callback(lambda t: future.set_result(t.result()))
                result_future = self.saved[key]
                
            result = await result_future
            print(f'{result=}')
            return result

        return lambda: asyncio.run(wrapped_save_fn())

KL = KeyLookup() # singleton

class Cacher(ABC):

    def persist(self, q: Query, tag: Optional[str]) -> Query:
        """ Marks a query as persistabe. """
        return q._add_extensions(Persistable(self, tag))

    @abstractmethod
    async def _persist(self, rq: RenderedQuery, key: int, tag: Optional[str]) -> Query:
        """ Returns a function which will save the query, and a function which returns a query that will retrieve the saved one. """
        pass


class TempTableCacher(Cacher):
    def __init__(self, connection: Any):
        self._con = connection

    async def _persist(self, rq: RenderedQuery, key: int, tag: Optional[str]) -> Query:
        table_name = f'"csql_cache_{tag}_{key}"'

        sql, params = rq

        create_sql = RenderedQuery(
            sql=f'''
            create temporary table if not exists {table_name}
            as
            {sql}
            ''',
            parameters=params
        )

        logger.debug(f'Executing persist SQL:\n{create_sql.sql}\nwith params: {create_sql.parameters}')
        c = self._con.cursor()
        try:
            c.execute(*create_sql.db)
        finally:
            c.close()

        retrieve_sql = Q(f'''select * from {table_name}''') # maybe copy overrides and stuff?
        return retrieve_sql



# class SnowflakeResultSetCacher(Cacher):
#     def __init__(self, connection: 'snowflake.connector.Connection'):
#         self._con = connection

#     async def _persist(self, rq: RenderedQuery, key: int) -> Query:

#         sql, params = rq

#         logger.debug(f'Executing persist SQL:\n{sql}\nwith params: {params}')
#         c = self._con.cursor()
#         try:
#             c.execute(sql, params)
#             qid = c.sfqid
#         finally:
#             c.close()

#         retrieve_sql = Q(f'''select * from table(result_scan('{qid}')''')
#         return retrieve_sql

