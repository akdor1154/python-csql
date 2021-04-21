from typing import *
from ..models.query import Parameters, ParameterList
from ..models.dialect import SQLDialect, ParamStyle
from ..utils import assert_never
from collections.abc import Collection as CollectionABC
import functools
from itertools import chain
import abc
from abc import ABC

ScalarParameterValue = Any
SQL = NewType('SQL', str)

class ParamList():
	"""This is designed to be returned and passed directly to your DB API. It acts like a list."""

	_params: List[ScalarParameterValue]

	def __init__(self) -> None:
		self._params = []

	def add(self, param: ScalarParameterValue) -> int:
		self._params.append(param)
		return len(self._params)-1

	def render(self) -> ParameterList:
		return ParameterList(*self._params)

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

	def _renderScalar(self, paramValue: ScalarParameterValue) -> SQL:
		index = self.renderedParams.add(paramValue)
		return self._renderScalarSql(index)

	def _renderCollection(self, paramValues: Collection[ScalarParameterValue]) -> SQL:
		_params = [
			self._renderScalar(paramValue)
			for paramValue in paramValues
		]

		return SQL(f'( {",".join(_params)} )')

	def render(self, paramKey: str, parameters: Parameters) -> SQL:
		paramValue = parameters.params[paramKey]
		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			param = self._renderCollection(paramValue)
		else:
			param = self._renderScalar(paramValue)
		return param


class QMark(ParameterRenderer):

	def _renderScalarSql(self, paramIndex: int) -> SQL:
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
