#!/usr/bin/env python
#
## Natural Language Toolkit: Deprecated Function & Class Finder
#
# Copyright (C) 2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id:$

"""
This command-line tool takes a list of python files or directories,
and searches them for calls to deprecated NLTK functions, or uses of
deprecated NLTK classes.  For each use of a deprecated object it
finds, it will print out a warning containing the offending line, as
well as its line number and containing file name.  If the terminal has
color support (and if epydoc is installed), then the offending
identifier will be highlighted in red.
"""

#: Any deprecated names listed here will be treated as if they're
#: methods, even if they're really functions.  This is useful for
#: preventing lots of false postives for things like
#: "tokenize.word(...)" -- treating them as a method means they'll only
#: get flagged if they're preceeded by a dot.
TREAT_AS_METHOD = [
    #'word', 'line', 'whitespace'
    ]

######################################################################
# Imports
######################################################################

import os, re, sys, tokenize, textwrap
import nltk, nltk.corpus
from doctest import DocTestParser
from cStringIO import StringIO

######################################################################
# Regexps
######################################################################

#: A little over-simplified, but it'll do.
STRING_PAT = (r'\s*[ur]{0,2}(?:'
              '"""[\s\S]*?"""|'  '"[^"\n]+?"|'
              "'''[\s\S]*?'''|"  "'[^'\n]+?'" ")\s*")
STRING_RE = re.compile(STRING_PAT)

STRINGS_PAT = '%s(?:[+]?%s)*' % (STRING_PAT, STRING_PAT)
STRINGS_RE = re.compile(STRINGS_PAT)

# Define a regexp to search for deprecated definitions.
DEPRECATED_DEF_PAT = (
    r'^\s*@deprecated\s*\(\s*(%s)\s*\)\s*\n+' % STRINGS_PAT +
    r'\s*def\s*(\w+).*' + 
    r'|' +
    r'^\s*class\s*(\w+)\(.*Deprecated.*\):\s*')
DEPRECATED_DEF_RE = re.compile(DEPRECATED_DEF_PAT, re.MULTILINE)

CORPUS_READ_METHOD_RE = re.compile(
    '(%s)\.read\(' % ('|'.join(re.escape(n) for n in dir(nltk.corpus))))

######################################################################
# Globals
######################################################################
# Yes, it's bad programming practice, but this is a little hack
# script. :)  These get initialized by find_deprecated_defs.

deprecated_funcs = {}
deprecated_classes = {}
deprecated_methods = {}

try:
    from epydoc.cli import TerminalController
except ImportError:
    class TerminalController:
        def __getattr__(self, attr): return ''

term = TerminalController()

######################################################################
# Code
######################################################################

def strip_quotes(s):
    s = s.strip()
    while (s and (s[0] in "ur") and (s[-1] in "'\"")):
        s = s[1:]
    while (s and (s[0] in "'\"" and (s[0] == s[-1]))):
        s = s[1:-1]
    s = s.strip()
    return s

def find_deprecated_defs(pkg_dir):
    """
    Return a list of all functions marked with the @deprecated
    decorator, and classes with an immediate Deprecated base class, in
    all Python files in the given directory.
    """
    # Walk through the directory, finding python files.
    for root, dirs, files in os.walk(pkg_dir):
        for filename in files:
            if filename.endswith('.py'):
                # Search the file for any deprecated definitions.
                s = open(os.path.join(root, filename)).read()
                for m in DEPRECATED_DEF_RE.finditer(s):
                    if m.group(2):
                        name = m.group(2)
                        msg = ' '.join(strip_quotes(s) for s in
                                       STRING_RE.findall(m.group(1)))
                        msg = ' '.join(msg.split())
                        if (m.group()[0] in ' \t' or
                            name in TREAT_AS_METHOD):
                            deprecated_methods[name] = msg
                        else:
                            deprecated_funcs[name] = msg
                    else:
                        name = m.group(3)
                        m2 = STRING_RE.match(s, m.end())
                        if m2: msg = strip_quotes(m2.group())
                        else: msg = ''
                        msg = ' '.join(msg.split())
                        deprecated_classes[name] = msg

def print_deprecated_uses(paths):
    dep_names = set()
    dep_files = set()
    for path in sorted(paths):
        if os.path.isdir(path):
            dep_names.update(print_deprecated_uses(
                [os.path.join(path,f) for f in os.listdir(path)]))
        elif path.endswith('.py'):
            print_deprecated_uses_in(open(path).readline, path,
                                     dep_files, dep_names, 0)
        elif path.endswith('.doctest') or path.endswith('.txt'):
            for example in DocTestParser().get_examples(open(path).read()):
                ex = StringIO(example.source)
                print_deprecated_uses_in(ex.readline, path, dep_files,
                                         dep_names, example.lineno)
    return dep_names

def print_deprecated_uses_in(readline, path, dep_files, dep_names,
                             lineno_offset):
    tokiter = tokenize.generate_tokens(readline)
    context = ['']
    for (typ, tok, start, end, line) in tokiter:
        # Remember the previous line -- it might contain
        # the @deprecated decorator.
        if line is not context[-1]:
            context.append(line)
            if len(context) > 5: del context[0]
        esctok = re.escape(tok)
        # Ignore all tokens except deprecated names.
        if not (tok in deprecated_classes or
                (tok in deprecated_funcs and
                 re.search('\b%s\s*\(' % esctok, line)) or
                (tok in deprecated_methods and
                 re.search('(?!<\bself)[.]\s*%s\s*\(' % esctok, line))):
            continue
        # Hack: only complain about read if it's used after a corpus.
        if tok == 'read' and not CORPUS_READ_METHOD_RE.search(line):
            continue
        # Ignore deprecated definitions:
        if DEPRECATED_DEF_RE.search(''.join(context)):
            continue
        # Print a header for the first use in a file:
        if path not in dep_files:
            print '\n'+term.BOLD + path + term.NORMAL
            print '  %slinenum%s' % (term.YELLOW, term.NORMAL)
            dep_files.add(path)
        # Mark the offending token.
        dep_names.add(tok)
        if term.RED: sub = term.RED+tok+term.NORMAL
        elif term.BOLD: sub = term.BOLD+tok+term.NORMAL
        else: sub = '<<'+tok+'>>'
        line = re.sub(r'\b%s\b' % esctok, sub, line)
        # Print the offending line.
        print '  %s[%5d]%s %s' % (term.YELLOW, start[0]+lineno_offset,
                                  term.NORMAL, line.rstrip())


def main():
    paths = sys.argv[1:] or ['.']

    print 'Importing nltk...'
    try:
        import nltk
    except ImportError:
        print 'Unable to import nltk -- check your PYTHONPATH.'
        sys.exit(-1)
        
    print 'Finding definitions of deprecated funtions & classes in nltk...'
    find_deprecated_defs(nltk.__path__[0])

    print 'Looking for possible uses of deprecated funcs & classes...'
    dep_names = print_deprecated_uses(paths)

    if not dep_names:
        print 'No deprecated funcs or classes found!'
    else:
        print "\n"+term.BOLD+"What you should use instead:"+term.NORMAL
        for name in sorted(dep_names):
            msg = (deprecated_funcs.get(name, '') or
                   deprecated_classes.get(name, '') or
                   deprecated_methods.get(name, ''))
            print textwrap.fill(term.RED+name+term.NORMAL+': '+msg,
                                width=75, initial_indent=' '*2,
                                subsequent_indent=' '*6)
            
if __name__ == '__main__':
    main()
    
