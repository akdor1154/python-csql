.. _persist:

Persistance / Caching
*********************

.. include:: ../README.md
   :parser: myst_parser.sphinx_
   :start-after: <!-- (persist)= -->
   :end-before: <!-- (end-persist)= -->


How it Works
============

The way this works is that when a query marked with ``.persist(cache)`` is built/rendered, it is passed to the
``cache`` to save, and the ``cache`` returns a replacement retrieval query to access its result.
The `retrieval` query is then used whenever the query is rendered, on its own or downstream.

For the above example:

>>> con = some_connection()
>>> # define cache
>>> cache = csql.contrib.persist.TempTableCacher(con)
>>> # define query, no execution yet
>>> q1 = Q(f'select id, date, rank() over (partition by name order by date) as rank from customers')
>>> q2 = Q(f'select date, count(*) from {q1}').persist(cache, 'q2') # note this time we gave a tag.

>>> # reference it, still no execution
>>> q3 = Q(f'select count(*) from {q2}')

>>> # build it in some way:
>>> q3.preview_pd(con) # or q3.db, q3.build(), etc. # doctest: +IGNORE_RESULT

Now the fun happens:

#. we are rendering SQL of ``q3``
#. when the ``q3`` renderer gets to the reference to ``q2``, it calls ``cache.persist(q2)``

   #. which runs, roughly,

      .. code-block:: py

         temp_name = f'csql_cache_{tag}_{key}'
         con.execute(f'create temp table {temp_name} as {q2.sql}')

      which is the slow query we're wanting to save the results of to
      avoid re-execution.
   #. and returns, roughly
      ``return Q(f'select * from {temp_name}')``
#. so instead of the q3 renderer seeing the original q2, it sees
   ``Q(f'select * from csql_cache_q2_asdf1234')``
#. and so gets rendered into

   .. code-block:: SQL

      with _subQuery0 as (
         select * from csql_cache_q2_asdf1234
      )
      select count(*) from _subQuery0

Additionally, queries are keyed by their content and parameter values, so previously cached queries
can be detected and re-used by the cacher where possible.


``csql.persist``
=================

.. automodule:: csql.persist
   :imported-members:
   :exclude-members: Cacher, Key

   .. autoclass:: Cacher
      :exclude-members: persist
      :private-members: _persist

   .. class:: Key

      A cache key. Type alias of ``str``.