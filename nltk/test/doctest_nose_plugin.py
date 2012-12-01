# -*- coding: utf-8 -*-
from __future__ import print_function
from nose.suite import ContextList
import re
import doctest
from nose.plugins.base import Plugin
from nose.util import tolist
from nose.plugins.doctests import Doctest

ALLOW_UNICODE = doctest.register_optionflag('ALLOW_UNICODE')

class _UnicodeOutputChecker(doctest.OutputChecker):
    _literal_re = re.compile(r"(\W|^)[uU]([rR]?[\'\"])", re.UNICODE)

    def _remove_u_prefixes(self, txt):
        return re.sub(self._literal_re, r'\1\2', txt)

    def check_output(self, want, got, optionflags):
        res = doctest.OutputChecker.check_output(self, want, got, optionflags)
        if res:
            return True
        if not (optionflags & ALLOW_UNICODE):
            return False

        # ALLOW_UNICODE is active and want != got
        cleaned_want = self._remove_u_prefixes(want)
        cleaned_got = self._remove_u_prefixes(got)
        res = doctest.OutputChecker.check_output(self, cleaned_want, cleaned_got, optionflags)
        return res

_checker = _UnicodeOutputChecker()

class DoctestPluginHelper(object):
    """
    This mixin adds print_function future import to all test cases.

    It also adds support for '#doctest +ALLOW_UNICODE' option that
    makes DocTestCase think u'foo' == 'foo'.
    """
    def loadTestsFromFile(self, filename):
        cases = super(DoctestPluginHelper, self).loadTestsFromFile(filename)

        for case in cases:
            if isinstance(case, ContextList):
                yield ContextList([self._patchTestCase(c) for c in case], case.context)
            else:
                yield self._patchTestCase(case)

    def loadTestsFromModule(self, module):
        """Load doctests from the module.
        """
        for suite in super(DoctestPluginHelper, self).loadTestsFromModule(module):
            cases = [self._patchTestCase(case) for case in suite._get_tests()]
            yield self.suiteClass(cases, context=module, can_split=False)

    def _patchTestCase(self, case):
        if case:
            case._dt_test.globs['print_function'] = print_function
            case._dt_checker = _checker
        return case


    def configure(self, options, config):
        # it is overriden in order to fix doctest options discovery

        Plugin.configure(self, options, config)
        self.doctest_result_var = options.doctest_result_var
        self.doctest_tests = options.doctest_tests
        self.extension = tolist(options.doctestExtension)
        self.fixtures = options.doctestFixtures
        self.finder = doctest.DocTestFinder()

        #super(DoctestPluginHelper, self).configure(options, config)
        self.optionflags = 0
        if options.doctestOptions:
            flags = ",".join(options.doctestOptions).split(',')
            for flag in flags:
                try:
                    if flag.startswith('+'):
                        self.optionflags |= doctest.OPTIONFLAGS_BY_NAME[flag[1:]]
                    elif flag.startswith('-'):
                        self.optionflags &= ~doctest.OPTIONFLAGS_BY_NAME[flag[1:]]
                    else:
                        raise ValueError(
                            "Must specify doctest options with starting " +
                            "'+' or '-'.  Got %s" % (flag,))
                except (AttributeError, KeyError):
                    raise ValueError("Unknown doctest option %s" %
                                     (flag[1:],))



class DoctestFix(DoctestPluginHelper, Doctest):
    pass
