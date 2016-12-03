#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
import sys
import os
import nose
from nose.plugins.manager import PluginManager
from nose.plugins.doctests import Doctest
from nose.plugins import builtin

NLTK_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, NLTK_ROOT)

NLTK_TEST_DIR = os.path.join(NLTK_ROOT, 'nltk')

if __name__ == '__main__':
    # there shouldn't be import from NLTK for coverage to work properly
    from doctest_nose_plugin import DoctestFix

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

    # allow passing extra options and running individual tests
    # Examples:
    #
    #    python runtests.py semantics.doctest
    #    python runtests.py --with-id -v
    #    python runtests.py --with-id -v nltk.featstruct

    args = sys.argv[1:]
    if not args:
        args = [NLTK_TEST_DIR]

    if all(arg.startswith('-') for arg in args):
        # only extra options were passed
        args += [NLTK_TEST_DIR]

    arguments = [
        '--exclude=', # why is this needed?
        #'--with-xunit',
        #'--xunit-file=$WORKSPACE/nosetests.xml',
        #'--nocapture',
        '--with-doctest',
        #'--doctest-tests',
        #'--debug=nose,nose.importer,nose.inspector,nose.plugins,nose.result,nose.selector',
        '--doctest-extension=.doctest',
        '--doctest-fixtures=_fixt',
        '--doctest-options=+ELLIPSIS,+NORMALIZE_WHITESPACE,+IGNORE_EXCEPTION_DETAIL,+ALLOW_UNICODE,doctestencoding=utf-8',
        #'--verbosity=3',
    ] + args

    nose.main(argv=arguments, plugins=manager.plugins)
