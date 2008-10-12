# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
import cPickle
import cStringIO
import zlib

from nltk_contrib.tiger.graph import NodeType, TigerGraph, NonterminalNode, TerminalNode

__all__ = ("GraphSerializer", "GraphDeserializer")

class GraphSerializer(object):
    def __init__(self):
        self._feature_value_map = {}
        self._feature_count = {
            NodeType.TERMINAL: 0, 
            NodeType.NONTERMINAL:  0
        }
        self.graphs = 0
        self.total_size = 0
        
    def set_edge_label_map(self, edge_label_map):
        self._edge_label_map = edge_label_map
    
    def set_secedge_label_map(self, secedge_label_map):
        self._secedge_label_map = secedge_label_map
    
    def add_feature_value_map(self, feature_name, domain, position, value_map):
        self._feature_count[domain] += 1
        self._feature_value_map[feature_name] = (position, value_map, domain)
        
    def _convert_edges(self, edge_list, label_map):
        l = []
        for label, target_id in edge_list:
            l.append(label_map[label])
            l.append(target_id)
        return tuple(l)

    def serialize_graph(self, graph):
        self.graphs += 1
        nts = []
        se_nts = []
        ts = []
        se_ts = []
        
        for node in graph.terminals():
            feature_list = [None] * self._feature_count[node.TYPE]
            for key, value in node.features.iteritems():
                descriptor = self._feature_value_map[key]
                assert descriptor[2] is node.TYPE
                feature_list[descriptor[0]] = descriptor[1][value]
            
            if node.secedges is None:
                ts.extend((node.id, tuple(feature_list), node.order))
            else:
                se_ts.extend((node.id, tuple(feature_list), node.order, 
                              self._convert_edges(node.secedges, self._secedge_label_map)))
            
        
        for node in graph.nonterminals():
            feature_list = [None] * self._feature_count[node.TYPE]
            for key, value in node.features.iteritems():
                descriptor = self._feature_value_map[key]
                assert descriptor[2] is node.TYPE
                feature_list[descriptor[0]] = descriptor[1][value]
            
            edges = self._convert_edges(node.edges, self._edge_label_map)
            
            if node.secedges is None:
                nts.extend((node.id, tuple(feature_list), edges))
            else:
                se_nts.extend((node.id, tuple(feature_list), edges, 
                               self._convert_edges(node.secedges, self._secedge_label_map)))
        
        d = cStringIO.StringIO()
        p = cPickle.Pickler(d, protocol = 2)
        p.dump(graph.root_id)
        for l in (nts, ts, se_nts, se_ts):
            p.dump(tuple(l))
        
        s = zlib.compress(d.getvalue())
        self.total_size += len(s)
        return s
    

class GraphDeserializer(object):
    def __init__(self, edge_label_rmap, secedge_label_rmap, t_feature_rmap, nt_feature_rmap):
        self._edge_label_rmap = edge_label_rmap
        self._secedge_label_rmap = secedge_label_rmap
        self._t_features = t_feature_rmap
        self._nt_features = nt_feature_rmap

    def _get_edge_list(self, edge_data, label_rmap):
        return [(label_rmap[edge_data[i]], edge_data[i+1])
                 for i in xrange(0, len(edge_data), 2)]
        
    def _get_features(self, fmap, stored):
        return dict(
            (fmap[idx][0], fmap[idx][1][value])
            for idx, value in enumerate(stored) if value is not None)
    
    def get_root_id(self, graph_data_buffer):
        up = cPickle.Unpickler(cStringIO.StringIO(zlib.decompress(graph_data_buffer)))
        return up.load()
    
    def deserialize_graph(self, graph_id, graph_data_buffer):
        graph = TigerGraph(graph_id)
        up = cPickle.Unpickler(cStringIO.StringIO(zlib.decompress(graph_data_buffer)))

        graph.root_id = up.load()
        data = up.load()
        for i in xrange(0, len(data), 3):
            node = NonterminalNode(data[i])
            node.features  = self._get_features(self._nt_features, data[i+1])

            node.edges = self._get_edge_list(data[i+2], self._edge_label_rmap)
            
            graph.nodes[node.id] = node
        
        data = up.load()
        for i in xrange(0, len(data), 3):
            node = TerminalNode(data[i])
            node.features  = self._get_features(self._t_features, data[i+1])
            node.order = data[i+2]
            graph.nodes[node.id] = node
        
        data = up.load()
        for i in xrange(0, len(data), 4):
            node = NonterminalNode(data[i])
            node.features  = self._get_features(self._nt_features, data[i+1])
            node.edges = self._get_edge_list(data[i+2], self._edge_label_rmap)
            node.secedges = self._get_edge_list(data[i+3], self._secedge_label_rmap)
            
            graph.nodes[node.id] = node
            
        data = up.load()
        for i in xrange(0, len(data), 4):
            node = TerminalNode(data[i])
            node.features  = self._get_features(self._t_features, data[i+1])
            node.order = data[i+2]
            node.secedges = self._get_edge_list(data[i+3], self._secedge_label_rmap)
            
            graph.nodes[node.id] = node
        
        return graph
