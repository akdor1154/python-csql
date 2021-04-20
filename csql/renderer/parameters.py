from typing import *
from ..models.query import Parameters
from ..models.dialect import SQLDialect, ParamStyle
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
	@abc.abstractmethod
	def render(self, paramKey: str, parameters: Parameters) -> RenderedParameter:
		pass

	@staticmethod
	def get(dialect: SQLDialect) -> Type['ParameterRenderer']:
		if dialect.paramstyle == ParamStyle.numeric:
			return ColonNumeric
		elif dialect.paramstyle == ParamStyle.numeric_dollar:
			return DollarNumeric
		else:
			raise NotImplementedError(f'unknown paramstyle {dialect.paramstyle}')

#I can't decide if this should be stateful or not.
# Either this is stateful or the SQLRenderer needs to maintain special
# state to be able to handle numeric parameters.
# I will leave this stateless for now but will probably change it
# if I ever handle other parameter styles (e.g. qmark)
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
		paramValue = parameters.params[paramKey]

		key = id(parameters) ^ hash(paramKey)

		if key in self.renderedKeys:
			preRendered = self.renderedKeys[key]
			return RenderedParameter(
				sql=preRendered.sql,
				values=[]
			)

		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			param = self._renderCollection(paramValue)
		else:
			param = self._renderScalar(paramValue)

		self.renderedKeys = {**self.renderedKeys, key: param}

		return param


class ColonNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f':{startFrom}'

class DollarNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f'${startFrom}'
