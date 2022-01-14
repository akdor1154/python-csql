Controlling SQL Output
**********************

.. _sql-dialects:

SQL Dialects
============

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: <!-- (sql-dialects)= -->
   :end-before: <!-- (end-sql-dialects)= -->


``csql.dialect``
=================

.. automodule:: csql.dialect
   :imported-members:
   :exclude-members: SQLDialect,ParamStyle,Limit,InferOrDefault


   .. autoclass:: SQLDialect
      :exclude-members: paramstyle, limit

   .. autoclass:: csql.dialect.ParamStyle()
   .. autoclass:: csql.dialect.Limit()
   .. autoclass:: csql.dialect.InferOrDefault()


.. _overrides:

Advanced Customization
======================

If the :ref:`sql-dialects` system isn't enough, you have the ability to reach in
and provide alternative rendering implementations. You can do anything here, from
rendering parameters differently, all the way through to pre-processing and assembling
Queries in an arbitrary way.

To customize rendering with your own implementations, pass an :class:`csql.overrides.Overrides` to
:meth:`csql.Query.build` or :func:`csql.Q` ``overrides``. For example:

.. code-block:: py

   from csql.render.param import ParameterRenderer

   class MyParamRenderer(ParameterRenderer):
      ... # left as an exercize for the reader

   overrides = Overrides(paramRenderer=MyParamRenderer)

   p = Parameters(val=123)
   q = Q('select * from thingers where id = {p['val']})
   q.build(overrides=overrides)

Like dialects, overrides will by default propagate if they've been set on referenced queries:

   >>> from csql.overrides import Overrides
   >>> o = Overrides()
   >>> q1 = Q(f'select * from thinger', overrides=o)
   >>> q2 = Q(f'select count(*) from {q1}')
   >>> assert q2.default_overrides == o

.. automodule:: csql.overrides

   .. autoclass:: csql.overrides.Overrides
      :no-members:

   .. autoclass:: csql.overrides.InferOrDefault
      :no-members:

Parameter Rendering
-------------------

The builtin parameter renderers are found in :mod:`csql.render.param`.

``csql.render.param``
---------------------

.. automodule:: csql.render.param

   .. autoclass:: QMark
      :no-members:
   .. autoclass:: ColonNumeric
      :no-members:
   .. autoclass:: DollarNumeric
      :no-members:

   To customize parameter rendering, subclass :class:`csql.render.param.ParameterRenderer`.

   .. autoclass:: csql.render.param.ParameterRenderer
      :members: _renderScalarSql
      :private-members: _renderScalarSql
      :no-undoc-members:

   .. autoclass:: csql.render.param.SQL

      A ``NewType`` alias for a ``str`` representing a chunk of SQL.

   .. autoclass:: csql.render.param.AutoKey

Query Renderering
-----------------

The big one... this lets you override how queries are constructed.
Currently the only implementation is :class:`csql.render.query.BoringSQLRenderer`,
but there may be others added in future (e.g. I can imagine some poor soul might
need to render as a big mess of nested subqueries instead of a CTE)

``csql.render.query``
---------------------

.. automodule:: csql.render.query

   .. autoclass:: BoringSQLRenderer
      :no-members:

   .. autoclass:: QueryRenderer
      :no-members:

      You should subclass this guy if you want to handle rendering yourself.
      I'm reserving the right to change this API, though - be warned.
