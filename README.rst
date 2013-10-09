
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
Making an alias called ``mishmash`` is suggested since it saves having to
type redundant information, like calling the Python interpretor or specifying
the same database options over and over again. To invoke without an alias
use the ``-m`` option provided by Python.::
  
  $ python -m mishmash --help

Once you decide on a database you can make an alias. For example, it is easiest
to start with ``sqlite``.::

  $ alias mishmash="mishmash --db-type=sqlite --database=${HOME}/mishmash.db"
  $ alias mishmash="mishmash --db-type=postgresql --database=mishmash --username=travis --password=travis"

Inialize the database tables with the ``init`` command.::

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

