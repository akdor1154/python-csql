from __future__ import annotations

from dataclasses import dataclass
from typing import *

if TYPE_CHECKING:
	import csql
	import csql.render.param
	import csql.render.query


@dataclass(frozen=True)
class Overrides:
	paramRenderer: Optional[Type[csql.render.param.ParameterRenderer]] = None
	queryRenderer: Optional[Type[csql.render.query.QueryRenderer]] = None


import dataclasses


@dataclasses.dataclass(frozen=True)
class InferOrDefault:
	overrides: Optional[csql.overrides.Overrides]
