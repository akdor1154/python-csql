from typing import *
from ..renderer.parameters import ParameterRenderer
from ..renderer.query import QueryRenderer
from dataclasses import dataclass

@dataclass(frozen=True)
class Overrides:
    paramRenderer: Optional[Type[ParameterRenderer]] = None
    queryRenderer: Optional[Type[QueryRenderer]] = None
