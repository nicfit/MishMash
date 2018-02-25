========
Usage
========

Configuration
-------------

MishMash ships with a default configuration that should work out of the
box with no extra additional settings by using a SQLite database saved in
``${HOME}/mishmash.db``.  Running ``mishmash info`` with demonstrate this,
afterwards ``mishmash.db`` will exist in your home directory and be
initialized with the database schema.

.. code-block:: bash

    $ mishmash info
    $ sqlite3 /home/travis/mishmash.db
    sqlite> select * from artists;
    1|Various Artists|Various Artists|2014-10-11 01:12:10.246406|||
    sqlite>

To see the current configuration use info command's ``--default-config``
option. You may wish to capture this output for writing custom configuration
files.

.. code-block:: bash

    $ mishmash --default-config
    [mishmash]
    sqlalchemy.url = sqlite:////home/travis/mishmash.db

    [loggers]
    keys = root, sqlalchemy, eyed3, mishmash

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = INFO
    handlers = console

    ... more config ...

The first change most users will want to do is change the database that
MishMash uses. The ``-D/--database`` option make this easy. In this example,
information about ./mymusic.db SQLite database and the mymusic PostgreSQL
database is displayed.

.. code-block:: bash

    $ mishmash --database=sqlite:///mymusic.db info
    $ mishmash -D postgresql://mishmash@localhost:5432/mymusic info

In you wish to make additional configuration changes, or would like to avoid
needing to type the database URL all the time, a configuration is needed.  The
file may contain the entire configuration or only
the values you wish to change (i.e. changes are applied to the default
configuration).  With the settings saved to a file use the ``-c/--config``
option to have MishMash use it. In this examples the database URL and
a logging level are modified.

.. code-block:: bash

    $ cat example.ini
    [mishmash]
    sqlalchemy.url = postgresql://mishmash@localhost:5432/mymusic

    [logger_sqlalchemy]
    level = DEBUG

    $ mishmash -c example.ini info

You can avoid typing ``-c/--config`` option by setting the file name in the
``MISHMASH_CONFIG`` environment variable.

.. code-block:: bash

    $ export MISHMASH_CONFIG=/etc/mishmash.ini

None of the options for controlling configuration are mutually exclusive,
complex setups can be made by combining them. The order of precedence is
show below::

    Default <-- -c/--config <-- MISHMASH_CONFIG <-- -D/--database

Items to the left are lower precedence and the direction arrows (``<--``) show
the order in which the options are merged.  For example, local machine changes
(local.ini) could be merged with the global site configuration (site.ini) and
the PostgreSQL server at dbserver.example.com is used regardless then the other
files set.

.. code-block:: bash

    $ MISHMASH_CONFIG=local.ini mishmish -c site.ini -D postgresql://dbserver.example.com:5432/music

Databases
---------
The first requirement is deciding a database for MishMash to use. One of the
great things about SQLAlchemy is its support for a multitude of databases, feel
free to try whichever you would like but that the only back-ends that are
currently tested/supported are::

* Postgresql
* SQLite; limited testing.

The default value uses a SQLite database called 'mishmash.db' in the user's
home directory.::

    sqlite:///${HOME}/mishmash.db

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

    postgresql://mishmash:mishmash@localhost/mishmash_test


Setup of initial database and roles:::

    $ createuser --createdb mishmash
    $ createdb -E utf8 -U mishmash mishmash

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

mishmash info
-------------
The ``info`` command displays details about the current settings and database.
TODO

mishmash sync
-------------
The ``sync`` command imports music metadata into the database.
TODO

mishmash web
-------------
The ``web`` command runs the web interface.
TODO

mishmash merge-artists
----------------------
TODO

mishmash split-artists
----------------------
TODO


.. _SQLAlchemy database URLs: http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html#database-urls
.. _PostgreSQL documentation: http://www.postgresql.org/docs/
