# Natural Language Toolkit: Unit Tests
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit tests for the NLTK modules.
"""

import unittest, sys

def _file_to_module(filename):
    """
    Convert a filename to a module name.  Warning: this may not be
    totally portable.  But it should at least work on unix/windows.
    """
    # Not portable.
    (base, ext) = filename.split('.')
    if ext != 'py': return None
    
    if base[-9:] == '/__init__':
        base = base[:-9]
    return '.'.join(base.split('/'))

def _load_modules(module_filenames, verbosity=0):
    """
    Given a list of module filenames, load the corresponding modules,
    and return a list of those modules.
    """
    # Extract the module names.
    mnames = [_file_to_module(name) for name in module_filenames
              if name[-16:] != 'test/__init__.py']

    modules = []
    if verbosity>0: print 'Importing modules:'
    for mname in mnames:
        if mname == None: continue
        if verbosity>0: print '  - %s' % mname
        try:
            exec('import '+mname)
            exec('modules.append('+mname+')')
        except:
            print 'Warning: failed to import %s' % mname

    return modules

def testsuite(module_names, verbosity=0):
    """
    Return a PyUnit testsuite for the NLP toolkit
    """
    modules = _load_modules(module_names, verbosity-1)

    if verbosity>0:
        print 'Testing modules:'
        for module in modules:
            print '  - %s' % module.__name__
            if verbosity>1: print '     ('+module.__file__+')'
    
    return unittest.TestSuite([m.testsuite() for m in modules]) 

def test(module_names, verbosity=0):
    """
    Run unit tests for the NLP toolkit; print results to stdout/stderr
    """
    # Ensure that the type safety level is set to full.
    import nltk.chktype
    nltk.chktype.type_safety_level(1000)
    
    import unittest
    runner = unittest.TextTestRunner(verbosity=verbosity)
    success = runner.run(testsuite(module_names, verbosity)).wasSuccessful()

    if not success:
        sys.exit(1)
        

def usage(name):
    print """
    Usage: %s [-v] files...
    """ % name
    return 0

if __name__ == '__main__':
    files = []
    verbosity = 0

    for arg in sys.argv[1:]:
        if arg[:1] == '-':
            if arg[1:] in ('v', 'V', 'verbose', 'Verbose', 'VERBOSE'):
                verbosity += 1
            else:
                sys.exit(usage(sys.argv[0]))
        else:
            files.append(arg)
    if files:
        test(files, verbosity)
    else:
        usage(sys.argv[0])
