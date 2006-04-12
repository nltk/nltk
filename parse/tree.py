# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Class for representing hierarchical language structures, such as
syntax trees and morphological trees.
"""

import re, types
from nltk_lite import tokenize
from nltk_lite.parse import cfg
from nltk_lite.probability import ProbabilisticMixIn

######################################################################
## Trees
######################################################################

class Tree(list):
    """
    A hierarchical structure.

    Each C{Tree} represents a single hierarchical grouping of
    leaves and subtrees.  For example, each constituent in a syntax
    tree is represented by a single C{Tree}.

    A tree's children are encoded as a C{list} of leaves and subtrees,
    where a X{leaf} is a basic (non-tree) value; and a X{subtree} is a
    nested C{Tree}.

    Any other properties that a C{Tree} defines are known as
    X{node properties}, and are used to add information about
    individual hierarchical groupings.  For example, syntax trees use a
    NODE property to label syntactic constituents with phrase tags,
    such as \"NP\" and\"VP\".

    Several C{Tree} methods use X{tree positions} to specify
    children or descendants of a tree.  Tree positions are defined as
    follows:

      - The tree position M{i} specifies a C{Tree}'s M{i}th child.
      - The tree position C{()} specifies the C{Tree} itself.
      - If C{M{p}} is the tree position of descendant M{d}, then
        C{M{p}+(M{i})} specifies the C{M{i}}th child of M{d}.
    
    I.e., every tree position is either a single index C{M{i}},
    specifying C{self[M{i}]}; or a sequence C{(M{i1}, M{i2}, ...,
    M{iN})}, specifying
    C{self[M{i1}][M{i2}]...[M{iN}]}.
    """
    def __init__(self, node, children):
        """
        Construct a new tree.
        """
        if isinstance(children, (str, unicode)):
            raise TypeError, 'children should be a list, not a string'
        list.__init__(self, children)
        self.node = node

    #////////////////////////////////////////////////////////////
    # Comparison operators
    #////////////////////////////////////////////////////////////

    def __cmp__(self, other):
        c = cmp(self.node, other.node)
        if c != 0: return c
        else: return list.__cmp__(self, other)
    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return self.node == other.node and list.__eq__(self, other)
    def __ne__(self, other):
        return not (self == other)
    def __lt__(self, other):
        return cmp(self, other) < 0
    def __le__(self, other):
        return cmp(self, other) <= 0
    def __gt__(self, other):
        return cmp(self, other) > 0
    def __ge__(self, other):
        return cmp(self, other) >= 0
    
    #////////////////////////////////////////////////////////////
    # Disabled list operations
    #////////////////////////////////////////////////////////////

    def __mul__(self, v):
        raise TypeError('Tree does not support multiplication')
    def __rmul__(self, v):
        raise TypeError('Tree does not support multiplication')
    def __add__(self, v):
        raise TypeError('Tree does not support addition')
    def __radd__(self, v):
        raise TypeError('Tree does not support addition')

    #////////////////////////////////////////////////////////////
    # Indexing (with support for tree positions)
    #////////////////////////////////////////////////////////////

    def __getitem__(self, index):
        if isinstance(index, int):
            return list.__getitem__(self, index)
        else:
            if len(index) == 0:
                return self
            elif len(index) == 1:
                return self[int(index[0])]
            else:
                return self[int(index[0])][index[1:]]
    
    def __setitem__(self, index, value):
        if isinstance(index, int):
            return list.__setitem__(self, index, value)
        else:
            if len(index) == 0:
                raise IndexError('The tree position () may not be '
                                 'assigned to.')
            elif len(index) == 1:
                self[index[0]] = value
            else:
                self[index[0]][index[1:]] = value
    
    def __delitem__(self, index):
        if isinstance(index, int):
            return list.__delitem__(self, index)
        else:
            if len(index) == 0:
                raise IndexError('The tree position () may not be deleted.')
            elif len(index) == 1:
                del self[index[0]]
            else:
                del self[index[0]][index[1:]]
    
    #////////////////////////////////////////////////////////////
    # Basic tree operations
    #////////////////////////////////////////////////////////////
    
    def leaves(self):
        """
        @return: a list containing this tree's leaves.  The
            order of leaves in the tuple reflects the order of the
            leaves in the tree's hierarchical structure.
        @rtype: C{list}
        """
        leaves = []
        for child in self:
            if isinstance(child, Tree):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return leaves

    def flatten(self):
        """
        @return: a tree consisting of this tree's root connected directly to
            its leaves, omitting all intervening non-terminal nodes.
        @rtype: C{Tree}
        """
        return Tree(self.node, self.leaves())

    def height(self):
        """
        @return: The height of this tree.  The height of a tree
            containing no children is 1; the height of a tree
            containing only leaves is 2; and the height of any other
            tree is one plus the maximum of its children's
            heights.
        @rtype: C{int}
        """
        max_child_height = 0
        for child in self:
            if isinstance(child, Tree):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = max(max_child_height, 1)
        return 1 + max_child_height

    def treepositions(self, order='preorder'):
        """
        @param order: One of: C{preorder}, C{postorder}, C{bothorder},
            C{leaves}.
        """
        positions = []
        if order in ('preorder', 'bothorder'): positions.append( () )
        for i, child in enumerate(self):
            if isinstance(child, Tree):
                childpos = child.treepositions(order)
                positions.extend([(i,)+p for p in childpos])
            else:
                positions.append( (i,) )
        if order in ('postorder', 'bothorder'): positions.append( () )
        return positions

    def subtrees(self, filter=None):
        """
        Generate all the subtrees of this tree, optionally restricted
        to trees matching the filter function.
        @type: filter: C{function}
        @param: filter: the function to filter all local trees
        """
        if not filter or filter(self):
            yield self
        for child in self:
            if isinstance(child, Tree):
                for subtree in child.subtrees(filter):
                    yield subtree

    def productions(self):
        """
        Generate the productions that correspond to the non-terminal nodes of the tree.
        For each subtree of the form (P: C1 C2 ... Cn) this produces a production of the
        form P -> C1 C2 ... Cn.

        @rtype: list of C{cfg.Production}s
        """

        prods = [cfg.Production(cfg.Nonterminal(self.node), _child_names(self))]
        for child in self:
            if isinstance(child, Tree):
                prods += child.productions()
        return prods

    #////////////////////////////////////////////////////////////
    # Convert, copy
    #////////////////////////////////////////////////////////////

    # [classmethod]
    def convert(cls, val):
        """
        Convert a tree between different types.  C{cls} determines
        which class will be used to encode the new tree.  E.g.:

           >>> # Convert tree into a Tree:
           >>> tree = Tree.convert(tree)
           >>> # Convert tree into a ParentedTree:
           >>> tree = ParentedTree.convert(tree)
           >>> # Convert tree into a MultiParentedTree:
           >>> tree = MultiParentedTree.convert(tree)

        @type val: L{Tree}
        @param val: The tree that should be converted.
        @return: The new C{Tree}.
        """
        if isinstance(val, Tree):
            children = [cls.convert(child) for child in val]
            return cls(val.node, children)
        else:
            return val
    convert = classmethod(convert)

    def copy(self, deep=False):
        if not deep: return self.__class__(self.node, self)
        else: return self.__class__.convert(self)

    def _frozen_class(self): return ImmutableTree
    def freeze(self, leaf_freezer=None):
        frozen_class = self._frozen_class()
        if leaf_freezer is None:
            newcopy = frozen_class.convert(self)
        else:
            newcopy = self.copy(deep=True)
            for pos in newcopy.treepositions('leaves'):
                newcopy[pos] = leaf_freezer(newcopy[pos])
            newcopy = frozen_class.convert(newcopy)
        hash(newcopy) # Make sure the leaves are hashable.
        return newcopy

    #////////////////////////////////////////////////////////////
    # Visualization & String Representation
    #////////////////////////////////////////////////////////////
    
    def draw(self):
        """
        Open a new window containing a graphical diagram of this tree.
        """
        from nltk_lite.draw.tree import draw_trees
        draw_trees(self)

    def __repr__(self):
        childstr = ' '.join([repr(c) for c in self])
        return '(%s: %s)' % (self.node, childstr)

    def __str__(self):
        return self.pp()

    def _ppflat(self, nodesep, parens, quotes):
        childstrs = []
        for child in self:
            if isinstance(child, Tree):
                childstrs.append(child._ppflat(nodesep, parens, quotes))
            elif isinstance(child, str) and not quotes:
                childstrs.append('%s' % child)
            else:
                childstrs.append('%s' % child.__repr__())
        return '%s%s%s %s%s' % (parens[0], self.node, nodesep, 
                                ' '.join(childstrs), parens[1])

    def pp(self, margin=70, indent=0, nodesep=':', parens='()', quotes=True):
        """
        @return: A pretty-printed string representation of this tree.
        @rtype: C{string}
        @param margin: The right margin at which to do line-wrapping.
        @type margin: C{int}
        @param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lines.
        @type indent: C{int}
        @param nodesep: A string that is used to separate the node
            from the children.  E.g., the default value C{':'} gives
            trees like C{(S: (NP: I) (VP: (V: saw) (NP: it)))}.
        """

        # Try writing it on one line.
        s = self._ppflat(nodesep, parens, quotes)
        if len(s)+indent < margin:
            return s

        # If it doesn't fit on one line, then write it on multi-lines.
        s = '%s%s%s' % (parens[0], self.node, nodesep)
        for child in self:
            if isinstance(child, Tree):
                s += '\n'+' '*(indent+2)+child.pp(margin, indent+2,
                                                  nodesep, parens, quotes)
            else:
                s += '\n'+' '*(indent+2)+repr(child)
        return s+parens[1]

    def pp_treebank(self, margin=70, indent=0):
        return self.pp(margin, indent, nodesep='', quotes=False)

    def pp_latex_qtree(self):
        r"""
        Returns a representation of the tree compatible with the
        LaTeX qtree package. This consists of the string C{\Tree}
        followed by the parse tree represented in bracketed notation.

        For example, the following result was generated from a parse tree of
        the sentence C{The announcement astounded us}::

          \Tree [.I'' [.N'' [.D The ] [.N' [.N announcement ] ] ]
              [.I' [.V'' [.V' [.V astounded ] [.N'' [.N' [.N us ] ] ] ] ] ] ]

        See U{http://www.ling.upenn.edu/advice/latex.html} for the LaTeX
        style file for the qtree package.

        @return: A latex qtree representation of this tree.
        @rtype: C{string}
        """
        return r'\Tree ' + self.pp(indent=6, nodesep='', parens=('[.', ' ]'))
    

class ImmutableTree(Tree):
    def __setitem__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __setslice__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __delitem__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __delslice__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __iadd__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __imul__(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def append(self, v):
        raise ValueError, 'ImmutableTrees may not be modified'
    def extend(self, v):
        raise ValueError, 'ImmutableTrees may not be modified'
    def pop(self, v=None):
        raise ValueError, 'ImmutableTrees may not be modified'
    def remove(self, v):
        raise ValueError, 'ImmutableTrees may not be modified'
    def reverse(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def sort(self):
        raise ValueError, 'ImmutableTrees may not be modified'
    def __hash__(self):
        return hash( (self.node, tuple(self)) )


######################################################################
## Probabilistic trees
######################################################################
class ProbabilisticTree(Tree, ProbabilisticMixIn):
    def __init__(self, node, children, **prob_kwargs):
        ProbabilisticMixIn.__init__(self, **prob_kwargs)
        Tree.__init__(self, node, children)

    # We have to patch up these methods to make them work right:
    def _frozen_class(self): return ImmutableProbabilisticTree
    def __repr__(self):
        return '%s (p=%s)' % (Tree.__repr__(self), self.prob())
    def __str__(self):
        return '%s (p=%s)' % (self.pp(margin=60), self.prob())
    def __cmp__(self, other):
        c = Tree.__cmp__(self, other)
        if c != 0: return c
        return cmp(self.prob(), other.prob())
    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return Tree.__eq__(self, other) and self.prob()==other.prob()
    def copy(self, deep=False):
        if not deep: return self.__class__(self.node, self, prob=self.prob())
        else: return self.__class__.convert(self)
    def convert(cls, val):
        if isinstance(val, Tree):
            children = [cls.convert(child) for child in val]
            if isinstance(val, ProbabilisticMixIn):
                return cls(val.node, children, prob=val.prob())
            else:
                return cls(val.node, children, prob=1.0)
        else:
            return val
    convert = classmethod(convert)

class ImmutableProbabilisticTree(ImmutableTree, ProbabilisticMixIn):
    def __init__(self, node, children, **prob_kwargs):
        ProbabilisticMixIn.__init__(self, **prob_kwargs)
        ImmutableTree.__init__(self, node, children)

    # We have to patch up these methods to make them work right:
    def _frozen_class(self): return ImmutableProbabilisticTree
    def __repr__(self):
        return '%s (p=%s)' % (Tree.__repr__(self), self.prob())
    def __str__(self):
        return '%s (p=%s)' % (self.pp(margin=60), self.prob())
    def __cmp__(self, other):
        c = Tree.__cmp__(self, other)
        if c != 0: return c
        return cmp(self.prob(), other.prob())
    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return Tree.__eq__(self, other) and self.prob()==other.prob()
    def copy(self, deep=False):
        if not deep: return self.__class__(self.node, self, prob=self.prob())
        else: return self.__class__.convert(self)
    def convert(cls, val):
        if isinstance(val, Tree):
            children = [cls.convert(child) for child in val]
            if isinstance(val, ProbabilisticMixIn):
                return cls(val.node, children, prob=val.prob())
            else:
                return cls(val.node, children, prob=1)
        else:
            return val
    convert = classmethod(convert)


def _child_names(tree):
    names = []
    for child in tree:
        if isinstance(child, Tree):
            names.append(cfg.Nonterminal(child.node))
        else:
            names.append(child)
    return names

######################################################################
## Parsing
######################################################################
    
def bracket_parse(s):
    """
    Parse a treebank string and return a tree.  Trees are represented
    as nested brackettings, e.g. (S (NP (NNP John)) (VP (V runs))).

    @return: A tree corresponding to the string representation.
    @rtype: C{tree}
    @param s: The string to be converted
    @type s: C{string}
    """

    SPACE = re.compile(r'\s*')
    WORD = re.compile(r'\s*([^\s\(\)]*)\s*')

    # Skip any initial whitespace.
    pos = SPACE.match(s).end()

    stack = []
    while pos < len(s):
        # Beginning of a tree/subtree.
        if s[pos] == '(':
            match = WORD.match(s, pos+1)
            stack.append(Tree(match.group(1), []))
            pos = match.end()

        # End of a tree/subtree.
        elif s[pos] == ')':
            pos = SPACE.match(s, pos+1).end()
            if len(stack) == 1:
                if pos != len(s): raise ValueError
                tree = stack[0]
                # If the tree has an extra level with node='', then get
                # rid of it.  (E.g., "((S (NP ...) (VP ...)))")
                if tree.node == '':
                    tree = tree[0]
                else:
                    return tree
            stack[-2].append(stack[-1])
            stack.pop()

        # Leaf token.
        else:
            match = WORD.match(s, pos)
            leaf = match.group(1)
            stack[-1].append(leaf)
            pos = match.end()

    raise ValueError, 'mismatched parens'

def chunk(s, chunk_node="NP", top_node="S"):
    """
    Divide a string of chunked tagged text into
    chunks and unchunked tokens, and produce a C{Tree}.
    Chunks are marked by square brackets (C{[...]}).  Words are
    deliniated by whitespace, and each word should have the form
    C{I{text}/I{tag}}.  Words that do not contain a slash are
    assigned a C{tag} of C{None}.

    @return: A tree corresponding to the string representation.
    @rtype: C{tree}
    @param s: The string to be converted
    @type s: C{string}
    @param chunk_node: The label to use for chunk nodes
    @type chunk_node: C{string}
    @param top_node: The label to use for the root of the tree
    @type top_node: C{string}
    """

    WORD_OR_BRACKET = re.compile(r'\[|\]|[^\[\]\s]+')
    VALID = re.compile(r'^([^\[\]]+|\[[^\[\]]*\])*$')

    if not VALID.match(s):
        raise ValueError, 'Invalid token string (bad brackets)'
        
    stack = [Tree(top_node, [])]
    for match in WORD_OR_BRACKET.finditer(s):
        text = match.group()
        if text[0] == '[':
            chunk = Tree(chunk_node, [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif text[0] == ']':
            stack.pop()
        else:
            slash = text.rfind('/')
            if slash >= 0:
                tok = (text[:slash], text[slash+1:])
            else:
                tok = (text, None)
            stack[-1].append(tok)

    return stack[0]

### CONLL

_LINE_RE = re.compile('(\S+)\s+(\S+)\s+([IOB])-?(\S+)?')
def conll_chunk(s, chunk_types=("NP",), top_node="S"):
    """
    @return: A chunk structure for a single sentence
        encoded in the given CONLL 2000 style string.
    @rtype: L{Tree}
    """

    stack = [Tree(top_node, [])]

    for lineno, line in enumerate(tokenize.line(s)):

        # Decode the line.
        match = _LINE_RE.match(line)
        if match is None:
            raise ValueError, 'Error on line %d' % lineno
        (word, tag, state, chunk_type) = match.groups()

        # If it's a chunk type we don't care about, treat it as O.
        if (chunk_types is not None and
            chunk_type not in chunk_types):
            state = 'O'

        # For "Begin"/"Outside", finish any completed chunks -
        # also do so for "Inside" which don't match the previous token.
        mismatch_I = state == 'I' and chunk_type != stack[-1].node
        if state in 'BO' or mismatch_I:
            if len(stack) == 2: stack.pop()

        # For "Begin", start a new chunk.
        if state == 'B' or mismatch_I:
            chunk = Tree(chunk_type, [])
            stack[-1].append(chunk)
            stack.append(chunk)

        # Add the new word token.
        stack[-1].append((word, tag))

    return stack[0]

### IEER

_IEER_DOC_RE = re.compile(r'<DOC>\s*'
                          r'(<DOCNO>\s*(?P<docno>.+?)\s*</DOCNO>\s*)?'
                          r'(<DOCTYPE>\s*(?P<doctype>.+?)\s*</DOCTYPE>\s*)?'
                          r'(<DATE_TIME>\s*(?P<date_time>.+?)\s*</DATE_TIME>\s*)?'
                          r'<BODY>\s*'
                          r'(<HEADLINE>\s*(?P<headline>.+?)\s*</HEADLINE>\s*)?'
                          r'<TEXT>(?P<text>.*?)</TEXT>\s*'
                          r'</BODY>\s*</DOC>\s*', re.DOTALL)

_IEER_TYPE_RE = re.compile('<b_\w+\s+[^>]*?type="(?P<type>\w+)"')

def _ieer_read_text(s, top_node):
    stack = [Tree(top_node, [])]
    for piece_m in re.finditer('<[^>]+>|[^\s<]+', s):
        piece = piece_m.group()
        try:
            if piece.startswith('<b_'):
                m = _IEER_TYPE_RE.match(piece)
                if m is None: print 'XXXX', piece
                chunk = Tree(m.group('type'), [])
                stack[-1].append(chunk)
                stack.append(chunk)
            elif piece.startswith('<e_'):
                stack.pop()
#           elif piece.startswith('<'):
#               print "ERROR:", piece
#               raise ValueError # Unexpected HTML
            else:
                stack[-1].append(piece)
        except (IndexError, ValueError):
            raise ValueError('Bad IEER string (error at character %d)' %
                             piece_m.start())
    if len(stack) != 1:
        raise ValueError('Bad IEER string')
    return stack[0]

def ieer_chunk(s, chunk_types = ['LOCATION', 'ORGANIZATION', 'PERSON', 'DURATION',
               'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE'], top_node="S"):
    """
    Convert a string of chunked tagged text in the IEER named
    entity format into a chunk structure.  Chunks are of several
    types, LOCATION, ORGANIZATION, PERSON, DURATION, DATE, CARDINAL,
    PERCENT, MONEY, and MEASURE.

    @return: A chunk structure containing the chunked tagged text that is
        encoded in the given IEER style string.
    @rtype: L{Tree}
    """

    # Try looking for a single document.  If that doesn't work, then just
    # treat everything as if it was within the <TEXT>...</TEXT>.
    m = _IEER_DOC_RE.match(s)
    if m:
        return {
            'text': _ieer_read_text(m.group('text'), top_node),
            'docno': m.group('docno'),
            'doctype': m.group('doctype'),
            'date_time': m.group('date_time'),
            'headline': m.group('headline')
            }
    else:
        return _ieer_read_text(s, top_node)


######################################################################
## Demonstration
######################################################################
        
def demo():
    """
    A demonstration showing how C{Tree}s and C{Tree}s can be
    used.  This demonstration creates a C{Tree}, and loads a
    C{Tree} from the L{treebank<nltk.corpus.treebank>} corpus,
    and shows the results of calling several of their methods.
    """
    
    from nltk_lite.parse import tree

    # Demonstrate tree parsing.
    s = '(S (NP (DT the) (NN cat)) (VP (VBD ate) (NP (DT a) (NN cookie))))'
    t = tree.bracket_parse(s)
    print "Convert bracketed string into tree:"
    print t

    print "Display tree properties:"
    print t.node           # tree's constituent type
    print t[0]             # tree's first child
    print t[1]             # tree's second child
    print t.height()
    print t.leaves()
    print t[1]
    print t[1,1]
    print t[1,1,0]

    # Demonstrate tree modification.
    the_cat = t[0]
    the_cat.insert(1, tree.bracket_parse('(JJ big)'))
    print "Tree modification:"
    print t
    t[1,1,1] = tree.bracket_parse('(NN cake)')
    print t
    print

    # Demonstrate probabilistic trees.

    pt = tree.ProbabilisticTree('x', ['y', 'z'], prob=0.5)
    print "Probabilistic Tree:"
    print pt
    print

    # Demonstrate parsing of treebank output format.
    t = tree.bracket_parse(t.pp_treebank())[0]
    print "Convert tree to bracketed string and back again:"
    print t.pp_treebank()
    print t
    print

    # Demonstrate LaTeX output
    print "LaTeX output:"
    print t.pp_latex_qtree()
    print

    # Demonstrate Productions
    print "Production output:"
    print t.productions()
    print

    # Demonstrate chunk parsing
    s = "[ Pierre/NNP Vinken/NNP ] ,/, [ 61/CD years/NNS ] old/JJ ,/, will/MD join/VB [ the/DT board/NN ] ./."
    from tree import chunk
    print "Chunk Parsing:"
    print chunk(s, chunk_node='NP').pp()
    print

    s = """
These DT B-NP
research NN I-NP
protocols NNS I-NP
offer VBP B-VP
to TO B-PP
the DT B-NP
patient NN I-NP
not RB O
only RB O
the DT B-NP
very RB I-NP
best JJS I-NP
therapy NN I-NP
which WDT B-NP
we PRP B-NP
have VBP B-VP
established VBN I-VP
today NN B-NP
but CC B-NP
also RB I-NP
the DT B-NP
hope NN I-NP
of IN B-PP
something NN B-NP
still RB B-ADJP
better JJR I-ADJP
. . O
"""
    print conll_chunk(s, chunk_types=('NP', 'PP', 'VP')).pp()


if __name__ == '__main__':
    demo()
