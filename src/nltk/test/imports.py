# Natural Language Toolkit: Test that all imports are proper
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A test suite that checks to make sure that all imports of nltk modules
use absolute paths.

In particular, check that all nltk modules import each other with
statements that have the forms:

    >>> import nltk.token
    >>> from nltk.token import *

and not the forms:

    >>> import token
    >>> from token import *

This convention ensures that the same module is not imported twice,
even if it is imported with both relative and absolute paths.  It also
reduces confusion if two modules have the same relative name (eg
C{nltk.token} and C{nltk.speech.token}).
"""

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////

import unittest, re, os.path

class ImportTestCase(unittest.TestCase):    
    def testAbsoluteImportNames(self):
        'Check that all imports use absolute names.'
        self._failures = []
        self._find_nltk_modules()
        for path in self._paths:
            contents = open(path).read()
            self._curpath = path
            self._IMPORT_RE.sub(self._check_import, contents)

        if self._failures:
            msg = '\nBad imports: All nltk imports must use absolute names'
            for failure in self._failures:
                msg += '\n  - %s\n        >>> import %s' % failure
            self.fail(msg)

    # A regular expression that searches for import statements:
    _IMPORT_RE = re.compile(r'\bfrom\s+([\w.]+)\s+import' + '|' +
                            r'\bimport\s+([^;\n]*)')
    
    def _check_import(self, match):
        str = match.group(1) or match.group(2)
        str = re.sub(r'as\s+[\w.]+', '', str)
        modules = str.replace(',', ' ').split()
        for module in modules:
            if self._relnames.has_key(module):
                self._failures.append((self._curpath, module))
        
    def _find_nltk_modules(self):
        "@return: A list of all submodules of the nltk package."
        # Get the path of the nltk package.
        import nltk
        nltk_path = os.path.abspath(nltk.__path__[0])

        # Find all modules in nltk.
        self._paths = []
        os.path.walk(nltk_path, self._walker, self._paths)

        # Remove this module (its docstring would flag an error)
        imports_path = os.path.join(nltk_path, 'test', 'imports.py')
        del self._paths[self._paths.index(imports_path)]

        # Convert each module name to a package name.
        self._relnames = {}
        for path in self._paths:
            if path == os.path.join(nltk_path, '__init__.py'): continue
            for name in self._find_relnames(path, nltk_path):
                self._relnames[name] = 1

    def _find_relnames(self, path, root):
        if path.endswith('.py'): path = path[:-3]
        if path.endswith('.cc'): path = path[:-3]
        if path.endswith('.c'): path = path[:-2]
        if path.endswith('__init__'): path = os.path.split(path)[0]
        p1, p2 = os.path.split(path)
        if p1 == '' or p2 == '':
            raise ValueError('Failed to convert path to module')
        elif p1 == root:
            return [p2]
        else:
            return [p2] + ['%s.%s' % (base, p2)
                           for base in self._find_relnames(p1, root)]

    def _walker(self, paths, dirname, fnames):
        """
        A directory walker (for L{os.path.walk()}) that searches for
        nltk modules.
        @see: L{_find_nltk_modules}
        """
        paths += [os.path.join(dirname, fname)
                  for fname in fnames
                  if (fname.endswith('.py') or
                      fname.endswith('.cc') or
                      fname.endswith('.c'))]

def testsuite():
    t1 = unittest.makeSuite(ImportTestCase, 'test')
    return unittest.TestSuite( (t1,) )

def test():
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()
