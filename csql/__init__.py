from __future__ import annotations
# anything exported through here is considered public api.
# mypy: implicit-reexport
from ._.api import (
	Q,
)
from ._.models.query import (
	Query,
	Parameters,
	ParameterValue,
	ParameterPlaceholder,
	RenderedQuery,
	ParameterList as _Deprecated_ParameterList
)

from ._.models.overrides import Overrides

__all__ = [
	'Q',
	'Query',
	'Parameters',
	'ParameterValue'
	'ParameterPlaceholder',
	'RenderedQuery',
	'ParameterList'
]

import typing
def __getattr__(name: str) -> typing.Any:
	if name == 'ParameterList':
		from warnings import warn
		warn(f'ParameterList is deprecated. It\'s now just a type alias, and it will be removed from public exports in a future release.', DeprecationWarning)
		return _Deprecated_ParameterList
	raise AttributeError(f'module {__name__} has no attribute {name}.')