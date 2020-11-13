import re
from weakref import WeakValueDictionary
from typing import *
import re

if TYPE_CHECKING:
	from ..models.query import QueryBit


class InstanceTracking():

	instances: "WeakValueDictionary[int, InstanceTracking]" = WeakValueDictionary()

	# we need to keep some strong refs around for the case where
	# someone does an fstring with an immediate value:
	# Q("asdf{Q('fdsa')}")
	# -> Q( "asdf" + str(Q('fsda')) )
	# -> Q( "asdf" + "<querybit:1234>") < - at this point there are no references to Q('fdsa') so it is GC'd
	# -> Q( "asdf<querybut:1234" )
	# -> ["asdf", instances[1234]] <- bang, 1234 does not exist, it's been GC'd
	formattedInstances: Dict[int, "InstanceTracking"] = dict()

	def __post_init__(self) -> None:
		InstanceTracking.instances[id(self)] = self

	def __format__(self, spec: str) -> str:
		self._hold()
		return f'〈QueryBit:{id(self)}〉'

	def _hold(self) -> None:
		InstanceTracking.formattedInstances[id(self)] = self

	def _unhold(self) -> None:
		if id(self) in InstanceTracking.formattedInstances:
			del InstanceTracking.formattedInstances[id(self)]

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


regex = re.compile(r'〈QueryBit:(\d+)〉')
def _parseInterpolatedString(s: str) -> Iterable[Union[str, "QueryBit"]]:
	matches = regex.finditer(s)
	i = 0 # end of last processed match
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

def getQueryParts(s: str) -> List[Union[str, "QueryBit"]]:
	return [
		bit
		for bit in _parseInterpolatedString(s)
		if bit != ""
	]
