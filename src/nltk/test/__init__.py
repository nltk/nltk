# Natural Language Toolkit: Unit Tests
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit tests for the NLTK modules.  These tests are intented to ensure
that changes that we make to NLTK's code don't accidentally introduce
bugs.

Each module in this package tests a specific aspect of NLTK.  Modules
are typically named for the module or class that they test (e.g.,
L{nltk.test.token} performs tests on the L{nltk.token} module).

This package can be run as a script from the command line, with the
following syntax::

    python nltk/test/__init__.py -v nltk/test/*.py

This command is called by the \"C{test}\" target in the NLTK Makefile.
"""

# Import required packages.  Unfortunately, there's a naming conflict
# between nltk.token and the stdlib module 'token', which means we
# have to do some path shuffling to successfully import 'doctest'.
import sys, os, os.path
if __name__ == '__main__': del sys.path[0]

import doctest, unittest, trace, StringIO, re

#######################################################################
# Test runner
#######################################################################

def testsuite():
    testsuites = []
    
    path = os.path.split(__file__)[0]
    for file in os.listdir(path):
        if not file.endswith('.py'): continue
        if file.startswith('__init__'): continue
        try: exec('import nltk.test.%s as m' % file[:-3])
        except: print 'Error importing %s' % file

        # Add unittest tests.
        #if hasattr(m, 'testsuite'):
        #    testsuites.append(m.testsuite())

        # Add doctest tests.
        try: testsuites.append(doctest.DocTestSuite(m))
        except: pass
        
    return unittest.TestSuite(testsuites)

# def _file_to_module(filename):
#     """
#     Convert a filename to a module name.  Warning: this may not be
#     totally portable.  But it should at least work on unix/windows.
#     """
#     # Not portable.
#     (base, ext) = filename.split('.')
#     if ext != 'py': return None
    
#     if base[-9:] == '/__init__':
#         base = base[:-9]
#     return '.'.join(base.split('/'))

# def _load_modules(module_filenames, verbosity=0):
#     """
#     Given a list of module filenames, load the corresponding modules,
#     and return a list of those modules.
#     """
#     # Extract the module names.
#     mnames = [_file_to_module(name) for name in module_filenames
#               if name[-16:] != 'test/__init__.py']

#     modules = []
#     if verbosity>0: print 'Importing modules:'
#     for mname in mnames:
#         if mname == None: continue
#         if verbosity>0: print '  - %s' % mname
#         try:
#             exec('import '+mname)
#             exec('modules.append('+mname+')')
#         except:
#             print 'Warning: failed to import %s' % mname

#     return modules

# def _testsuite(module_names, verbosity=0):
#     """
#     Return a PyUnit testsuite for the NLP toolkit
#     """
#     modules = _load_modules(module_names, verbosity-1)

#     if verbosity>0:
#         print 'Testing modules:'
#         for module in modules:
#             print '  - %s' % module.__name__
#             if verbosity>1: print '     ('+module.__file__+')'
    
#     return unittest.TestSuite([m.testsuite() for m in modules]) 

def test(verbosity=0):
    """
    Run unit tests for the NLP toolkit; print results to stdout/stderr.
    @param module_names: A list of filenames of test modules.
    """
    # Ensure that the type safety level is set to full.
    import nltk.chktype
    nltk.chktype.type_safety_level(1000)
    
    global success
    runner = unittest.TextTestRunner(verbosity=verbosity)
    success = runner.run(testsuite()).wasSuccessful()

def test_coverage(verbosity, coverdir):
    tracer = trace.Trace(ignoredirs=[sys.prefix, sys.exec_prefix,],
                         trace=0, count=1)
    tracer.run('test(%d)' % verbosity)
    r = tracer.results()

    sys.stdout = StringIO.StringIO()
    r.write_results(show_missing=True, summary=True,
                    coverdir=coverdir)

    # Hack the summary output to look nicer.
    summary = sys.stdout.getvalue()
    sys.stdout = sys.__stdout__
    def subfunc(m):
        module_name = os.path.abspath(m.group(2))
        module_name = module_name.replace('\\', '/')
        module_name = re.sub('.*/nltk/', 'nltk.', module_name)
        module_name = module_name.replace('/__init__.py', '')
        module_name = module_name.replace('/','.')
        module_name = module_name.replace('.py', '')
        if module_name.startswith('nltk.test'): return ''
        return m.group(1)+module_name+'\n'
    summary = re.sub('( +\S+ +\S+ +)\S+ +\((\S*nltk\S+)\)\n',
                     subfunc, summary)
    print summary

def usage(name):
    print """
    Usage: %s [-v] [-c] coverdir
    """ % name
    return 0

def cli():
    """
    The command line interface for the NLP test suite.  Usage::

        python nltk/test/__init__.py [-v] [-c] 
    """
    verbosity = 0
    coverage = False
    coverdir = None

    for arg in sys.argv[1:]:
        if arg[:1] == '-':
            if arg[1:].lower() in ('v', 'verbose'):
                verbosity += 1
            elif arg[1:].lower() in ('c', 'coverage'):
                coverage = True
            else:
                sys.exit(usage(sys.argv[0]))
        else:
            if coverdir: sys.exit(usage(sys.argv[0]))
            coverdir = arg
    if coverage:
        test_coverage(verbosity, coverdir)
    else:
        test(verbosity)

    global success
    try: return success
    except: return -1

if __name__ == '__main__':
    cli()

