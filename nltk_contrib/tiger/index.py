# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Classes and methods related to the TIGER corpus on-disk index."""
import operator
import array

__all__ = ("IndexNodeId", "CONTINUOUS", "DISCONTINUOUS")

ID = 0
EDGE_LABEL = 1
CONTINUITY = 2
LEFT_CORNER = 3
RIGHT_CORNER = 4
TOKEN_ORDER = 5
GORN_ADDRESS = 6


CONTINUOUS = 1
DISCONTINUOUS = 3

class IndexNodeId(tuple):
    __slots__ = ()
    NODE_BIT_WIDTH = 12
    NODE_BITMASK = (1 << NODE_BIT_WIDTH) - 1

    def __new__(cls, graph_id, node_id):
        return tuple.__new__(cls, (graph_id, node_id))
    
    def __repr__(self):
        return "IndexNodeId(%i, %i)" % self
    
    def __reduce__(self):
        return (IndexNodeId, (self[0], self[1]))
    
    @classmethod
    def from_int(cls, i):
        return tuple.__new__(cls, (i >> 12, i & IndexNodeId.NODE_BITMASK))
    
    def to_int(self):
        return self[0] << self.NODE_BIT_WIDTH | self[1]
    
    def check(self):
        return self.graph_id < (1 << 20) and self.node_id < (1 << self.NODE_BIT_WIDTH)
    
    graph_id = property(operator.itemgetter(0))
    node_id = property(operator.itemgetter(1))

def gorn2db(address_tuple):
    return buffer(array.array("b", address_tuple).tostring())
