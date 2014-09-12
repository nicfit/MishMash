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

At the command line

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

Additional dependencies should be installed if developing MishMish::

    $ pip install -r dev-requirements.txt
