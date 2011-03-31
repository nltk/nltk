#!/usr/bin/env python
#
# Natural Language Toolkit: tree->image rendering script
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Render treebank-like tree strings, and write the output to an image
file.  Rendering is performed by L{tree_to_image()}.  Usage:

  - Simple trees use parenthases to define consituents.  The first
    element in each parenthasized substring is the node, and the
    remaining elements are subtrees or leaves::
      (S (NP John) (VP (V saw) (NP Mary)))
    
  - Constituents that should be drawn with a 'roof' (i.e., a triangle
    between the node & its children, rather than individual lines)
    are marked using angle brackets::
      (S (NP John) <VP saw Mary>)

  - Subscripting is done using underscore (similar to latex).  If
    the subscripted string is more than one character long, it should
    be enclosed in brackets::
      (S (NP Mary_i) (VP was (VP seen t_i)))

  - Substrings can be italicized by using '*...*' (like rst)::
      (S (NP *Mary_i*) (VP was (VP seen *t_i*)))

  - Backslash can be used to escape characters that would otherwise
    be treated as markup (i.e., any of C{'<>()_* '}).  Note that this
    list includes space::
      (S (NP Mary) (VP went (PP to (NP New\ York))))

Requires Imagemagick C{convert}.
"""

import re, sys, os
import tkinter.font
import tempfile
import pickle
from nltk.draw.util import SequenceWidget, TextWidget, SpaceWidget, CanvasFrame
from nltk.draw.tree import TreeSegmentWidget

CONVERT = 'convert'

# hackery..
# sys.path.append('/Users/edloper/nltk/')
if '/sw/bin' not in os.environ['PATH']:
    os.environ['PATH'] += ':/sw/bin'

def tokenize(s, regexp):
    pos = 0
    for m in re.finditer(regexp, s):
        if m.start() != pos: raise ValueError('tokenization error')
        pos = m.end()
        yield m.group()

def tree_to_widget(s, canvas):
    """
    Parse a tree string, and return a corresponding widget.  See the
    module docstring for the format of C{s}.
    """
    WORD = r'(\\\\|\\[^\\\n]|[^\\\s()<>])+'
    TOKEN_RE = re.compile(r'\(\s*%s|<\s*%s|\)|>|%s|\s+' % (WORD, WORD, WORD))
    stack = [[]]
    for tok in tokenize(s.strip(), TOKEN_RE):
        if tok.strip() == '':
            pass
        elif tok[:1] in '(<':
            node = word_to_widget(tok[1:].strip(), canvas,
                                  color='#004080', bold=True)
            roof = (tok[:1] == '<')
            stack[-1].append(dict(canvas=canvas, node=node, roof=roof))
            stack.append([])
        elif tok[:1] in ')>':
            subtrees = stack.pop()
            node_kwargs = stack[-1][-1]
            stack[-1][-1] = TreeSegmentWidget(subtrees=subtrees, **node_kwargs)
        else:
            leaf = word_to_widget(tok.strip(), canvas, color='#008040')
            stack[-1].append(leaf)

    if not len(stack) == 1 and len(stack[0])==1:
        raise ValueError('unbalanced parens?')
    return stack[0][0]

def parse_word(s):
    italic = False
    subscript = False
    piece = ''
    
    for tok in tokenize(s, r'\*|_{|}|_[^{]|\\.|[^\\_\*]'):
        if tok == '*':
            yield italic, subscript, piece
            italic = not italic
            piece = ''
        elif tok == '_{':
            yield italic, subscript, piece
            if subscript: raise ValueError('nested italics?')
            subscript = True
            piece = ''
        elif tok.startswith('_'):
            yield italic, subscript, piece
            if subscript: raise ValueError('nested italics?')
            yield italic, True, tok[1]
            piece = ''
        elif tok == '}':
            yield italic, subscript, piece
            if not subscript: raise ValueError('} needs backslash')
            subscript = False
            piece = ''
        else:
            piece += tok

    if italic: raise ValueError('expected * to close italics')
    if subscript: raise ValueError('expected }')
    yield italic, subscript, piece

metrics = {}
def word_to_widget(s, canvas, basefont='helvetica', fontsize=12,
                   color='black', bold=False):
    """
    Parse a node or leaf substring from a tree string, and return a
    corresponding widget.
    """
    textwidgets = []

    # Convert each piece of the word to a widget.
    for (italic, subscript, text) in parse_word(s):
        if not text: continue
        # Strip remaining backslashes
        text = re.sub(r'\\(.)', r'\1', text)
        # Decide on a font
        size = fontsize
        if subscript: size = size*2/3
        slant = italic and 'italic' or 'roman'
        weight = bold and 'bold' or 'normal'
        font = tkinter.font.Font(family=basefont, size=size, weight=weight,
                           slant=slant)
        # Create the widget.
        textwidgets.append(TextWidget(canvas, text, font=font, color=color))

        global metrics
        metrics[basefont, size, weight, slant] = font.metrics()

    # If there's only one widget, return it; otherwise, use a
    # sequencewidget to join them.  Use align=bottom to make
    # subscripting work.
    if len(textwidgets) == 0:
        w = SpaceWidget(canvas, 1, 1)
        w.set_width(0)
        w.set_height(0)
        return w
    if len(textwidgets) == 1:
        return textwidgets[0]
    else:
        return SequenceWidget(canvas, align='bottom', space=-2, *textwidgets)

try: _canvas_frame
except NameError: _canvas_frame = None

def tree_to_ps(s, outfile):
    global _canvas_frame
    if _canvas_frame is None:
        _canvas_frame = CanvasFrame()

    # May throw ValueError:
    widget = tree_to_widget(s, _canvas_frame.canvas())

    _canvas_frame.canvas()['scrollregion'] = (0, 0, 1, 1)
    _canvas_frame.add_widget(widget)
    _canvas_frame.print_to_file(outfile)
    bbox = widget.bbox()
    _canvas_frame.destroy_widget(widget)

    ## Testing..
    #for (key, val) in metrics.items():
    #    print key, '\n  ', val
    
    return bbox[2:]

# # hmm.. a bit of a hack..  e.g., no backslashing allowed:
# from nltk.parse.tree import bracket_parse, Tree
# def tree_to_qtree(s):
#     return '\Tree %s' % _tree_to_qtree(bracket_parse(s))
# def _tree_to_qtree(tree):
#     if isinstance(tree, Tree):
#         return ('[.{%s} %s ]' %
#                 (tree.node, ' '.join([_tree_to_qtree(c) for c in tree])))
#     elif tree.startswith('<') and tree.endswith('>'):
#         return '\qroof{%s}' % ' '.join([_tree_to_qtree(c) for c in tree])
#     else:
#         return tree

def run(cmd):
    try:
        import subprocess # requires python 2.4
        subprocess.call(cmd)
    except ImportError:
        os.system(' '.join(cmd))

def tree_to_image(s, outfile, density=72):
    """
    Render the treebank-like tree C{s}, and write the rendered image
    to an image file using the given filename (C{outfile}).  Output
    files are generated using Imagemagick 'convert', so the output
    file format will be automatically determined from C{outfile}'s
    extension.
    """
    # Check the cache.  If it's already there, do nothing.
    cachefile = os.path.join(os.path.split(outfile)[0],
                             'treecache.pickle')
    if os.path.exists(cachefile):
        try:
            cache = pickle.load(open(cachefile, 'r'))
            if cache.get(outfile, None) == (s, density):
                return
        except:
            cache = {}
    else:
        cache = {}

    psfile = tempfile.mktemp(suffix='.ps')
    try:
        # Draw the tree to postscript
        w,h = tree_to_ps(s, psfile)

        # Convert to the desired format.
        if outfile.endswith('.ps'):
            run(['cp', psfile, outfile])
        else:
            run([CONVERT,
                 '-density', str(density),
                 '-crop', '0x0',
                 psfile, outfile])

    finally:
        if os.path.exists(psfile):
            os.remove(psfile)

    # Update the cache
    cache[outfile] = (s, density)
    out = open(cachefile, 'w')
    pickle.dump(cache, out)
    out.close()

def cli():
    if len(sys.argv) != 3:
        print(('Usage: %s <infile> <outfile>' % sys.argv[0]))
        sys.exit(-1)
    print(('%s -> %s' % (sys.argv[1], sys.argv[2])))
    tree_to_image(open(sys.argv[1]).read(), sys.argv[2])

if __name__ == '__main__':
    cli()
