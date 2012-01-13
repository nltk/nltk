NLTK testing
============

1. Obtain nltk source code;
2. install virtualenv and tox::

       pip install virtualenv
       pip install tox

3. make sure python2.5, python2.6, python2.7 and pypy executables are in system PATH.
   It is OK not to have all the executables, tests will be executed for available interpreters.

4. Make sure all NLTK data is downloaded (see `nltk.download()`);

5. run 'tox' command from the root nltk folder.

It may take a long time at first run, but the subsequent runs will be much faster.
Please consult http://tox.testrun.org/ for more info about the tox tool.