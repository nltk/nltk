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
#   - add x-to-y methods for treebank, etc.
#   - traces!! Whee.

"""

Classes for representing text-trees.  A X{text-tree type} is a
hierarchical data structures over a text, such as syntax tree.
Individual occurances of text-tree types are known as X{text-tree
tokens}.  Note that several different text-tree tokens might all have
the same text-tree type.  For example, if the sentence \"the dog
chased the cat\" occurs three times in a document, each occurance of
the sentence will have a different text-tree token; but all three
text-tree tokens will have the same text-tree type.

The tree module defines the C{Tree} class to represent text-tree
types, and the C{TreeToken} class to represent text-tree tokens.
C{TreeToken} is a subclass of C{Token}; thus, C{TreeToken}s have
locations, which can be used to distinguish different C{TreeToken}s
with the same text-tree type.  See the documentation for the C{Tree}
and C{TreeToken} classes for more information on how text-tree types
and tokens are represented.

Text-tree types can be constructed from strings using any one of a
number of X{parsing functions}.  These function differ in that they
read different formats; and they produce text-tree types with
different kinds of nodes and leaves.  Currently, the following parsing 
functions are defined:

    - C{parse_treebank()}: Parses treebank-style syntax trees.

@see: nltk.token
"""

import token

from token import Token
from token import Location
import re
from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import SliceType as _SliceType
from types import IntType as _IntType
from types import StringType as _StringType
from types import NoneType as _NoneType
from types import ListType as _ListType
from types import InstanceType as _InstanceType

def _pytype(obj):
    """
    @return: the pytype of C{obj}.  For class instances, this is
        their class; for all other objects, it is their type, as
        returned by type().
    @rtype: C{type} or C{class}
    @param obj: The object whose pytype should be returned.
    @type obj: (any)
    """
    if type(obj) == _InstanceType:
        return obj.__class__
    else:
        return type(obj)

##//////////////////////////////////////////////////////
##  Text Trees (Type)
##//////////////////////////////////////////////////////
class Tree:
    """
    A homogenous hierarchical structure spanning text types.  A
    C{Tree} consists of a X{node value} and zero or more X{children}.

    The node value associates information with the entire C{Tree}.
    For example, node values might be used to label syntactic
    constituants with phrase tags, such as \"NP\" and\"VP\".

    The children encode the hierarchical contents of the C{Tree}.
    Each child is either a X{leaf} or a X{subtree}.  Leaves are the
    text types over which the C{Tree} is defined.  Subtrees are
    C{Tree} objects that are used to encode the structure of the
    C{Tree}.

    A C{Tree}'s X{leaf set} consists of the leaf children of the
    C{Tree} and the leaf sets of its subtrees.  All leaves in a tree's
    leaf set must have the same pytype.  A C{Tree}'s X{nodes values
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

    def node(self):
        """
        Return this C{Tree}'s node value.  The node value associates
        information with the entire C{Tree}.  For example, node values
        might be used to label syntactic constituants with phrase
        tags, such as \"NP\" and\"VP\".
    
        @return: this C{Tree}'s node value.
        @rtype: (nodetype)
        """
        return self._node

    def children(self):
        """
        Return this C{Tree}'s children.

        @return: this C{Tree}'s children.
        @rtype: C{tuple}
        """
        return self._children

    def __getitem__(self, index):
        """
        @return: the specified child or children.
        @rtype: C{Tree} or (leaftype); or C{list} of (C{Tree} or (leaftype))
        @param index: An integer or slice indicating which children to 
            return.
        @type index: C{int} or C{slice}
        @raise IndexError: If the specified child does not exist.
        """
        _chktype("Tree.__getitem__", 1, index, (_IntType, _SliceType))
        if type(index) == _SliceType:
            return self._children[index.start:index.stop]
        else:
            return self._children[index]

    def __len__(self):
        """
        @return: The number of children this C{Tree} has.
        @rtype: C{int}
        """
        return len(self._children)

    def pp(self, margin=70, indent=0):
        """
        @return: A pretty-printed string representation of this C{Tree}.
        @rtype: C{string}
        @param margin: The right margin at which to do line-wrapping.
        @type margin: C{int}
        @param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lnes.
        @type indent: C{int}
        """
        _chktype("Tree.pp", 1, margin, (_IntType,))
        _chktype("Tree.pp", 2, indent, (_IntType,))
        rep = repr(self)
        if len(rep)+indent < margin:
            return rep
        str = '('+repr(self._node)+':'
        for child in self._children:
            if isinstance(child, Tree):
                str += '\n'+' '*(indent+2)+child.pp(margin, indent+2)
            else:
                str += '\n'+' '*(indent+2)+repr(child)
        return str+')'

    def __repr__(self):
        """
        @return: A concise string representation of this C{Tree}.
        @rtype: C{string}
        """
        str = '('+repr(self._node)+':'
        for child in self._children:
            str += ' '+repr(child)
        return str+')'

    def __str__(self):
        """
        @return: A verbose string representation of this C{Tree}.
        @rtype: C{string}
        """
        return self.pp()

    def leaves(self):
        """
        @return: a tuple containing this C{Tree}'s leaf set.  The
            order of leaves in the tuple reflects the order of the
            leaves in the C{Tree}'s hierarchical structure.
        @rtype: C{tuple} of (leaftype)
        """
        leaves = []
        for child in self._children:
            if isinstance(child, Tree):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return tuple(leaves)

    def nodes(self):
        """
        @return: a new C{Tree} that contains all of this C{Tree}'s
            nodes, but no leaves.
        @rtype: C{Tree}
        """
        newchildren = []
        for child in self._children:
            if isinstance(child, Tree):
                newchildren.append(child.nodes())
        return Tree(self.node(), *newchildren)

    def height(self):
        """
        @return: The height of this C{Tree}.  The height of a C{Tree}
            containing no children is 1; the height of a C{Tree}
            containing only leaves is 2; and the height of any other
            C{Tree} is one plus the maximum of its children's
            heights.
        @rtype: C{int}
        """
        max_child_height = 0
        for child in self._children:
            if isinstance(child, Tree):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = 1
        return 1 + max_child_height

    def __eq__(self, other):
        """
        @return: true if this C{Tree} is equal to C{other}.  In
            particular, return true if C{self.node()==other.node()},
            C{self.len()==other.len()}, and C{self[i]==other[i]} for
            all i, 0 <= i < self.len()
        @rtype: C{boolean}
        """
        _chkclass(self, other)
        return (self._node == other._node and
                self._children == other._children)

    def __hash__(self):
        return hash((self._node, self._children))

    def __ne__(self, other):
        """
        @return: true if this C{Tree} is not equal to C{other}.  In
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
                             "defined over Trees")

    def draw(self):
        """
        Open a graphical window containing a diagram of the text
        tree.
        
        @rtype: None
        """
        # Note: this method introduces a circular dependancy between
        # modules.  However, this circularity is only a matter of
        # convenience.  In particular, we believe that it is more
        # intuitive for students to run "mytree.draw()" than
        # "draw.tree.drawtree(mytree)".
        import nltk.draw.tree
        nltk.draw.tree.TreeView(self)

##//////////////////////////////////////////////////////
##  Text Tree Tokens
##//////////////////////////////////////////////////////
class TreeToken(token.Token):
    """
    A homogenous hierarchical structure spanning text tokens.  I.e., a
    single occurance of a C{Tree}.  A C{TreeToken} consists of a
    X{node value} and zero or more X{children}.

    The node value associates information with the entire
    C{TreeToken}.  For example, node values might be used to label
    syntactic constituants with phrase tags, such as \"NP\" and\"VP\".

    The children encode the hierarchical contents of the C{TreeToken}.
    Each child is either a X{leaf} or a X{subtree}.  Leaves are the
    text tokens over which the C{TreeToken} is defined.  Subtrees are
    C{TreeToken} objects that are used to encode the structure of the
    C{TreeToken}.

    A C{Tree}'s X{leaf set} consists of the leaf children of the
    C{Tree} and the leaf sets of its subtrees.  All leaves in a tree's
    leaf set must have text types with the same pytype.  A C{Tree}'s
    X{nodes values set} consists of the node value of the C{Tree} and
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

            >>> Tree('np', Token('the', 0), Token('cat', 1))
            ('np': 'the' 'cat')@[0:2]

        Note that the children should not be given as a single list.
        If you need to consturct a C{TreeToken} from a list of
        children, use the following syntax:

            >>> children = (Token('the', 0), Token('cat', 1))
            >>> Tree('np', *children)
            ('np': 'the' 'cat')@[0:2]

        @param node: The new C{Tree}'s node value.
        @type node: (nodetype)
        @param children: The new C{Tree}'s children.
        @type children: C{Tree} or C{Token}
        """
        _chktype("TreeToken", -1, children, ( (token.Token, TreeToken),) )
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
            self._location = token.Location(start, end,
                                            unit=prevloc.unit(),
                                            source=prevloc.source())

    def node(self):
        """
        Return this C{TreeToken}'s node value.  The node value
        associates information with the entire C{TreeToken}.  For
        example, node values might be used to label syntactic
        constituants with phrase tags, such as \"NP\" and\"VP\".
    
        @return: this C{TreeToken}'s node value.
        @rtype: (nodetype)
        """
        return self._node

    def children(self):
        """
        Return this C{TreeToken}'s children.

        @return: this C{TreeToken}'s children.
        @rtype: C{tuple}
        """
        return self._children

    def __getitem__(self, index):
        """
        @return: the specified child or children.
        @rtype: C{TreeToken} or C{Token};
            or C{list} of (C{TreeToken} or C{Token})
        @param index: An integer or slice indicating which children to 
            return.
        @type index: C{int} or C{slice}
        @raise IndexError: If the specified child does not exist.
        """
        _chktype("Tree.__getitem__", 1, index, (_IntType, _SliceType))
        if type(index) == _SliceType:
            return self._children[index.start:index.stop]
        else:
            return self._children[index]

    def __len__(self): 
        """
        @return: The number of children this C{TreeToken} has.
        @rtype: C{int}
        """
        return len(self._children)
    
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

    # [sb: this should be called loc() not location()]
    def location(self):
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

    # [sb: for future compatibility]
    def loc(self):
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
        _chktype("TreeToken.pp", 1, margin, (_IntType,))
        _chktype("TreeToken.pp", 2, indent, (_IntType,))
        if self.loc() is None: locstr = '@[?]'
        else: locstr = repr(self.loc())
        return self.type().pp(margin-len(locstr), indent)+locstr

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

    def leaves(self):
        """
        @return: a tuple containing this C{TreeToken}'s leaf set.  The
            order of leaves in the tuple reflects the order of the
            leaves in the C{TreeToken}'s hierarchical structure.
        @rtype: C{tuple} of C{Token}
        """
        leaves = []
        for child in self._children:
            if isinstance(child, TreeToken):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return tuple(leaves)

    def nodes(self):
        """
        @return: a new C{TreeToken} that contains all of this
            C{TreeToken}'s nodes, but no leaves.
        @rtype: C{TreeToken}
        """
        newchildren = []
        for child in self._children:
            if isinstance(child, TreeToken):
                newchildren.append(child.nodes())
        return TreeToken(self.node(), *newchildren)

    def height(self):
        """
        @return: The height of this C{TreeToken}.  The height of a
            C{TreeToken} containing no children is 1; the height of a
            C{TreeToken} containing only leaves is 2; and the height
            of any other C{TreeToken} is one plus the maximum of its
            children's heights.
        @rtype: C{int}
        """
        max_child_height = 0
        for child in self._children:
            if isinstance(child, TreeToken):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = 1
        return 1 + max_child_height

    def __hash__(self):
        return hash((self._node, self._children))

    def __eq__(self, other):
        """
        @return: true if this C{TreeToken} is equal to C{other}.  In
            particular, return true if C{self.node()==other.node()},
            C{self.len()==other.len()}, and C{self[i]==other[i]} for
            all i, 0 <= i < self.len()
        @rtype: C{boolean}
        """
        _chkclass(self, other)
        return (self._node == other._node and
                self._children == other._children)

    def __ne__(self, other):
        """
        @return: true if this C{TreeToken} is not equal to C{other}.
            In particular, return false if
            C{self.node()==other.node()}, C{self.len()==other.len()},
            and C{self[i]==other[i]} for all i, 0 <= i < self.len()
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
                             "defined over TreeTokens")

    def draw(self):
        """
        Open a graphical window containing a diagram of the text
        tree token.

        @rtype: None
        """
        # Note: this method introduces a circular dependancy between
        # modules.  However, this circularity is only a matter of
        # convenience.  In particular, we believe that it is more
        # intuitive for students to run "mytree.draw()" than
        # "draw.tree.drawtree(mytree)".
        import nltk.draw.tree
        nltk.draw.tree.TreeView(self)

##//////////////////////////////////////////////////////
##  Conversion Routines
##//////////////////////////////////////////////////////

def parse_treebank(str):
    """
    Given a string containing a Treebank-style representation of a
    syntax tree, return a C{Tree} representing that syntax tree.
    """
    _chktype("parse_treebank", 1, str, (_StringType,))
    
    # Rather than trying to parse the string ourselves, we will rely
    # on the Python parser.  This procedure isn't immediately easy to
    # understand, but if you add a "print str" after each call to
    # re.sub, and try it out on an example, you should be able to
    # figure out what's going on.

    # Backslash any quote marks or backslashes in the string.
    str = re.sub(r'([\\"\'])', r'\\\1', str)

    # Add quote marks and commas around words.
    str = re.sub('([^() ]+)', r'"\1",', str)

    # Add commas after close parenthases.
    str = re.sub(r'\)', '),', str)
    
    # Add calls to the Tree constructor.
    str = re.sub(r'\(', 'Tree(', str)

    # Strip whitespace and get rid of the comma after the last ')' 
    str = str.strip()[:-1]

    # Use "eval" to convert the string (is this safe?)
    try:
        result = eval(str)
        return result[0]
    except:
        raise ValueError('Bad Treebank-style string')
