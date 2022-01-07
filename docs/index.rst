.. csql documentation master file, created by
   sphinx-quickstart on Sun Dec  5 15:14:25 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to csql's documentation!
================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

csql autodoc!
=============

.. automodule:: csql
   :members:
   :exclude-members: Q, Parameters, Query, RenderedQuery
   :undoc-members:

   .. autofunction:: Q
   .. autoclass:: Parameters
      :exclude-members: __init__, __new__
      :class-doc-from: class
      :members:
   .. autoclass:: Query
      :class-doc-from: class
      :exclude-members: __init__, __new__
      :members:
      :undoc-members:
   .. autoclass:: RenderedQuery
      :class-doc-from: class
      :exclude-members: __init__, __new__
      :members:


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
