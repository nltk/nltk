#
# Natural Language Toolkit:
# Text Trees
# Edward Loper
#
# Created [06/22/01 01:35 AM]
# $Id$
#

# To do:
#   - add reference documentation
#   - enforce consistancy conditions
#   - add more type checking, esp for __eq__ etc

import token
from chktype import chktype as _chktype
from types import SliceType as _SliceType
from types import IntType as _IntType
from types import StringType as _StringType
from types import NoneType as _NoneType
from types import ListType as _ListType

##//////////////////////////////////////////////////////
##  Text Trees (Type)
##//////////////////////////////////////////////////////
class Tree:
    def __init__(self, node, *children):
        self._node = node
        self._children = children

    def node(self): return self._node

    def __getitem__(self, index):
        _chktype("Tree.__getitem__", 1, index, (_IntType, _SliceType))
        if type(index) == _SliceType:
            return self._children[index.start:index.stop]
        else:
            return self._children(index)
        print dir(index)

    def __len__(self): return len(self._children)

    def __repr__(self):
        str = '('+repr(self._node)+':'
        for child in self._children:
            str += ' '+repr(child)
        return str+')'

    def pp(self, indent=0, margin=70):
        rep = repr(self)
        if len(rep)+indent < margin:
            return rep
        str = '('+repr(self._node)+':'
        for child in self._children:
            if isinstance(child, Tree):
                str += '\n'+' '*(indent+2)+child.pp(indent+2, margin)
            else:
                str += '\n'+' '*(indent+2)+repr(child)
        return str+')'

    def __str__(self):
        return self.pp()

    def leaves(self):
        """
        @return: an ordered list of this C{Tree}'s leaves
        @rtype: C{tuple} of (leaftype)
        """
        leaves = []
        for child in self._children:
            if isinstance(child, Tree):
                leaves.extend(child.leaves)
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
        return Tree(self.node, newchildren)

##//////////////////////////////////////////////////////
##  Text Tree Tokens
##//////////////////////////////////////////////////////
class TreeToken(token.Token):
    def __init__(self, node, *children):
        self._node = node
        self._children = children

    def type(self):
        typechildren = []
        for child in self._children:
            typechildren.append(child.type())
        return Tree(self._node, *typechildren)

    def _firstloc(self):
        firstloc = None
        for i in range(len(self._children)):
            if isinstance(self._children[i], TreeToken):
                firstloc = self._children[i]._firstloc()
                if firstloc != None: return firstloc
            else:
                return self._children[i].source()

    def _lastloc(self):
        lastloc = None
        for i in range(len(self._children)-1,-1,-1):
            if isinstance(self._children[i], TreeToken):
                lastloc = self._children[i]._lastloc()
                if lastloc != None: return lastloc
            else:
                return self._children[i].source()
    
    def source(self):
        firstloc = self._firstloc()
        lastloc = self._lastloc()
        return token.Location(firstloc.start(), lastloc.end(),
                              firstloc.source(), lastloc.unit())

    def __repr__(self):
        return repr(self.type())+repr(self.source())

    def __str__(self):
        return str(self.type())+str(self.source())

def test():
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

if __name__ == '__main__':
    test()
