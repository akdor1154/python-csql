from typing import *
from .query import QueryBit, Query, PreBuild, ParameterPlaceholder, Parameters
import dataclasses

class PartReplacer(Protocol):
	'''
	A PartReplacer is a function that is called on each of a Query's QueryParts,
	and is expected to return a replacement Part, or the same Part unchanged. This
	means you can go changing parameters, adding sql comments, etc.
	'''
	def __call__(self, p: Union[str, QueryBit]) -> Union[str, QueryBit]: pass

class QueryReplacer(Protocol):
	'''
	A QueryReplacer is a function that is called on a single Query, and is expected
	to return a copy of the input Query that has been modiifed in some way.

	If no change is needed, it should return the input Query unchanged.

	QueryReplacers should not recurse into other queries found in queryParts - recursion
	is handled by `_replace_queries_in_tree()`, which takes a QueryReplacer as input and applies
	it recursively.
	'''
	def __call__(self, q: Query) -> Query: pass

def replace_queries_in_tree(fn: QueryReplacer, q: Query) -> Query:
	"""Replace every q in a tree with fn(q), beginning with the leaves."""
	import functools

	def replace_queries(p: Union[str, QueryBit]) -> Union[str, QueryBit]:
		if isinstance(p, Query):
			return rewrite_query(p)
		else:
			return p

	@functools.lru_cache(maxsize=None)
	def rewrite_query(q: Query) -> Query:

		new_q = _replace_query_parts(replace_queries, q)

		result = fn(new_q)

		if not isinstance(result, Query):
			raise TypeError(f'{fn} returned None! fn passed to QueryReplacer needs to always return a Query.')
		
		return result

	return rewrite_query(q)

def _replace_query_parts(fn: PartReplacer, q: Query) -> Query:
	"""Replaces every bit in q with fn(bit). If the result is the same, q is returned unchanged."""
	new_parts = tuple(fn(part) for part in q.queryParts)
	if new_parts == q.queryParts:
		return q
	else:
		return dataclasses.replace(q, queryParts=new_parts)

def params_replacer(newParams: Optional[Dict[str, Any]]) -> QueryReplacer:
	''' This builds a QueryReplacer that handles re-parameterization. '''
	if newParams is None:
		return lambda q: q

	_newParams = Parameters(**newParams) # checks if hashable.
	
	def part_replacer(p: Union[str, QueryBit]) -> Union[str, QueryBit]:
		if (isinstance(p, ParameterPlaceholder) and isinstance(p.key, str) and p.key in _newParams):
			return _newParams[p.key]
		else:
			return p

	def query_replacer(q: Query) -> Query:
		return _replace_query_parts(part_replacer, q)

	return query_replacer

def pre_build_replacer() -> QueryReplacer:
	''' This builds a QueryReplacer that handles executing pre-build hooks. '''
	def query_replacer(q: Query) -> Query:
		if (preBuild := q._get_extension(PreBuild)) is None:
			return q
		result = preBuild.hook()
		if result is None:
			return q
		elif isinstance(result, Query):
			return result
		else:
			raise Exception(f'prebuild needs to return None or a Query, it returned {repr(result)}!')
	return query_replacer