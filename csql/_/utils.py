from typing import *
from typing import NoReturn # py 3.6
if TYPE_CHECKING:
	from .models.dialect import SQLDialect, Limit
	from .models.query import Query

#https://stackoverflow.com/a/34073559/5264127
T = TypeVar('T')
R = TypeVar('R')
class Collector(Generic[T, R]):
	returned: R
	def __init__(self, generator: Generator[T, None, R]):
		self.generator = generator
	def __iter__(self) -> Iterator[T]:
		self.returned = yield from self.generator


def unique(gen: Iterable[T], fn:Callable[[T], Any] = hash) -> Iterable[T]:
	seen = set()
	for val in gen:
		if fn(val) in seen:
			continue
		yield val
		seen.add(fn(val))

def assert_never(x: NoReturn) -> NoReturn:
	assert False, f'Unhandled type: {type(x).__name__}'

def limit_query(query: 'Query', rows: int, dialect: 'SQLDialect') -> 'Query':
	from .api import Q
	from .models.dialect import Limit
	if dialect.limit is Limit.limit:
		return Q(f"select * from {query} limit {rows}")
	elif dialect.limit is Limit.top_n:
		return Q(f"select top({rows}) * from {query}")
	elif dialect.limit is Limit.ansi:
		return Q(f"select * from {query} fetch first {rows} rows only")
	else:
		assert_never(dialect.limit)