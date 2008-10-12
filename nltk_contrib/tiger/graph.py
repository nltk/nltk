# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
from collections import deque
from copy import deepcopy

from nltk_contrib.tiger.utils.enum import Enum, enum_member

__all__ = ("NodeType", "TerminalNode", "NonterminalNode", "TigerGraph", "veeroot_graph")

DEFAULT_VROOT_EDGE_LABEL = "--"


class NodeType(Enum):
    __fields__  = ("key",)

    TERMINAL = enum_member("T")
    NONTERMINAL = enum_member("N")
    UNKNOWN = enum_member("FREC")
    
    @staticmethod
    def fromkey(type_key):
        if type_key == "T":
            return NodeType.TERMINAL
        elif type_key == "N":
            return NodeType.NONTERMINAL
        else:
            raise ValueError, "Unknown domain key '%s'." % (type_key,)
    
    def __invert__(self):
        if self is self.__class__.TERMINAL:
            return self.__class__.NONTERMINAL
        elif self is self.__class__.NONTERMINAL:
            return self.__class__.TERMINAL
        else:
            raise ValueError, "Cannot invert '%s'." % (self,)


class _TigerNode(object):
    __slots__ = ("id", "features", "secedges", "TYPE")

    def __init__(self, id_):
        self.id = id_
        self.features = {}
        self.secedges = None

    def __eq__(self, other):
        return self.TYPE is other.TYPE and self.id == other.id \
               and self.features == other.features and self.secedges == other.secedges

    def __ne__(self, other):
        return not (self == other)


class TerminalNode(_TigerNode):
    __slots__ = ("order", )
    TYPE = NodeType.TERMINAL
    
    def __init__(self, id_):
        _TigerNode.__init__(self, id_)
        self.order = None
    
    def __eq__(self, other):
        return self.order == other.order and super(TerminalNode, self).__eq__(other)
    
    def __repr__(self): # pragma: nocover
        return "T(%s, %s, %s, %s)" % (self.id, self.features, self.order,
                                      [] if self.secedges is None else self.secedges)
    
    def __deepcopy__(self, memo):
        n = TerminalNode(self.id)
        n.order = self.order
        n.features = deepcopy(self.features, memo)
        n.secedges = deepcopy(self.secedges, memo)
        return n


class NonterminalNode(_TigerNode):
    __slots__ = ("edges",)
    TYPE = NodeType.NONTERMINAL
    
    def __init__(self, id_):
        super(NonterminalNode, self).__init__(id_)
        self.edges = None
        
    def __eq__(self, other):
        return self.edges == other.edges and super(NonterminalNode, self).__eq__(other)

    def __repr__(self): # pragma: nocover
        return "NT(%s, %s, %s, %s)" % (self.id, self.features, self.edges, 
                                       [] if self.secedges is None else self.secedges)

    def __iter__(self):
        return iter(self.edges)
    
    def __deepcopy__(self, memo):
        n = NonterminalNode(self.id)
        n.features = deepcopy(self.features, memo)
        n.secedges = deepcopy(self.secedges, memo)
        n.edges = deepcopy(self.edges, memo)
        return n
        
    
def veeroot_graph(graph, roots, edge_label = DEFAULT_VROOT_EDGE_LABEL):
    vroot_id = "%s_VROOT" % (graph.id,)
    
    assert vroot_id not in graph.nodes, \
           "Graph %s already has a node named '%s_VROOT'" % (graph.id, vroot_id)
    
    vroot_node = NonterminalNode(vroot_id)
    vroot_node.edges = [(edge_label, child_id) for child_id in roots]
    graph.root_id = vroot_id
    graph.nodes[vroot_id] = vroot_node

    
class NodeIndexData(object):
    __slots__ = ("id", "edge_label", "gorn_address")

    def __init__(self, id_, **kwargs):
        self.id = id_
        self.edge_label = None
        self.gorn_address = None
        for name, value in kwargs.iteritems():
            setattr(self, name, value)

            
class TerminalIndexData(NodeIndexData):
    __slots__ = ("order", )

    def __init__(self, id_, **kwargs):
        super(TerminalIndexData, self).__init__(id_, **kwargs)
        
            
class NonterminalIndexData(NodeIndexData):
    __slots__ = ("is_continuous", "arity", "token_arity", "left_corner", "right_corner", "children_type")

    def __init__(self, id_, **kwargs):
        self.is_continuous = True        
        super(NonterminalIndexData, self).__init__(id_, **kwargs)


class TigerGraph(object):
    __slots__ = ("id", "root_id", "nodes")
    def __init__(self, id_):
        self.id = id_
        self.nodes = {}
        self.root_id = None

    def __eq__(self, other):
        return self.id == other.id and self.nodes == other.nodes  and self.root_id == other.root_id
    
    def __ne__(self, other):
        return not (self == other)
    
    def __iter__(self):
        return self.nodes.itervalues()
    
    def terminals(self):
        return (n for n in self.nodes.itervalues() if n.TYPE is NodeType.TERMINAL)

    def nonterminals(self):
        return (n for n in self.nodes.itervalues() if n.TYPE is NodeType.NONTERMINAL)

    def copy(self):
        g = TigerGraph(self.id)
        g.root_id = self.root_id
        g.nodes = self.nodes.copy()
        return g
    
    def get_roots(self):
        unconnected = set(self.nodes)
        
        if self.nodes[self.root_id].TYPE is NodeType.NONTERMINAL:
            worklist = deque([self.root_id])
            while len(worklist) > 0:
                node_id = worklist.popleft()
                for label, child_id in self.nodes[node_id]:
                    unconnected.remove(child_id)
                    if self.nodes[child_id].TYPE is NodeType.NONTERMINAL:
                        worklist.append(child_id)
        
        return unconnected
    
    def compute_node_information(self):
        terminals = {}
        nonterminals = {}
        
        self._compute_dominance(terminals, nonterminals)
        self._compute_corners(nonterminals)

        return nonterminals.values(), terminals.values()

    def _compute_corners(self, nonterminals):
        def traverse(node_id, node_data):
            corners = []
            for label, child_id in self.nodes[node_id].edges:
                if self.nodes[child_id].TYPE is NodeType.TERMINAL:
                    corners.append(child_id)
                else:
                    corners += traverse(child_id, nonterminals[child_id])
            
            lco = node_data.left_corner = min(corners, key = lambda x: self.nodes[x].order)
            rco = node_data.right_corner = max(corners, key = lambda x: self.nodes[x].order)
            
            node_data.is_continuous = (
                node_data.token_arity == self.nodes[rco].order - self.nodes[lco].order + 1)
            return lco, rco
        
        if self.nodes[self.root_id].TYPE is NodeType.NONTERMINAL:
            traverse(self.root_id, nonterminals[self.root_id])

    def _get_children_type(self, node):
        x = 0
        for child in node:
            if self.nodes[child[1]].TYPE is NodeType.TERMINAL:
                x |= 1
            else:
                x |= 2
        return x
        
    def _compute_dominance(self, terminals, nonterminals):
        def traverse(node, gorn_address):
            token_arity = 0
            
            for idx, (label, child_id) in enumerate(node.edges):
                child_address = gorn_address + (idx, )
                child_node = self.nodes[child_id]
                if child_node.TYPE is NodeType.TERMINAL:
                    terminals[child_id] = TerminalIndexData(child_id, edge_label = label,
                                                            gorn_address = child_address, 
                                                            order = child_node.order)
                    token_arity += 1
                else:
                    d = nonterminals[child_id] = NonterminalIndexData(
                        child_id, edge_label = label, gorn_address = child_address,
                        arity = len(child_node.edges), 
                        children_type = self._get_children_type(child_node))
                    d.token_arity = traverse(child_node, child_address)
                    token_arity += d.token_arity
                    
            return token_arity
        
        
        root_node = self.nodes[self.root_id]
        if root_node.TYPE is NodeType.TERMINAL:
            terminals[self.root_id] = TerminalIndexData(self.root_id, gorn_address = (),
                                                        order = root_node.order)
        else:
            d = nonterminals[self.root_id] = NonterminalIndexData(
                self.root_id, gorn_address = (), arity = len(root_node.edges), 
                children_type = self._get_children_type(root_node))
        
            d.token_arity = traverse(root_node, ())
