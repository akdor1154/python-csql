

.. _basic_usage:

***********
Basic Usage
***********

.. include:: ../README.rst
   :end-before: .. _end-intro:


.. _reparam:

.. include:: ../README.rst
   :start-after: .. _reparam:
   :end-before: .. _end-reparam:

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

