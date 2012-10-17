NLTK testing
============

1. Obtain nltk source code;
2. install virtualenv and tox::

       pip install virtualenv
       pip install tox

3. make sure python2.6, python2.7, python3.2, python3.3
   and pypy executables are in system PATH. It is OK not to have all the
   executables, tests will be executed for available interpreters.

4. Make sure all NLTK data is downloaded (see `nltk.download()`);

5. run 'tox' command from the root nltk folder. It will install dependencies
   and run `nltk/test/runtests.py` script for all available interpreters.
   You may pass any options to runtests.py script separating them by '--'.

It may take a long time at first run, but the subsequent runs will be much faster.
Please consult http://tox.testrun.org/ for more info about the tox tool.

Examples
--------

Run tests for python 2.7 in verbose mode; executing only tests
that failed in the last test run::

    tox -e py27 -- -v --failed


Run tree doctests for all available interpreters::

    tox -- tree.doctest

Run a selected unit test for the Python 3.2::

    tox -e py32 -- -v nltk.test.unit.test_seekable_unicode_stream_reader

