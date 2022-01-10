from __future__ import annotations
import functools
from typing import TYPE_CHECKING
from ..models.query import PreBuild, Query, QueryBit, QueryExtension, RenderedQuery
from ..models.query_replacers import QueryReplacer
from dataclasses import dataclass
from ..renderer.query import QueryRenderer
from csql import Q
from abc import ABC, abstractmethod
from typing import *
import threading
import asyncio
import uuid
import logging
import pickle
import hashlib

if TYPE_CHECKING:
    import csql
    import csql.persist

logger = logging.getLogger(name=__name__)

@dataclass(frozen=True)
class Persistable(QueryExtension):
    """ Attached directly to a slow query. """
    cacher: 'Cacher'

    tag: Optional[str]
    'User-supplied tag, to potentially be used by Cacher to give readable names to things it caches.'

def  cache_replacer(queryRenderer: QueryRenderer) -> QueryReplacer:
    def replacer(q: Query) -> Query:
        if (p := q._get_extension(Persistable)) is None:
            return q

        # q is persistable.
        save_fn = KL._make_save_fn(q, queryRenderer, p.cacher, p.tag)

        #return q._add_extensions(PreBuild(save_fn))
        return save_fn()
    return replacer

Key = str # I keep changing my mind between str, int, bytes...

class KeyLookup():

    saved: Dict[Key, Awaitable[Query]] = {}
    lock = threading.Lock()

    def _get_key(self, rq: RenderedQuery, tag: Optional[str]) -> Key:
        key_long = pickle.dumps((rq.sql, tag, *rq.parameters))
        key_hash = hashlib.sha1(key_long).hexdigest()
        return key_hash

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
                    task = asyncio.create_task(c._persist(rq, key, tag))

                    def task_done(t: 'asyncio.Task[Query]') -> None:
                        try:
                            future.set_result(t.result())
                        except Exception as e:
                            future.set_exception(e)
                    task.add_done_callback(task_done)


                result_future = self.saved[key]

            return await result_future

        return lambda: asyncio.run(wrapped_save_fn())

KL = KeyLookup() # singleton

class Cacher(ABC):

    """
    Abstract Base Class to represent a persistence/caching method.

    To define your own persistance method, you can create a concrete subclass of this.
    Your implementation only needs to define a single method, :meth:`_persist`.

    For example, you might want to write a cacher for SAP HANA - HANA has special syntax
    for temp tables, so the builtin :class:`csql.contrib.persist.TempTableCacher` won't work.

    .. code-block:: py

        class MyCoolHanaCacher(Cacher):
            def __init__(self, con):
                self.con = con
            async def _persist(self, rq: RenderedQuery, key: str, tag: Optional[str]):
                # name our temp table - arbitrary, but if we make it some stable function of `key`
                #   then we can avoid re-computing in future executions as well.
                # Additionally, we put `tag` in there too to be nice to the user, but this isn\'t
                # strictly needed.
                table_name = f'csql_cache_{tag}_{key}'
                with con.cursor() as c:
                    try:
                        c.execute(
                            f'create local temporary table #{table_name} as {rq.sql}',
                            rq.params
                        )
                    except Exception as e:
                        if 'existing table' in e: pass # hana has no 'if exists' clause
                        else: raise
                return Q(f'select * from #{table_name}')

    """

    def persist(self, q: Query, tag: Optional[str]) -> Query:
        """
        Marks a query as persistabe.
        :meta private:
        """
        return q._add_extensions(Persistable(self, tag))

    @abstractmethod
    async def _persist(self, rq: csql.RenderedQuery, key: csql.persist.Key, tag: Optional[str]) -> csql.Query:
        """
        This should take a RenderedQuery, save it (keyed by the given ``key``), and
        return a Query that returns the saved data.

        :param rq:  the :class:`csql.RenderedQuery` you need to save. Remember, ``RenderedQuery``
                    already has its SQL and parameters prepared and ready to go to a database.

        :param key: a unique ``key`` to identify the query you've been given.

        :param tag: a ``tag`` supplied by the user, e.g. if they call ``q.persist(your_cacher, 'some_tag')``.
                    If you want, you can include this in the name of your cached data, to make it easy
                    for curious users e.g. to poke around and see what query resulted in what table.

        ``key`` is a query content hash that is stable across sessions, so you can avoid re-executing expensive queries
        if the given key has already been saved in the database (e.g. ``create table if not exists my_table_{key}``).

        ``csql`` already maintains a record of ``key``-s saved in the `current` process, but this won't persist if
        the python process is restarted - however your tables potentially could, which is where using ``key`` becomes
        helpful.

        For example, you could write

        .. code-block:: py

            def _persist(self, rq, key, tag):
                table_name = f'csql_cache_{tag}_{key}'
                with self.con.cursor() as c:
                    c.execute(f'create table if not exists my_user.{table_name} as {rq.sql}', params)
                return Q(f'select * from my_user.{table_name}')

        if you were comfortable with leaving permanent tables around in your database.

        While you do need to declare your ``_persist`` implementation as `async`, you don't need to worry about
        actually writing a proper async implementation. Normal blocking database calls
        are fine.


        """
        pass


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

