import functools
from typing import TYPE_CHECKING
from ..models.query import PreBuild, Query, QueryBit, QueryExtension, QueryReplacer, RenderedQuery
from ..renderer.query import QueryRenderer
from csql import Q
from abc import ABC, abstractmethod
from functools import cache, partial
from typing import *
import logging

logger = logging.getLogger(name=__name__)

@QueryExtension.register
class Persistable(NamedTuple):
    """ Attached directly to a slow query. """
    cacher: 'Cacher'

def  _cache_replacer(queryRenderer: QueryRenderer) -> QueryReplacer:
    def replacer(q: Query) -> Query:
        if (p := q._get_extension(Persistable)) is None:
            return q
    
        # q is persistable.
        save_fn, retrieve_q = p.cacher._persist(q, queryRenderer)
        retrieve_q.extensions.add(PreBuild(save_fn))
        return retrieve_q
    return replacer

class Cacher(ABC):

    def persist(self, q: Query) -> Query:
        """ Marks a query as persistabe. """
        q.extensions.add(Persistable(self))
        return q

    @abstractmethod
    def _persist(self, q: Query, qr: QueryRenderer) -> Tuple[Callable[[], None], Callable[[], Query]]:
        """ Returns a function which will save the query, and a function which returns a query that will retrieve the saved one. """
        pass


class TempTableCacher(Cacher):
    def __init__(self, connection: Any):
        self._con = connection
        self._saved: Set[int] = set()

    def _get_key(self, q: Query, qr: QueryRenderer) -> Tuple[RenderedQuery, int]:
        rq = qr.render(q)
        return rq, hash((rq.sql, *rq.parameters))
    
    def do_once(self, key):
        def decorator(fn):
            @functools.wraps(fn)
            def wrapped(*args, **kwargs):
                if key in self._saved:
                    return
                r = fn(*args, **kwargs)
                self._saved.add(key)
                return r
            return wrapped
        return decorator


    def _persist(self, q: Query, qr: QueryRenderer) -> Tuple[Callable[[], None], Callable[[], Query]]:

        (sql, params), key = self._get_key(q, qr)

        table_name = f'"csql_cache_{key}"'

        create_sql = RenderedQuery(
            sql=f'''
            create temporary table if not exists {table_name}
            as
            {sql}
            ''',
            parameters=params
        )

        retrieve_sql = Q(f'''select * from {table_name}''') # maybe copy overrides and stuff?

        @self.do_once(key)
        def save_fn() -> None:
            logger.debug(f'Executing persist SQL:\n{create_sql.sql}\nwith params: {create_sql.parameters}')
            c = self._con.cursor()
            try:
                c.execute(*create_sql.db)
            finally:
                c.close()

        def retrieve_fn():
            assert key in self._saved, 'Has not been saved yet!'
            return retrieve_sql

        return (save_fn, lambda: retrieve_sql)
        
        # return (create_sql, retrieve_sql)

