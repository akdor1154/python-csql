from typing import TYPE_CHECKING
from ..models.query import Query, QueryBit
#from ..models.persisted_query import PersistedQuery
from csql import Q
from abc import ABC, abstractmethod
from functools import cache
from typing import *

class ProcessResult(NamedTuple):
    save_sql: Tuple[str, List[Any]]
    processed_query: Query

class Cacher(ABC):

    def persist(self, q: Query) -> Query:
        retrieve_q = self._persist(q)
        return PersistedQuery(
            q,
            self
        )

    @abstractmethod
    def _persist(self, q: Query):
        pass

    @abstractmethod
    def maybe_cache_part(q: Query) -> Optional[Tuple[str, Query]]:
        # check if this specific query should be persisted.
        pass


    def process(self, q: Query) -> Query:
        """ Called just before a query is rendered. """

        # probably needs to do sql stuff as well.

        # this cache is not to do with the caching process.
        # this one is just to make sure we only process
        # each Q in the dep tree once.
        
        # first, go through deps and find the ones we want to persist
        done: Dict[int, Query] = {}
        def preprocess_deps():
            for d in list(q._getDeps()):
                key = id(d)
                processed = self.maybe_cache_part(d)
                if processed is not None:
                    sql, new_q = processed
                    yield sql
                    done[key] = new_q
                else:
                    done[key] = q
        pre_sql = list(preprocess_deps())

        @cache
        def rewrite_query(q: Query) -> Query:
            def get_parts():
                for part in q.queryParts:
                    if isinstance(part, Query):
                        processed = done[id(part)]
                        yield rewrite_query(processed)
                    else:
                        yield part
            return Query(
                queryParts=list(get_parts()),
                default_dialect=q.default_dialect,
                default_overrides=q.default_overrides
            )

        return pre_sql, rewrite_query(q)



class TempTableCacher(Cacher):
    def __init__(self, connection):
        self.con = connection

    def _get_key(q: Query):
        sql, params = q.build()
        return sql, params, hash(sql, *params)


    def _persist(self, q: Query):

        sql, params, key = self._get_key(q)

        table_name = f'csql_cache_{key}'

        create_sql = (
            f'''
            create temporary table {table_name} if not exists
            as
            {sql}
            ''',
            params
        )

        retrieve_sql = Q(f'''select * from {table_name}''')

        self.con.cursor().insuert...
        
        # return (create_sql, retrieve_sql)




top = Q('select something heavy').persist()

bottom = Q('select * from {top}')

preview(bottom)