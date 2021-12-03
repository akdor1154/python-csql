from abc import ABCMeta
from dataclasses import dataclass
from .query import QueryLike, Query, InstanceTracking, RenderedQuery, SQLDialect, ScalarParameterValue
from typing import *

if TYPE_CHECKING:
	from ..cacher.cacher import Cacher
	from .overrides import Overrides

@dataclass
class PersistableQuery(Query, InstanceTracking):
	cacher: Cacher
