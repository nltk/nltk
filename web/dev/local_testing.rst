NLTK testing
============

1. Obtain nltk source code;
2. install virtualenv and tox::

       pip install virtualenv
       pip install tox

3. make sure currently supported python versions
   and pypy executables are in system PATH. It is OK not to have all the
   executables, tests will be executed for available interpreters.

4. Make sure all NLTK data is downloaded (see ``nltk.download()``);

5. run 'tox' command from the root nltk folder. It will install dependencies
   and run ``nltk/test/runtests.py`` script for all available interpreters.
   You may pass any options to runtests.py script separating them by '--'.

It may take a long time at first run, but the subsequent runs will
be much faster.

Please consult http://tox.testrun.org/ for more info about the tox tool.

Examples
--------

Run tests for python 3.6 in verbose mode; executing only tests
that failed in the last test run::

    tox -e py36 -- -v --failed


Run tree doctests for all available interpreters::

    tox -- tree.doctest

Run a selected unit test for Python 3.7::

    tox -e py37 -- -v nltk.test.unit.test_seekable_unicode_stream_reader

By default, numpy, scipy and scikit-learn are installed in tox virtualenvs.
This is slow, requires working build toolchain and is not always feasible.
In order to skip numpy & friends, use ``..-nodeps`` environments::

    tox -e py36-nodeps,py37,pypy

It is also possible to run tests without tox. This way NLTK would be tested
only under single interpreter, but it may be easier to have numpy and other
libraries installed this way. In order to run tests without tox, make sure
``nose >= 1.2.1`` is installed and execute runtests.py script::

    nltk/test/runtests.py


Writing tests
-------------

Unlike most open-source projects, NLTK test suite is doctest-based.
This format is very expressive, and doctests are usually read
as documentation. We don't want to rewrite them to unittests;
if you're contributing code to NLTK please prefer doctests
for testing.

Doctests are located at ``nltk/test/*.doctest`` text files and
in docstrings for modules, classes, methods and functions.

That said, doctests have their limitations and sometimes it is better to use
unittests. Test should be written as unittest if some of the following apply:

* test deals with non-ascii unicode and Python 2.x support is required;
* test is a regression test that is not necessary for documentational purposes.

Unittests currently reside in ``nltk/test/unit/test_*.py`` files; nose
is used for test running.

If a test should be written as unittest but also has a documentational value
then it should be duplicated as doctest, but with a "# doctest: +SKIP" option.

There are some gotchas with NLTK doctests (and with doctests in general):

* Use ``print("foo")``, not ``print "foo"``: NLTK doctests act
  like ``from __future__ import print_functions`` is in use.

* Don't write ``+ELLIPSIS``, ``+NORMALIZE_WHITESPACE``,
  ``+IGNORE_EXCEPTION_DETAIL`` flags (they are already ON by default in NLTK).

* Do not write doctests that has non-ascii output (they are not supported in
  Python 2.x). Incorrect::

      >>> greeting
      u'Привет'

  The proper way is to rewrite such doctest as unittest.

* In order to conditionally skip a doctest in a separate
  ``nltk/test/foo.doctest`` file, create ``nltk.test/foo_fixt.py``
  file from the following template::

      # <a comment describing why should the test be skipped>

      def setup_module(module):
          from nose import SkipTest

          if some_condition:
              raise SkipTest("foo.doctest is skipped because <...>")

* In order to conditionally skip all doctests from the module/class/function
  docstrings, put the following function in a top-level module namespace::

      # <a comment describing why should the tests from this module be skipped>

      def setup_module(module):
          from nose import SkipTest

          if some_condition:
              raise SkipTest("doctests from nltk.<foo>.<bar> are skipped because <...>")

  A good idea is to define ``__all__`` in such module and omit
  ``setup_module`` from ``__all__``.

  It is not possible to conditionally skip only some doctests from a module.

* Do not expect the exact float output; this may fail on some machines::

      >>> some_float_constant
      0.867

  Use ellipsis in this case to make the test robust (or compare the values)::

      >>> some_float_constant
      0.867...

      >>> abs(some_float_constant - 0.867) < 1e-6
      True

* Do not rely on dictionary or set item order. Incorrect::

      >>> some_dict
      {"x": 10, "y": 20}

  The proper way is to sort the items and print them::

      >>> for key, value in sorted(some_dict.items()):
      ...     print(key, value)
      x 10
      y 20

If the code requires some external dependencies, then

* tests for this code should be skipped if the dependencies are not available:
  use ``setup_module`` for doctests (as described above) and
  ``nltk.test.unit.utils.skip / skipIf`` decorators or ``nose.SkipTest``
  exception for unittests;
* if the dependency is a Python package, it should be added to tox.ini
  (but not to ..-nodeps environments).
