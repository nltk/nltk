#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys
import os
import nose

NLTK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, NLTK_ROOT)

NLTK_TEST_DIR = os.path.join(NLTK_ROOT, 'nltk')


# These tests are expected to fail.
# NOTE: Remember to remove tests from this list after they have been fixed.
FAILING_TESTS = [
    "ccg.doctest", # This test randomly fails - nondeterministic output
    "collocations.doctest",
    "corpus.doctest",
    "portuguese_en.doctest",
    "probability.doctest",
    "relextract.doctest",
]

# These tests require extra dependencies and should not run by default
# TODO: Run the tests if the relevant dependeices are present on the system
DEPENDENT_TESTS = [
#    "classify.doctest",
    "discourse.doctest",
    "drt.doctest",
    "gluesemantics.doctest",
    "inference.doctest",
    "nonmonotonic.doctest",
]

EXCLUDED_TESTS = FAILING_TESTS + DEPENDENT_TESTS
_EXCLUDE_ARGV = ['--exclude='+test for test in EXCLUDED_TESTS]

if __name__ == '__main__':
    from nltk.test.doctest_nose_plugin import DoctestFix
    from nose.plugins.manager import PluginManager
    from nose.plugins.doctests import Doctest
    from nose.plugins import builtin

    class NltkPluginManager(PluginManager):
        """
        Nose plugin manager that replaces standard doctest plugin
        with a patched version.
        """
        def loadPlugins(self):
            for plug in builtin.plugins:
                if plug != Doctest:
                    self.addPlugin(plug())
            self.addPlugin(DoctestFix())
            super(NltkPluginManager, self).loadPlugins()

    manager = NltkPluginManager()
    manager.loadPlugins()

    nose.main(argv=sys.argv[1:] + _EXCLUDE_ARGV + [
            #'--with-xunit',
            #'--xunit-file=$WORKSPACE/nosetests.xml',
            '--with-doctest',
            '--doctest-extension=.doctest',
            '--doctest-options=+ELLIPSIS,+NORMALIZE_WHITESPACE,+IGNORE_EXCEPTION_DETAIL',
            #'--verbosity=3',
            NLTK_TEST_DIR
        ], plugins=manager.plugins)
