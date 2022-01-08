

.. _basic_usage:

***********
Basic Usage
***********

.. include:: ../README.rst
   :end-before: .. _end-intro:

``csql``
========

.. currentmodule:: csql


.. automodule:: csql
   :members:
   :exclude-members: Q, Parameters, Query, RenderedQuery
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

.. _reparam:

.. include:: ../README.rst
   :start-after: .. _reparam:
   :end-before: .. _end-reparam:
