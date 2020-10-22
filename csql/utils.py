from typing import *


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