# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""A simple, non-validating parser for TIGER-XML corpora.

The `TigerParser` simply reads out metadata information and creates instances of
`nltk_contrib.tiger.graph.TigerGraph` from the sentences contained in the corpus.

No checks for completeness or soundness of the graph specification are made, so the
parser should be able to handle problematic corpora as well. 
"""
from functools import partial

from nltk_contrib.tiger.utils.etree_xml import IterParseHandler, element_handler
from nltk_contrib.tiger.graph import NonterminalNode, TerminalNode, TigerGraph, NodeType

__all__ = ("parse_tiger_corpus", "TigerParser")

class TigerParser(IterParseHandler):
    """A parser for TIGER-XML corpora.
    
    Corpora are parsed using the `parse` method and fed into an indexer.
    
    Indexers will receive the following data:
    
     Corpus metadata: `set_metadata(d)`
      - `d`: a dictionary of `(key, value)` metadata entries
       
     Edge labels: `set_edge_labels(d)`:
      - `d`: a dictionary with `(edge_label, description)` entries. The descriptions may be `None`, 
        if not given in the corpus
     
     Secondary edge labels: `set_secedge_labels(d)`
      - `d`: a dictionary with `(secedge_label, description)` entries. The descriptions may 
        be `None`, if not given in the corpus
    
     Features: `add_feature(name, domain, d)`
      - `name`: the name of the feature
      - `domain`: the domain, a member of `nltk_contrib.tiger.graph.NodeType`
      - `d`: a dictionary with `(value, description)` entries. The descriptions may 
        be `None`, if not given in the corpus

     Graphs: `add_graph(g)`
      - `g`: an instance of `nltk_contrib.tiger.graph.Graph`
      
    Indexers may make the following assumptions:
     - `set_metadata` will be invoked before everything else.
     - after the first call to `add_graph`, only other `add_graph` calls will be made.
     
    These assumptions might not hold true in case of erroneous TIGER-XML files. No
    schema checks are currently done, mostly due to the fact that incremental parsing
    with the ElementTree API does not support this.
    """
    def __init__(self):
        super(TigerParser, self).__init__()
        self._indexer = None
        
    @element_handler("meta")
    def handle_meta(self, elem):
        """Reads out corpus metadata information and feeds it to the indexer."""
        self._indexer.set_metadata(
            dict((child.tag, child.text.strip()) for child in elem))

    @element_handler("feature")
    def handle_feature(self, elem):
        """Feeds feature information (values, descriptions) to the indexer."""
        self._handle_annotation(elem, 
                                partial(self._indexer.add_feature, elem.get("name"), 
                                        NodeType.fromkey(elem.get("domain")[0])))
    
    @element_handler("edgelabel")
    def handle_edgelabels(self, elem):
        """Feeds all edge labels (label strings, descriptions) to the indexer."""
        self._handle_annotation(elem, self._indexer.set_edge_labels)
        
    @element_handler("secedgelabel")
    def handle_secedgelabels(self, elem):
        """Feeds all secondary edge labels (label strings, descriptions) to the indexer."""
        self._handle_annotation(elem, self._indexer.set_secedge_labels)
    
    @classmethod
    def _handle_annotation(cls, elem, report_function):
        """Generic method to send {value: description} dictionaries to the indexer."""
        report_function(dict((value.get("name"), value.text.strip() if value.text else None)
                             for value in elem))

    @element_handler("s")
    def handle_sentence(self, sentence):
        """Creates a `TigerGraph` for a sentence specification and feeds it to the indexer."""
        graph = TigerGraph(sentence.get("id"))
        
        graph_elem = sentence.find("graph")
        
        self._read_nodes(graph_elem.getiterator("t"), graph.nodes, TerminalNode, 
                         self._postproc_terminal)
        self._read_nodes(graph_elem.getiterator("nt"), graph.nodes, NonterminalNode, 
                         self._postproc_nonterminal)
        
        graph.root_id = graph_elem.get("root")

        self._indexer.add_graph(graph)
        return self.DELETE_BRANCH

    def _postproc_terminal(self, node, node_elem):
        node.order = int(node_elem.get("id").split("_")[-1]) - 1
    
    def _postproc_nonterminal(self, node, node_elem):
        node.edges = [
            (edge.get("label"), edge.get("idref"))
            for edge in node_elem.getiterator("edge")]
        
    @classmethod
    def _read_nodes(cls, node_elems, graph, node_cls, pproc):
        """Reads all elements from `node_elems` and adds them to the graph.
        
        Tiger nodes will be created using `node_cls`, and store feature values, secondary edges,
        edges (nonterminals only) and token order (terminals only) in the node objects.
        """
        for node_elem in node_elems:
            node = node_cls(node_elem.get("id"))
            for feature_name, value in node_elem.attrib.iteritems():
                if feature_name == "id":
                    continue
                node.features[feature_name] = value
                
            graph[node.id] = node
            pproc(node, node_elem)

            secedges = [
                (edge.get("label"), edge.get("idref"))
                for edge in node_elem.getiterator("secedge")]
            
            if secedges:
                node.secedges = secedges
                
    def parse(self, path, indexer):
        """Parses the TIGER-XML corpus in `path` and sends all data to `indexer`."""
        self._indexer = indexer
        self._parse(path)

            
def parse_tiger_corpus(filename, indexer):
    """Parses the TIGER-XML corpus in `filename` and sends it to `indexer`."""
    t = TigerParser()
    t.parse(filename, indexer)
