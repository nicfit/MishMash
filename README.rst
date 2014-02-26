===============================
MishMash
===============================

.. image:: https://badge.fury.io/py/mishmash.png
    :target: http://badge.fury.io/py/mishmash

.. image:: https://travis-ci.org/nicfit/mishmash.png?branch=master
        :target: https://travis-ci.org/nicfit/mishmash

.. image:: https://pypip.in/d/mishmash/badge.png
        :target: https://crate.io/packages/mishmash?version=latest


Python music database.

* Free software: GPL license
* Documentation: http://mishmash.rtfd.org.

Features
--------
FIXME

Misc Notes:
~~~~~~~~~~~

Database URL::

  sqlite:///:memory: (or, sqlite://)
  sqlite:///relative/path/to/file.db
  sqlite:////absolute/path/to/file.db

  postgresql://user:passwd@host:5432/mishmash

Command line::

  $ mishmash -D ... init
  $ mishmash --database=... init

Environment::

  $ export MISHMASH_DB=...

Initialize the database tables with the ``init`` command.::

  $ mishmash init --help
  $ mishmash init
  $ mishmash init --drop-all


postgresql
~~~~~~~~~~
::

  $ su - postgres
  $ createuser -d -P <USER>
  $ exit
  $ createdb -U <USER> -T template0 -E UTF8 mishmash

