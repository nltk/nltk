# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Open questions:
#     Should "tree" and "treetoken" be "ttree" and "ttreetoken" or
#       "treettoken" or even "ttreettoken"? :)
#     Should TreeToken.nodes() return a Tree or a TreeToken?

# To do:
#   - How should we handle traces and/or movement?

"""
Classes for representing hierarchical structures over text.  These
structures are called X{text-tree type}s, and individual occurances of
text-tree types are known as X{text-tree tokens}.  Note that several
different text-tree tokens might all have the same text-tree type.
For example, if the sentence \"the dog chased the cat\" occurs three
times in a document, each occurance of the sentence will have a
different text-tree token; but all three text-tree tokens will have
the same text-tree type.  The term X{text-tree} (or X{tree} for short)
can be used to refer to both text-tree types and text-tree tokens.

The tree module defines the C{Tree} class to represent text-tree
types, and the C{TreeToken} class to represent text-tree tokens.
C{TreeToken} is a subclass of C{Token}; thus, C{TreeToken}s have
locations, which can be used to distinguish different C{TreeToken}s
with the same text-tree type.  C{Tree}s and C{TreeToken}s are both
children of the abstract class C{AbstractTree}, which defines many
procedures that the two classes have in common.  See the documentation
for the C{Tree} and C{TreeToken} classes for more information on how
text-tree types and tokens are represented.

Text-tree types can be constructed from strings using any one of a
number of X{parsing functions}.  These function differ in that they
read different formats; and they produce text-tree types with
different kinds of nodes and leaves.  Currently, the following parsing 
functions are defined:

    - C{parse_treebank()}: Parses treebank-style syntax trees.

@see: nltk.token
@sort: AbstractTree, Tree, TreeToken, TreebankTokenizer,
    ProbabilisticTree, ProbabilisticTreeToken
@group Tokenization: TreebankTokenizer
@group Probabilistic Trees: Probabilistic*
"""

from nltk.token import Token, Location, TokenizerI
from nltk.probability import ProbabilisticMixIn
import re
from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
import types

def _pytype(obj):
    """
    @return: the pytype of C{obj}.  For class instances, this is
        their class; for all other objects, it is their type, as
        returned by type().
    @rtype: C{type} or C{class}
    @param obj: The object whose pytype should be returned.
    @type obj: (any)
    """
    if type(obj) == types.InstanceType:
        return obj.__class__
    else:
        return type(obj)

##//////////////////////////////////////////////////////
##  Abstract Tree (base class)
##//////////////////////////////////////////////////////
class AbstractTree:
    """
    An abstract class for homogenous hierarchical structures spanning
    text types or tokens.  C{AbstractClass} defines many member
    functions that are shared by C{Tree} and C{TreeToken}.
    C{AbstractTree} is an abstract class, and it should not be
    directly instantiated.

    C{AbstractTree} requires that its subclasses define the member
    variables C{_node} and C{_children}, containing the node value and
    a tuple of the children, respectively.
    """
    def __init__(self):
        raise AssertionError('AbstractTree is an abstract class')
    
    def node(self):
        """
        @return: this tree's node value.  The node value associates
            information with the entire tree.  For example, node
            values might be used to label syntactic constituents with
            phrase tags, such as \"NP\" and\"VP\".
        @rtype: I{nodetype}
        """
        return self._node

    def children(self):
        """
        @return: this tree's children.
        @rtype: C{tuple}
        """
        return self._children

    def __getitem__(self, index):
        """
        @return: the specified child, children, or descendant.  If
            C{index} is an integer, then return
            C{self.children()[index]}.  If C{index} is a span
            C{start:stop}, then return C{self.children()[start:stop]}.
            If C{index} is a tuple C{M{i1}, M{i2}, ..., M{in}}, then
            return C{self.children()[M{i1}][M{i2}]...[M{in}]}.            
        @rtype: I{tree} or I{leaftype};
            or C{list} of (I{tree} or I{leaftype})
        @param index: An integer, slice, or tree position indicating
            which children to return.
        @type index: C{int} or C{slice} or (C{list} of C{int})
        @raise IndexError: If the specified child does not exist.
        """
        assert _chktype(1, index, types.IntType,
                        types.SliceType, types.TupleType)
        if type(index) == types.IntType:
            return self._children[index]
        elif type(index) == types.SliceType:
            return self._children[index.start:index.stop]
        elif len(index) == 0:
            return self
        elif len(index) == 1:
            return self._children[index[0]]
        elif isinstance(self._children[index[0]], AbstractTree):
            return self._children[index[0]][index[1:]]
        else:
            raise IndexError('Bad tree position')

    def __len__(self):
        """
        @return: The number of children this tree has.
        @rtype: C{int}
        """
        return len(self._children)

    def leaves(self):
        """
        @return: a tuple containing this tree's leaf set.  The
            order of leaves in the tuple reflects the order of the
            leaves in the tree's hierarchical structure.
        @rtype: C{tuple} of I{leaftype}
        """
        leaves = []
        for child in self._children:
            if isinstance(child, AbstractTree):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return tuple(leaves)

    def nodes(self):
        """
        @return: a new tree that contains all of this tree's
            nodes, but no leaves.
        @rtype: I{tree}
        """
        newchildren = [c.nodes() for c in self._children
                       if isinstance(c, AbstractTree)]
        # Return a new tree containing only the nodes.
        # "self.__class__" is the constructor for this class.
        return self.__class__(self.node(), *newchildren)

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
        for child in self._children:
            if isinstance(child, AbstractTree):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = 1
        return 1 + max_child_height

    def with_substitution(self, treepos, substitution):
        """
        @return: A new tree that is equal to this
            tree, except that the subtree or leaf identified
            by C{treepos} is replaced by C{substitution}.
        @rtype: I{tree}
        @param treepos: A list of child indices specifying the path
            from the root of the tree to the subtree or leaf that
            should be replaced.
        @type treepos: C{list} of C{int}
        @param substitution: The new subtree or leaf that should be
            substituted in to this tree.
        @type substitution: I{tree} or I{leaftype}
        """
        assert _chktype(1, treepos, (types.IntType,), [types.IntType])
        if treepos == ():
            return substitution
        else:
            if not (0 <= treepos[0] < len(self._children)):
                raise IndexError('Bad tree position')
            
            # Find the new child list.
            new_children = list(self._children)
            child = self._children[treepos[0]]
            if isinstance(child, AbstractTree):
                newchild = child.with_substitution(treepos[1:], substitution)
                new_children[treepos[0]] = newchild
            elif len(treepos) == 1:
                new_children[treepos[0]] = substitution
            else:
                raise IndexError('Bad tree position')

            # Return a tree with the new child list.
            # "self.__class__" is the constructor for this class.
            return self.__class__(self._node, *new_children)
    
    def __eq__(self, other):
        """
        @return: true if this tree is equal to C{other}.  In
            particular, return true if C{self.node()==other.node()},
            C{self.len()==other.len()}, and C{self[i]==other[i]} for
            all i, 0 <= i < self.len()
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and
                self._node == other._node and
                self._children == other._children)

    def __hash__(self):
        return hash((self._node, self._children))

    def __ne__(self, other):
        """
        @return: true if this tree is not equal to C{other}.  In
            particular, return false if C{self.node()==other.node()},
            C{self.len()==other.len()}, and C{self[i]==other[i]} for
            all i, 0 <= i < self.len()
        @rtype: C{boolean}
        """
        return not (self == other)

    def __cmp__(self, other):
        """
        No ordering relationship is defined over C{Tokens}; raise an
        exception.

        @raise AssertionError:
        """
        raise AssertionError("Ordering relations are not "+
                             "defined over trees")

    def draw(self):
        """
        Open a new window containing a graphical diagram of this tree.
        
        @rtype: None
        """
        # Note: this method introduces a circular dependency between
        # modules.  However, this circularity is only a matter of
        # convenience.  In particular, we believe that it is more
        # intuitive for students to run "mytree.draw()" than
        # "draw.tree.drawtree(mytree)".
        from nltk.draw.tree import draw_trees
        draw_trees(self)

    # These are necessary to allow pickling.  The reason is that we're
    # keeping a type inside AbstractTree (in _nodetype and
    # _leaftype)..  Which can't be pickled; we may decide to stop
    # enforcing consistancy among node & leaf types, in which case we
    # could get rid of this.
    def __getstate__(self):
        return [self._node, self._children]
    def __setstate__(self, state):
        [node, children] = state
        self.__init__(node, *children)

##//////////////////////////////////////////////////////
##  Text Trees (Type)
##//////////////////////////////////////////////////////
class Tree(AbstractTree):
    """
    A homogenous hierarchical structure spanning text types.  A
    C{Tree} consists of a X{node value} and zero or more X{children}.

    The node value associates information with the entire C{Tree}.
    For example, node values might be used to label syntactic
    constituents with phrase tags, such as \"NP\" and\"VP\".

    The children encode the hierarchical contents of the C{Tree}.
    Each child is either a X{leaf} or a X{subtree}.  Leaves are the
    text types over which the C{Tree} is defined.  Subtrees are
    C{Tree} objects that are used to encode the structure of the
    C{Tree}.

    A tree's children can be accessed using the indexing operator:

        >>> tree = Tree('S', Tree('NP', 'the', 'cat'),
        ...                  Tree('VP', 'ate'))
        >>> tree[0]
        ('NP': 'the', 'cat')
        >>> tree[1][0]
        'ate'

    A tree's children can be iterated over using C{for} expressions:

        >>> for child in tree:
        ...     print child
        ('NP': 'the', 'cat')
        ('VP': 'ate')

    A tree's descendants can be accessed using tree positions.  A
    X{tree position} is a tuple of child indices specifying the path
    from a tree's root to one of its descendants.  In particular, the
    tree position C{()} specifies the root of a tree; and if C{M{p}}
    is the tree position of descendant M{d}, then C{M{p}+(M{i})}
    specifies the C{M{i}}th child of M{d}.  Tree positions may be used
    with the indexing operator to access a tree or its descendants:

        >>> tree[1, 0]
        'ate'
        >>> pos = (0, 1)
        >>> tree[pos]
        'cat'
        >>> tree[()]
        ('S': ('NP': 'the', 'cat'), ('VP': 'ate'))

    Type Checking
    =============
    A C{Tree}'s X{leaf set} consists of the leaf children of the
    C{Tree} and the leaf sets of its subtrees.  All leaves in a tree's
    leaf set must have the same pytype.  A C{Tree}'s X{node value
    set} consists of the node value of the C{Tree} and the node value
    sets of its subtrees.  All node values in a tree's node value set
    must have the same pytype.

    @ivar _nodetype: The pytype of this C{Tree}'s nodes.  (Used to 
        enforce consistancy conditions).
    @type _nodetype: C{type} or C{class}
    @ivar _leaftype: The pytype of this C{Tree}'s leaves. (Used to
        enforce consistancy conditions).
    @type _leaftype: C{type} or C{class}
    """
    def __init__(self, node, *children):
        """
        Construct a new C{Tree} object, with the given node value and
        children.  For example:

            >>> Tree('np', 'the', 'cat')
            ('np': 'the' 'cat')

        Note that the children should not be given as a single list;
        doing so will cause that list to be treated as a single leaf.
        If you need to consturct a C{Tree} from a list of children,
        use the following syntax:

            >>> children = ('the', 'cat')
            >>> Tree('np', *children)
            ('np': 'the' 'cat')

        @param node: The new C{Tree}'s node value.
        @type node: (nodetype)
        @param children: The new C{Tree}'s children.
        @type children: C{Tree} or (leaftype)
        """
        self._node = node
        self._children = children

        # Derive our _nodetype and _leaftype.  If there are no
        # consistant values for _nodetype and _leaftype, raise an
        # exception.
        self._nodetype = _pytype(node)
        self._leaftype = None
        for child in children:
            if isinstance(child, Tree):
                c_nodetype = child._nodetype
                c_leaftype = child._leaftype
            else:
                c_nodetype = None
                c_leaftype = _pytype(child)
            if (c_nodetype is not None and
                self._nodetype != c_nodetype):
                raise TypeError("All nodes in a Tree must have the "+
                                "same Python type.")
            if (self._leaftype is not None and c_leaftype is not None and
                self._leaftype != c_leaftype):
                raise TypeError("All leaves in a Tree must have the "+
                                "same Python type.")
            if (self._leaftype == None and c_leaftype is not None):
                self._leaftype = c_leaftype

    def pp(self, margin=70, indent=0):
        """
        @return: A pretty-printed string representation of this tree.
        @rtype: C{string}
        @param margin: The right margin at which to do line-wrapping.
        @type margin: C{int}
        @param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lines.
        @type indent: C{int}
        """
        assert _chktype(1, margin, types.IntType)
        assert _chktype(2, indent, types.IntType)
        rep = repr(self)
        if len(rep)+indent < margin:
            return rep
        str = '('+repr(self._node)+':'
        for child in self._children:
            if isinstance(child, AbstractTree):
                str += '\n'+' '*(indent+2)+child.pp(margin, indent+2)
            else:
                str += '\n'+' '*(indent+2)+repr(child)
        return str+')'

    # Contributed by trevorcohn1@users.sf.net
    def latex_qtree(self, first=True):
        """
        Returns a representation of the tree token compatible with the LaTeX
        qtree package. This consists of the string C{\\Tree} followed by
        the parse tree represented in bracketed notation.

        For example, the following result was generated from a parse tree of
        the sentence C{The announcement astounded us}:

        \Tree [.I'' [.N'' [.D The ] [.N' [.N announcement ] ] ]
            [.I' [.V'' [.V' [.V astounded ] [.N'' [.N' [.N us ] ] ] ] ] ] ]

        See C{http://www.ling.upenn.edu/advice/latex.html} for the LaTeX=
        style file for the qtree package.

        @return: A latex qtree representation of this tree.
        @rtype: C{string}
        @param first: Internal flag used in recursive call.
        @type first: boolean
        """
        str = ''
        if first:
            str = '\\Tree '
        str += '[.' + repr(self._node) + ' ' 
        for child in self._children:
            if isinstance(child, AbstractTree):
                str += child.latex_qtree(False) + ' '
            else:
                str += repr(child) + ' '
        str += ']'
        return str

    def __repr__(self):
        """
        @return: A concise string representation of this tree.
        @rtype: C{string}
        """
        str = '('+repr(self._node)+':'
        for child in self._children:
            str += ' '+repr(child)
        return str+')'

    def __str__(self):
        """
        @return: A verbose string representation of this tree.
        @rtype: C{string}
        """
        return self.pp()

class ProbabilisticTree(Tree, ProbabilisticMixIn):
    def __init__(self, p, node, *children):
        ProbabilisticMixIn.__init__(self, p)
        Tree.__init__(self, node, *children)
    def pp(self, margin=70, indent=0):
        return Tree.pp(self, margin, indent) + (' (p=%s)' % self._p)
    def __repr__(self):
        return Tree.__repr__(self) + (' (p=%s)' % self._p)
    def __str__(self):
        return self.pp()
        
##//////////////////////////////////////////////////////
##  Text Tree Tokens
##//////////////////////////////////////////////////////
class TreeToken(AbstractTree, Token):
    """
    A homogenous hierarchical structure spanning text tokens.  I.e., a
    single occurance of a C{Tree}.  A C{TreeToken} consists of a
    X{node value} and zero or more X{children}.

    The node value associates information with the entire
    C{TreeToken}.  For example, node values might be used to label
    syntactic constituents with phrase tags, such as \"NP\" and\"VP\".

    The children encode the hierarchical contents of the C{TreeToken}.
    Each child is either a X{leaf} or a X{subtree}.  Leaves are the
    text tokens over which the C{TreeToken} is defined.  Subtrees are
    C{TreeToken} objects that are used to encode the structure of the
    C{TreeToken}.

    A tree's children can be accessed using the indexing operator:

        >>> words = tokenizer.tokenize("the cat ate")
        >>> treetok = TreeToken('S', TreeToken('NP', words[0], words[1]),
        ...                          TreeToken('VP', words[2]))
        >>> treetok[0]
        ('NP': 'the' 'cat')@[0w:2w]
        >>> treetok[1][0]
        'ate'@[2w]

    A tree's children can be iterated over using C{for} expressions:

        >>> for child in treetok:
        ...     print child
        ('NP': 'the' 'cat')@[0w:2w]
        ('VP': 'ate')@[2w]

    A tree's descendants can be accessed using tree positions.  A
    X{tree position} is a tuple of child indices specifying the path
    from a tree's root to one of its descendants.  In particular, the
    tree position C{()} specifies the root of a tree; and if C{M{p}}
    is the tree position of descendant M{d}, then C{M{p}+(M{i})}
    specifies the C{M{i}}th child of M{d}.  Tree positions may be used
    with the indexing operator:

        >>> treetok[1, 0]
        'ate'@[2w]
        >>> pos = (0, 1)
        >>> treetok[pos]
        'cat'@[1w]
        >>> treetok[()]
        ('S': ('NP': 'the', 'cat'), ('VP': 'ate'))@[0w:3w]

    Type Checking
    =============
    A C{TreeToken}'s X{leaf set} consists of the leaf children of the
    C{TreeToken} and the leaf sets of its subtrees.  All leaves in a tree's
    leaf set must have text types with the same pytype.  A C{TreeToken}'s
    X{node value set} consists of the node value of the C{TreeToken} and
    the node value sets of its subtrees.  All node values in a tree's
    node value set must have the same pytype.

    @ivar _nodetype: The pytype of this C{TreeToken}'s nodes.  (Used to 
        enforce consistancy conditions).
    @type _nodetype: C{type} or C{class}
    @ivar _leaftype: The pytype of this C{TreeToken}'s leaves' types.
        (Used to enforce consistancy conditions).
    @type _leaftype: C{type} or C{class}
    @ivar _loc: The location of this TreeToken.  Computed to enforce
        consistancy conditions; also used by the loc() method.
    @type _loc: C{Location}
    """
    def __init__(self, node, *children):
        """
        Construct a new C{TreeToken} object, with the given node value
        and children.  For example:

            >>> words = tokenizer.tokenize("the cat")
            >>> TreeToken('np', words[0], words[1])
            ('np': 'the' 'cat')@[0:2]

        Note that the children should not be given as a single list.
        If you need to consturct a C{TreeToken} from a list of
        children, use the following syntax:

            >>> TreeToken('np', *words)
            ('np': 'the' 'cat')@[0:2]

        @param node: The new C{TreeToken}'s node value.
        @type node: (nodetype)
        @param children: The new C{TreeToken}'s children.
        @type children: C{TreeToken} or C{Token}
        """
        assert _chktype('vararg', children, (Token, TreeToken))
        self._node = node
        self._children = children

        # Derive our _nodetype and _leaftype.  If there are no
        # consistant values for _nodetype and _leaftype, raise an
        # exception.
        self._nodetype = _pytype(node)
        self._leaftype = None
        for child in children:
            if isinstance(child, TreeToken):
                c_nodetype = child._nodetype
                c_leaftype = child._leaftype
            else:
                c_nodetype = None
                c_leaftype = _pytype(child.type())
            if (c_nodetype is not None and
                self._nodetype != c_nodetype):
                raise TypeError("All nodes in a TreeToken must "+
                                "have the same Python type.")
            if (self._leaftype is not None and c_leaftype is not None and
                self._leaftype != c_leaftype):
                raise TypeError("All leaves in a TreeToken must "+
                                "have the same Python type.")
            if (self._leaftype == None and c_leaftype is not None):
                self._leaftype = c_leaftype

        # Find/check our location.
        start = None
        end = None
        prevloc = None
        try:
            ordered = 1
            for child in children:
                loc = child.loc()
                if loc is None: continue
                if start is None: start = loc.start()
                end = loc.end()
                if prevloc is not None and not (prevloc < loc):
                    ordered = 0
                prevloc = loc
        except ValueError:
            raise ValueError("The leaves of a TreeToken must have "+
                             "compatible units and sources.")
        if not ordered:
            raise ValueError("The leaves of a TreeToken "+ 
                             "must be properly ordered.")
        if prevloc is None:
            self._location = None
        else:
            self._location = Location(start, end,
                                      unit=prevloc.unit(),
                                      source=prevloc.source())

    def type(self):
        """
        Return the C{Tree} of which this C{TreeToken} is an occurance.
        In particular, return the text tree obtained by replacing all
        of this C{TreeToken}'s leaves with their types.
            
        @return: the C{Tree} of which this C{TreeToken} is an occurance.
        @rtype: C{Tree}
        """
        typechildren = []
        for child in self._children:
            typechildren.append(child.type())
        return Tree(self._node, *typechildren)

    def loc(self):
        """
        Return the location of this C{TreeToken}.  If none of the
        leaves of this C{TreeToken} have locations, then this location
        is defined as C{None}.  Otherwise, it is the location
        beginning with the first leaf's start index, ending with the
        last leaf's end index, and with a unit and source equal to
        that of every leaf's location.

        As with any C{TreeToken}, a token with a location of C{None}
        is not equal to any other token, even if their types are
        equal.
        
        @return: the location of this C{TreeToken}.
        @rtype: C{Location}
        """
        return self._location

    def pp(self, margin=70, indent=0):
        """
        @return: A pretty-printed string representation of this
            C{TreeToken}. 
        @rtype: C{string}
        @param margin: The right margin at which to do line-wrapping.
        @type margin: C{int}
        @param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lnes.
        @type indent: C{int}
        """
        assert _chktype(1, margin, types.IntType)
        assert _chktype(2, indent, types.IntType)
        if self.loc() is None: locstr = '@[?]'
        else: locstr = repr(self.loc())
        return self.type().pp(margin-len(locstr), indent)+locstr

    def latex_qtree(self):
        return self.type().latex_qtree()

    def __repr__(self):
        """
        @return: A concise string representation of this C{TreeToken}.
        @rtype: C{string}
        """
        if self.loc() is None:
            return repr(self.type())+'@[?]'
        else:
            return repr(self.type())+repr(self.loc())
        
    def __str__(self):
        """
        @return: A verbose string representation of this C{TreeToken}.
        @rtype: C{string}
        """
        return self.pp()

class ProbabilisticTreeToken(TreeToken, ProbabilisticMixIn):
    def __init__(self, p, node, *children):
        ProbabilisticMixIn.__init__(self, p)
        TreeToken.__init__(self, node, *children)
    def pp(self, margin=70, indent=0):
        return TreeToken.pp(self) + (' (p=%s)' % self._p)
    def __repr__(self):
        return TreeToken.__repr__(self) + (' (p=%s)' % self._p)
    def __str__(self):
        return self.pp()
        
##//////////////////////////////////////////////////////
##  Conversion Routines
##//////////////////////////////////////////////////////

def parse_treebank(str):
    """
    Given a string containing a Treebank-style representation of a
    syntax tree, return a C{Tree} representing that syntax tree.
    """
    assert _chktype(1, str, types.StringType)
    
    # Rather than trying to parse the string ourselves, we will rely
    # on the Python parser.  This procedure isn't immediately easy to
    # understand, but if you add a "print str" after each call to
    # re.sub, and try it out on an example, you should be able to
    # figure out what's going on.

    # Get rid of any newlines, etc.
    str = ' '.join(str.split())

    # Backslash any quote marks or backslashes in the string.
    str = re.sub(r'([\\"\'])', r'\\\1', str)

    # Add quote marks and commas around words.
    str = re.sub('([^() ]+)', r'"\1",', str)

    # Add commas after close parenthases.
    str = re.sub(r'\)', '),', str)
    
    # Add calls to the Tree constructor.
    str = re.sub(r'\(', 'Tree(', str)

    # Eliminate empty nodes
    str = re.sub(r'Tree\(\)', r'Tree(" ")', str)

    # Strip whitespace and get rid of the comma after the last ')' 
    str = str.strip()[:-1]

    # Use "eval" to convert the string
    try:
        result = eval(str)
        return result
    except:
        raise ValueError('Bad Treebank-style string')

class TreebankTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into C{TreeTokens}.
    The text should consist of a sequence of Treebank-style syntax
    trees.  Each word in the tree is encoded as a L{Token} whose type
    is string; and each constituant is encoded as a L{TreeToken}
    composed from its children.  Tree nodes are encoded as strings.
    Location indices start at zero, and have a default unit of
    C{'w'} (for \"word\").

    Parenthases that do not have node value are ignored.  For example,
    in the following call to C{tokenize()}, the outermost parenthases
    are ignored:

       >>> TreebankTokenizer().tokenize('((S (NP He) (VP (V ate))))')
       [('S': ('NP': 'He'@[0w]) ('VP': ('V': 'ate'@[1w])))]
    """
    def tokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI

        # Remember the unit & source for tokens.
        self._unit = unit
        self._source = source

        # This is used to keep track of word indices for creating
        # Locations of Tokens:
        self._wordnum = 0
        
        # Rather than trying to parse the string ourselves, we will
        # rely on the Python parser.  This procedure isn't immediately
        # easy to understand, but if you add a "print str" after each
        # call to re.sub, and try it out on an example, you should be
        # able to figure out what's going on.
        trees = []
        for treestr in self._split_into_trees(str):
            # Get rid of any newlines, etc.
            treestr = ' '.join(treestr.split())

            # Backslash any quote marks or backslashes in the string.
            treestr = re.sub(r'([\\"\'])', r'\\\1', treestr)

            # Add quote marks and calls to Token() for words.
            treestr = re.sub(r'(\(?[^() ]+|\(|\))', self._token_sub, treestr)

            # Eliminate empty nodes (these *shouldn't* exist)
            treestr = re.sub(r'TreeToken\(\)', r'TreeToken(" ")', treestr)

            # Strip whitespace and get rid of the comma after the last ')' 
            treestr = treestr.strip()[:-1]

            # Use "eval" to convert the string
            try:
                trees.append(eval(treestr))
            except:
                raise ValueError('Bad Treebank-style string')
        return trees

    def _identity(self, x):
        """
        A helper function for L{_token_sub()}.
        @return: C{x}
        """
        return x
    
    def _token_sub(self, match):
        r"""
        A helper function for L{tokenize}.  This is used as the
        C{replacement} argument of a call to C{re.sub()}.  It is used
        to perform the following transformations on a string:
          - Replace C{'I{word}'} with C{'Token(I{word}, I{location})'}
            (where C{I{locaiton}} is the location for I{word}).
          - Replace C{'(I{node}'} with C{'TreeToken(I{node}, '}
          - Replace any other C{'('} with C{'self._identity('}
          - Replace C{')'}, with C{'),'}
        """
        word = match.group(1)
        if word[:1] == ')':
            return '),'
        if word[:1] == '(':
            # It's a node (=constituant)
            if len(word) > 1:
                return 'TreeToken(%r,' % word[1:]
            else:
                # Special case: ignore parens with no token??
                return 'self._identity('
        else:
            # It's a leaf (=word)
            self._wordnum += 1
            return ('Token(%r, Location(%d, '% (word, self._wordnum-1) +
                    'unit=self._unit, source=self._source)),')

    def _split_into_trees(self, str):
        '''
        Given a string that contains a series of treebank trees, split
        it into a list of substrings, where each contains a single
        treebank tree.
        '''
        trees = []
        parens = 0
        start = pos = 0
        PAREN_RE = re.compile('[()]')

        while pos < len(str):
            # Find the next parenthasis.
            match = PAREN_RE.search(str, pos)

            # If no parenthasis is found, we're done.
            if match == None:
                if str[pos:].split():
                    raise ValueError('Bad Treebank-style string')
                break

            # Update our position.
            pos = match.end()

            # Process the parenthasis.
            if match.group() == '(':
                if parens == 0: start = pos-1
                parens += 1
            elif match.group() == ')':
                parens -= 1
                if parens == 0:
                    trees.append(str[start:pos])
                elif parens < 0:
                    raise ValueError('Bad Treebank-style string')

        return trees
