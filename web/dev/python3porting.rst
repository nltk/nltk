NLTK Python 3 support
=====================

The following text is not a general comprehensive Python 3.x porting guide;
it provides some information about the approach using for NLTK Python 3 port.

Porting Strategy
----------------

NLTK is being ported to Python 3 using single codebase strategy:
NLTK should work from a single codebase in Python 2.x and 3.x.

Python 2.5 compatibility is dropped in order to take advantage of
new ``__future__`` imports, ``b`` bytestring marker, new
``except Exception as e`` syntax and better standard library compatibility.

General notes
^^^^^^^^^^^^^

There are good existing guides for writing Python 2.x - 3.x compatible
code, e.g.

* http://docs.python.org/dev/howto/pyporting.html
* http://python3porting.com/
* https://docs.djangoproject.com/en/dev/topics/python3/

Take a look at them to have an idea how the approach works and what
is changed in Python 3.

python-modernize
^^^^^^^^^^^^^^^^

`python-modernize <https://github.com/mitsuhiko/python-modernize>`_ script
was used for tedious parts of python3 porting. Take a look at the docs for
more information. The process was:

* Run NLTK test suite under Python 2.x;
* fix one specific aspect of NLTK by running one of python-modernize fixers;
* take a look at changes python-modernize proposes, fix stupid things;
* run NLTK test suite again under Python 2.x and make sure there are no
  regressions.

After python-modernize code wouldn't be necessary Python 3.x compatible but
further porting would be easier and there shouldn't be 2.x regressions.

nltk.compat
^^^^^^^^^^^

There is a helper ``nltk.compat`` module that is loosely based on a great
`six`_ library. It provides simple utilities for wrapping over differences
between Python 2 and Python 3. Moved imports, removed/renamed builtins
and type names differences goes there.

.. note::

   We don't use `six`_ directly because it doesn't work well
   bundled and NLTK needs extra custom 2+3 helpers anyway.

.. _six: http://packages.python.org/six/


map vs imap, items vs iteritems, ...
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A number of Python builtins and builtin methods returns lists under
Python 2.x and iterators under Python 3.x. There are 3 possible ways
to workaround this:

1) use non-iterator versions of functions and methods under Python 3.x
   (e.g. cast ``zip`` result to list);
2) convert Python 2.x code to iterator versions (e.g. replace ``zip``
   with ``itertools.izip`` when possible);
3) let the code behave different under Python 2.x and Python 3.x.

In this NLTK port (1) and (3) methods are used; (3) is preferred.
This way there are no breaking interface changes for Python 2.x code
and Python 3.x code remains idiomatic (it is surprising for a dict
subclass ``items`` method to return a list under Python 3.x).

Existing code that uses NLTK will have to be ported from
Python 2.x to 3.x anyway so I think such interface changes are acceptable.

Doctests porting notes
----------------------

NLTK test suite is mostly doctest-based. Most usual rules apply to
porting doctests code. But ther are some issues that make the
process harder, so in order to make doctests work under
Python 2.x and Python 3.x extra tricks are needed.

``__future__`` imports
^^^^^^^^^^^^^^^^^^^^^^

Python's doctest runner doesn't support __future__ imports.
They are executed but has no effect in doctests' code.
These imports are quite useful for making code Python 2.x + 3.x
compatible so there are some methods to overcome the limitation.

* ``from __future__ import print_function``: it may seem the import works
  because ``print(foo)`` works under python 2.x; but it works only because
  (foo) == foo; ``print(foo, bar)`` prints tuple; ``print(foo, sep=' ')``
  raises an exception. In order to make print() work this future import
  is injected to all doctests' globals within NLTK test suite
  (implementation: ``nltk.test.doctest_nose_plugin.DoctestPluginHelper``).
  So NLTK's doctests shouldn't import print_function but they should
  assume this import is in effect.

* ``from __future__ import unicode_literals``: there is no sane way to
  use non-ascii constants in doctests under python 2.x
  (see http://bugs.python.org/issue1293741 ); doctests with non-ascii
  constants should be better rewritten as unittests or as doctests
  without non-ascii constants.

  Tests may use variables with unicode values though. In order to print
  such values and have the same output under python 2 and python 3 the
  following trick may be used::

      >>> print(unicode_value.encode('unicode-escape').decode('ascii'))

  But it may be a better idea to avoid this trick and rewrite the test to
  unittest format instead.

* ``from __future__ import division``: it is usually not hard to cast
  results to int or float to have the same semantics under python 2 and 3.


Unicode strings __repr__
^^^^^^^^^^^^^^^^^^^^^^^^

Representation of unicode strings is different in Python 2.x and Python 3.x
even if they contain only ascii characters.

Python 2.x::

    >>> x = b'foo'.decode('ascii')
    >>> x
    u'foo'

Python 3.x::

    >>> x = b'foo'.decode('ascii')
    >>> x
    'foo'

(Note the missing 'u' in Python 3 example).

In order to simplify things NLTK's custom doctest runner
(see ``nltk.test.doctest_nose_plugin.DoctestPluginHelper``) doesn't
take 'u''s into account; it just considers u'foo' and 'foo' equal;
developer is free to write u'foo' or 'foo'.

This is not absolutely correct but if this distinction is important
then doctest should be converted to unittest.

There are other possible fixes for the ``__repr__`` issue but they
all make doctests less readable.

For single variables ``print`` may be used. Python 2.x::

    >>> print(x)
    foo

Python 3.x::

    >>> print(x)
    foo

This won't help with container types. Python 2.x::

    >>> print([x, x])
    [u'foo', u'foo']

Possible fixes for lists are::

    >>> for txt in [x, x]:
    ...     print(x)
    foo
    foo

or::

    >>> print(", ".join([x, x]))
    foo, foo


Float values representation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The exact representation of float values may vary across Python interpreters
(this is not only a Python 3.x - specific issue). So instead of this::

    >>> recall
    0.8888888888889

write this::

    >>> print(recall)
    0.88888888888...

Auto-fixing of the common constructions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The porting may be tedious, there is a lot of search/replace work
(e.g. ``print foo`` -> ``print(foo)`` or
``raise Exception, e`` -> ``raise Exception as e``). In order to overcome
this use 2to3 utility, e.g.::

    $ 2to3 -d -f print nltk/test/*.doctest

Pass '-w' option to write changes. It is a good idea to apply
fixers one-by-one, run test suite before and after fixing and check things
manually.
