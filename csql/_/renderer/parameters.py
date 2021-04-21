from typing import *
from ..models.query import Parameters, ParameterList, ParameterPlaceholder
from ..models.dialect import SQLDialect, ParamStyle
from ..utils import assert_never
from collections.abc import Collection as CollectionABC
import functools
from itertools import chain
import abc
import collections
from abc import ABC

ScalarParameterValue = Any
SQL = NewType('SQL', str)

class ParamList:
	_params: List[ScalarParameterValue]
	_keys: Dict[str, List[List[int]]]
		# key: [
		# 	[1,2,3], # first time it was used
		# 	[5,6,7], # second time
		# 	...
		# ]

	def __init__(self) -> None:
		self._params = []
		self._keys = collections.defaultdict(list)

	def add(self, param: ScalarParameterValue) -> int:
		self._params.append(param)
		return len(self._params)-1

	def registerKey(self, key: str, indices: List[int]) -> None:
		self._keys[key].append(indices)

	def render(self) -> ParameterList:
		return ParameterList(*self._params, keys=dict(self._keys))

class ParameterRenderer(ABC):

	renderedParams: ParamList

	@staticmethod
	def get(dialect: SQLDialect) -> Type['ParameterRenderer']:
		if dialect.paramstyle is ParamStyle.numeric:
			return ColonNumeric
		elif dialect.paramstyle is ParamStyle.numeric_dollar:
			return DollarNumeric
		elif dialect.paramstyle is ParamStyle.qmark:
			return QMark
		else:
			assert_never(dialect.paramstyle)

	def __init__(self) -> None:
		self.renderedParams = ParamList()

	@abc.abstractmethod
	def _renderScalarSql(self, index: int, key: Optional[str]) -> SQL:
		pass

	def _renderScalar(self, paramKey: Optional[str], paramValue: ScalarParameterValue) -> Tuple[int, SQL]:
		index = self.renderedParams.add(paramValue)
		return (index, self._renderScalarSql(index, paramKey))

	def _renderCollection(self, paramKey: str, paramValues: Collection[ScalarParameterValue]) -> Tuple[List[int], SQL]:
		_params = [
			self._renderScalar(None, paramValue)
			for paramValue in paramValues
		]
		indices = [i for i, sql in _params]
		sql = [sql for i, sql in _params]

		return (indices, SQL(f'( {",".join(sql)} )'))

	def renderList(self) -> ParameterList:
		return self.renderedParams.render()

	def render(self, param: ParameterPlaceholder) -> SQL:
		paramKey = param.key
		paramValue = param.value
		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			indices, sql = self._renderCollection(paramKey, paramValue)
		else:
			index, sql = self._renderScalar(paramKey, paramValue)
			indices = [index]
		self.renderedParams.registerKey(paramKey, indices)
		return sql


class QMark(ParameterRenderer):

	def _renderScalarSql(self, index: int, key: Optional[str]) -> SQL:
		return SQL('?')

class NumericParameterRenderer(ParameterRenderer, ABC):

	renderedKeys: Dict[int, SQL]
	paramNumberFrom: int

	def __init__(self) -> None:
		super().__init__()
		self.renderedKeys = {}
		self.paramNumberFrom = 1

	@abc.abstractmethod
	def _renderIndex(self, index: int) -> SQL:
		pass

	def _renderScalarSql(self, index: int, key: Optional[str]) -> SQL:
		return self._renderIndex(index + self.paramNumberFrom)

	def render(self, param: ParameterPlaceholder) -> SQL:
		key = id(param.parameters) ^ hash(param.key)

		if key in self.renderedKeys:
			preRendered = self.renderedKeys[key]
			return preRendered
		else:
			sql = super().render(param)
			self.renderedKeys = {**self.renderedKeys, key: sql}
			return sql


class ColonNumeric(NumericParameterRenderer):
	def _renderIndex(self, index: int) -> SQL:
		return SQL(f':{index}')

class DollarNumeric(NumericParameterRenderer):
	def _renderIndex(self, index: int) -> SQL:
		return SQL(f'${index}')
