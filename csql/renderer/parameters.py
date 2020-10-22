from typing import *
from ..models.query import Parameters
from collections.abc import Collection as CollectionABC
import functools
from itertools import chain

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

#I can't decide if this should be stateful or not.
# Either this is stateful or the SQLRenderer needs to maintain special
# state to be able to handle numeric parameters.
# I will leave this stateless for now but will probably change it
# if I ever handle other parameter styles (e.g. qmark)
class NumericParameterRenderer:

	@classmethod
	def _renderCollection(Self, paramValues: Collection[ScalarParameterValue], startFrom: int) -> _RenderedNumericParameter:
		params: List[RenderedParameter] = []
		i = startFrom
		for paramValue in paramValues:
			rendered = Self._renderScalar(paramValue, i)

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

	@classmethod
	def _renderScalar(Self, paramValue: ScalarParameterValue, startFrom: int) -> _RenderedNumericParameter:
		param = RenderedParameter(
			sql=f':{startFrom}',
			values=[paramValue]
		)
		return _RenderedNumericParameter(param=param, nextStartFrom=startFrom+1)

	@classmethod
	def render(Self, paramKey: str, parameters: Parameters, state: RendererState) -> RenderedNumericParameter:
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
			(param, nextStartFrom) = Self._renderCollection(paramValue, state.nextStartFrom)
		else:
			(param, nextStartFrom) = Self._renderScalar(paramValue, state.nextStartFrom)

		return RenderedNumericParameter(
			param=param,
			nextState=RendererState(
				renderedKeys = {**state.renderedKeys, key: param},
				nextStartFrom = nextStartFrom
			)
		)

	@classmethod
	def initialState(Self) -> RendererState:
		return RendererState({}, 1)