from typing import *
from ..models.query import Parameters, ParameterList
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

class ParamList():
	"""This is designed to be returned and passed directly to your DB API. It acts like a list."""

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
	def _renderScalarSql(self, index: int) -> SQL:
		pass

	def _renderScalar(self, paramValue: ScalarParameterValue) -> Tuple[int, SQL]:
		index = self.renderedParams.add(paramValue)
		return (index, self._renderScalarSql(index))

	def _renderCollection(self, paramValues: Collection[ScalarParameterValue]) -> Tuple[List[int], SQL]:
		_params = [
			self._renderScalar(paramValue)
			for paramValue in paramValues
		]
		indices = [i for i, sql in _params]
		sql = [sql for i, sql in _params]

		return (indices, SQL(f'( {",".join(sql)} )'))

	def render(self, paramKey: str, parameters: Parameters) -> SQL:
		paramValue = parameters.params[paramKey]
		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			indices, param = self._renderCollection(paramValue)
		else:
			index, param = self._renderScalar(paramValue)
			indices = [index]
		self.renderedParams.registerKey(paramKey, indices)
		return param


class QMark(ParameterRenderer):

	def _renderScalarSql(self, index: int) -> SQL:
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

	def _renderScalarSql(self, index: int) -> SQL:
		return self._renderIndex(index + self.paramNumberFrom)

	def render(self, paramKey: str, parameters: Parameters) -> SQL:
		key = id(parameters) ^ hash(paramKey)

		if key in self.renderedKeys:
			preRendered = self.renderedKeys[key]
			return preRendered
		else:
			param = super().render(paramKey, parameters)
			self.renderedKeys = {**self.renderedKeys, key: param}
			return param


class ColonNumeric(NumericParameterRenderer):
	def _renderIndex(self, index: int) -> SQL:
		return SQL(f':{index}')

class DollarNumeric(NumericParameterRenderer):
	def _renderIndex(self, index: int) -> SQL:
		return SQL(f'${index}')