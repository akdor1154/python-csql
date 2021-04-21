from csql.render.param import ParameterRenderer, SQL
from typing import *


class UDFParameterRenderer(ParameterRenderer):
	def _renderScalarSql(self, index: int, key: Optional[str]) -> SQL:
		"Override rendering to render parameters as just their key"
		if key is None:
			raise ValueError('All parameters must be named. This means collection parameters won\'t work.')
		return SQL(key)
