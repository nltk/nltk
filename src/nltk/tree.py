# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# To do:
#   - How should we handle traces and/or movement?

"""

Classes for representing hierarchical language structures, such as
syntax trees and morphological trees.  A single tree is represented by
a nested structure of X{tree segments}, where each tree segment
encodes a single hierarchical grouping.  Each tree segment is encoded
with a L{Tree} object, or one of its two subclasses.

For most purposes, the base class C{Tree} is sufficient.  But in cases
where parent pointers are needed, the C{ParentedTree} or
C{MultiParentedTree} subclasses can be used.  The C{ParentedTree}
implementation is appropriate when each subtree has a unique parent;
and the C{MultiParentedTree} implementation is appropriate when a
single subtree can be shared by multiple parents.  Different tree
classes should never be mixed within a single tree.
"""

from nltk.token import Token, CharSpanLocation, FrozenToken, TreeContextPointer
from nltk.tokenizer import TokenizerI
from nltk import PropertyIndirectionMixIn
from nltk.probability import ProbabilisticMixIn, ImmutableProbabilisticMixIn
import re
from nltk.chktype import chktype
from nltk.chktype import classeq as _classeq
import types

######################################################################
## Trees
######################################################################

class Tree(list):
    """
    A hierarchical structure.

    Each C{Tree} represents a single hierarchical grouping of
    leaves and subtrees.  For example, each constituent in a syntax
    tree is represented by a single C{Tree}.

    The C{CHILDREN} property is used to record a C{Tree}'s
    hierarchical contents.  These contents are encoded as a C{list} of
    leaves and subtrees, where a X{leaf} is a basic (non-tree) value;
    and a X{subtree} is a nested C{Tree}.

    Any other properties that a C{Tree} defines are known as
    X{node properties}, and are used to add information about
    individual hierarchical groupings.  For eample, syntax trees use a
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
        if isinstance(children, str):
            raise TypeError, 'children should be a list, not a string'
        list.__init__(self, children)
        self.node = node

    #////////////////////////////////////////////////////////////
    # Convert, copy, & freeze
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

        @type tree: L{Tree}
        @param tree: The tree that should be converted.
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
    # Comparison operators
    #////////////////////////////////////////////////////////////

    def __cmp__(self, other):
        c = cmp(self.node, other.node)
        if c != 0: return c
        else: return list.__cmp__(self, other)
    def __eq__(self, other):
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
    # Indexing (w/ support for tree positions)
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
    
    def __detitem__(self, index):
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
        childstr = ' '.join([repr(c) for c in self])
        return '(%s: %s)' % (self.node, childstr)

    def __str__(self):
        return self.pp()

    def _ppflat(self, nodesep, parens):
        childstrs = []
        for child in self:
            if isinstance(child, Tree):
                childstrs.append(child._ppflat(nodesep, parens))
            else:
                childstrs.append('%s' % child)
        return '%s%s%s %s%s' % (parens[0], self.node, nodesep, 
                                ' '.join(childstrs), parens[1])

    def pp(self, margin=70, indent=0, nodesep=':', parens='()'):
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
        assert chktype(1, margin, types.IntType)
        assert chktype(2, indent, types.IntType)

        # Try writing it on one line.
        s = self._ppflat(nodesep, parens)
        if len(s)+indent < margin:
            return s

        # If it doesn't fit on one line, then write it on multi-lines.
        s = '%s%s%s' % (parens[0], self.node, nodesep)
        for child in self:
            if isinstance(child, Tree):
                s += '\n'+' '*(indent+2)+child.pp(margin, indent+2,
                                                  nodesep, parens)
            else:
                s += '\n'+' '*(indent+2)+repr(child)
        return s+parens[1]

    def pp_treebank(self, margin=70, indent=0):
        return self.pp(margin, indent, '')

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
    
    #////////////////////////////////////////////////////////////
    # Parsing
    #////////////////////////////////////////////////////////////
    
    # [XX] Note that this only parses treebank strings; it doesn't handle
    # strings like (S: (NP: I) (VP: (V: saw) (NP: him))), where there's a
    # ":" separator.
    # [staticmethod]
    def parse(s, leafparser=None):
        try:
            treetok, pos = Tree._parse(s, 0, leafparser)
            if pos != len(s): raise ValueError
            return treetok
        except:
            raise #ValueError('Bad treebank tree')
    parse = staticmethod(parse)

    def parse_iter(s, leafparser=None):
        pos = 0
        while pos < len(s):
            try:
                treetok, pos = Tree._parse(s, pos, leafparser)
                yield treetok
            except:
                raise
                raise ValueError('Bad treebank tree')
        # Check that we made it to the end of the string.
        if pos != len(s): raise ValueError('Bad treebank tree')
    parse_iter = staticmethod(parse_iter)

    def _parse(s, pos, leafparser):
        SPACE = re.compile(r'\s*')
        WORD = re.compile(r'\s*([^\s\(\)]*)\s*')

        # Skip any initial whitespace.
        pos = SPACE.match(s, pos).end()

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
                if len(stack) == 1: return stack[0], pos
                stack[-2].append(stack[-1])
                stack.pop()

            # Leaf token.
            else:
                match = WORD.match(s, pos)
                if leafparser is None: leaf = match.group(1)
                else: leaf = leafparser(match.group(1), (pos, match.end(1)))
                stack[-1].append(leaf)
                pos = match.end()

        raise ValueError, 'mismatched parens'
    _parse = staticmethod(_parse)

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
## Parented Trees & Multi-Parented Trees
######################################################################

class AbstractParentedTree(Tree):
    """
    A specialized list that is used to hold the children of a
    C{(Multi)ParentedTree}.  This class is responsible for
    maintaining all C{(Multi)ParentedTree}s' parent pointers.  In
    particular:
    
      - Whenever a new child is added, L{_setparent} is called,
        which should update that child's parent pointer to point
        at self.
        
      - Whenever a child is removed, L{_delparent} is called, which
        should remove the child's parent pointer to self.

    The definitions of C{_delparent} and C{_setparent} are left to the
    subclasses, since they need to be different for
    C{ParentedTree} and C{MultiParentedTree}.
    """
    def __init__(self, node, children):
        super(AbstractParentedTree, self).__init__(node, children)
        for child in children:
            self._setparent(child)
        
    #////////////////////////////////////////////////////////////
    # Parent management
    #////////////////////////////////////////////////////////////

    def _setparent(self, child):
        """
        Update C{child}'s parent pointer to point to self.
        """
        raise AssertionError, 'Abstract base class'
    
    def _delparent(self, child):
        """
        Remove self from C{child}'s parent pointer.
        """
        raise AssertionError, 'Abstract base class'

    #////////////////////////////////////////////////////////////
    # Methods that add/remove children
    #////////////////////////////////////////////////////////////
    # Every method that adds or removes a child must make
    # appropriate calls to _setparent() and _delparent().
    
    def __delitem__(self, i):
        self._delparent(self[i])
        super(AbstractParentedTree, self).__delitem__(i)

    def __delslice__(self, start, end):
        for i in range(start, end): self._delparent(self[i])
        super(AbstractParentedTree, self).__delslice__(start, end)

    def __setitem__(self, i, child):
        self._delparent(self[i])
        self._setparent(child)
        super(AbstractParentedTree, self).__setitem__(i, child)

    def __setslice__(self, start, end, children):
        for i in range(start, end): self._delparent(self[i])
        for val in children: self._setparent(val)
        super(AbstractParentedTree, self).__setslice__(start, end, children)

    def append(self, child):
        self._setparent(child)
        super(AbstractParentedTree, self).append(child)

    def extend(self, children):
        for val in children: self._setparent(val)
        super(AbstractParentedTree, self).extend(children)

    def insert(self, i, child):
        self._setparent(child)
        super(AbstractParentedTree, self).insert(i, child)

    def pop(self):
        self._delparent(self[-1])
        return super(AbstractParentedTree, self).pop()

    def remove(self, child):
        i = self.index(child)
        self._delparent(self[i])
        super(AbstractParentedTree, self).remove(child)

class ParentedTree(AbstractParentedTree):
    """
    A specialized version of C{Tree} that uses the C{PARENT}
    property to point a unique parent.  For C{ParentedTrees} with
    no parent, the C{PARENT} property's value is C{None}.

    Each C{ParentedTree} may have at most one parent.  In
    particular, subtrees may not be shared.  Any attempt to reuse a
    single C{ParentedTree} as a child of more than one parent (or
    as multiple children of the same parent) will cause a
    C{ValueError} exception to be raised.
    
    The C{PARENT} property is maintained automatically.  Any attempt
    to directly modify or delete it will result in a C{ValueError}
    exception.

    C{ParentedTrees} should never be used in the same tree as C{Trees}
    or C{MultiParentedTrees}.  Mixing tree implementations may result
    in incorrect parent pointers and in C{ValueError} exceptions.
    """
    def __init__(self, node, children):
        self._parent = None
        super(ParentedTree, self).__init__(node, children)

    def parent(self):
        return self._parent

    def _delparent(self, child):
        ## Ignore leaves.
        if not isinstance(child, Tree): return
        
        # Sanity check: child's parent should be self
        assert child._parent == self
        
        # Delete child's parent pointer.
        child._parent = None

    def _setparent(self, child):
        ## Ignore leaves.
        if not isinstance(child, Tree): return

        # If child is a non-parented tree, complain.
        if (isinstance(child, Tree) and
            not isinstance(child, ParentedTree)):
            raise ValueError('inserting a non-parented subtree '+
                             'into a parented tree')

        # If child already has a parent, complain.
        if child._parent is not None:
            raise ValueError, 'redefining parent for %r' % child

        # Set child's parent pointer.
        child._parent = self
        
class MultiParentedTree(AbstractParentedTree):
    """
    A specialized version of C{Tree} that uses the C{PARENTS}
    property to store a list of pointers to its parents.  For
    C{ParentedTrees} with no parent, the C{PARENTS} property's
    value is C{[]}.

    Each C{MultiParentedTree} may have zero or more parents.  In
    particular, subtrees may be shared.  If a single
    C{MultiParentedTree} is used as multiple children of the same
    parent, then that parent will appear multiple times in its
    C{PARENTS} property.
    
    The C{PARENTS} property is maintained automatically, and should
    never be directly modified.  

    C{MultiParentedTrees} should never be used in the same tree as
    C{Trees} or C{ParentedTrees}.  Mixing tree implementations may
    result in incorrect parent pointers and in C{ValueError}
    exceptions.
    """
    def __init__(self, node, children):
        self._parents = []
        super(MultiParentedTree, self).__init__(node, children)

    def parents(self):
        return self._parents[:]

    def _delparent(self, child):
        ## Ignore leaves.
        if not isinstance(child, Tree): return
        
        # Sanity check: one of child's parents should be self
        assert self in child._parents
        
        # Delete (one copy of) child's parent pointer to self
        child._parents.remove(self)

    def _setparent(self, child):
        # Ignore leaves.
        if not isinstance(child, Tree): return

        # If child is a non-parented tree, complain.
        if (isinstance(child, Tree) and
            not isinstance(child, MultiParentedTree)):
            raise ValueError('inserting a non-multi-parented subtree '+
                             'into a multi-parented tree')

        # Add self as a parent pointer.
        child._parents.append(self)
    
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
    import nltk.tree; reload(nltk.tree) # [XX]
    from nltk.util import DemoInterpreter
    d = DemoInterpreter()
    d.start('Tree Demo')
    d.silent("from nltk.tree import *")
    
    # Demonstrate tree parsing.
    d("s = '(S (NP (DT the) (NN cat)) "+
      "(VP (VBD ate) (NP (DT a) (NN cookie))))'")
    d("tree = Tree.parse(s)")
    d("print tree")
    d.hline()

    # Demonstrate basic tree accessors.
    d("print tree.node           # tree's constituant type")
    d("print tree[0]             # tree's first child")
    d("print tree[1]             # tree's second child")
    d("print tree.height()")
    d("print tree.leaves()")
    d("print tree[1]")
    d("print tree[1,1]")
    d("print tree[1,1,0]")
    d.hline()

    # Demonstrate tree modification.
    d("the_cat = tree[0]")
    d("the_cat.insert(1, Tree.parse('(JJ big)'))")
    d("print tree")
    d("tree[1,1,1] = Tree.parse('(NN cake)')")
    d("print tree")
    d.hline()

    # Demonstrate parented trees
    d("tree = ParentedTree.convert(tree)   # Add parent pointers")
    d("cake = tree[1,1,1]")
    d("print cake")
    d("# The parent() method returns a parent pointer:")
    d("print cake.parent()")
    d("print cake.parent().parent().parent()")
    d("# A root tree's parent is None:")
    d("print tree.parent()")
    d("t = ProbabilisticTree.convert(tree)")
    d("print t; print t.__class__")
    d.end()

    # Demonstrate the treebank token reader.
    d.silent("from nltk.tokenreader.treebank import *")
    d("reader = TreebankTokenReader(add_locs=True, SUBTOKENS='WORDS')")
    d("treetok = reader.read_token(tree.pp_treebank())")
    d("print treetok.exclude('LOC')['WORDS']")
    d("print treetok['TREE']")

if __name__ == '__main__':
    demo()
