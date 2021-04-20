from typing import *
from ..models.query import Parameters
from ..models.dialect import SQLDialect, ParamStyle
from ..utils import assert_never
from collections.abc import Collection as CollectionABC
import functools
from itertools import chain
import abc
from abc import ABC

ScalarParameterValue = Any
class RenderedParameter(NamedTuple):
	sql: str
	values: List[ScalarParameterValue]

class ParameterRenderer(ABC):
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

	@abc.abstractmethod
	def _renderScalar(self, paramValue: ScalarParameterValue) -> RenderedParameter:
		pass

	def _renderCollection(self, paramValues: Collection[ScalarParameterValue]) -> RenderedParameter:
		_params = [
			self._renderScalar(paramValue)
			for paramValue in paramValues
		]

		return RenderedParameter(
			sql=f'( {",".join(p.sql for p in _params)} )',
			values=[
				value
				for param in _params
				for value in param.values
			]
		)

	def render(self, paramKey: str, parameters: Parameters) -> RenderedParameter:
		paramValue = parameters.params[paramKey]
		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			param = self._renderCollection(paramValue)
		else:
			param = self._renderScalar(paramValue)
		return param


class QMark(ParameterRenderer):

	def _renderScalar(self, paramValue: ScalarParameterValue) -> RenderedParameter:
		return RenderedParameter(
			sql='?',
			values=[paramValue]
		)

class NumericParameterRenderer(ParameterRenderer, ABC):

	class GimmeAnIndex:
		_i: int
		def __init__(self, start: int):
			self._i = start
		def take(self) -> int:
			i = self._i
			self._i += 1
			return i

	renderedKeys: Dict[int, RenderedParameter]
	indexGranter: GimmeAnIndex

	def __init__(self) -> None:
		self.renderedKeys = {}
		self.indexGranter = NumericParameterRenderer.GimmeAnIndex(1)

	def _renderCollection(self, paramValues: Collection[ScalarParameterValue]) -> RenderedParameter:
		_params = [
			self._renderScalar(paramValue)
			for paramValue in paramValues
		]

		return RenderedParameter(
			sql=f'( {",".join(p.sql for p in _params)} )',
			values=[
				value
				for param in _params
				for value in param.values
			]
		)

	@abc.abstractmethod
	def _renderSql(self, paramIndex: int) -> str:
		pass

	def _renderScalar(self, paramValue: ScalarParameterValue) -> RenderedParameter:
		paramIndex = self.indexGranter.take()

		return RenderedParameter(
			sql=self._renderSql(paramIndex),
			values=[paramValue]
		)
		return

	def render(self, paramKey: str, parameters: Parameters) -> RenderedParameter:
		key = id(parameters) ^ hash(paramKey)

		if key in self.renderedKeys:
			preRendered = self.renderedKeys[key]
			return RenderedParameter(
				sql=preRendered.sql,
				values=[]
			)
		else:
			param = super().render(paramKey, parameters)
			self.renderedKeys = {**self.renderedKeys, key: param}
			return param


class ColonNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f':{startFrom}'

class DollarNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f'${startFrom}'
