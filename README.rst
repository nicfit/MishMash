
Requirements
------------
::

  $ pip install -r requirements.txt

A virtual environment (especially useful for development) can be created with
the provided helper script.::

  $ ./mkenv.sh mishmash
  $ workon mishmash


Usage
-----
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
----------
::

  $ su - postgres
  $ createuser -d -P <USER>
  $ exit
  $ createdb -U <USER> -T template0 -E UTF8 mishmash


mishmash.web
------------


