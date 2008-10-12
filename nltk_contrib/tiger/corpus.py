# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module provides a single point of access to all functionality of a TigerSearch corpus
once its index has been created.
"""
from nltk_contrib.tiger.indexer import graph_serializer
from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.index import IndexNodeId
from nltk_contrib.tiger.query import TsqlQueryEvaluator

__all__ = ("Corpus", )

# TODO: provide methods for accessing edge labels and feature values.


class CorpusInfo(object):
    def __init__(self, db):
        self._cursor = db.cursor()
        self.corpus_size = self._cursor.execute("SELECT COUNT(*) FROM graphs").fetchone()[0]
        
    def get_feature_names(self, node_type):
        if node_type is NodeType.UNKNOWN:
            return frozenset(row[0] for row in self._cursor.execute(
                "SELECT name FROM features"))
        else:
            return frozenset(row[0] for row in self._cursor.execute(
                "SELECT name FROM features WHERE domain = ?", (node_type.key, )))

    @property
    def feature_types(self):
        if not hasattr(self, "_feature_types"):
            self._feature_types = dict(
                (feat, node_type) 
                for node_type in [NodeType.TERMINAL, NodeType.NONTERMINAL]
                for feat in self.get_feature_names(node_type))

        return self._feature_types


class Corpus(object):
    """A class that provides access to a TIGER-XML corpus.
    
    
    Lifecycle
    =========
    Corpora should always be instantiated using the factory methods in `nltk_contrib.tiger`. When a corpus
    object is not used anymore, it should be `close()`ed.
    
    Graphs
    ======
    Graphs can be loaded by their ordinal, using the function `get_graph(o)`. Graph ordinals are in 
    the range ``[0..len(corpus)[``, and assigned by indexer that created the corpus. The Tiger
    corpus indexer assigns graph ids based on the order in the input file.
    
    XML ids and index ids
    =====================
    The `Corpus` class provides several methods to convert the internal index ids to the XML ids
    found in the TIGER-XML corpus, and vice versa:
    
     * `get_xml_node_id`
     * `get_xml_graph_id`
     * `get_index_node_id`
    
    Query Evaluation
    ================
    The method `get_query_evaluator` returns the TigerSearch query evaluator for this corpus.
    """
    DEFAULT_DESERIALIZER = graph_serializer.GraphDeserializer

    def __init__(self, treebank_id, db, db_provider):
        self.treebank_id = treebank_id
        
        self._db_provider = db_provider
        self._db = db
        self._info = CorpusInfo(db)
        
        self._cursor = self._db.cursor()
        
        self._deserializer = self.DEFAULT_DESERIALIZER(
            self._get_edge_label_rmap(),
            self._get_secedge_label_rmap(),
            self._get_feature_revmap(NodeType.TERMINAL),
            self._get_feature_revmap(NodeType.NONTERMINAL))
        
        self._evaluator = None

    def _get_edge_label_rmap(self):
        return [unicode(r[0]) 
                for r in self._cursor.execute("SELECT label FROM edge_labels ORDER BY id")]
    
    def _get_secedge_label_rmap(self):
        return [unicode(r[0]) 
                for r in self._cursor.execute("SELECT label FROM secedge_labels ORDER BY id")]
        
    def _get_domain_features(self, domain):
        return self._cursor.execute(
            "SELECT id, name FROM features WHERE domain = ? ORDER BY order_id",
            (domain.key,)).fetchall()
    
    def _get_feature_revmap(self, domain):
        l = []
        for row in self._get_domain_features(domain):
            values = []
            l.append((row[1], values))
            for r in self._cursor.execute(
                "SELECT value FROM feature_values WHERE feature_id = ? ORDER BY value_id", 
                (row[0],)):
                values.append(unicode(r[0]))
        return l
    
    def __iter__(self):
        """Returns an iterator that produces all graphs in this corpus, ordered by id."""
        c = self._db.cursor()
        for graph_id, graph_data in c.execute("SELECT id, data FROM graphs ORDER BY id"):
            yield self._deserializer.deserialize_graph(graph_id, graph_data)
    
    def __len__(self):
        """Returns the number of graphs in the corpus."""
        return self._info.corpus_size
    
    def get_index_node_id(self, xml_node_id):
        """Returns the index node id associated with the `xml_node_id` from the TIGER-XML file."""
        result = self._cursor.execute("SELECT id FROM node_data WHERE xml_node_id = ?", 
                                      (xml_node_id,)).fetchone()
        return IndexNodeId.from_int(result[0])

    def get_index_graph_id(self, xml_graph_id):
        """Returns the index id of the graph with the `xml_graph_id` from the TIGER-XML file."""
        result = self._cursor.execute("SELECT id FROM graphs WHERE xml_graph_id = ?", 
                                      (xml_graph_id,)).fetchone()
        return result[0]
        
    def get_xml_node_id(self, node_id):
        """Returns the XML id associated with `node_id` from the index."""
        result = self._cursor.execute("SELECT xml_node_id FROM node_data WHERE id = ?", 
                                      (node_id.to_int(),)).fetchone()
        return result[0]

    def get_xml_graph_id(self, graph_ordinal):
        """Returns the XML id of the graph with number `graph_ordinal`."""
        result = self._cursor.execute("SELECT xml_graph_id FROM graphs WHERE id = ?", 
                                      (graph_ordinal,)).fetchone()
        return result[0]
    
    def get_root_id(self, ordinal):
        assert 0 <= ordinal < len(self)
        result = self._cursor.execute("SELECT data FROM graphs WHERE id = ?", 
                                      (ordinal,)).fetchone()
        return self._deserializer.get_root_id(result[0])
        
    def get_graph(self, ordinal):
        """Returns the Tiger graph datastructure for the graph with number `ordinal`."""
        assert 0 <= ordinal < len(self)
        result = self._cursor.execute("SELECT id, data FROM graphs WHERE id = ?", 
                                      (ordinal,)).fetchone()
        return self._deserializer.deserialize_graph(result[0], result[1])
    
    def get_query_evaluator(self):
        """Returns the TigerSearch query evaluator for this corpus."""
        if self._evaluator is None:
            self._evaluator = TsqlQueryEvaluator(self._db, self._db_provider, self._info)
        return self._evaluator
        
    def close(self):
        """Closes the corpus.
        
        After a call to close, the corpus cannot be used any more.
        """
        self._db.close()
        self._db = None
        self._cursor = None
        self._evaluator = None
    
    def reopen(self):
        """Reopens the corpus.
        
        If the database connection was open before, it will be closed first.
        """
        if self._db:
            self.close()
        self._db = self._db_provider.connect()
        self._cursor = self._db.cursor()
        self._info = CorpusInfo(self._db)
    
