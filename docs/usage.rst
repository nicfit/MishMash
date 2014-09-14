========
Usage
========

Databases
---------
The first requirement a database for MishMash to use. One of the great things
about SQLAlchemy is its support for a multitude of databases, feel
free to try whatever you would like but be aware that the only back-ends that
are tested and supported are::

* Postgresql
* SQLite; limited testing.

MishMash uses a database URL to create connections. The URL is most commonly 
read from the ``MISHMASH_DB`` environment variable, while other applications
might use a configuration file. The default value uses a SQLite database
called 'mishmash.db' in the user's home directory.::

    $ export MISHMASH_DB="sqlite:///${HOME}/mishmash.db"

The URL in this example specifies the type of database (i.e. SQLite) and
the filename of the DB file. The following sections provide more URL
examples for Postgresql (where authentication credentials are required)
and SQLite but see the full documentation for `SQLAlchemy database URLs`_
for a complete reference.

Postgresql
~~~~~~~~~~
The pattern for Postgresql URLs is::

    postgresql://user:passwd@host:port/db_name

``user`` and ``passwd`` are the login credentials for accessing the database,
while ``host`` and ``port`` (the default is 5432) determine where to connect.
Lastly, the specific name of the database that contains the MishMash data
is given by ``db_name``. A specific example::

    export MISHMASH_DB='postgresql://mishmash:mishmash@localhost/mishmash_test'

See the official `PostgreSQL documentation`_ for setup and administration
details but a brief example creating a database for MishMash to serve as a
starting point might be helpful.

.. code-block:: bash

  # Become the postges user
  $ sudo su - postgres
  # Create a db user named mishmash with database creation permission.
  $ createuser -d -P mishmash
  # Close postgres user shell.
  $ exit
  # As user mishmash, create a suitable database named mishmash
  $ createdb -U mishmash -T template0 -E UTF8 mishmash

SQLite
~~~~~~
The pattern for SQLite URLs is::

    sqlite://filename

The slashes can be a little odd, so some examples::

  sqlite:///relative/path/to/filename.db
  sqlite:////absolute/path/to/filename.db
  sqlite:///:memory:

The last example specifies an in-memory database that only exists as long as
the application using it.

mishmash init
-------------

Initialize the database tables with the ``mishmash init`` command.

.. code-block:: bash

  # Initialize if the database is empty, otherwise the command does nothing.
  $ mishmash init
  # Delete entire database if it exists and re-initialize.
  $ mishmash init --drop-all

mishmash sync
-------------
TODO

mishmash info
-------------
TODO


.. _SQLAlchemy database URLs: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls
.. _PostgreSQL documentation: http://www.postgresql.org/docs/
