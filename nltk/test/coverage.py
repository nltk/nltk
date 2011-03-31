#!/usr/bin/env python
#
#             Perforce Defect Tracking Integration Project
#              <http://www.ravenbrook.com/project/p4dti/>
#
#                   COVERAGE.PY -- COVERAGE TESTING
#
#             Gareth Rees, Ravenbrook Limited, 2001-12-04
#
#
# 1. INTRODUCTION
#
# This module provides coverage testing for Python code.
#
# The intended readership is all Python developers.
#
# This document is not confidential.
#
# See [GDR 2001-12-04a] for the command-line interface, programmatic
# interface and limitations.  See [GDR 2001-12-04b] for requirements and
# design.

"""Usage:

coverage.py -x MODULE.py [ARG1 ARG2 ...]
    Execute module, passing the given command-line arguments, collecting
    coverage data.

coverage.py -e
    Erase collected coverage data.

coverage.py -r [-m] FILE1 FILE2 ...
    Report on the statement coverage for the given files.  With the -m
    option, show line numbers of the statements that weren't executed.

coverage.py -a [-d dir] FILE1 FILE2 ...
    Make annotated copies of the given files, marking statements that
    are executed with > and statements that are missed with !.  With
    the -d option, make the copies in that directory.  Without the -d
    option, make each copy in the same directory as the original.

Coverage data is saved in the file .coverage by default.  Set the
COVERAGE_FILE environment variable to save it somewhere else."""

import os
import re
import string
import sys
import atexit
import types


# 2. IMPLEMENTATION
#
# This uses the "singleton" pattern.
#
# The word "morf" means a module object (from which the source file can
# be deduced by suitable manipulation of the __file__ attribute) or a
# filename.
#
# When we generate a coverage report we have to canonicalize every
# filename in the coverage dictionary just in case it refers to the
# module we are reporting on.  It seems a shame to throw away this
# information so the data in the coverage dictionary is transferred to
# the 'cexecuted' dictionary under the canonical filenames.
#
# The coverage dictionary is called "c" and the trace function "t".  The
# reason for these short names is that Python looks up variables by name
# at runtime and so execution time depends on the length of variables!
# In the bottleneck of this application it's appropriate to abbreviate
# names to increase speed.

# A dictionary with an entry for (Python source file name, line number
# in that file) if that line has been executed.
c = {}

# t(f, x, y).  This method is passed to sys.settrace as a trace
# function.  See [van Rossum 2001-07-20b, 9.2] for an explanation of
# sys.settrace and the arguments and return value of the trace function.
# See [van Rossum 2001-07-20a, 3.2] for a description of frame and code
# objects.

def t(f, x, y):
    c[(f.f_code.co_filename, f.f_lineno)] = 1
    return t

the_coverage = None

class coverage:
    error = "coverage error"

    # Name of the cache file (unless environment variable is set).
    cache_default = ".coverage"

    # Environment variable naming the cache file.
    cache_env = "COVERAGE_FILE"

    # A map from canonical Python source file name to a dictionary in
    # which there's an entry for each line number that has been
    # executed.
    cexecuted = {}

    # Cache of results of calling the analysis() method, so that you can
    # specify both -r and -a without doing double work.
    analysis_cache = {}

    # Cache of results of calling the canonical_filename() method, to
    # avoid duplicating work.
    canonical_filename_cache = {}

    def __init__(self):
        global the_coverage
        if the_coverage:
            raise self.error("Only one coverage object allowed.")
        self.cache = os.environ.get(self.cache_env, self.cache_default)
        self.restore()
        self.analysis_cache = {}

    def help(self, error=None):
        if error:
            print(error)
            print()
        print(__doc__)
        sys.exit(1)

    def command_line(self):
        import getopt
        settings = {}
        optmap = {
            '-a': 'annotate',
            '-d:': 'directory=',
            '-e': 'erase',
            '-h': 'help',
            '-i': 'ignore-errors',
            '-m': 'show-missing',
            '-r': 'report',
            '-x': 'execute',
            }
        short_opts = string.join([o[1:] for o in list(optmap.keys())], '')
        long_opts = list(optmap.values())
        options, args = getopt.getopt(sys.argv[1:], short_opts,
                                      long_opts)
        for o, a in options:
            if o in optmap:
                settings[optmap[o]] = 1
            elif o + ':' in optmap:
                settings[optmap[o + ':']] = a
            elif o[2:] in long_opts:
                settings[o[2:]] = 1
            elif o[2:] + '=' in long_opts:
                settings[o[2:]] = a
            else:
                self.help("Unknown option: '%s'." % o)
        if settings.get('help'):
            self.help()
        for i in ['erase', 'execute']:
            for j in ['annotate', 'report']:
                if settings.get(i) and settings.get(j):
                    self.help("You can't specify the '%s' and '%s' "
                              "options at the same time." % (i, j))
        args_needed = (settings.get('execute')
                       or settings.get('annotate')
                       or settings.get('report'))
        action = settings.get('erase') or args_needed
        if not action:
            self.help("You must specify at least one of -e, -x, -r, "
                      "or -a.")
        if not args_needed and args:
            self.help("Unexpected arguments %s." % args)
        if settings.get('erase'):
            self.erase()
        if settings.get('execute'):
            if not args:
                self.help("Nothing to do.")
            sys.argv = args
            self.start()
            import __main__
            exec(compile(open(sys.argv[0]).read(), sys.argv[0], 'exec'), __main__.__dict__)
        if not args:
            args = list(self.cexecuted.keys())
        ignore_errors = settings.get('ignore-errors')
        show_missing = settings.get('show-missing')
        directory = settings.get('directory=')
        if settings.get('report'):
            self.report(args, show_missing, ignore_errors)
        if settings.get('annotate'):
            self.annotate(args, directory, ignore_errors)

    def start(self):
        sys.settrace(t)

    def stop(self):
        sys.settrace(None)

    def erase(self):
        global c
        c = {}
        self.analysis_cache = {}
        self.cexecuted = {}
        if os.path.exists(self.cache):
            os.remove(self.cache)

    # save().  Save coverage data to the coverage cache.

    def save(self):
        self.canonicalize_filenames()
        cache = open(self.cache, 'wb')
        import marshal
        marshal.dump(self.cexecuted, cache)
        cache.close()

    # restore().  Restore coverage data from the coverage cache (if it
    # exists).

    def restore(self):
        global c
        c = {}
        self.cexecuted = {}
        if not os.path.exists(self.cache):
            return
        try:
            cache = open(self.cache, 'rb')
            import marshal
            cexecuted = marshal.load(cache)
            cache.close()
            if isinstance(cexecuted, dict):
                self.cexecuted = cexecuted
        except:
            pass

    # canonical_filename(filename).  Return a canonical filename for the
    # file (that is, an absolute path with no redundant components and
    # normalized case).  See [GDR 2001-12-04b, 3.3].

    def canonical_filename(self, filename):
        if filename not in self.canonical_filename_cache:
            f = filename
            if os.path.isabs(f) and not os.path.exists(f):
                f = os.path.basename(f)
            if not os.path.isabs(f):
                for path in [os.curdir] + sys.path:
                    g = os.path.join(path, f)
                    if os.path.exists(g):
                        f = g
                        break
            cf = os.path.normcase(os.path.abspath(f))
            self.canonical_filename_cache[filename] = cf
        return self.canonical_filename_cache[filename]

    # canonicalize_filenames().  Copy results from "executed" to
    # "cexecuted", canonicalizing filenames on the way.  Clear the
    # "executed" map.

    def canonicalize_filenames(self):
        global c
        for filename, lineno in list(c.keys()):
            f = self.canonical_filename(filename)
            if f not in self.cexecuted:
                self.cexecuted[f] = {}
            self.cexecuted[f][lineno] = 1
        c = {}

    # morf_filename(morf).  Return the filename for a module or file.

    def morf_filename(self, morf):
        if isinstance(morf, types.ModuleType):
            if not hasattr(morf, '__file__'):
                raise self.error("Module has no __file__ attribute.")
            file = morf.__file__
        else:
            file = morf
        return self.canonical_filename(file)

    # analyze_morf(morf).  Analyze the module or filename passed as
    # the argument.  If the source code can't be found, raise an error.
    # Otherwise, return a pair of (1) the canonical filename of the
    # source code for the module, and (2) a list of lines of statements
    # in the source code.

    def analyze_morf(self, morf):
        if morf in self.analysis_cache:
            return self.analysis_cache[morf]
        filename = self.morf_filename(morf)
        ext = os.path.splitext(filename)[1]
        if ext == '.pyc':
            if not os.path.exists(filename[0:-1]):
                raise self.error("No source for compiled code '%s'."
                                   % filename)
            filename = filename[0:-1]
        elif ext != '.py':
            raise self.error("File '%s' not Python source." % filename)
        source = open(filename, 'r')
        import parser
        tree = parser.suite(source.read()).totuple(1)
        source.close()
        statements = {}
        self.find_statements(tree, statements)
        lines = list(statements.keys())
        lines.sort()
        result = filename, lines
        self.analysis_cache[morf] = result
        return result

    # find_statements(tree, dict).  Find each statement in the parse
    # tree and record the line on which the statement starts in the
    # dictionary (by assigning it to 1).
    #
    # It works by walking the whole tree depth-first.  Every time it
    # comes across a statement (symbol.stmt -- this includes compound
    # statements like 'if' and 'while') it calls find_statement, which
    # descends the tree below the statement to find the first terminal
    # token in that statement and record the lines on which that token
    # was found.
    #
    # This algorithm may find some lines several times (because of the
    # grammar production statement -> compound statement -> statement),
    # but that doesn't matter because we record lines as the keys of the
    # dictionary.
    #
    # See also [GDR 2001-12-04b, 3.2].

    def find_statements(self, tree, dict):
        import symbol, token
        if token.ISNONTERMINAL(tree[0]):
            for t in tree[1:]:
                self.find_statements(t, dict)
            if tree[0] == symbol.stmt:
                self.find_statement(tree[1], dict)
        elif (tree[0] == token.NAME
              and tree[1] in ['elif', 'except', 'finally']):
            dict[tree[2]] = 1

    def find_statement(self, tree, dict):
        import token
        while token.ISNONTERMINAL(tree[0]):
            tree = tree[1]
        dict[tree[2]] = 1

    # format_lines(statements, lines).  Format a list of line numbers
    # for printing by coalescing groups of lines as long as the lines
    # represent consecutive statements.  This will coalesce even if
    # there are gaps between statements, so if statements =
    # [1,2,3,4,5,10,11,12,13,14] and lines = [1,2,5,10,11,13,14] then
    # format_lines will return "1-2, 5-11, 13-14".

    def format_lines(self, statements, lines):
        pairs = []
        i = 0
        j = 0
        start = None
        pairs = []
        while i < len(statements) and j < len(lines):
            if statements[i] == lines[j]:
                if start == None:
                    start = lines[j]
                end = lines[j]
                j = j + 1
            elif start:
                pairs.append((start, end))
                start = None
            i = i + 1
        if start:
            pairs.append((start, end))
        def stringify(pair):
            start, end = pair
            if start == end:
                return "%d" % start
            else:
                return "%d-%d" % (start, end)
        return string.join(list(map(stringify, pairs)), ", ")

    def analysis(self, morf):
        filename, statements = self.analyze_morf(morf)
        self.canonicalize_filenames()
        if filename not in self.cexecuted:
            self.cexecuted[filename] = {}
        missing = []
        for line in statements:
            if line not in self.cexecuted[filename]:
                missing.append(line)
        return (filename, statements, missing,
                self.format_lines(statements, missing))

    def morf_name(self, morf):
        if isinstance(morf, types.ModuleType):
            return morf.__name__
        else:
            return os.path.splitext(os.path.basename(morf))[0]

    def report(self, morfs, show_missing=1, ignore_errors=0):
        if not isinstance(morfs, list):
            morfs = [morfs]
        max_name = max([5,] + list(map(len, list(map(self.morf_name, morfs)))))
        fmt_name = "%%- %ds  " % max_name
        fmt_err = fmt_name + "%s: %s"
        header = fmt_name % "Name" + " Stmts   Exec  Cover"
        fmt_coverage = fmt_name + "% 6d % 6d % 5d%%"
        if show_missing:
            header = header + "   Missing"
            fmt_coverage = fmt_coverage + "   %s"
        print(header)
        print("-" * len(header))
        total_statements = 0
        total_executed = 0
        for morf in morfs:
            name = self.morf_name(morf)
            try:
                _, statements, missing, readable  = self.analysis(morf)
                n = len(statements)
                m = n - len(missing)
                if n > 0:
                    pc = 100.0 * m / n
                else:
                    pc = 100.0
                args = (name, n, m, pc)
                if show_missing:
                    args = args + (readable,)
                print(fmt_coverage % args)
                total_statements = total_statements + n
                total_executed = total_executed + m
            except KeyboardInterrupt:
                raise
            except:
                if not ignore_errors:
                    type, msg = sys.exc_info()[0:2]
                    print(fmt_err % (name, type, msg))
        if len(morfs) > 1:
            print("-" * len(header))
            if total_statements > 0:
                pc = 100.0 * total_executed / total_statements
            else:
                pc = 100.0
            args = ("TOTAL", total_statements, total_executed, pc)
            if show_missing:
                args = args + ("",)
            print(fmt_coverage % args)

    # annotate(morfs, ignore_errors).

    blank_re = re.compile("\\s*(#|$)")
    else_re = re.compile("\\s*else\\s*:\\s*(#|$)")

    def annotate(self, morfs, directory=None, ignore_errors=0):
        for morf in morfs:
            try:
                filename, statements, missing, _ = self.analysis(morf)
                source = open(filename, 'r')
                if directory:
                    dest_file = os.path.join(directory,
                                             os.path.basename(filename)
                                             + ',cover')
                else:
                    dest_file = filename + ',cover'
                dest = open(dest_file, 'w')
                lineno = 0
                i = 0
                j = 0
                covered = 1
                while 1:
                    line = source.readline()
                    if line == '':
                        break
                    lineno = lineno + 1
                    while i < len(statements) and statements[i] < lineno:
                        i = i + 1
                    while j < len(missing) and missing[j] < lineno:
                        j = j + 1
                    if i < len(statements) and statements[i] == lineno:
                        covered = j >= len(missing) or missing[j] > lineno
                    if self.blank_re.match(line):
                        dest.write('  ')
                    elif self.else_re.match(line):
                        # Special logic for lines containing only
                        # 'else:'.  See [GDR 2001-12-04b, 3.2].
                        if i >= len(statements) and j >= len(missing):
                            dest.write('! ')
                        elif i >= len(statements) or j >= len(missing):
                            dest.write('> ')
                        elif statements[i] == missing[j]:
                            dest.write('! ')
                        else:
                            dest.write('> ')
                    elif covered:
                        dest.write('> ')
                    else:
                        dest.write('! ')
                    dest.write(line)
                source.close()
                dest.close()
            except KeyboardInterrupt:
                raise
            except:
                if not ignore_errors:
                    raise


# Singleton object.
the_coverage = coverage()

# Module functions call methods in the singleton object.
def start(args): return the_coverage.start(*args)
def stop(args): return the_coverage.stop(*args)
def erase(args): return the_coverage.erase(*args)
def analysis(args): return the_coverage.analysis(*args)
def report(args): return the_coverage.report(*args)

# Save coverage data when Python exits.  (The atexit module wasn't
# introduced until Python 2.0, so use sys.exitfunc when it's not
# available.)
try:
    import atexit
    atexit.register(the_coverage.save)
except ImportError:
    atexit.register(the_coverage.save)

# Command-line interface.
if __name__ == '__main__':
    the_coverage.command_line()


# A. REFERENCES
#
# [GDR 2001-12-04a] "Statement coverage for Python"; Gareth Rees;
# Ravenbrook Limited; 2001-12-04;
# <http://www.garethrees.org/2001/12/04/python-coverage/>.
#
# [GDR 2001-12-04b] "Statement coverage for Python: design and
# analysis"; Gareth Rees; Ravenbrook Limited; 2001-12-04;
# <http://www.garethrees.org/2001/12/04/python-coverage/design.html>.
#
# [van Rossum 2001-07-20a] "Python Reference Manual (releae 2.1.1)";
# Guide van Rossum; 2001-07-20;
# <http://www.python.org/doc/2.1.1/ref/ref.html>.
#
# [van Rossum 2001-07-20b] "Python Library Reference"; Guido van Rossum;
# 2001-07-20; <http://www.python.org/doc/2.1.1/lib/lib.html>.
#
#
# B. DOCUMENT HISTORY
#
# 2001-12-04 GDR Created.
#
# 2001-12-06 GDR Added command-line interface and source code
# annotation.
#
# 2001-12-09 GDR Moved design and interface to separate documents.
#
# 2001-12-10 GDR Open cache file as binary on Windows.  Allow
# simultaneous -e and -x, or -a and -r.
#
# 2001-12-12 GDR Added command-line help.  Cache analysis so that it
# only needs to be done once when you specify -a and -r.
#
# 2001-12-13 GDR Improved speed while recording.  Portable between
# Python 1.5.2 and 2.1.1.
#
#
# C. COPYRIGHT AND LICENSE
#
# This file is copyright (c) 2001 Gareth Rees.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1.  Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
# 2.  Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDERS AND CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
# TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
#
#
# $Id: //info.ravenbrook.com/project/p4dti/version/2.4/test/coverage.py#1 $
