# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Nathan Bodenstab <bodenstab@cslu.ogi.edu> (tree transforms)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Class for representing hierarchical language structures, such as
syntax trees and morphological trees.
"""

import re, string
import nltk.cfg
from nltk.probability import ProbabilisticMixIn

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
        @return: a list containing this tree's leaves.
            The order reflects the order of the
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
                positions.extend((i,)+p for p in childpos)
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

        @rtype: list of C{Production}s
        """

        if not isinstance(self.node, str):
            raise TypeError, 'Productions can only be generated from trees having node labels that are strings'

        prods = [nltk.cfg.Production(nltk.cfg.Nonterminal(self.node), _child_names(self))]
        for child in self:
            if isinstance(child, Tree):
                prods += child.productions()
        return prods

    def pos(self):
        """
        @return: a list of tuples containing leaves and pre-terminals (part-of-speech tags).
            The order reflects the order of the
            leaves in the tree's hierarchical structure.
        @rtype: C{list} of C{tuples}
        """
        pos = []
        for child in self:
            if isinstance(child, Tree):
                pos.extend(child.pos())
            else:
                pos.append((child, self.node))
        return pos

    #////////////////////////////////////////////////////////////
    # Transforms
    #////////////////////////////////////////////////////////////

    def chomsky_normal_form(self, factor = "right", horzMarkov = None, vertMarkov = 0, childChar = "|", parentChar = "^"):
        """
        This method can modify a tree in three ways:
        1. Convert a tree into its Chomsky Normal Form (CNF) equivalent -- Every subtree
        has either two non-terminals or one terminal as its children.  This process
        requires the creation of more "artificial" non-terminal nodes.
        2. Markov (vertical) smoothing of children in new artificial nodes
        3. Horizontal (parent) annotation of nodes
      
        @param tree: The Tree to be modified
        @type  tree: C{Tree}
        @param factor: Right or left factoring method (default = "right")
        @type  factor: C{string} = [left|right]
        @param horzMarkov: Markov order for sibling smoothing in artificial nodes (None (default) = include all siblings)
        @type  horzMarkov: C{int} | None
        @param vertMarkov: Markov order for parent smoothing (0 (default) = no vertical annotation)
        @type  vertMarkov: C{int} | None
        @param childChar: A string used in construction of the artificial nodes, separating the head of the
                          original subtree from the child nodes that have yet to be expanded (default = "|")
        @type  childChar: C{string}
        @param parentChar: A string used to separate the node representation from its vertical annotation
        @type  parentChar: C{string}
        """
        from treetransforms import chomsky_normal_form
        chomsky_normal_form(self, factor, horzMarkov, vertMarkov, childChar, parentChar)
            
    def un_chomsky_normal_form(self, expandUnary = True, childChar = "|", parentChar = "^", unaryChar = "+"):
        """
        This method modifies the tree in three ways:
          1. Transforms a tree in Chomsky Normal Form back to its original structure (branching greater than two)
          2. Removes any parent annotation (if it exists)
          3. (optional) expands unary subtrees (if previously collapsed with collapseUnary(...) )
      
        @param tree: The Tree to be modified
        @type  tree: C{Tree}
        @param expandUnary: Flag to expand unary or not (default = True)
        @type  expandUnary: C{boolean}
        @param childChar: A string separating the head node from its children in an artificial node (default = "|")
        @type  childChar: C{string}
        @param parentChar: A sting separating the node label from its parent annotation (default = "^")
        @type  parentChar: C{string}
        @param unaryChar: A string joining two non-terminals in a unary production (default = "+")
        @type  unaryChar: C{string}  
        """
        from treetransforms import un_chomsky_normal_form
        un_chomsky_normal_form(self, expandUnary, childChar, parentChar, unaryChar)

    def collapse_unary(self, collapsePOS = False, collapseRoot = False, joinChar = "+"):
        """
        Collapse subtrees with a single child (ie. unary productions)
        into a new non-terminal (Tree node) joined by 'joinChar'.
        This is useful when working with algorithms that do not allow
        unary productions, and completely removing the unary productions
        would require loss of useful information.  The Tree is modified 
        directly (since it is passed by reference) and no value is returned.
    
        @param tree: The Tree to be collapsed
        @type  tree: C{Tree}
        @param collapsePOS: 'False' (default) will not collapse the parent of leaf nodes (ie. 
                            Part-of-Speech tags) since they are always unary productions
        @type  collapsePOS: C{boolean}
        @param collapseRoot: 'False' (default) will not modify the root production
                             if it is unary.  For the Penn WSJ treebank corpus, this corresponds
                             to the TOP -> productions.
        @type collapseRoot: C{boolean}
        @param joinChar: A string used to connect collapsed node values (default = "+")
        @type  joinChar: C{string}
        """
        from treetransforms import collapse_unary
        collapse_unary(self, collapsePOS, collapseRoot, joinChar)

    #////////////////////////////////////////////////////////////
    # Convert, copy
    #////////////////////////////////////////////////////////////

    # [classmethod]
    def convert(cls, val):
        """
        Convert a tree between different subtypes of Tree.  C{cls} determines
        which class will be used to encode the new tree.

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
        from nltk.draw.tree import draw_trees
        draw_trees(self)

    def __repr__(self):
        childstr = ", ".join(repr(c) for c in self)
        return 'Tree(%r, [%s])' % (self.node, childstr)

    def __str__(self):
        return self.pprint()

    def pprint(self, margin=70, indent=0, nodesep='', parens='()', quotes=False):
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
        s = self._pprint_flat(nodesep, parens, quotes)
        if len(s)+indent < margin:
            return s

        # If it doesn't fit on one line, then write it on multi-lines.
        if isinstance(self.node, basestring): 
            s = '%s%s%s' % (parens[0], self.node, nodesep)
        else:
            s = '%s%r%s' % (parens[0], self.node, nodesep)
        for child in self:
            if isinstance(child, Tree):
                s += '\n'+' '*(indent+2)+child.pprint(margin, indent+2,
                                                  nodesep, parens, quotes)
            elif isinstance(child, tuple):
                s += '\n'+' '*(indent+2)+ "/".join(child)
            elif isinstance(child, str) and not quotes:
                s += '\n'+' '*(indent+2)+ '%s' % child
            else:
                s += '\n'+' '*(indent+2)+ '%r' % child
        return s+parens[1]

    def pprint_latex_qtree(self):
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
        return r'\Tree ' + self.pprint(indent=6, nodesep='', parens=('[.', ' ]'))
    
    def _pprint_flat(self, nodesep, parens, quotes):
        childstrs = []
        for child in self:
            if isinstance(child, Tree):
                childstrs.append(child._pprint_flat(nodesep, parens, quotes))
            elif isinstance(child, tuple):
                childstrs.append("/".join(child))
            elif isinstance(child, str) and not quotes:
                childstrs.append('%s' % child)
            else:
                childstrs.append('%r' % child)
        if isinstance(self.node, basestring):
            return '%s%s%s %s%s' % (parens[0], self.node, nodesep, 
                                    string.join(childstrs), parens[1])
        else:
            return '%s%r%s %s%s' % (parens[0], self.node, nodesep, 
                                    string.join(childstrs), parens[1])

# [xx] this really should do some work to make sure self.node isn't
# modified.
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
        return '%s (p=%s)' % (self.pprint(margin=60), self.prob())
    def __cmp__(self, other):
        c = Tree.__cmp__(self, other)
        if c != 0: return c
        return cmp(self.prob(), other.prob())
    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return Tree.__eq__(self, other) and self.prob()==other.prob()
    def __ne__(self, other):
        return not (self == other)
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
        return '%s [%s]' % (Tree.__repr__(self), self.prob())
    def __str__(self):
        return '%s [%s]' % (self.pprint(margin=60), self.prob())
    def __cmp__(self, other):
        c = Tree.__cmp__(self, other)
        if c != 0: return c
        return cmp(self.prob(), other.prob())
    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return Tree.__eq__(self, other) and self.prob()==other.prob()
    def __ne__(self, other):
        return not (self == other)
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
            names.append(nltk.cfg.Nonterminal(child.node))
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
    
    if pos == len(s): # only got whitespace
        return None

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
                return tree
            stack[-2].append(stack[-1]) # [xx] might get index out of range
            stack.pop()

        # Leaf token.
        else:
            match = WORD.match(s, pos)
            leaf = match.group(1)
            stack[-1].append(leaf)
            pos = match.end()

    raise ValueError, 'mismatched parens'


def sinica_parse(s):
    """
    Parse a Sinica Treebank string and return a tree.  Trees are represented as nested brackettings,
    as shown in the following example (X represents a Chinese character):
    S(goal:NP(Head:Nep:XX)|theme:NP(Head:Nhaa:X)|quantity:Dab:X|Head:VL2:X)#0(PERIODCATEGORY)

    @return: A tree corresponding to the string representation.
    @rtype: C{tree}
    @param s: The string to be converted
    @type s: C{string}
    """
    tokens = re.split(r'([()| ])', s)
    for i in range(len(tokens)):
        if tokens[i] == '(':
            tokens[i-1], tokens[i] = tokens[i], tokens[i-1]     # pull nonterminal inside parens
        elif ':' in tokens[i]:
            fields = tokens[i].split(':')
            if len(fields) == 2:                                # non-terminal
                tokens[i] = fields[1]
            else:
                tokens[i] = "(" + fields[-2] + " " + fields[-1] + ")"
        elif tokens[i] == '|':
            tokens[i] = ''

    treebank_string = string.join(tokens)
    return bracket_parse(treebank_string)

#    s = re.sub(r'^#[^\s]*\s', '', s)  # remove leading identifier
#    s = re.sub(r'\w+:', '', s)       # remove role tags

#    return s

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
    
    from nltk import tree

    # Demonstrate tree parsing.
    s = '(S (NP (DT the) (NN cat)) (VP (VBD ate) (NP (DT a) (NN cookie))))'
    t = tree.bracket_parse(s)
    print "Convert bracketed string into tree:"
    print t
    print t.__repr__()

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

    # Tree transforms
    print "Collapse unary:"
    t.collapse_unary()
    print t
    print "Chomsky normal form:"
    t.chomsky_normal_form()
    print t
    print

    # Demonstrate probabilistic trees.
    pt = tree.ProbabilisticTree('x', ['y', 'z'], prob=0.5)
    print "Probabilistic Tree:"
    print pt
    print

    # Demonstrate parsing of treebank output format.
    t = tree.bracket_parse(t.pprint())
    print "Convert tree to bracketed string and back again:"
    print t
    print

    # Demonstrate LaTeX output
    print "LaTeX output:"
    print t.pprint_latex_qtree()
    print

    # Demonstrate Productions
    print "Production output:"
    print t.productions()
    print

    # Demonstrate tree nodes containing objects other than strings
    t.node = ('test', 3)
    print t

if __name__ == '__main__':
    demo()

__all__ = ['ImmutableProbabilisticTree', 'ImmutableTree', 'ProbabilisticMixIn',
           'ProbabilisticTree', 'Tree', 'bracket_parse', 'demo', 'sinica_parse']
