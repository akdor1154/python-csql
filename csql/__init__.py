from __future__ import annotations

# anything exported through here is considered public api.
# mypy: implicit-reexport
from ._.api import (
	Q,
)
from ._.models.query import (
	ParameterList as _Deprecated_ParameterList,
)
from ._.models.query import (
	ParameterPlaceholder,
	Parameters,
	ParameterValue,
	Query,
	QueryBit,
	RenderedQuery,
)
from .overrides import Overrides as _Deprecated_Overrides

__all__ = [
	"ParameterPlaceholder",
	"ParameterValue",
	"Parameters",
	"Parameters",
	"Q",
	"Query",
	"QueryBit",
	"RenderedQuery",
]

import typing


def __getattr__(name: str) -> typing.Any:
	if name == "ParameterList":
		from warnings import warn

		warn(
			"ParameterList is deprecated. It's now just a type alias, and it will be removed from public exports in a future release.",
			DeprecationWarning,
			stacklevel=2,
		)
		return _Deprecated_ParameterList
	elif name == "Overrides":
		from warnings import warn

		warn(
			"csql.Overrides has moved to csql.overrides.Overrides. Please import from there, it will be enforced in a later release.",
			DeprecationWarning,
			stacklevel=2,
		)
		return _Deprecated_Overrides
	raise AttributeError(f"module {__name__} has no attribute {name}.")
