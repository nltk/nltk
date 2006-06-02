#!/usr/bin/env python2.4
#
# A Test Driver for Doctest
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#
# Provided as-is; use at your own risk; no warranty; no promises; enjoy!

"""
A driver for testing interactive python examples in text files and
docstrings.  This doctest driver performs three functions:

  - checking: Runs the interactive examples, and reports any examples
    whose actual output does not match their expected output.

  - debugging: Runs the interactive examples, and enters the debugger
    whenever an example's actual output does not match its expected
    output.

  - updating: Runs the interactive examples, and replaces the expected
    output with the actual output whenever they don't match.  This is
    used to update the output for new or out-of-date examples.

A number of other flags can be given; call the driver with the
`--help` option for a complete list.
"""

import os, os.path, sys, unittest, pdb, bdb, re, tempfile, traceback
from doctest import *
from doctest import DocTestCase
from optparse import OptionParser, OptionGroup, Option
from StringIO import StringIO

__version__ = '0.1'

###########################################################################
# Utility Functions
###########################################################################
# These are copied from doctest; I don't import them because they're
# private.  See the versions in doctest for docstrings, etc.

class _OutputRedirectingPdb(pdb.Pdb):
    def __init__(self, out):
        self.__out = out
        pdb.Pdb.__init__(self)

    def trace_dispatch(self, *args):
        save_stdout = sys.stdout
        sys.stdout = self.__out
        pdb.Pdb.trace_dispatch(self, *args)
        sys.stdout = save_stdout

def _exception_traceback(exc_info):
    excout = StringIO()
    exc_type, exc_val, exc_tb = exc_info
    traceback.print_exception(exc_type, exc_val, exc_tb, file=excout)
    return excout.getvalue()

class _SpoofOut(StringIO):
    def getvalue(self):
        result = StringIO.getvalue(self)
        if result and not result.endswith("\n"):
            result += "\n"
        if hasattr(self, "softspace"):
            del self.softspace
        return result

    def truncate(self,   size=None):
        StringIO.truncate(self, size)
        if hasattr(self, "softspace"):
            del self.softspace

###########################################################################
# Update Runner
###########################################################################

class UpdateRunner(DocTestRunner):
    """
    A subclass of `DocTestRunner` that checks the output of each
    example, and replaces the expected output with the actual output
    for any examples that fail.

    `UpdateRunner` can be used:
      - To automatically fill in the expected output for new examples.
      - To correct examples whose output has become out-of-date.

    However, care must be taken not to update an example's expected
    output with an incorrect value.
    """
    def __init__(self, verbose=False, mark_updates=False):
        self._mark_updates = mark_updates
        DocTestRunner.__init__(self, verbose=verbose)

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        self._new_want = {}
        (f,t) = DocTestRunner.run(self, test, compileflags, out, clear_globs)

        # Update the test's docstring, and the lineno's of the
        # examples, by breaking it into lines and replacing the old
        # expected outputs with the new expected outputs.
        old_lines = test.docstring.split('\n')
        new_lines = []
        lineno = 0
        offset = 0

        for example in test.examples:
            # Copy the lines up through the start of the example's
            # output from old_lines to new_lines.
            got_start = example.lineno + example.source.count('\n')
            new_lines += old_lines[lineno:got_start]
            lineno = got_start
            # Do a sanity check to make sure we're at the right lineno
            # (In particular, check that the example's expected output
            # appears in old_lines where we expect it to appear.)
            if example.want:
                assert (example.want.split('\n')[0] == 
                        old_lines[lineno][example.indent:]), \
                        'Line number mismatch at %d' % lineno
            # Skip over the old expected output.
            old_len = example.want.count('\n')
            lineno += old_len
            # Mark any changes we make.
            if self._mark_updates and example in self._new_want:
                new_lines.append(' '*example.indent + '... ' + 
                                 '# [!!] OUTPUT AUTOMATICALLY UPDATED [!!]')
            # Add the new expected output.
            new_want = self._new_want.get(example, example.want)
            if new_want:
                new_want = '\n'.join([' '*example.indent+l
                                      for l in new_want[:-1].split('\n')])
                new_lines.append(new_want)
            # Update the example's want & lieno fields
            example.want = new_want
            example.lineno += offset
            offset += example.want.count('\n') - old_len
        # Add any remaining lines
        new_lines += old_lines[lineno:]

        # Update the test's docstring.
        test.docstring = '\n'.join(new_lines)

        # Return failures & tries
        return (f,t)

    def report_start(self, out, test, example):
        pass

    def report_success(self, out, test, example, got):
        pass

    def report_unexpected_exception(self, out, test, example, exc_info):
        replacement = _exception_traceback(exc_info)
        self._new_want[example] = replacement
        if self._verbose:
            self._report_replacement(out, test, example, replacement)

    def report_failure(self, out, test, example, got):
        self._new_want[example] = got
        if self._verbose:
            self._report_replacement(out, test, example, got)

    def _report_replacement(self, out, test, example, replacement):
        want = '\n'.join(['    '+l for l in example.want.split('\n')[:-1]])
        repl = '\n'.join(['    '+l for l in replacement.split('\n')[:-1]])
        if want and repl:
            diff = 'Replacing:\n%s\nWith:\n%s\n' % (want, repl)
        elif want:
            diff = 'Removing:\n%s\n' % want
        elif repl:
            diff = 'Adding:\n%s\n' % repl
        out(self._header(test, example) + diff)

    DIVIDER = '-'*70
    def _header(self, test, example):
        if test.filename is None:
            tag = ("On line #%s of %s" %
                   (example.lineno+1, test.name))
        elif test.lineno is None:
            tag = ("On line #%s of %s in %s" %
                   (example.lineno+1, test.name, test.filename))
        else:
            lineno = test.lineno+example.lineno+1
            tag = ("On line #%s of %s (%s)" %
                   (lineno, test.filename, test.name))
        source_lines = example.source.rstrip().split('\n')
        return (self.DIVIDER + '\n' + tag + '\n' +
                '    >>> %s\n' % source_lines[0] +
                ''.join(['    ... %s\n' % l for l in source_lines[1:]]))

###########################################################################
# Debugger
###########################################################################

def _indent(s, indent=4):
    return re.sub('(?m)^(?!$)', indent*' ', s)

import keyword, token, tokenize
class Debugger:
    # Just using this for reporting:
    runner = DocTestRunner()

    def __init__(self, checker=None, set_trace=None):
        if checker is None:
            checker = OutputChecker()
        self.checker = checker
        if set_trace is None:
            set_trace = pdb.Pdb().set_trace
        self.set_trace = set_trace

    def _check_output(self, example):
        want = example.want
        optionflags = self._get_optionflags(example)
        got = sys.stdout.getvalue()
        sys.stdout.truncate(0)
        if not self.checker.check_output(want, got, optionflags):
            self.runner.report_failure(self.save_stdout.write, 
                                       self.test, example, got)
            return False
        else:
            return True

    def _check_exception(self, example):
        want_exc_msg = example.exc_msg
        optionflags = self._get_optionflags(example)
        exc_info = sys.exc_info()
        got_exc_msg = traceback.format_exception_only(*exc_info[:2])[-1]
        if not self.checker.check_output(want_exc_msg, got_exc_msg,
                                         optionflags):
            got = _exception_traceback(exc_info)
            self.runner.report_failure(self.save_stdout.write,
                                       self.test, example, got)
            return False
        else:
            return True

    def _print_if_not_none(self, *args):
        if args == (None,):
            pass
        elif len(args) == 1:
            print `args[0]`
        else:
            print `args` # not quite right: >>> 1,

    def _comment_line(self, line):
        "Return a commented form of the given line"
        line = line.rstrip()
        if line:
            return '# '+line
        else:
            return '#'

    def _script_from_examples(self, s):
        output = []
        examplenum = 0
        for piece in DocTestParser().parse(s):
            if isinstance(piece, Example):
                self._script_from_example(piece, examplenum, output)
                examplenum += 1
            else:
                # Add non-example text.
                output += [self._comment_line(l)
                           for l in piece.split('\n')[:-1]]
        # Combine the output, and return it.
        return '\n'.join(output)

    _CHK_OUT = 'if not CHECK_OUTPUT(__examples__[%d]): __set_trace__()'
    _CHK_EXC = 'if not CHECK_EXCEPTION(__examples__[%d]): __set_trace__()'

    def _script_from_example(self, example, i, output):
        source = self._simulate_compile_singlemode(example.source)[:-1]

        if example.exc_msg is None:
            output.append(source)
            output.append(self._CHK_OUT % i)
        else:
            output.append('try:')
            output.append(_indent(source))
            output.append('    '+self._CHK_OUT % i)
            output.append('except:')
            output.append('    '+self._CHK_EXC % i)

    def _simulate_compile_singlemode(self, s):
        # Calculate line offsets
        lines = [0, 0]
        pos = 0
        while 1:
            pos = s.find('\n', pos)+1
            if not pos: break
            lines.append(pos)
        lines.append(len(s))

        oldpos = 0
        parenlevel = 0
        deflevel = 0
        output = []
        stmt = []

        text = StringIO(s)
        tok_gen = tokenize.generate_tokens(text.readline)
        for toktype, tok, (srow,scol), (erow,ecol), line in tok_gen:
            newpos = lines[srow] + scol
            stmt.append(s[oldpos:newpos])
            if tok != '':
                stmt.append(tok)
            oldpos = newpos + len(tok)

            # Update the paren level.
            if tok in '([{':
                parenlevel += 1
            if tok in '}])':
                parenlevel -= 1

            if tok in ('def', 'class') and deflevel == 0:
                deflevel = 1
            if deflevel and toktype == token.INDENT:
                deflevel += 1
            if deflevel and toktype == token.DEDENT:
                deflevel -= 1

            # Are we starting a statement?
            if ((toktype in (token.NEWLINE, tokenize.NL, tokenize.COMMENT,
                             token.INDENT, token.ENDMARKER) or
                 tok==':') and parenlevel == 0):
                if deflevel == 0 and self._is_expr(stmt[1:-2]):
                    output += stmt[0]
                    output.append('__print__((')
                    output += stmt[1:-2]
                    output.append('))')
                    output += stmt[-2:]
                else:
                    output += stmt
                stmt = []
        return ''.join(output)

    def _is_expr(self, stmt):
        stmt = [t for t in stmt if t]
        if not stmt:
            return False

        # An assignment signifies a non-exception, *unless* it
        # appears inside of parens (eg, ``f(x=1)``.)
        parenlevel = 0
        for tok in stmt:
            if tok in '([{': parenlevel += 1
            if tok in '}])': parenlevel -= 1
            if (parenlevel == 0 and 
                tok in ('=', '+=', '-=', '*=', '/=', '%=', '&=', '+=',
                       '^=', '<<=', '>>=', '**=', '//=')):
                return False

        # Any keywords *except* "not", "or", "and", "lambda", "in", "is"
        # signifies a non-expression.
        if stmt[0] in ("assert", "break", "class", "continue", "def",
                       "del", "elif", "else", "except", "exec",
                       "finally", "for", "from", "global", "if",
                       "import", "pass", "print", "raise", "return",
                       "try", "while", "yield"):
            return False
        return True

    def _get_optionflags(self, example):
        optionflags = 0
        for (flag, val) in example.options.items():
            if val:
                optionflags |= flag
            else:
                optionflags &= ~flag
        return optionflags

    def debug(self, test, pm=False):
        self.test = test

        # Save the old stdout
        self.save_stdout = sys.stdout

        # Convert the source docstring to a script.
        script = self._script_from_examples(test.docstring)

        # Create a debugger.
        debugger = _OutputRedirectingPdb(sys.stdout)

        # Patch pdb.set_trace to restore sys.stdout during interactive
        # debugging (so it's not still redirected to self._fakeout).
        save_set_trace = pdb.set_trace
        pdb.set_trace = debugger.set_trace

        # Write the script to a temporary file.  Note that
        # tempfile.NameTemporaryFile() cannot be used.  As the docs
        # say, a file so created cannot be opened by name a second
        # time on modern Windows boxes, and execfile() needs to open
        # it.
        srcfilename = tempfile.mktemp(".py", "doctestdebug_")
        f = open(srcfilename, 'w')
        f.write(script)
        f.close()

        # Set up the globals
        test.globs['CHECK_OUTPUT'] = self._check_output
        test.globs['CHECK_EXCEPTION'] = self._check_exception
        test.globs['__print__'] = self._print_if_not_none
        test.globs['__set_trace__'] = debugger.set_trace
        test.globs['__examples__'] = self.test.examples
        try:
            if pm is False:
                debugger.run("execfile(%r)" % srcfilename,
                             test.globs, test.globs)
            else:
                try:
                    sys.stdout = _SpoofOut()
                    try:
                        execfile(srcfilename, test.globs)
                    except bdb.BdbQuit:
                        return
                    except:
                        sys.stdout = self.save_stdout
                        exc_info = sys.exc_info()
                        exc_msg = traceback.format_exception_only(
                            exc_info[0], exc_info[1])[-1]
                        self.save_stdout.write(self.runner.DIVIDER+'\n')
                        self.save_stdout.write('Unexpected exception:\n' +
                                               _indent(exc_msg))
                        raise
                        #self.post_mortem(debugger, exc_info[2])
                finally:
                    sys.stdout = self.save_stdout
        finally:
            sys.set_trace = save_set_trace
            os.remove(srcfilename)

    def post_mortem(self, debugger, t):
        debugger.reset()
        while t.tb_next is not None:
            t = t.tb_next
        debugger.interaction(t.tb_frame, t)

###########################################################################
# Helper functions
###########################################################################

# Name can be:
#   - The filename of a text file
#   - The filename of a python file
#   - The dotted name of a python module

# Return a list of test!
def find(name):
    # Check for test names
    if ':' in name:
        (name, testname) = name.split(':')
    else:
        testname = None

    if os.path.exists(name):
        filename = os.path.normpath(os.path.abspath(name))
        ext = os.path.splitext(filename)[-1]
        if (ext[-3:] != '.py' and ext[-4:-1] != '.py'):
            # It's a text file; return the filename.
            if testname is not None:
                raise ValueError("test names can't be specified "
                                 "for text files")
            s = open(filename).read()
            test = DocTestParser().get_doctest(s, {}, name, filename, 0)
            return [test]
        else:
            # It's a python file; import it.  Make sure to set the
            # path correctly.
            basedir, modname = find_module_from_filename(filename)
            orig_path = sys.path[:]
            try:
                sys.path.insert(0, basedir)
                module = import_from_name(modname)
            finally:
                sys.path[:] = orig_path
    else:
        module = import_from_name(name)

    # Find tests.
    tests = DocTestFinder().find(module)
    if testname is not None:
        testname = '%s.%s' % (module.__name__, testname)
        tests = [t for t in tests if t.name.startswith(testname)]
        if len(tests) == 0:
            raise ValueError("test not found")
    return tests

def import_from_name(name):
    try:
        return __import__(name, globals(), locals(), ['*'])
    except Exception, e:
        raise ValueError, str(e)
    except:
        raise ValueError, 'Error importing %r' % name

def find_module_from_filename(filename):
    """
    Given a filename, return a tuple `(basedir, module)`, where
    `module` is the module's name, and `basedir` is the directory it
    should be loaded from (this directory should be added to the
    path to import it).  Packages are handled correctly.
    """
    (basedir, file) = os.path.split(filename)
    (module_name, ext) = os.path.splitext(file)

    # If it's a package, then import with the directory name (don't
    # use __init__ as the module name).
    if module_name == '__init__':
        (basedir, module_name) = os.path.split(basedir)

    # If it's contained inside a package, then find the base dir.
    if (os.path.exists(os.path.join(basedir, '__init__.py')) or
        os.path.exists(os.path.join(basedir, '__init__.pyc')) or
        os.path.exists(os.path.join(basedir, '__init__.pyw'))):
        package = []
        while os.path.exists(os.path.join(basedir, '__init__.py')):
            (basedir,dir) = os.path.split(basedir)
            if dir == '': break
            package.append(dir)
        package.reverse()
        module_name = '.'.join(package+[module_name])

    return (basedir, module_name)

###########################################################################
# Basic Actions
###########################################################################

def run(names, optionflags, verbosity):
    suite = unittest.TestSuite()
    for name in names:
        try:
            for test in find(name):
                suite.addTest(DocTestCase(test, optionflags))
        except ValueError, e:
            print >>sys.stderr, ('%s: Error processing %s -- %s' %
                                 (sys.argv[0], name, e))
    unittest.TextTestRunner(verbosity=verbosity).run(suite)

def debug(names, optionflags, verbosity, pm=True):
    debugger = Debugger()
    for name in names:
        try:
            for test in find(name):
                debugger.debug(test, pm)
        except ValueError, e:
            raise
            print >>sys.stderr, ('%s: Error processing %s -- %s' %
                                 (sys.argv[0], name, e))

def update(names, optionflags, verbosity):
    parser = DocTestParser()
    runner = UpdateRunner(verbose=True)
    for name in names:
        try:
            # Make sure we're running on a text file.
            tests = find(name)
            if len(tests) != 1 or tests[0].lineno != 0:
                raise ValueError('update can only be used with text files')
            test = tests[0]

            # Run the updater!
            (failures, tries) = runner.run(test)

            # Confirm the changes.
            if failures == 0:
                print 'No updates needed!'
            else:
                print '*'*70
                print '%d examples updated.' % failures
                print '-'*70
                sys.stdout.write('Accept updates? [y/N] ')
                sys.stdout.flush()
                if sys.stdin.readline().lower().strip() in ('y', 'yes'):
                    # Make a backup of the original contents.
                    backup = test.filename+'.bak'
                    print 'Renaming %s -> %s' % (name, backup)
                    os.rename(test.filename, backup)
                    # Write the new contents.
                    print 'Writing updated version to %s' % test.filename
                    out = open(test.filename, 'w')
                    out.write(test.docstring)
                    out.close()
                else:
                    print 'Updates rejected!'
        except ValueError, e:
            raise
            print >>sys.stderr, ('%s: Error processing %s -- %s' %
                                 (sys.argv[0], name, e))

###########################################################################
# Main script
###########################################################################

# Action options
CHECK_OPT    = Option("--check",
               action="store_const", dest="action", const="check", 
               default="check",
               help="Verify the output of the doctest examples in the "
                    "given files.")

UPDATE_OPT   = Option("--update", "-u",
               action="store_const", dest="action", const="update",
               help="Update the expected output for new or out-of-date "
                    "doctest examples in the given files.  In "
                    "particular, find every example whose actual output "
                    "does not match its expected output; and replace its "
                    "expected output with its actual output.  You will "
                    "be asked to verify the changes before they are "
                    "written back to the file; be sure to check them over "
                    "carefully, to ensure that you don't accidentally "
                    "create broken test cases.")

DEBUG_OPT    = Option("--debug", 
               action="store_const", dest="action", const="debug",
               help="Verify the output of the doctest examples in the "
                    "given files.  If any example fails, then enter the "
                    "python debugger.")

# Reporting options
VERBOSE_OPT  = Option("-v", "--verbose", 
               action="count", dest="verbosity", default=1,
               help="Increase verbosity.")

QUIET_OPT    = Option("-q", "--quiet",
               action="store_const", dest="verbosity", const=0,
               help="Decrease verbosity.")

UDIFF_OPT    = Option("--udiff", '-d',
               action="store_const", dest="udiff", const=1, default=0,
               help="Display test failures using unified diffs.")

CDIFF_OPT    = Option("--cdiff",
               action="store_const", dest="cdiff", const=1, default=0,
               help="Display test failures using context diffs.")

NDIFF_OPT    = Option("--ndiff",
               action="store_const", dest="ndiff", const=1, default=0,
               help="Display test failures using ndiffs.")

# Output Comparison options
ELLIPSIS_OPT = Option("--ellipsis",
               action="store_const", dest="ellipsis", const=1, default=0,
               help="Allow \"...\" to be used for ellipsis in the "
                    "expected output.")
NORMWS_OPT   = Option("--normalize_whitespace",
               action="store_const", dest="normws", const=1, default=0,
               help="Ignore whitespace differences between "
                    "the expected output and the actual output.")

def main():
    # Create the option parser.
    optparser = OptionParser(usage='%prog [options] NAME ...',
                             version="Edloper's Doctest Driver, "
                                     "version %s" % __version__)

    action_group = OptionGroup(optparser, 'Actions (default=check)')
    action_group.add_options([CHECK_OPT, UPDATE_OPT, DEBUG_OPT])
    optparser.add_option_group(action_group)

    reporting_group = OptionGroup(optparser, 'Reporting')
    reporting_group.add_options([VERBOSE_OPT, QUIET_OPT,
                                 UDIFF_OPT, CDIFF_OPT, NDIFF_OPT])
    optparser.add_option_group(reporting_group)

    compare_group = OptionGroup(optparser, 'Output Comparison')
    compare_group.add_options([ELLIPSIS_OPT, NORMWS_OPT])
    optparser.add_option_group(compare_group)

    # Extract optionflags and the list of file names.
    optionvals, names = optparser.parse_args()
    if len(names) == 0:
        optparser.error("No files specified")
    optionflags = (optionvals.udiff * REPORT_UDIFF |
                   optionvals.cdiff * REPORT_CDIFF |
                   optionvals.ellipsis * ELLIPSIS |
                   optionvals.normws * NORMALIZE_WHITESPACE)

    # Perform the requested action.
    if optionvals.action == 'check':
        run(names, optionflags, optionvals.verbosity)
    elif optionvals.action == 'update':
        update(names, optionflags, optionvals.verbosity)
    elif optionvals.action == 'debug':
        debug(names, optionflags, optionvals.verbosity)
    else:
        optparser.error('INTERNAL ERROR: Bad action %s' % optionvals.action)

if __name__ == '__main__': main()
