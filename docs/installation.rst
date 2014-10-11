============
Installation
============

Using pip
------------
At the command line::

    $ pip install mishmash

Or, if you have virtualenvwrapper installed::

    $ mkvirtualenv mishmash
    $ pip install mishmash

Using a source distribution
-----------------------------
At the command line:

.. parsed-literal::

    $ tar zxf MishMish-|version|.tar.gz
    $ cd MishMish-|version|
    $ python setup.py install

From BitBucket
--------------
At the command line::

    $ hg clone https://bitbucket.org/nicfit/mishmash
    $ cd mishmash
    $ python setup.py install

Additional dependencies should be installed if developing MishMash::

    $ pip install -r dev-requirements.txt

Dependencies
-------------
All the required software dependencies are installed using either 
``requirements.txt`` files or by ``python install setup.py``, including the
Postgresql adapter ``psycopg2``. To try a different SQLAlchemy engine you must
install it separately.
