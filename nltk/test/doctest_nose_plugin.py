# -*- coding: utf-8 -*-
"""
Patched version of nose doctest plugin.
See https://github.com/nose-devs/nose/issues/7
"""
from __future__ import print_function
from nose.plugins.base import Plugin
from nose.util import tolist
import os
import sys
import re
from nose.plugins.doctests import (Doctest, src, log, anyp, getmodule,
                                   DocTestCase, DocFileCase, ContextList)
from nose.plugins.doctests import doctest

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

class _DoctestFix(Doctest):

    def options(self, parser, env):
        super(_DoctestFix, self).options(parser, env)
        parser.add_option('--doctest-options', action="append",
                          dest="doctestOptions",
                          metavar="OPTIONS",
                          help="Specify options to pass to doctest. " +
                          "Eg. '+ELLIPSIS,+NORMALIZE_WHITESPACE'")

#    def configure(self, options, config):
#        ... it is fixed in DoctestPluginHelper

    def loadTestsFromModule(self, module):
        """Load doctests from the module.
        """
        log.debug("loading from %s", module)
        if not self.matches(module.__name__):
            log.debug("Doctest doesn't want module %s", module)
            return
        try:
            tests = self.finder.find(module)
        except AttributeError:
            log.exception("Attribute error loading from %s", module)
            # nose allows module.__test__ = False; doctest does not and throws
            # AttributeError
            return
        if not tests:
            log.debug("No tests found in %s", module)
            return
        tests.sort()
        module_file = src(module.__file__)
        # FIXME this breaks the id plugin somehow (tests probably don't
        # get wrapped in result proxy or something)
        cases = []
        for test in tests:
            if not test.examples:
                continue
            if not test.filename:
                test.filename = module_file
            cases.append(DocTestCase(test,
                                     optionflags=self.optionflags,
                                     result_var=self.doctest_result_var))
        if cases:
            yield self.suiteClass(cases, context=module, can_split=False)

    def loadTestsFromFile(self, filename):
        """Load doctests from the file.

        Tests are loaded only if filename's extension matches
        configured doctest extension.

        """
        if self.extension and anyp(filename.endswith, self.extension):
            name = os.path.basename(filename)
            dh = open(filename)
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
                    fixture_context = __import__(
                        fixt_mod, globals(), locals(), ["nop"])
                except ImportError as e:
                    log.debug(
                        "Could not import %s: %s (%s)", fixt_mod, e, sys.path)
                log.debug("Fixture module %s resolved to %s",
                          fixt_mod, fixture_context)
                if hasattr(fixture_context, 'globs'):
                    globs = fixture_context.globs(globs)
            parser = doctest.DocTestParser()
            test = parser.get_doctest(
                doc, globs=globs, name=name,
                filename=filename, lineno=0)
            if test.examples:
                case = DocFileCase(
                    test,
                    optionflags=self.optionflags,
                    setUp=getattr(fixture_context, 'setup_test', None),
                    tearDown=getattr(fixture_context, 'teardown_test', None),
                    result_var=self.doctest_result_var)
                if fixture_context:
                    yield ContextList((case,), context=fixture_context)
                else:
                    yield case
            else:
                yield False # no tests to load

    def makeTest(self, obj, parent):
        """Look for doctests in the given object, which will be a
        function, method or class.
        """
        name = getattr(obj, '__name__', 'Unnammed %s' % type(obj))
        doctests = self.finder.find(obj, module=getmodule(parent), name=name)
        if doctests:
            for test in doctests:
                if len(test.examples) == 0:
                    continue
                yield DocTestCase(test, obj=obj, optionflags=self.optionflags,
                                  result_var=self.doctest_result_var)

def _plugin_supports_doctest_options(plugin_cls):
    import optparse
    plugin = plugin_cls()
    parser = optparse.OptionParser()
    plugin.options(parser, {})
    return parser.has_option('--doctest-options')


class DoctestPluginHelper(object):
    """
    This mixin adds print_function future import to all test cases.

    It also adds support for '#doctest +ALLOW_UNICODE' option that
    makes DocTestCase think u'foo' == 'foo'.
    """
    def loadTestsFromFile(self, filename):
        cases = super(DoctestPluginHelper, self).loadTestsFromFile(filename)
        for case in cases:
            if case:
                case._dt_test.globs['print_function'] = print_function
                case._dt_checker = _checker
            yield case

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



if _plugin_supports_doctest_options(Doctest):
    class DoctestFix(DoctestPluginHelper, Doctest):
        pass
else:
    class DoctestFix(DoctestPluginHelper, _DoctestFix):
        pass
