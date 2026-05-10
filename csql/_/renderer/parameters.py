from __future__ import annotations

import abc
import zoneinfo
from abc import ABC
from collections.abc import Collection
from collections.abc import Collection as CollectionABC
from datetime import date, datetime
from typing import (
	TYPE_CHECKING,
	NewType,
)

from ..models.dialect import ParamStyle, SQLDialect
from ..models.query import (
	AutoKey,
	ParameterList,
	ParameterPlaceholder,
	ScalarParameterValue,
)
from ..utils import assert_never

SQL = NewType("SQL", str)

if TYPE_CHECKING:
	import csql.render.param


class ParamList:
	_params: list[ScalarParameterValue]
	_param_names: list[str | None]

	def __init__(self) -> None:
		self._params = []
		self._param_names = []

	def add(
		self, param: ScalarParameterValue, name: AutoKey | str | None, fmt: str = ""
	) -> int:
		self._params.append(param)
		self._param_names.append(name if isinstance(name, str) else None)
		return len(self._params) - 1

	def render(self) -> tuple[ParameterList, tuple[str | None, ...]]:
		return tuple(self._params), tuple(self._param_names)


class ParameterRenderer(ABC):
	"""
	This is a base class to define how SQL parameters are rendered.

	A new ``ParameterRenderer`` is created each time a :class:`csql.Query`
	is built, and :meth:`_renderScalarSql` is called once for each
	parameter that needs to be placed into full :class:`csql.RenderedQuery`. These are called in
	the order the parameters appear in the rendered query.
	"""

	renderedParams: ParamList
	":meta private:"

	@staticmethod
	def get(dialect: SQLDialect) -> type[ParameterRenderer]:
		if dialect.paramstyle is ParamStyle.numeric:
			return ColonNumeric
		elif dialect.paramstyle is ParamStyle.numeric_dollar:
			return DollarNumeric
		elif dialect.paramstyle is ParamStyle.qmark:
			return QMark
		elif dialect.paramstyle is ParamStyle.clickhouse:
			return Clickhouse
		else:
			assert_never(dialect.paramstyle)

	def __init__(self) -> None:
		self.renderedParams = ParamList()

	@abc.abstractmethod
	def _renderScalarSql(
		self, index: int, key: AutoKey | str | None, fmt: str
	) -> csql.render.param.SQL:
		"""
		This is called once for each parameter that needs to be rendered
		into a :class:`csql.RenderedQuery`. Implementations might be simple:
		for example, the builtin :class:`csql.render.param.QMark` renderer just
		defines

		.. code-block:: py

		        def _renderScalarSql(self, index, key):
		                return SQL('?')

		:param index: - the index of the current parameter in the rendered query. Numbered from 0.
		:param key: - the (possibly missing) name of the current parameter.
		:param fmt: - the format spec passed at f-string time, e.g. `f"select {p["param"]:spec}"`.
		"""

	def _renderScalar(
		self, paramKey: AutoKey | str | None, paramValue: ScalarParameterValue, fmt: str
	) -> tuple[int, SQL]:
		index = self.renderedParams.add(paramValue, paramKey, fmt)
		return (index, self._renderScalarSql(index, paramKey, fmt))

	def _renderCollection(
		self,
		paramKey: AutoKey | str,
		paramValues: Collection[ScalarParameterValue],
	) -> tuple[list[int], SQL]:
		_params = [
			self._renderScalar(None, paramValue, "") for paramValue in paramValues
		]
		indices = [i for i, _sql in _params]
		sql = [sql for _i, sql in _params]

		return (indices, SQL(f"( {','.join(sql)} )"))

	def renderList(self) -> tuple[ParameterList, tuple[str | None, ...]]:
		return self.renderedParams.render()

	def render(self, param: ParameterPlaceholder) -> SQL:
		paramKey = param.key
		paramValue = param.value
		fmt = param.fmt
		if isinstance(paramValue, CollectionABC) and not isinstance(paramValue, str):
			_indices, sql = self._renderCollection(paramKey, paramValue)  # pyright: ignore[reportUnknownArgumentType]
		else:
			index, sql = self._renderScalar(paramKey, paramValue, fmt)
			_indices = [index]
		return sql


class QMark(ParameterRenderer):
	"""
	A ``ParameterRenderer`` that renders param placeholders as '?'.
	"""

	def _renderScalarSql(self, index: int, key: str | AutoKey | None, fmt: str) -> SQL:
		return SQL("?")


class NumericParameterRenderer(ParameterRenderer, ABC):
	renderedKeys: dict[int, SQL]
	paramNumberFrom: int

	def __init__(self) -> None:
		super().__init__()
		self.renderedKeys = {}
		self.paramNumberFrom = 1

	@abc.abstractmethod
	def _renderIndex(self, index: int) -> SQL:
		pass

	def _renderScalarSql(self, index: int, key: str | AutoKey | None, fmt: str) -> SQL:
		return self._renderIndex(index + self.paramNumberFrom)

	def render(self, param: ParameterPlaceholder) -> SQL:
		# should be able to hash(AutoKey) directly, but I was hitting a flakey test
		key = (param._key_context or 0) ^ hash(
			param.key if isinstance(param.key, str) else param.key.k
		)

		if key in self.renderedKeys:
			preRendered = self.renderedKeys[key]
			return preRendered
		else:
			sql = super().render(param)
			self.renderedKeys = {**self.renderedKeys, key: sql}
			return sql


class ColonNumeric(NumericParameterRenderer):
	"""
	A ``ParameterRenderer`` that renders param placeholders like ':1'.
	"""

	def _renderIndex(self, index: int) -> SQL:
		return SQL(f":{index}")


class DollarNumeric(NumericParameterRenderer):
	"""
	A ``ParameterRenderer`` that renders param placeholders like '$1'.
	"""

	def _renderIndex(self, index: int) -> SQL:
		return SQL(f"${index}")


class Clickhouse(ParameterRenderer):
	def _renderScalarSql(self, index: int, key: AutoKey | str | None, fmt: str) -> SQL:
		if key is None:
			raise ValueError("clickhouse params don't work if key is None!")
		return SQL(f"{{{key.k if isinstance(key, AutoKey) else key}:{fmt}}}")

	def render(self, param: ParameterPlaceholder) -> SQL:
		if (fmt := param.fmt) == "":
			if isinstance(param.value, str):
				fmt = "String"
			elif isinstance(param.value, int):
				fmt = "Int64"
			elif isinstance(param.value, datetime):
				tz = param.value.tzinfo
				if tz is not None and isinstance(tz, zoneinfo.ZoneInfo):
					# 3 is default precision in clickhouse.. sometimes.
					fmt = f"DateTime64(3, '{tz.key}')"
				else:
					fmt = "DateTime64"
			elif isinstance(param.value, date):
				fmt = "Date"
			elif isinstance(param.value, float):
				fmt = "Float64"
		newParam = param._withFmt(fmt)
		return super().render(newParam)
