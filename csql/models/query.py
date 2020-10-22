from typing import *
from dataclasses import dataclass
from abc import ABCMeta
from ..utils import unique
from textwrap import dedent

class RenderedQuery(NamedTuple):
	sql: str
	parameters: List[Any]

class QueryBit(metaclass=ABCMeta):
	pass

@dataclass
class Query(QueryBit):
	queryParts: List[Union[str, QueryBit]]
	parameters: "Parameters"

	def _getDeps_(self) -> Iterable["Query"]:
		queryDeps = (part for part in self.queryParts if isinstance(part, Query))
		for dep in queryDeps:
			yield from dep._getDeps_()
			yield dep

	def _getDeps(self) -> Iterable["Query"]:
		return unique(self._getDeps_(), fn=id)

	def build(self) -> RenderedQuery:
		from ..renderer.query import BoringSQLRenderer
		return BoringSQLRenderer.render(self)


@dataclass
class ParameterPlaceholder(QueryBit):
	key: str

	# MAYBE...
	def __format__(self, spec: str) -> str:
		raise Exception(dedent(f'''
			ParameterPlaceholder (key {self.key}) was directly put in an f-string.
			You need to wrap your sql in a lambda.
			Bad:
				Q(f"select blah where val = p['{self.key}'].", p)
			Good:
				Q(lambda: f"select blah where val = p['{self.key}'], p)
			Sorry!'''
		))


class Parameters:
	params: Dict[str, Any]

	def __init__(self, **kwargs: Any):
		self.params = kwargs

	def __getitem__(self, key: str) -> ParameterPlaceholder:
		paramVal = self.params[key] # check existence
		return ParameterPlaceholder(key=key)
