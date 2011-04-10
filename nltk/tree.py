# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Nathan Bodenstab <bodenstab@cslu.ogi.edu> (tree transforms)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Class for representing hierarchical language structures, such as
syntax trees and morphological trees.
"""

# TODO: add LabelledTree (can be used for dependency trees)

import re
import string

from grammar import Production, Nonterminal
from probability import ProbabilisticMixIn
from util import slice_bounds

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
    def __new__(cls, node_or_str=None, children=None):
        if node_or_str is None:
            return list.__new__(cls) # used by copy.deepcopy
        if children is None:
            if not isinstance(node_or_str, basestring):
                raise TypeError("%s: Expected a node value and child list "
                                "or a single string" % cls.__name__)
            return cls.parse(node_or_str)
        else:
            if (isinstance(children, basestring) or
                not hasattr(children, '__iter__')):
                raise TypeError("%s() argument 2 should be a list, not a "
                                "string" % cls.__name__)
            return list.__new__(cls, node_or_str, children)
    
    def __init__(self, node_or_str, children=None):
        """
        Construct a new tree.  This constructor can be called in one
        of two ways:

          - C{Tree(node, children)} constructs a new tree with the
            specified node value and list of children.
            
          - C{Tree(s)} constructs a new tree by parsing the string
            C{s}.  It is equivalent to calling the class method
            C{Tree.parse(s)}.
        """
        # Because __new__ may delegate to Tree.parse(), the __init__
        # method may end up getting called more than once (once when
        # constructing the return value for Tree.parse; and again when
        # __new__ returns).  We therefore check if `children` is None
        # (which will cause __new__ to call Tree.parse()); if so, then
        # __init__ has already been called once, so just return.
        if children is None: return
        
        list.__init__(self, children)
        self.node = node_or_str

    #////////////////////////////////////////////////////////////
    # Comparison operators
    #////////////////////////////////////////////////////////////

    def __eq__(self, other):
        if not isinstance(other, Tree): return False
        return self.node == other.node and list.__eq__(self, other)
    def __ne__(self, other):
        return not (self == other)
    def __lt__(self, other):
        if not isinstance(other, Tree): return False
        return self.node < other.node or list.__lt__(self, other)
    def __le__(self, other):
        if not isinstance(other, Tree): return False
        return self.node <= other.node or list.__le__(self, other)
    def __gt__(self, other):
        if not isinstance(other, Tree): return True
        return self.node > other.node or list.__gt__(self, other)
    def __ge__(self, other):
        if not isinstance(other, Tree): return False
        return self.node >= other.node or list.__ge__(self, other)
    
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
        if isinstance(index, (int, slice)):
            return list.__getitem__(self, index)
        else:
            if len(index) == 0:
                return self
            elif len(index) == 1:
                return self[int(index[0])]
            else:
                return self[int(index[0])][index[1:]]
    
    def __setitem__(self, index, value):
        if isinstance(index, (int, slice)):
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
        if isinstance(index, (int, slice)):
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
        @type filter: C{function}
        @param filter: the function to filter all local trees
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

        if not isinstance(self.node, basestring):
            raise TypeError, 'Productions can only be generated from trees having node labels that are strings'

        prods = [Production(Nonterminal(self.node), _child_names(self))]
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

    def leaf_treeposition(self, index):
        """
        @return: The tree position of the C{index}-th leaf in this
            tree.  I.e., if C{tp=self.leaf_treeposition(i)}, then
            C{self[tp]==self.leaves()[i]}.
        
        @raise IndexError: If this tree contains fewer than C{index+1}
            leaves, or if C{index<0}.
        """
        if index < 0: raise IndexError('index must be non-negative')

        stack = [(self, ())]
        while stack:
            value, treepos = stack.pop()
            if not isinstance(value, Tree):
                if index == 0: return treepos
                else: index -= 1
            else:
                for i in range(len(value)-1, -1, -1):
                    stack.append( (value[i], treepos+(i,)) )

        raise IndexError('index must be less than or equal to len(self)')

    def treeposition_spanning_leaves(self, start, end):
        """
        @return: The tree position of the lowest descendant of this
            tree that dominates C{self.leaves()[start:end]}.
        @raise ValueError: if C{end <= start}
        """
        if end <= start:
            raise ValueError('end must be greater than start')
        # Find the tree positions of the start & end leaves, and
        # take the longest common subsequence.
        start_treepos = self.leaf_treeposition(start)
        end_treepos = self.leaf_treeposition(end-1)
        # Find the first index where they mismatch:
        for i in range(len(start_treepos)):
            if i == len(end_treepos) or start_treepos[i] != end_treepos[i]:
                return start_treepos[:i]
        return start_treepos

    #////////////////////////////////////////////////////////////
    # Transforms
    #////////////////////////////////////////////////////////////

    def chomsky_normal_form(self, factor = "right", horzMarkov = None, vertMarkov = 0, childChar = "|", parentChar = "^"):
        """
        This method can modify a tree in three ways:
        
          1. Convert a tree into its Chomsky Normal Form (CNF)
             equivalent -- Every subtree has either two non-terminals
             or one terminal as its children.  This process requires
             the creation of more"artificial" non-terminal nodes.
          2. Markov (vertical) smoothing of children in new artificial
             nodes
          3. Horizontal (parent) annotation of nodes
      
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
        
          1. Transforms a tree in Chomsky Normal Form back to its
             original structure (branching greater than two)
          2. Removes any parent annotation (if it exists)
          3. (optional) expands unary subtrees (if previously
             collapsed with collapseUnary(...) )
          
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
    # Parsing
    #////////////////////////////////////////////////////////////

    @classmethod
    def parse(cls, s, brackets='()', parse_node=None, parse_leaf=None,
              node_pattern=None, leaf_pattern=None, 
              remove_empty_top_bracketing=False):
        """
        Parse a bracketed tree string and return the resulting tree.
        Trees are represented as nested brackettings, such as::

          (S (NP (NNP John)) (VP (V runs)))

        @type s: C{str}
        @param s: The string to parse
        
        @type brackets: length-2 C{str}
        @param brackets: The bracket characters used to mark the
            beginning and end of trees and subtrees.
            
        @type parse_node: C{function}
        @type parse_leaf: C{function}
        @param parse_node, parse_leaf: If specified, these functions
            are applied to the substrings of C{s} corresponding to
            nodes and leaves (respectively) to obtain the values for
            those nodes and leaves.  They should have the following
            signature:

               >>> parse_node(str) -> value

            For example, these functions could be used to parse nodes
            and leaves whose values should be some type other than
            string (such as L{FeatStruct <nltk.featstruct.FeatStruct>}).
            Note that by default, node strings and leaf strings are
            delimited by whitespace and brackets; to override this
            default, use the C{node_pattern} and C{leaf_pattern}
            arguments.

        @type node_pattern: C{str}
        @type leaf_pattern: C{str}
        @param node_pattern, leaf_pattern: Regular expression patterns
            used to find node and leaf substrings in C{s}.  By
            default, both nodes patterns are defined to match any
            sequence of non-whitespace non-bracket characters.

        @type remove_empty_top_bracketing: C{bool}
        @param remove_empty_top_bracketing: If the resulting tree has
            an empty node label, and is length one, then return its
            single child instead.  This is useful for treebank trees,
            which sometimes contain an extra level of bracketing.

        @return: A tree corresponding to the string representation C{s}.
            If this class method is called using a subclass of C{Tree},
            then it will return a tree of that type.
        @rtype: C{Tree}
        """
        if not isinstance(brackets, basestring) or len(brackets) != 2:
            raise TypeError('brackets must be a length-2 string')
        if re.search('\s', brackets):
            raise TypeError('whitespace brackets not allowed')
        # Construct a regexp that will tokenize the string.
        open_b, close_b = brackets
        open_pattern, close_pattern = (re.escape(open_b), re.escape(close_b))
        if node_pattern is None:
            node_pattern = '[^\s%s%s]+' % (open_pattern, close_pattern)
        if leaf_pattern is None:
            leaf_pattern = '[^\s%s%s]+' % (open_pattern, close_pattern)
        token_re = re.compile('%s\s*(%s)?|%s|(%s)' % (
            open_pattern, node_pattern, close_pattern, leaf_pattern))
        # Walk through each token, updating a stack of trees.
        stack = [(None, [])] # list of (node, children) tuples
        for match in token_re.finditer(s):
            token = match.group()
            # Beginning of a tree/subtree
            if token[0] == open_b:
                if len(stack) == 1 and len(stack[0][1]) > 0:
                    cls._parse_error(s, match, 'end-of-string')
                node = token[1:].lstrip()
                if parse_node is not None: node = parse_node(node)
                stack.append((node, []))
            # End of a tree/subtree
            elif token == close_b:
                if len(stack) == 1:
                    if len(stack[0][1]) == 0:
                        cls._parse_error(s, match, open_b)
                    else:
                        cls._parse_error(s, match, 'end-of-string')
                node, children = stack.pop()
                stack[-1][1].append(cls(node, children))
            # Leaf node
            else:
                if len(stack) == 1:
                    cls._parse_error(s, match, open_b)
                if parse_leaf is not None: token = parse_leaf(token)
                stack[-1][1].append(token)

        # check that we got exactly one complete tree.
        if len(stack) > 1:
            cls._parse_error(s, 'end-of-string', close_b)
        elif len(stack[0][1]) == 0:
            cls._parse_error(s, 'end-of-string', open_b)
        else:
            assert stack[0][0] is None
            assert len(stack[0][1]) == 1
        tree = stack[0][1][0]
        
        # If the tree has an extra level with node='', then get rid of
        # it.  E.g.: "((S (NP ...) (VP ...)))"
        if remove_empty_top_bracketing and tree.node == '' and len(tree) == 1:
            tree = tree[0]
        # return the tree.
        return tree

    @classmethod
    def _parse_error(cls, s, match, expecting):
        """
        Display a friendly error message when parsing a tree string fails.
        @param s: The string we're parsing.
        @param match: regexp match of the problem token.
        @param expecting: what we expected to see instead.
        """
        # Construct a basic error message
        if match == 'end-of-string':
            pos, token = len(s), 'end-of-string'
        else:
            pos, token = match.start(), match.group()
        msg = '%s.parse(): expected %r but got %r\n%sat index %d.' % (
            cls.__name__, expecting, token, ' '*12, pos)
        # Add a display showing the error token itsels:
        s = s.replace('\n', ' ').replace('\t', ' ')
        offset = pos
        if len(s) > pos+10:
            s = s[:pos+10]+'...'
        if pos > 10:
            s = '...'+s[pos-10:]
            offset = 13
        msg += '\n%s"%s"\n%s^' % (' '*16, s, ' '*(17+offset))
        raise ValueError(msg)
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
        return '%s(%r, [%s])' % (self.__class__.__name__, self.node, childstr)

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
            elif isinstance(child, basestring) and not quotes:
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
            elif isinstance(child, basestring) and not quotes:
                childstrs.append('%s' % child)
            else:
                childstrs.append('%r' % child)
        if isinstance(self.node, basestring):
            return '%s%s%s %s%s' % (parens[0], self.node, nodesep, 
                                    string.join(childstrs), parens[1])
        else:
            return '%s%r%s %s%s' % (parens[0], self.node, nodesep, 
                                    string.join(childstrs), parens[1])

class ImmutableTree(Tree):
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        super(ImmutableTree, self).__init__(node_or_str, children)
        # Precompute our hash value.  This ensures that we're really
        # immutable.  It also means we only have to calculate it once.
        try:
            self._hash = hash( (self.node, tuple(self)) )
        except (TypeError, ValueError):
            raise ValueError("ImmutableTree's node value and children "
                             "must be immutable")
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
        return self._hash

    def _set_node(self, node):
        """Set self._node.  This will only succeed the first time the
        node value is set, which should occur in Tree.__init__()."""
        if hasattr(self, 'node'):
            raise ValueError, 'ImmutableTrees may not be modified'
        self._node = node
    def _get_node(self):
        return self._node
    node = property(_get_node, _set_node)

######################################################################
## Parented trees
######################################################################

class AbstractParentedTree(Tree):
    """
    An abstract base class for L{Tree}s that automatically maintain
    pointers to their parents.  These parent pointers are updated
    whenever any change is made to a tree's structure.  Two subclasses
    are currently defined:

      - L{ParentedTree} is used for tree structures where each subtree
        has at most one parent.  This class should be used in cases
        where there is no"sharing" of subtrees.
        
      - L{MultiParentedTree} is used for tree structures where a
        subtree may have zero or more parents.  This class should be
        used in cases where subtrees may be shared.

    Subclassing
    ===========
    The C{AbstractParentedTree} class redefines all operations that
    modify a tree's structure to call two methods, which are used by
    subclasses to update parent information:
    
      - L{_setparent()} is called whenever a new child is added.
      - L{_delparent()} is called whenever a child is removed.
    """
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        super(AbstractParentedTree, self).__init__(node_or_str, children)
        # iterate over self, and *not* children, because children
        # might be an iterator.
        for i, child in enumerate(self):
            if isinstance(child, Tree):
                self._setparent(child, i, dry_run=True)
        for i, child in enumerate(self):
            if isinstance(child, Tree):
                self._setparent(child, i)
        
    #////////////////////////////////////////////////////////////
    # Parent management
    #////////////////////////////////////////////////////////////

    def _setparent(self, child, index, dry_run=False):
        """
        Update C{child}'s parent pointer to point to self.  This
        method is only called if C{child}'s type is L{Tree}; i.e., it
        is not called when adding a leaf to a tree.  This method is
        always called before the child is actually added to C{self}'s
        child list.

        @type child: L{Tree}
        @type index: C{int}
        @param index: The index of C{child} in C{self}.
        @raise TypeError: If C{child} is a tree with an impropriate
            type.  Typically, if C{child} is a tree, then its type needs
            to match C{self}'s type.  This prevents mixing of
            different tree types (single-parented, multi-parented, and
            non-parented).
        @param dry_run: If true, the don't actually set the child's
            parent pointer; just check for any error conditions, and
            raise an exception if one is found.
        """
        raise AssertionError('Abstract base class')
    
    def _delparent(self, child, index):
        """
        Update C{child}'s parent pointer to not point to self.  This
        method is only called if C{child}'s type is L{Tree}; i.e., it
        is not called when removing a leaf from a tree.  This method
        is always called before the child is actually removed from
        C{self}'s child list.
        
        @type child: L{Tree}
        @type index: C{int}
        @param index: The index of C{child} in C{self}.
        """
        raise AssertionError('Abstract base class')

    #////////////////////////////////////////////////////////////
    # Methods that add/remove children
    #////////////////////////////////////////////////////////////
    # Every method that adds or removes a child must make
    # appropriate calls to _setparent() and _delparent().

    def __delitem__(self, index):
        # del ptree[start:stop]
        if isinstance(index, slice):
            start, stop = slice_bounds(self, index)
            # Clear all the children pointers.
            for i in xrange(start, stop):
                if isinstance(self[i], Tree):
                    self._delparent(self[i], i)
            # Delete the children from our child list.
            super(AbstractParentedTree, self).__delitem__(index)
            
        # del ptree[i]
        elif isinstance(index, int):
            if index < 0: index += len(self)
            if index < 0: raise IndexError('index out of range')
            # Clear the child's parent pointer.
            if isinstance(self[index], Tree):
                self._delparent(self[index], index)
            # Remove the child from our child list.
            super(AbstractParentedTree, self).__delitem__(index)

        # del ptree[()]
        elif len(index) == 0:
            raise IndexError('The tree position () may not be deleted.')
        
        # del ptree[(i,)]
        elif len(index) == 1:
            del self[index[0]]
            
        # del ptree[i1, i2, i3]
        else:
            del self[index[0]][index[1:]]

    def __setitem__(self, index, value):
        # ptree[start:stop] = value
        if isinstance(index, slice):
            start, stop = slice_bounds(self, index)
            # make a copy of value, in case it's an iterator
            if not isinstance(value, (list, tuple)):
                value = list(value)
            # Check for any error conditions, so we can avoid ending
            # up in an inconsistent state if an error does occur.
            for i, child in enumerate(value):
                if isinstance(child, Tree):
                    self._setparent(child, start+i, dry_run=True)
            # clear the child pointers of all parents we're removing
            for i in xrange(start, stop):
                if isinstance(self[i], Tree):
                    self._delparent(self[i], i)
            # set the child pointers of the new children.  We do this
            # after clearing *all* child pointers, in case we're e.g.
            # reversing the elements in a tree.
            for i, child in enumerate(value):
                if isinstance(child, Tree):
                    self._setparent(child, start+i)
            # finally, update the content of the child list itself.
            super(AbstractParentedTree, self).__setitem__(index, value)

        # ptree[i] = value
        elif isinstance(index, int):
            if index < 0: index += len(self)
            if index < 0: raise IndexError('index out of range')
            # if the value is not changing, do nothing.
            if value is self[index]:
                return
            # Set the new child's parent pointer.
            if isinstance(value, Tree):
                self._setparent(value, index)
            # Remove the old child's parent pointer
            if isinstance(self[index], Tree):
                self._delparent(self[index], index)
            # Update our child list.
            super(AbstractParentedTree, self).__setitem__(index, value)

        # ptree[()] = value
        elif len(index) == 0:
            raise IndexError('The tree position () may not be assigned to.')

        # ptree[(i,)] = value
        elif len(index) == 1:
            self[index[0]] = value

        # ptree[i1, i2, i3] = value
        else:
            self[index[0]][index[1:]] = value

    def append(self, child):
        if isinstance(child, Tree):
            self._setparent(child, len(self))
        super(AbstractParentedTree, self).append(child)

    def extend(self, children):
        for child in children:
            if isinstance(child, Tree):
                self._setparent(child, len(self))
            super(AbstractParentedTree, self).append(child)

    def insert(self, index, child):
        # Handle negative indexes.  Note that if index < -len(self),
        # we do *not* raise an IndexError, unlike __getitem__.  This
        # is done for consistency with list.__getitem__ and list.index.
        if index < 0: index += len(self)
        if index < 0: index = 0
        # Set the child's parent, and update our child list.
        if isinstance(child, Tree):
            self._setparent(child, index)
        super(AbstractParentedTree, self).insert(index, child)

    def pop(self, index=-1):
        if index < 0: index += len(self)
        if index < 0: raise IndexError('index out of range')
        if isinstance(self[index], Tree):
            self._delparent(self[index], index)
        return super(AbstractParentedTree, self).pop(index)

    # n.b.: like `list`, this is done by equality, not identity!
    # To remove a specific child, use del ptree[i].
    def remove(self, child):
        index = self.index(child)
        if isinstance(self[index], Tree):
            self._delparent(self[index], index)
        super(AbstractParentedTree, self).remove(child)

    # We need to implement __getslice__ and friends, even though
    # they're deprecated, because otherwise list.__getslice__ will get
    # called (since we're subclassing from list).  Just delegate to
    # __getitem__ etc., but use max(0, start) and max(0, stop) because
    # because negative indices are already handled *before*
    # __getslice__ is called; and we don't want to double-count them.
    if hasattr(list, '__getslice__'):
        def __getslice__(self, start, stop):
            return self.__getitem__(slice(max(0, start), max(0, stop)))
        def __delslice__(self, start, stop):
            return self.__delitem__(slice(max(0, start), max(0, stop)))
        def __setslice__(self, start, stop, value):
            return self.__setitem__(slice(max(0, start), max(0, stop)), value)

class ParentedTree(AbstractParentedTree):
    """
    A L{Tree} that automatically maintains parent pointers for
    single-parented trees.  The following read-only property values
    are automatically updated whenever the structure of a parented
    tree is modified: L{parent}, L{parent_index}, L{left_sibling},
    L{right_sibling}, L{root}, L{treeposition}.

    Each C{ParentedTree} may have at most one parent.  In
    particular, subtrees may not be shared.  Any attempt to reuse a
    single C{ParentedTree} as a child of more than one parent (or
    as multiple children of the same parent) will cause a
    C{ValueError} exception to be raised.
    
    C{ParentedTrees} should never be used in the same tree as C{Trees}
    or C{MultiParentedTrees}.  Mixing tree implementations may result
    in incorrect parent pointers and in C{TypeError} exceptions.
    """
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        
        self._parent = None
        """The parent of this Tree, or C{None} if it has no parent."""

        super(ParentedTree, self).__init__(node_or_str, children)

    def _frozen_class(self): return ImmutableParentedTree
    
    #/////////////////////////////////////////////////////////////////
    # Properties
    #/////////////////////////////////////////////////////////////////

    def _get_parent_index(self):
        if self._parent is None: return None
        for i, child in enumerate(self._parent):
            if child is self: return i
        assert False, 'expected to find self in self._parent!'

    def _get_left_sibling(self):
        parent_index = self._get_parent_index()
        if self._parent and parent_index > 0:
            return self._parent[parent_index-1]
        return None # no left sibling
    
    def _get_right_sibling(self):
        parent_index = self._get_parent_index()
        if self._parent and parent_index < (len(self._parent)-1):
            return self._parent[parent_index+1]
        return None # no right sibling
    
    def _get_treeposition(self):
        if self._parent is None: return ()
        else: return (self._parent._get_treeposition() +
                      (self._get_parent_index(),))

    def _get_root(self):
        if self._parent is None: return self
        else: return self._parent._get_root()

    parent = property(lambda self: self._parent, doc="""
        The parent of this tree, or C{None} if it has no parent.""")
    
    parent_index = property(_get_parent_index, doc="""
        The index of this tree in its parent.  I.e.,
        C{ptree.parent[ptree.parent_index] is ptree}.  Note that
        C{ptree.parent_index} is not necessarily equal to
        C{ptree.parent.index(ptree)}, since the C{index()} method
        returns the first child that is I{equal} to its argument.""")

    left_sibling = property(_get_left_sibling, doc="""
        The left sibling of this tree, or C{None} if it has none.""")

    right_sibling = property(_get_right_sibling, doc="""
        The right sibling of this tree, or C{None} if it has none.""")

    root = property(_get_root, doc="""
        The root of this tree.  I.e., the unique ancestor of this tree
        whose parent is C{None}.  If C{ptree.parent} is C{None}, then
        C{ptree} is its own root.""")

    treeposition = property(_get_treeposition, doc="""
        The tree position of this tree, relative to the root of the
        tree.  I.e., C{ptree.root[ptree.treeposition] is ptree}.""")
    treepos = treeposition # [xx] alias -- which name should we use?

    #/////////////////////////////////////////////////////////////////
    # Parent Management
    #/////////////////////////////////////////////////////////////////

    def _delparent(self, child, index):
        # Sanity checks
        assert isinstance(child, ParentedTree)
        assert self[index] is child
        assert child._parent is self

        # Delete child's parent pointer.
        child._parent = None

    def _setparent(self, child, index, dry_run=False):
        # If the child's type is incorrect, then complain.
        if not isinstance(child, ParentedTree):
            raise TypeError('Can not insert a non-ParentedTree '+
                            'into a ParentedTree')

        # If child already has a parent, then complain.
        if child._parent is not None:
            raise ValueError('Can not insert a subtree that already '
                             'has a parent.')

        # Set child's parent pointer & index.
        if not dry_run:
            child._parent = self

class MultiParentedTree(AbstractParentedTree):
    """
    A L{Tree} that automatically maintains parent pointers for
    multi-parented trees.  The following read-only property values are
    automatically updated whenever the structure of a multi-parented
    tree is modified: L{parents}, L{parent_indices}, L{left_siblings},
    L{right_siblings}, L{roots}, L{treepositions}.
    
    Each C{MultiParentedTree} may have zero or more parents.  In
    particular, subtrees may be shared.  If a single
    C{MultiParentedTree} is used as multiple children of the same
    parent, then that parent will appear multiple times in its
    C{parents} property.

    C{MultiParentedTrees} should never be used in the same tree as
    C{Trees} or C{ParentedTrees}.  Mixing tree implementations may
    result in incorrect parent pointers and in C{TypeError} exceptions.
    """
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        
        self._parents = []
        """A list of this tree's parents.  This list should not
           contain duplicates, even if a parent contains this tree
           multiple times."""

        super(MultiParentedTree, self).__init__(node_or_str, children)

    def _frozen_class(self): return ImmutableMultiParentedTree
    
    #/////////////////////////////////////////////////////////////////
    # Properties
    #/////////////////////////////////////////////////////////////////

    def _get_parent_indices(self):
        return [(parent, index)
                for parent in self._parents
                for index, child in enumerate(parent)
                if child is self]

    def _get_left_siblings(self):
        return [parent[index-1]
                for (parent, index) in self._get_parent_indices()
                if index > 0]

    def _get_right_siblings(self):
        return [parent[index+1]
                for (parent, index) in self._get_parent_indices()
                if index < (len(parent)-1)]

    def _get_roots(self):
        return self._get_roots_helper({}).values()

    def _get_roots_helper(self, result):
        if self._parents:
            for parent in self._parents:
                parent._get_roots_helper(result)
        else:
            result[id(self)] = self
        return result

    parents = property(lambda self: list(self._parents), doc="""
        The set of parents of this tree.  If this tree has no parents,
        then C{parents} is the empty set.  To check if a tree is used
        as multiple children of the same parent, use the
        L{parent_indices} property.

        @type: C{list} of L{MultiParentedTree}""")

    left_siblings = property(_get_left_siblings, doc="""
        A list of all left siblings of this tree, in any of its parent
        trees.  A tree may be its own left sibling if it is used as
        multiple contiguous children of the same parent.  A tree may
        appear multiple times in this list if it is the left sibling
        of this tree with respect to multiple parents.

        @type: C{list} of L{MultiParentedTree}""")
    
    right_siblings = property(_get_right_siblings, doc="""
        A list of all right siblings of this tree, in any of its parent
        trees.  A tree may be its own right sibling if it is used as
        multiple contiguous children of the same parent.  A tree may
        appear multiple times in this list if it is the right sibling
        of this tree with respect to multiple parents.

        @type: C{list} of L{MultiParentedTree}""")
                              
    roots = property(_get_roots, doc="""
        The set of all roots of this tree.  This set is formed by
        tracing all possible parent paths until trees with no parents
        are found.

        @type: C{list} of L{MultiParentedTree}""")

    def parent_indices(self, parent):
        """
        Return a list of the indices where this tree occurs as a child
        of C{parent}.  If this child does not occur as a child of
        C{parent}, then the empty list is returned.  The following is
        always true::

          for parent_index in ptree.parent_indices(parent):
              parent[parent_index] is ptree
        """
        if parent not in self._parents: return []
        else: return [index for (index, child) in enumerate(parent)
                      if child is self]

    def treepositions(self, root):
        """
        Return a list of all tree positions that can be used to reach
        this multi-parented tree starting from C{root}.  I.e., the
        following is always true::

          for treepos in ptree.treepositions(root):
              root[treepos] is ptree
        """
        if self is root:
            return [()]
        else:
            return [treepos+(index,)
                    for parent in self._parents
                    for treepos in parent.treepositions(root)
                    for (index, child) in enumerate(parent) if child is self]

                              
    #/////////////////////////////////////////////////////////////////
    # Parent Management
    #/////////////////////////////////////////////////////////////////

    def _delparent(self, child, index):
        # Sanity checks
        assert isinstance(child, MultiParentedTree)
        assert self[index] is child
        assert len([p for p in child._parents if p is self]) == 1
        
        # If the only copy of child in self is at index, then delete
        # self from child's parent list.
        for i, c in enumerate(self):
            if c is child and i != index: break
        else:
            child._parents.remove(self)

    def _setparent(self, child, index, dry_run=False):
        # If the child's type is incorrect, then complain.
        if not isinstance(child, MultiParentedTree):
            raise TypeError('Can not insert a non-MultiParentedTree '+
                            'into a MultiParentedTree')

        # Add self as a parent pointer if it's not already listed.
        if not dry_run:
            for parent in child._parents:
                if parent is self: break
            else:
                child._parents.append(self)
    
class ImmutableParentedTree(ImmutableTree, ParentedTree):
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        super(ImmutableParentedTree, self).__init__(node_or_str, children)

class ImmutableMultiParentedTree(ImmutableTree, MultiParentedTree):
    def __init__(self, node_or_str, children=None):
        if children is None: return # see note in Tree.__init__()
        super(ImmutableMultiParentedTree, self).__init__(node_or_str, children)

######################################################################
## Probabilistic trees
######################################################################
class ProbabilisticTree(Tree, ProbabilisticMixIn):
    def __new__(cls, node_or_str, children=None, **prob_kwargs):
        return super(ProbabilisticTree, cls).__new__(
            cls, node_or_str, children)
    def __init__(self, node_or_str, children=None, **prob_kwargs):
        if children is None: return # see note in Tree.__init__()
        Tree.__init__(self, node_or_str, children)
        ProbabilisticMixIn.__init__(self, **prob_kwargs)

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
    def __new__(cls, node_or_str, children=None, **prob_kwargs):
        return super(ImmutableProbabilisticTree, cls).__new__(
            cls, node_or_str, children)
    def __init__(self, node_or_str, children=None, **prob_kwargs):
        if children is None: return # see note in Tree.__init__()
        ImmutableTree.__init__(self, node_or_str, children)
        ProbabilisticMixIn.__init__(self, **prob_kwargs)

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
            names.append(Nonterminal(child.node))
        else:
            names.append(child)
    return names

######################################################################
## Parsing
######################################################################
    
def bracket_parse(s):
    """
    Use Tree.parse(s, remove_top_empty_bracketing=True) instead.
    """
    raise NameError("Use Tree.parse(s, remove_top_empty_bracketing=True) instead.")

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
    t = Tree(s)
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
           'ProbabilisticTree', 'Tree', 'bracket_parse',
           'sinica_parse', 'ParentedTree', 'MultiParentedTree',
           'ImmutableParentedTree', 'ImmutableMultiParentedTree']
