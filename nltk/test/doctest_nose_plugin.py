# -*- coding: utf-8 -*-
"""
Patched version of nose doctest plugin.
See https://github.com/nose-devs/nose/issues/7
"""
from nose.plugins.doctests import *

class _DoctestFix(Doctest):

    def options(self, parser, env):
        super(_DoctestFix, self).options(parser, env)
        parser.add_option('--doctest-options', action="append",
                          dest="doctestOptions",
                          metavar="OPTIONS",
                          help="Specify options to pass to doctest. " +
                          "Eg. '+ELLIPSIS,+NORMALIZE_WHITESPACE'")

    def configure(self, options, config):
        super(_DoctestFix, self).configure(options, config)
        self.optionflags = 0
        if options.doctestOptions:
            flags = ",".join(options.doctestOptions).split(',')
            for flag in flags:
                try:
                    if flag.startswith('+'):
                        self.optionflags |= getattr(doctest, flag[1:])
                    elif flag.startswith('-'):
                        self.optionflags &= ~getattr(doctest, flag[1:])
                    else:
                        raise ValueError(
                            "Must specify doctest options with starting " +
                            "'+' or '-'.  Got %s" % (flag,))
                except AttributeError:
                    raise ValueError("Unknown doctest option %s" %
                                     (flag[1:],))

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
                except ImportError, e:
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

if _plugin_supports_doctest_options(Doctest):
    class DoctestFix(Doctest):
        pass
else:
    class DoctestFix(_DoctestFix):
        pass
