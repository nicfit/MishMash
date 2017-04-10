Release History
===============

.. :changelog:

v0.3b3 (2017-04-09) : Prayers for Rain
---------------------------------------

New
~~~
- UTC sync times and per lib last_sync. Fixes #6, #7.
- Db test fixtures, etc.

Changes
~~~~~~~
- mishmash.data.init now returns the 3-tuple (engine, SessionMaker, connection).
  Previously a 2-tuple, sans connection, was returned.
  The new mishmash.database.DatebaseInfo namedtuple is the actual return type,
  if you prefer not to unpack the return value.

v0.3b2 (2017-03-12) : Nine Patriotic Hymns For Children
-------------------------------------------------------

Fix
~~~
- Protect against not being the first to call
  multiprocessing.set_start_method.


v0.3b1 (2017-03-12) : Nine Patriotic Hymns For Children
-------------------------------------------------------

New
~~~
- Mismash sync --monitor (using inotify)
- Test beginnings.

Changes
~~~~~~~
- Label_id renamed tag_id. Fixes #65.
- Mishmash.database.init accepts the DB URL as its first arguments, NO
  LONGER a Config object.

Fix
~~~
- Postgres service on Travis-CI.
- Restored gitchangelog fork.


v0.3b0 (2017-02-26)
-------------------------

* Initial release
