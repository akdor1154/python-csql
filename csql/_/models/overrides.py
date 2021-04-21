from typing import *
from ..renderer.parameters import ParameterRenderer
from ..renderer.query import SQLRenderer
from dataclasses import dataclass

@dataclass
class Overrides:
    paramRenderer: Optional[Type[ParameterRenderer]] = None
    queryRenderer: Optional[Type[SQLRenderer]] = None
