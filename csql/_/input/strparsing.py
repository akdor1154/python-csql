from __future__ import annotations

import contextvars
import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar, cast
from weakref import WeakValueDictionary

if TYPE_CHECKING:
	from typing_extensions import Self

	from ..models.query import QueryBit


class InstanceTracking:
	instances: ClassVar[WeakValueDictionary[int, InstanceTracking]] = (
		WeakValueDictionary()
	)

	# we need to keep some strong refs around for the case where
	# someone does an fstring with an immediate value:
	# Q("asdf{Q('fdsa')}")
	# -> Q( "asdf" + str(Q('fsda')) )
	# -> Q( "asdf" + "<querybit:1234>") < - at this point there are no references to Q('fdsa') so it is GC'd
	# -> Q( "asdf<querybut:1234" )
	# -> ["asdf", instances[1234]] <- bang, 1234 does not exist, it's been GC'd
	formattedInstances: ClassVar[dict[int, InstanceTracking]] = {}

	def __post_init__(self) -> None:
		InstanceTracking.instances[hash(self)] = self

	def _withFmt(self, fmt: str) -> Self:
		return self

	def __format__(self, fmt: str) -> str:

		newSelf = self._withFmt(fmt)
		newSelf._hold()
		return f"〈QueryBit:{hash(newSelf)}〉"

	def _hold(self) -> None:
		InstanceTracking.formattedInstances[hash(self)] = self

	def _unhold(self) -> None:
		if hash(self) in InstanceTracking.formattedInstances:
			del InstanceTracking.formattedInstances[hash(self)]


# bunch of nonsense to make the instance tracking work even if this module is reloaded -
# it's common for csql to be used in python notebooks with ipython's autoreload extension.
for var, val in contextvars.copy_context().items():
	if var.name == "_csql_instance_tracking":
		PersistIT, prev = var, val
		break
else:
	PersistIT, prev = (
		contextvars.ContextVar[type[InstanceTracking]]("_csql_instance_tracking"),
		None,
	)
if prev is not None:
	print(f"copying from previous: {prev.instances=}")
	InstanceTracking.instances = prev.instances
	InstanceTracking.formattedInstances = prev.formattedInstances
PersistIT.set(InstanceTracking)

# problem:
# intermediate values are GCd before they can be recalled
# Q("asdf{Q('fdsa')}")
# -> Q( "asdf" + str(Q('fsda')) )
# -> Q( "asdf" + "<querybit:1234>") < - at this point there are no references to Q('fdsa') so it is GC'd
# -> Q( "asdf<querybut:1234" )
# -> ["asdf", instances[1234]] <- bang, 1234 does not exist, it's been GC'd

# solutions:
# - preserve a ref - how?? may not be possible or pleasant
# - use a real dict to preserve a ref
# -


regex = re.compile(r"〈QueryBit:(-?\d+)〉")


def _parseInterpolatedString(s: str) -> Iterable[str | QueryBit]:
	matches = regex.finditer(s)
	i = 0  # end of last processed match
	for match in matches:
		matchStart = match.start()
		matchEnd = match.end()

		idStr = match[1]
		queryBit = InstanceTracking.instances[int(idStr)]
		queryBit._unhold()

		yield s[i:matchStart]
		yield cast("QueryBit", queryBit)
		i = matchEnd

	yield s[i:]


def getQueryParts(s: str) -> tuple[str | QueryBit, ...]:
	return tuple(bit for bit in _parseInterpolatedString(s) if bit != "")
