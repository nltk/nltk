# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module contains high-level classes for evaluating TigerSearch queries.
"""
from nltk_contrib.tiger.query.factory import QueryFactory
from nltk_contrib.tiger.query.nodesearcher import NodeSearcher
from nltk_contrib.tiger.query.querybuilder import QueryBuilder
from nltk_contrib.tiger.query.result import ResultBuilder, ParallelResultBuilder
from nltk_contrib.tiger.query.tsqlparser import TsqlParser
from nltk_contrib.tiger.utils.parallel import use_parallel_processing

__all__ = ["TsqlQueryEvaluator"]

class TsqlQueryEvaluator(object):
    """The main class for preparing and evaluating TigerSearch queries.
    
    A façade class that pulls together the parser and the query builder.
    """
    
    class Context(object):
        """The evaluator context.
        
        Each query evaluator has one context, which is used during query
        preparation.
        """

        def __init__(self, db, db_provider, corpus_info):
            self.db = db
            self.db_provider = db_provider
            self._nodesearcher = None
            self.allow_parallel = True
            self.corpus_info = corpus_info
        
        def _use_parallel(self):
            return self.db_provider.can_reconnect() and use_parallel_processing and self.allow_parallel
        
        def get_result_builder_class(self, has_constraints):
            return ParallelResultBuilder if self._use_parallel() and has_constraints \
                   else ResultBuilder

        @property
        def nodesearcher(self):
            if self._nodesearcher is None:
                self._nodesearcher = NodeSearcher(self.db)
            return self._nodesearcher
                
        
    def __init__(self, db, db_provider, corpus_info):
        self._context = TsqlQueryEvaluator.Context(db, db_provider, corpus_info)
        self._parser = TsqlParser()
        self._query_factory = QueryFactory(self._context)

    def new_builder(self):
        """Returns a new query builder.
        
        Query builders can be used to define a TIGERSearch query programmatically rather
        than having to create a query string.
        """
        return QueryBuilder(self._query_factory)
    
    def set_allow_parallel(self, value):
        """Allow or prohibit use of parallelized processing for the query evaluator."""
        self._context.allow_parallel = value
        
    def prepare_query(self, query_str):
        """Creates a query object from a TIGER query string."""
        return self._query_factory.from_ast(
            self._parser.parse_query(query_str))
    
    def evaluate(self, query_str):
        """Immediately evaluates a TIGER query query."""
        return self.prepare_query(query_str).evaluate()
