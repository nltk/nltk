# Natural Language Toolkit: Interface to Mallet Machine Learning Package
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A set of functions used to interface with the external Mallet_ machine learning
package. Before mallet can be used, you should tell NLTK where it can find
the mallet package, using the ``config_mallet()`` function. Typical usage:

.. doctest::
    :options: +SKIP

    >>> from nltk.classify import mallet
    >>> mallet.config_mallet() # pass path to mallet as argument if needed
    [Found mallet: ...]

.. _Mallet: http://mallet.cs.umass.edu/
"""

import os
import os.path

from nltk.internals import find_binary, java

######################################################################
#{ Configuration
######################################################################

_mallet_home = None
_mallet_classpath = None
def config_mallet(mallet_home=None):
    """
    Configure NLTK's interface to the Mallet machine learning package.

    :type mallet_home: str
    :param mallet_home: The full path to the mallet directory. If not
        specified, then NLTK will search the system for a mallet directory;
        and if one is not found, it will raise a ``LookupError`` exception.
    """
    global _mallet_home, _mallet_classpath

    # We don't actually care about this binary -- we just use it to
    # make sure we've found the right directory.
    mallethon_bin = find_binary(
        'mallet', mallet_home,
        env_vars=['MALLET',  'MALLET_HOME'],
        binary_names=['mallethon'],
        url='http://mallet.cs.umass.edu')
    # Record the location where mallet lives.
    bin_dir = os.path.split(mallethon_bin)[0]
    _mallet_home = os.path.split(bin_dir)[0]
    # Construct a classpath for using mallet.
    lib_dir = os.path.join(_mallet_home, 'lib')
    if not os.path.isdir(lib_dir):
        raise ValueError('While configuring mallet: directory %r '
                         'not found.' % lib_dir)
    _mallet_classpath = os.path.pathsep.join([os.path.join(lib_dir, filename)
                                  for filename in sorted(os.listdir(lib_dir))
                                  if filename.endswith('.jar')])


def call_mallet(cmd, classpath=None, stdin=None, stdout=None, stderr=None,
                blocking=True):
    """
    Call `nltk.internals.java` with the given command, and with the classpath
    modified to include both ``nltk.jar`` and all the ``.jar`` files defined by
    Mallet.

    See `nltk.internals.java` for parameter and return value descriptions.
    """
    if _mallet_classpath is None:
        config_mallet()

    # Set up the classpath
    if classpath is None:
        classpath = _mallet_classpath
    else:
        classpath += os.path.pathsep + _mallet_classpath
    # Delegate to java()
    return java(cmd, classpath, stdin, stdout, stderr, blocking)
