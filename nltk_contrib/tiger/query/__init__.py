# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module holds all classes that are used to evaluate TIGERSearch queries.


*Modules*:
 * `ast`: the classes that make up the ASTs (abstract syntax trees) of a query
 * `ast_utils`: various helper methods and classes for query ASTs
 * `ast_visitor`: visitor-style base class for query ASTs
 * `constraints`: implementations of all TIGERSearch operators 
 * `evaluator`: façade class that can be used to create and evaluate queries
 * `exceptions`: exceptions classes
 * `factory`: factory classes for result builders
 * `nodesearcher`: class for loading nodes from the index based on TIGERSearch node descriptions
 * `node_variable`: classes for handling typed node variables in queries
 * `predicates`: implementations of all node and node set predicates
 * `querybuilder`: a class for simple programmatic creation of TIGERSearch queries.
 * `result`: classes for building result sets for queries and constraint checkers
 * `tsqlparser`: a PyParsing parser for the TIGERSearch query language
"""
from nltk_contrib.tiger.query.exceptions import *
from nltk_contrib.tiger.query.evaluator import TsqlQueryEvaluator
