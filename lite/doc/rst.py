#!/usr/bin/env python
#
# Natural Language Toolkit: Documentation generation script
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

r"""

This is a customized driver for converting docutils reStructuredText
documents into HTML and LaTeX.  It customizes the standard writers in
the following way:
    
    - Source code highlighting is added to all doctest blocks.  In
      the HTML output, highlighting is performed using css classes:
      'pysrc-prompt', 'pysrc-keyword', 'pysrc-string', 'pysrc-comment',
      and 'pysrc-output'.  In the LaTeX output, highlighting uses five
      new latex commands: '\pysrcprompt', '\pysrckeyword',
      '\pysrcstring', '\pysrccomment', and '\pyrcoutput'.
      De

"""

import re, os.path, textwrap
from optparse import OptionParser

import docutils.core, docutils.nodes
from docutils.writers import Writer
from docutils.writers.html4css1 import HTMLTranslator, Writer as HTMLWriter
from docutils.writers.latex2e import LaTeXTranslator, Writer as LaTeXWriter

######################################################################
#{ HTML Output
######################################################################

HTML_SETTINGS = {
    'stylesheet': '../nltkdoc.css',
    'stylesheet_path': None,
    }

class CustomizedHTMLWriter(HTMLWriter):
    def __init__(self):
        HTMLWriter.__init__(self)
        self.translator_class = CustomizedHTMLTranslator

class CustomizedHTMLTranslator(HTMLTranslator):
    def visit_doctest_block(self, node):
        pysrc = colorize_doctestblock(str(node[0]), self._markup_pysrc)
        self.body.append(self.starttag(node, 'pre', CLASS='doctest-block'))
        self.body.append(pysrc)
        self.body.append('\n</pre>\n')
        raise docutils.nodes.SkipNode

    def depart_doctest_block(self, node):
        pass
                          
    def _markup_pysrc(self, s, tag):
        return '<span class="pysrc-%s">%s</span>' % (tag, self.encode(s))

######################################################################
#{ LaTeX Output
######################################################################

LATEX_SETTINGS = {
    'output_encoding': 'utf-8',
    'output_encoding_error_handler': 'backslahsreplace',
    'use_latex_docinfo': True,
    'font_encoding': 'C10,T1',
    'stylesheet': '../definitions.sty'
    }

class CustomizedLaTeXWriter(LaTeXWriter):
    def __init__(self):
        LaTeXWriter.__init__(self)
        self.translator_class = CustomizedLaTeXTranslator

class CustomizedLaTeXTranslator(LaTeXTranslator):
    
    # Not sure why we need this, but the old Makefile did it so I will
    # to:
    encoding = '\\usepackage[%s,utf8x]{inputenc}\n'
    
    def __init__(self, document):
        LaTeXTranslator.__init__(self, document)
        # This needs to go before the \usepackage{inputenc}:
        self.head_prefix.insert(1, '\\usepackage[cjkgb]{ucs}\n')
        # Make sure we put these *before* the stylesheet include line.
        self.head_prefix.insert(-2, textwrap.dedent("""\
            % For Python source code:
            \\usepackage{alltt}
            % Python source code: Prompt
            \\newcommand{\\pysrcprompt}[1]{\\textbf{#1}}
            % Python source code: Source code
            \\newcommand{\\pysrckeyword}[1]{\\textbf{#1}}
            \\newcommand{\\pysrcstring}[1]{\\textit{#1}}
            \\newcommand{\\pysrcother}[1]{\\textbf{#1}}
            % Python source code: Comments
            \\newcommand{\\pysrccomment}[1]{\\textrm{#1}}
            % Python source code: Output
            \\newcommand{\\pysrcoutput}[1]{#1}\n"""))
        
    def visit_doctest_block(self, node):
        pysrc = colorize_doctestblock(str(node[0]), self._markup_pysrc)
        self.body.append('\\begin{alltt}\n')
        self.body.append(pysrc)
        self.body.append('\\end{alltt}\n')
        raise docutils.nodes.SkipNode

    def depart_doctest_block(self, node):
        pass

    def _markup_pysrc(self, s, tag):
        return '\\pysrc%s{%s}' % (tag, self.encode(s))
        
######################################################################
#{ Source Code Highlighting
######################################################################

# Regular expressions for colorize_doctestblock
_KEYWORDS = ["del", "from", "lambda", "return", "and", "or", "is", 
             "global", "not", "try", "break", "else", "if", "elif", 
             "while", "class", "except", "import", "pass", "raise",
             "continue", "finally", "in", "print", "def", "for"]
_KEYWORD = '|'.join([r'(\b%s\b)' % _KW for _KW in _KEYWORDS])
_STRING = '|'.join([r'("""("""|.*?((?!").)"""))', r'("("|.*?((?!").)"))',
                    r"('''('''|.*?[^\\']'''))", r"('('|.*?[^\\']'))"])
_COMMENT = '(#.*?$)'
_PROMPT = r'^\s*(?:>>>|\.\.\.)(?:\s|$)'

PROMPT_RE = re.compile('(%s)' % _PROMPT, re.MULTILINE | re.DOTALL)
'''The regular expression used to find Python prompts (">>>" and
"...") in doctest blocks.'''

DOCTEST_RE = re.compile(
    '(?P<STRING>%s)|(?P<COMMENT>%s)|(?P<KEYWORD>%s)|(?P<PROMPT>%s)|.+?' %
    (_STRING, _COMMENT, _KEYWORD, _PROMPT), re.MULTILINE | re.DOTALL)
'''The regular expression used by L{_doctest_sub} to colorize doctest
blocks.'''

def colorize_doctestblock(s, markup_func):
    """
    Colorize the given doctest string C{s} using C{markup_func()}.
    C{markup_func()} should be a function that takes a substring and a
    tag, and returns a colorized version of the substring.  E.g.:

        >>> def html_markup_func(s, tag):
        ...     return '<span class="%s">%s</span>' % (tag, s)

    The tags that will be passed to the markup function are: 
        - C{prompt} -- a Python prompt (>>> or ...)
        - C{keyword} -- a Python keyword (for, if, etc.)
        - C{string} -- a string literal
        - C{comment} -- a comment
        - C{output} -- the output from a doctest block.
        - C{other} -- anything else (does *not* include output.)
    """
    pysrc = [] # the source code part of a docstest block (lines)
    pyout = [] # the output part of a doctest block (lines)
    result = []
    out = result.append

    def subfunc(match):
        if match.group('PROMPT'):
            return markup_func(match.group(), 'prompt')
        if match.group('KEYWORD'):
            return markup_func(match.group(), 'keyword')
        if match.group('COMMENT'):
            return markup_func(match.group(), 'comment')
        if match.group('STRING') and '\n' not in match.group():
            return markup_func(match.group(), 'string')
        elif match.group('STRING'):
            # It's a multiline string; colorize the string & prompt
            # portion of each line.
            pieces = [markup_func(s, ['string','prompt'][i%2])
                      for i, s in enumerate(PROMPT_RE.split(match.group()))]
            return ''.join(pieces)
        else:
            return markup_func(match.group(), 'other')
    
    for line in s.split('\n')+['\n']:
        if PROMPT_RE.match(line):
            pysrc.append(line)
            if pyout:
                result.append(markup_func('\n'.join(pyout).strip(), 'output'))
                pyout = []
        else:
            pyout.append(line)
            if pysrc:
                pysrc = DOCTEST_RE.sub(subfunc, '\n'.join(pysrc))
                result.append(pysrc.strip())
                #result.append(markup_func(pysrc.strip(), 'python'))
                pysrc = []

    remainder = '\n'.join(pyout).strip()
    if remainder:
        result.append(markup_func(remainder, 'output'))
        
    return '\n'.join(result)

######################################################################
#{ Main Script
######################################################################

__version__ = 0.1

def parse_args():
    optparser = OptionParser()

    optparser.add_option("--html", 
        action="store_const", dest="action", const="html",
        help="Write HTML output.")
    optparser.add_option("--latex", "--tex",
        action="store_const", dest="action", const="latex",
        help="Write LaTeX output.")

    optparser.set_defaults(action='html')

    options, filenames = optparser.parse_args()
    return options, filenames

def main():
    options, filenames = parse_args()

    if options.action == 'html':
        writer = CustomizedHTMLWriter()
        output_ext = '.html'
        settings = HTML_SETTINGS
    elif options.action == 'latex':
        writer = CustomizedLaTeXWriter()
        output_ext = '.tex'
        settings = LATEX_SETTINGS
    else:
        assert 0, 'bad action'

    for in_file in filenames:
        out_file = os.path.splitext(in_file)[0] + output_ext
        if in_file == out_file: out_file += output_ext
        docutils.core.publish_file(source_path=in_file,
                                   destination_path=out_file,
                                   writer=writer,
                                   settings_overrides=settings)

if __name__ == '__main__':
    main()
