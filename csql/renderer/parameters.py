from typing import *
from ..models.query import Parameters
from collections.abc import Collection as CollectionABC
import functools
from itertools import chain
import abc
from abc import ABC

ScalarParameterValue = Any
class RenderedParameter(NamedTuple):
	sql: str
	values: List[ScalarParameterValue]

# internal state
class _RenderedNumericParameter(NamedTuple):
	param: RenderedParameter
	nextStartFrom: int

class RendererState(NamedTuple):
	renderedKeys: Dict[int, RenderedParameter]
	nextStartFrom: int

class RenderedNumericParameter(NamedTuple):
	param: RenderedParameter
	nextState: RendererState


class ParameterRenderer(ABC):
	@abc.abstractmethod
	def render(self, paramKey: str, parameters: Parameters, state: RendererState) -> RenderedNumericParameter:
		pass

	@abc.abstractmethod
	def initialState(self) -> RendererState:
		pass

#I can't decide if this should be stateful or not.
# Either this is stateful or the SQLRenderer needs to maintain special
# state to be able to handle numeric parameters.
# I will leave this stateless for now but will probably change it
# if I ever handle other parameter styles (e.g. qmark)
class NumericParameterRenderer(ParameterRenderer, ABC):

	def _renderCollection(self, paramValues: Collection[ScalarParameterValue], startFrom: int) -> _RenderedNumericParameter:
		params: List[RenderedParameter] = []
		i = startFrom
		for paramValue in paramValues:
			rendered = self._renderScalar(paramValue, i)

			params.append(rendered.param)
			i = rendered.nextStartFrom

		return _RenderedNumericParameter(
			param=RenderedParameter(
				sql=f'( {",".join(p.sql for p in params)} )',
				values=[
					value
					for param in params
					for value in param.values
				]
			),
			nextStartFrom = i
		)

	@abc.abstractmethod
	def _renderSql(Self, startFrom: int) -> str:
		pass

	def _renderScalar(self, paramValue: ScalarParameterValue, startFrom: int) -> _RenderedNumericParameter:
		param = RenderedParameter(
			sql=self._renderSql(startFrom),
			values=[paramValue]
		)
		return _RenderedNumericParameter(param=param, nextStartFrom=startFrom+1)

	def render(self, paramKey: str, parameters: Parameters, state: RendererState) -> RenderedNumericParameter:
		paramValue = parameters.params[paramKey]

		key = id(parameters) ^ hash(paramKey)

		if key in state.renderedKeys:
			preRendered = state.renderedKeys[key]
			return RenderedNumericParameter(
				param=RenderedParameter(
					sql=preRendered.sql,
					values=[]
				),
				nextState=state
			)

		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			(param, nextStartFrom) = self._renderCollection(paramValue, state.nextStartFrom)
		else:
			(param, nextStartFrom) = self._renderScalar(paramValue, state.nextStartFrom)

		return RenderedNumericParameter(
			param=param,
			nextState=RendererState(
				renderedKeys = {**state.renderedKeys, key: param},
				nextStartFrom = nextStartFrom
			)
		)

	def initialState(self) -> RendererState:
		return RendererState({}, 1)

class ColonNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f':{startFrom}'

class DollarNumeric(NumericParameterRenderer):
	def _renderSql(Self, startFrom: int) -> str:
		return f'${startFrom}'
