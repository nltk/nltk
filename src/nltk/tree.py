#
# Natural Language Toolkit:
# Text Trees
# Edward Loper
#
# Created [06/22/01 01:35 AM]
# $Id$
#

# To do:
#   - add (more) reference documentation
#   - add more type checking, esp for __eq__ etc
#   - add x-to-y methods for treebank, etc.
#   - traces!! Whee.

import token
from chktype import chktype as _chktype
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
    A homogenous hierarchical structure over text tokens.  A C{Tree}
    consists of a X{node value} and zero or more X{children}.

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
    leaf set must have the same type.  A C{Tree}'s X{nodes values set}
    consists of the node value of the C{Tree} and the node value sets
    of its subtrees.  All node values in a tree's node value set must
    have the same type.
    """
    def __init__(self, node, *children):
        """
        Construct a new Tree object, with the given node value and
        children.  For example:

            >>> Tree('np', 'the', 'cat')
            ('np': 'the' 'cat')

        Note that the children should not be given as a
        single list; doing so will cause that list to be treated as a
        single child token.  If you need to consturct a C{Tree} from a 
        list of children, use the following syntax:

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
            if (c_nodetype != None and
                self._nodetype != c_nodetype):
                raise TypeError("All nodes in a Tree must have the "+
                                "same Python type.")
            if (self._leaftype != None and c_leaftype != None and
                self._leaftype != c_leaftype):
                raise TypeError("All leaves in a Tree must have the "+
                                "same Python type.")
            if (self._leaftype == None and c_leaftype != None):
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
            return self._children(index)
        print dir(index)

    def __len__(self):
        """
        @return: The number of children this C{Tree} has.
        @rtype: C{int}
        """
        return len(self._children)

    def __repr__(self):
        """
        @return: A concise string representation of this C{Tree}.
        @rtype: C{string}
        """
        str = '('+repr(self._node)+':'
        for child in self._children:
            str += ' '+repr(child)
        return str+')'

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

##//////////////////////////////////////////////////////
##  Text Tree Tokens
##//////////////////////////////////////////////////////
class TreeToken(token.Token):
    def __init__(self, node, *children):
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
            if (c_nodetype != None and
                self._nodetype != c_nodetype):
                raise TypeError("All nodes in a TreeToken must "+
                                "have the same Python type.")
            if (self._leaftype != None and c_leaftype != None and
                self._leaftype != c_leaftype):
                raise TypeError("All leaves in a TreeToken must "+
                                "have the same Python type.")
            if (self._leaftype == None and c_leaftype != None):
                self._leaftype = c_leaftype

        # Find/check our location.
        start = None
        end = None
        prevloc = None
        try:
            for child in children:
                loc = child.location()
                if loc is None: continue
                if start is None: start = loc.start()
                end = loc.end()
                if prevloc != None and not (prevloc < loc):
                    raise ValueError("The leaves of a TreeToken "+ 
                                     "must be properly ordered.")
                prevloc = loc
        except ValueError:
            raise ValueError("The leaves of a TreeToken must have "+
                             "compatible units and sources.")
        if prevloc is None:
            self._location = None
        else:
            self._location = token.Location(start, end,
                                            unit=prevloc.unit(),
                                            source=prevloc.source())

    def __getitem__(self, index):
        _chktype("Tree.__getitem__", 1, index, (_IntType, _SliceType))
        if type(index) == _SliceType:
            return self._children[index.start:index.stop]
        else:
            return self._children(index)
        print dir(index)

    def __len__(self): return len(self._children)

    def type(self):
        typechildren = []
        for child in self._children:
            typechildren.append(child.type())
        return Tree(self._node, *typechildren)

    def location(self):
        return self._location

    def pp(self):
        if self.location() is None:
            return self.type().pp()+'@?'
        else:
            return self.type().pp()+repr(self.location())

    def __repr__(self):
        if self.location() is None:
            return repr(self.type())+'@?'
        else:
            return repr(self.type())+repr(self.location())
        
    def __str__(self):
        return self.pp()

def test():
    from token import Token
    t=Tree('ip', Tree('dp', Tree('d', 'a'), Tree('n', 'cat')),
           Tree('vp', Tree('v', 'saw'),
                Tree('dp', Tree('d', 'a'), Tree('n', 'dog'))))

    t2=TreeToken('ip',
                 TreeToken('dp',
                           TreeToken('d', Token('a',1)),
                           TreeToken('n', Token('cat',2))),
                 TreeToken('vp',
                           TreeToken('v', Token('saw',3)),
                           TreeToken('dp',
                                     TreeToken('d', Token('a',4)),
                                     TreeToken('n', Token('dog',5)))))
    print t
    print t2
    print t2.location()

if __name__ == '__main__':
    test()
