

.. _basic_usage:

***********
Basic Usage
***********

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: (intro)=
   :end-before: (end-intro)=


.. _params:

Easy Parameters
===============

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: (params)=
   :end-before: (end-params)=


.. _reparam:

Changing Parameter Values
=========================


.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: (reparam)=
   :end-before: (end-reparam)=

``csql``
========

.. currentmodule:: csql


.. automodule:: csql
   :members:
   :exclude-members: Q, Parameters, Query, RenderedQuery, ParameterValue
   :undoc-members:

   Q()
   ---
   .. autofunction:: Q

   Parameters()
   ------------
   .. autoclass:: Parameters
      :exclude-members: __init__, __new__
      :class-doc-from: class

   Query
   -----
   .. autoclass:: Query()
      :class-doc-from: class
      :exclude-members: __init__, __new__

   RenderedQuery
   -------------
   .. autoclass:: RenderedQuery()
      :class-doc-from: class
      :exclude-members: __init__, __new__

   Other
   -----
   .. class:: ParameterValue()

      Valid parameter value. You can use any hashable value here (so str, int, float, date, .. ) all fine.
      You can also use a ``Sequence`` of the above.

      Type alias for ``Hashable | Sequence[Hashable]``.
   
   .. autoclass:: ParameterPlaceholder()

