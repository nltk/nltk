# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2

from collections import defaultdict
from itertools import count
import logging

def get_version_string():
    import nltk
    return "nltk %s" % (nltk.__version__, )

from nltk_contrib.tiger.index import IndexNodeId, CONTINUOUS, DISCONTINUOUS, gorn2db
from nltk_contrib.tiger.graph import NodeType, veeroot_graph, DEFAULT_VROOT_EDGE_LABEL

__all__ = ("TigerCorpusIndexer",)

# think about splitting feature_values table into several small tables.
# add NOT NULLS everywhere

# TODO: create proper progress reporter interface, hand in

INDEX_VERSION = 3

class _Tables(object):
    FEATURES = """CREATE TABLE features
    (id INTEGER PRIMARY KEY, order_id INTEGER, name TEXT, domain TEXT)"""
    
    FEATURE_VALUES = """CREATE TABLE feature_values
    (feature_id INTEGER, value_id INTEGER, value TEXT, description TEXT, 
     UNIQUE(feature_id, value_id))"""
    
    EDGE_LABELS = """CREATE TABLE edge_labels
    (id INTEGER PRIMARY KEY, label TEXT UNIQUE, description TEXT)"""
    
    SECEDGE_LABELS = """CREATE TABLE secedge_labels
    (id INTEGER PRIMARY KEY, label TEXT UNIQUE, description TEXT)"""
    
    GRAPHS = """CREATE TABLE graphs
    (id INTEGER PRIMARY KEY, xml_graph_id TEXT, data BLOB)"""
    
    METADATA = """CREATE TABLE corpus_metadata 
    (key TEXT UNIQUE, value TEXT)"""

    INDEX_METADATA = """CREATE TABLE index_metadata 
    (key TEXT UNIQUE, value NONE)"""
    
    NODE_DATA = """CREATE TABLE node_data 
    (id INTEGER PRIMARY KEY, xml_node_id TEXT, edge_label INTEGER, 
    gorn_address BLOB, continuity INTEGER, arity INTEGER,
    tokenarity INTEGER, left_corner INTEGER, right_corner INTEGER, token_order INTEGER)"""

    FEATURE_IIDX_TEMPLATE = """CREATE TABLE feature_iidx_%s 
    (node_id INTEGER PRIMARY KEY NOT NULL, value_id INTEGER NOT NULL)"""
    
    SECEDGES = """CREATE TABLE secedges
    (origin_id INT, target_id INT, label_id INT)"""

    
class TigerCorpusIndexer(object):
    def __init__(self, db, graph_serializer, progress = False, always_veeroot = True):
        self._db = db
        self._cursor = db.cursor()
        self._progress = progress
        self._always_veeroot = always_veeroot
        
        self._graphs = 0
        
        self._cursor.execute(_Tables.FEATURES)
        self._cursor.execute(_Tables.FEATURE_VALUES)
        self._cursor.execute(_Tables.EDGE_LABELS)
        self._cursor.execute(_Tables.SECEDGE_LABELS)
        self._cursor.execute(_Tables.GRAPHS)
        self._cursor.execute(_Tables.METADATA)
        self._cursor.execute(_Tables.INDEX_METADATA)
        self._cursor.execute(_Tables.NODE_DATA)
        self._cursor.execute(_Tables.SECEDGES)
        
        self._serializer = graph_serializer
        self._open_list_features = []
        self._feature_count = {
            NodeType.TERMINAL: 0,
            NodeType.NONTERMINAL: 0}
        
        self._feature_iidx_stmts = {}
        self._feature_value_maps = {}

        self._insert_lists = defaultdict(list)
        self._store_creator_metadata()
        
    def _store_creator_metadata(self):
        self._add_index_metadata(creator=get_version_string(), index_version=INDEX_VERSION)
    
    def _add_index_metadata(self, **kwargs):
        self._cursor.executemany("INSERT INTO index_metadata (key, value) VALUES (?, ?)", 
                                 kwargs.iteritems())
        
    def set_metadata(self, metadata):
        self._cursor.executemany("INSERT INTO corpus_metadata (key, value) VALUES (?, ?)", 
                                 metadata.iteritems())
                             
    
    def add_feature(self, feature_name, domain, feature_values):
        order_id = self._feature_count[domain]
        self._feature_count[domain] += 1
        self._cursor.execute("INSERT INTO features (order_id, name, domain) VALUES (?, ?, ?)", 
                             (order_id, feature_name, domain.key))
        feature_id = self._cursor.lastrowid
        
        if len(feature_values) > 0:
            value_map = dict((feature_value, idx) for idx, feature_value in enumerate(feature_values))
            
            self._cursor.executemany("INSERT INTO feature_values (feature_id, value_id, value, description) VALUES (?, ?, ?, ?)",
                                     ((feature_id, value_map[value], value, description) 
                                      for value, description in feature_values.iteritems()))
        else:
            value_map = defaultdict(count().next)
            self._open_list_features.append((feature_id, value_map))
        
        self._feature_value_maps[feature_name] = (value_map, domain)
        self._serializer.add_feature_value_map(feature_name, domain, order_id, value_map)
        self._create_feature_value_index(feature_name)
        return feature_id

    
    def set_edge_labels(self, edge_labels):
        if self._always_veeroot:
            assert DEFAULT_VROOT_EDGE_LABEL in edge_labels, "no neutral edge label"
            
        self._cursor.executemany("INSERT INTO edge_labels (id, label, description) VALUES (?, ?, ?)", 
                                 ((idx, e[0], e[1]) for idx, e in enumerate(edge_labels.iteritems())))
        self._edge_label_map = dict(self._cursor.execute("SELECT label, id FROM edge_labels"))
        self._serializer.set_edge_label_map(self._edge_label_map)
    
    def set_secedge_labels(self, secedge_labels):
        self._cursor.executemany("INSERT INTO secedge_labels (id, label, description) VALUES (?, ?, ?)", 
                                 ((idx, e[0], e[1]) for idx, e in enumerate(secedge_labels.iteritems())))
        self._secedge_label_map = dict(self._cursor.execute("SELECT label, id FROM secedge_labels"))
        self._serializer.set_secedge_label_map(self._secedge_label_map)
    
    def _create_feature_value_index(self, feature_name):
        feature_name = str(feature_name)
        assert feature_name.isalpha()
        
        self._cursor.execute(_Tables.FEATURE_IIDX_TEMPLATE % (feature_name,))
        
        
        self._feature_iidx_stmts[feature_name] = "INSERT INTO feature_iidx_%s (node_id, value_id) VALUES (?, ?)" % (feature_name,)
    
    def get_terminal_index_data(self, node, node_ids):
        return (node_ids[node.id].to_int(), node.id, self._edge_label_map.get(node.edge_label, None),
                gorn2db(node.gorn_address), node.order)
    
    def get_nonterminal_index_data(self, node, node_ids):
        return (node_ids[node.id].to_int(), node.id, self._edge_label_map.get(node.edge_label, None),
                gorn2db(node.gorn_address),
                (CONTINUOUS if node.is_continuous else DISCONTINUOUS), 
                node.arity, node.token_arity, 
                node_ids[node.left_corner].to_int(), node_ids[node.right_corner].to_int(), 
                node.children_type)

    def _store_node_data(self, graph, node_ids):
        nonterminals, terminals = graph.compute_node_information()
        
        self._cursor.executemany("""INSERT INTO node_data 
        (id, xml_node_id, edge_label, gorn_address, continuity, arity, tokenarity, left_corner, right_corner, token_order) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                             (self.get_nonterminal_index_data(nt, node_ids) for nt in nonterminals))
        
        self._cursor.executemany("INSERT INTO node_data (id, xml_node_id, edge_label, gorn_address, token_order, continuity) VALUES (?, ?, ?, ?, ?, 0)",
                                 (self.get_terminal_index_data(t, node_ids) for t in terminals))
        
    
    def _index_feature_values(self, graph, node_ids):
        for node in graph:
            for feature_name, feature_value in node.features.iteritems():
                value_map, domain = self._feature_value_maps[feature_name]
                assert node.TYPE is domain
                self._insert_lists[feature_name].append((node_ids[node.id].to_int(), value_map[feature_value]))
        
        if self._graphs % 1000 == 0:
            self._flush_node_feature_values()
            
    def _index_secedges(self, graph, node_ids):
        for node in graph:
            if node.secedges is not None:
                self._cursor.executemany(
                    "INSERT INTO secedges (origin_id, target_id, label_id) VALUES (?, ?, ?)",
                    ((node_ids[node.id].to_int(), node_ids[graph.nodes[target_node].id].to_int(), 
                      self._secedge_label_map[label])
                     for label, target_node in node.secedges))
                
    def _flush_node_feature_values(self):
        for feature_name, values in self._insert_lists.iteritems():
            self._cursor.executemany(self._feature_iidx_stmts[feature_name], values)
        self._insert_lists = defaultdict(list)

    def _convert_ids(self, graph, node_ids): # split out into separate method
        def _convert_edgelist(l):
            return [(label, node_ids[target_xml_id]) 
                    for label, target_xml_id in l]
      
        graph.id = self._graphs
        graph.root_id = node_ids[graph.root_id]
        for xml_node_id in graph.nodes.keys():
            node = graph.nodes.pop(xml_node_id)
            node.id = node_ids[node.id]
            graph.nodes[node_ids[xml_node_id]] = node
            if node.secedges:
                node.secedges = _convert_edgelist(node.secedges)
            if node.TYPE is NodeType.NONTERMINAL:
                node.edges = _convert_edgelist(node.edges)

    def add_graph(self, graph):
        try:
            roots = graph.get_roots()
        except KeyError, e:
            logging.error("Graph %s is faulty: node %s referenced more than once.",
                          graph.id, e.args[0])
            return

        if self._always_veeroot:
            veeroot_graph(graph, roots)
        else:
            assert len(roots) == 1, "No auto-veerooting, but several unconnected subgraphs %s in %s." % (roots, graph.id)
                
        node_ids = dict((xml_node_id, IndexNodeId(self._graphs, idx))
                        for idx, xml_node_id in enumerate(graph.nodes))
        
        xml_id = graph.id
        self._store_node_data(graph, node_ids)
        self._index_feature_values(graph, node_ids)
        self._index_secedges(graph, node_ids)
        
        self._convert_ids(graph, node_ids)
        
        self._cursor.execute("INSERT INTO graphs (id, xml_graph_id, data) VALUES (?, ?, ?)",
                             (self._graphs, xml_id, buffer(self._serializer.serialize_graph(graph))))
        self._graphs += 1
        if self._progress and self._graphs % 100 == 0:
            print self._graphs
    
    def finalize(self, optimize = True):
        if self._progress:
            print "finalize"
        self._flush_node_feature_values()
        
        if self._progress:
            print "inserting feature values"
        for feature_id, feature_value_map in self._open_list_features:
            self._cursor.executemany("INSERT INTO feature_values (feature_id, value_id, value) VALUES (?, ?, ?)",
                                     ((feature_id, value_id, value) 
                                      for value, value_id in feature_value_map.iteritems()))
        del self._open_list_features

        if self._progress:
            print "Committing database"
        self._db.commit()

        self._cursor.execute("CREATE INDEX feature_id_idx ON feature_values (feature_id)")
        
        for feature_name in self._feature_value_maps:
            if self._progress:
                print "creating index for feature '%s'" % (feature_name,)
            self._cursor.execute("CREATE INDEX %s_iidx_idx ON feature_iidx_%s (value_id)" % (feature_name, feature_name))
        
        if self._progress:
            print "creating index for xml node ids"
        self._cursor.execute("CREATE UNIQUE INDEX xml_node_id_idx ON node_data (xml_node_id)")
        
        if self._progress:
            print "creating index for xml graph ids"
        self._cursor.execute("CREATE UNIQUE INDEX xml_graph_id_idx ON graphs (xml_graph_id)")
        
        if self._progress:
            print "creating secedge indices"
        self._cursor.execute("CREATE INDEX se_origin_idx ON secedges (origin_id)")
        self._cursor.execute("CREATE INDEX se_target_idx ON secedges (target_id)")

        self._db.commit()
        
        if optimize:
            if self._progress:
                print "Optimizing database"
            self._db.execute("VACUUM")
        
        self._add_index_metadata(finished = True)
        self._db.commit()
        
        self._db = None
        self._cursor = None
