"""
``csql.contrib.render.param`` contains alterantive :class:`csql.render.param.ParameterRenderer` implementations.
"""

from csql.render.param import ParameterRenderer, SQL
from typing import *


class UDFParameterRenderer(ParameterRenderer):
	"""
	``UDFParameterRenderer`` renders parameters as just their key, for use
	in a UDF body.

	Example:

	>>> p = Parameters(start=date(2021,5,5))
	>>> q = Q(f'select * from purchases where purchase_date > {p['date']})
	>>> q.build().sql
	select * from purchases where purchase_date > :1
	>>> udf_body = Overrides(paramRenderer=UDFParameterRenderer)
	>>> udf_body = q.build(overrides=udf_body).sql
	>>> udf_body
	select * from purchases where purchase_date > date
	>>> con.cursor().execute(f'''
	...   create or replace function my_func(date) as
	...   $$
	...   {udf_body}
	...   $$
	... ''')

	"""
	def _renderScalarSql(self, index: int, key: Optional[str]) -> SQL:
		"Override rendering to render parameters as just their key"
		if key is None:
			raise ValueError('All parameters must be named. This means collection parameters won\'t work.')
		return SQL(key)
