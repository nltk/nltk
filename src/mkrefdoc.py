#!/usr/local/bin/python
#
# Natural Language Toolkit:
# Reference documentation construction
# Edward Loper
#
# Created [06/22/01 01:35 AM]
# $Id$
#

"""
This script uses epydoc to generate the reference documentation for
the nltk package.  If epydoc is not available, it prints an error
message and returns.

Usage::

  mkrefdoc <target> [-check] [-private] [-verbose]

<target> specifies the target directory into which the documentation
will be written.  If this directory does not exist, the script will
print an error and exit.  If the C{-check} flag is specified, epydoc
will issue warnings for anyobjects that are not fully documented.  If
the C{-private} flag is specified, epydoc will generate documentation
for private objects.
"""

import sys
from epydoc.epydoc import Documentation, HTML_Doc, DocChecker

def builddocs(verbose):
    if verbose: print 'Importing the toolkit...'
    import nltk, nltk.chktype, nltk.probability, nltk.set
    import nltk.tagger, nltk.token, nltk.tree
    
    if verbose: print 'Building documentation...'
    doc = Documentation()
    for module in [nltk, nltk.chktype, nltk.probability,
                   nltk.set, nltk.tagger, nltk.token, nltk.tree]:
        if verbose: print '  -', module.__name__
        doc.add(module)
    return doc

def writedocs(d, directory, private, verbose):
    if verbose: sys.stdout.write('Writing documentation...')
    import nltk
    title = "nltk version "+nltk.__version__
    converter = HTML_Doc(d, title, private)
    converter.write(directory, verbose)
    if verbose: print

def checkdocs(d, verbose):
    if verbose: print 'Checking documentation...'
    c = DocChecker(d)
    c.check(DocChecker.MODULE | DocChecker.CLASS |
            DocChecker.FUNC | DocChecker.DESCR)
    c.check(DocChecker.PARAM | DocChecker.VAR |
            DocChecker.IVAR | DocChecker.CVAR |
            DocChecker.RETURN | DocChecker.DESCR |
            DocChecker.TYPE)

def main():
    check = 0
    private = 0
    verbose = 0
    args = sys.argv[:]
    for arg in args[1:]:
        if arg.lower() in ('-c', '-check', '--check'):
            check = 1
            args.remove(arg)
        elif arg.lower() in ('-p', '-private', '--private'):
            private = 1
            args.remove(arg)
        elif arg.lower() in ('-v', '-verbose', '--verbose'):
            verbose = 1
            args.remove(arg)
    if len(args) != 2:
        print __doc__
        sys.exit()
    directory = args[1]

    docs = builddocs(verbose)
    if check: checkdocs(docs, verbose)
    writedocs(docs, directory, private, verbose)
    
if __name__ == '__main__': main()
    
