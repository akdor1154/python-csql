"""
``csql.contrib.render.param`` contains alterantive :class:`csql.render.param.ParameterRenderer` implementations.
"""

from csql.render.param import ParameterRenderer, SQL, AutoKey
from typing import *


class UDFParameterRenderer(ParameterRenderer):
	"""
	``UDFParameterRenderer`` renders parameters as just their key, for use
	in a UDF body.

	Example:

	>>> p = Parameters(start=date(2021,5,5))
	>>> q = Q(f'''select * from purchases where purchase_date > {p['start']}''')
	>>> q.build().sql
	'select * from purchases where purchase_date > :1'
	>>> from csql.contrib.render.param import UDFParameterRenderer
	>>> udf_overrides = csql.Overrides(paramRenderer=UDFParameterRenderer)
	>>> udf_body = q.build(overrides=udf_overrides).sql
	>>> print(udf_body)
	select * from purchases where purchase_date > start
	>>> con = some_connection()
	>>> con.cursor().execute(f'''
	...   create function my_func(date) as
	...   $$
	...   {udf_body}
	...   $$
	... ''')
	>>> #

	"""
	def _renderScalarSql(self, index: int, key: Optional[Union[str, AutoKey]]) -> SQL:
		"Override rendering to render parameters as just their key"
		if key is None:
			raise ValueError('All parameters must be named. This means collection parameters won\'t work.')
		return SQL(key if isinstance(key, str) else key.k)
