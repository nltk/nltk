# -*- coding: utf-8 -*-
from __future__ import print_function
import re
import sys
import os
import codecs
import doctest
from nose.util import tolist, anyp
from nose.plugins.base import Plugin
from nose.suite import ContextList
from nose.plugins.doctests import Doctest, log, DocFileCase

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
        res = doctest.OutputChecker.check_output(
            self, cleaned_want, cleaned_got, optionflags
        )
        return res


_checker = _UnicodeOutputChecker()


class DoctestPluginHelper(object):
    """
    This mixin adds print_function future import to all test cases.

    It also adds support for:
        '#doctest +ALLOW_UNICODE' option that
        makes DocTestCase think u'foo' == 'foo'.

        '#doctest doctestencoding=utf-8' option that
        changes the encoding of doctest files
    """

    OPTION_BY_NAME = ('doctestencoding',)

    def loadTestsFromFileUnicode(self, filename):
        if self.extension and anyp(filename.endswith, self.extension):
            name = os.path.basename(filename)
            dh = codecs.open(filename, 'r', self.options.get('doctestencoding'))
            try:
                doc = dh.read()
            finally:
                dh.close()

            fixture_context = None
            globs = {'__file__': filename}
            if self.fixtures:
                base, ext = os.path.splitext(name)
                dirname = os.path.dirname(filename)
                sys.path.append(dirname)
                fixt_mod = base + self.fixtures
                try:
                    fixture_context = __import__(fixt_mod, globals(), locals(), ["nop"])
                except ImportError as e:
                    log.debug("Could not import %s: %s (%s)", fixt_mod, e, sys.path)
                log.debug("Fixture module %s resolved to %s", fixt_mod, fixture_context)
                if hasattr(fixture_context, 'globs'):
                    globs = fixture_context.globs(globs)
            parser = doctest.DocTestParser()
            test = parser.get_doctest(
                doc, globs=globs, name=name, filename=filename, lineno=0
            )
            if test.examples:
                case = DocFileCase(
                    test,
                    optionflags=self.optionflags,
                    setUp=getattr(fixture_context, 'setup_test', None),
                    tearDown=getattr(fixture_context, 'teardown_test', None),
                    result_var=self.doctest_result_var,
                )
                if fixture_context:
                    yield ContextList((case,), context=fixture_context)
                else:
                    yield case
            else:
                yield False  # no tests to load

    def loadTestsFromFile(self, filename):

        cases = self.loadTestsFromFileUnicode(filename)

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

        # super(DoctestPluginHelper, self).configure(options, config)
        self.optionflags = 0
        self.options = {}

        if options.doctestOptions:
            stroptions = ",".join(options.doctestOptions).split(',')
            for stroption in stroptions:
                try:
                    if stroption.startswith('+'):
                        self.optionflags |= doctest.OPTIONFLAGS_BY_NAME[stroption[1:]]
                        continue
                    elif stroption.startswith('-'):
                        self.optionflags &= ~doctest.OPTIONFLAGS_BY_NAME[stroption[1:]]
                        continue
                    try:
                        key, value = stroption.split('=')
                    except ValueError:
                        pass
                    else:
                        if not key in self.OPTION_BY_NAME:
                            raise ValueError()
                        self.options[key] = value
                        continue
                except (AttributeError, ValueError, KeyError):
                    raise ValueError("Unknown doctest option {}".format(stroption))
                else:
                    raise ValueError(
                        "Doctest option is not a flag or a key/value pair: {} ".format(
                            stroption
                        )
                    )


class DoctestFix(DoctestPluginHelper, Doctest):
    pass
