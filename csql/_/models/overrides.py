from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	import csql
	import csql.render.param
	import csql.render.query


@dataclass(frozen=True)
class Overrides:
	paramRenderer: type[csql.render.param.ParameterRenderer] | None = None
	queryRenderer: type[csql.render.query.QueryRenderer] | None = None


import dataclasses


@dataclasses.dataclass(frozen=True)
class InferOrDefault:
	overrides: csql.overrides.Overrides | None
