# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Query module exceptions

This module contains all exceptions that are thrown by the query evaluation engine.

All queries are subclasses of `TigerQueryError`, any other exception not caught by the 
evaluator methods are a bug.
"""

__all__ = ["TigerSyntaxError", "TigerQueryError", "ConflictError",
           "TigerTypeError", "PredicateTypeError", "MissingFeatureError"]

class TigerQueryError(Exception):
    """The base class of all TIGER query errors."""
    pass


class TigerSyntaxError(TigerQueryError):
    """An exception for query language syntax errors.
    
    Parameters:
     * `parse_exc`: the causing exception, a `pyparsing.ParseException`
    
    Attributes:
     * `cause`: the causing exception
    """
    def __init__(self, parse_exc):
        TigerQueryError.__init__(self)
        self.cause = parse_exc

    def __str__(self):
        return str(self.cause)
    

class UndefinedNameError(TigerQueryError):
    """An exception thrown on usage of an undefined name in a query.
    
    Parameters:
     * `name_domain`: the domain of the undefined name (see below)
     * `name`: the actual name
     
    Name domains:
     * features
     * predicates
     * edge labels
     * secondary edge labels
    """
    MSG = "Undefined %s '%s'."
    FEATURE = "feature"
    PREDICATE = "predicate"
    EDGELABEL = "edge label"
    SECEDGELABEL = "secondary edge label"

    def __init__(self, name_domain, name):
        TigerQueryError.__init__(
            self,
            self.MSG % (name_domain, name))
        
        
class ConflictError(TigerQueryError):
    """An exception for conflicting feature constraints.
    
    Parameters:
     * `variable_name`: the name of the variable where the conflict occurred
     
    Example: ``[cat="(NP & PP)"]``
    """
    pass


class TigerTypeError(TigerQueryError):
    """An exception for wrong types in node variables.
    
    Parameters:
     * `variable_name`: the name of the variable where the error occurred
     
    Example: ``[T & NT]``
    """
    def __init__(self, variable_name):
        TigerQueryError.__init__(
            self,
            "Conflicting type for node variable '%s'." % (variable_name, ))
        self.varname = variable_name


class PredicateTypeError(TigerQueryError):
    """An exception for type errors in predicate definitions.
    
    Example: ``arity(#a)``
    """
    pass


class MissingFeatureError(TigerQueryError):
    """An exception for signaling missing features.
    
    Exceptions of this type are feature requests.
    """
    pass
