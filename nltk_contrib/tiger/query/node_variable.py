# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Classes for handling node variables."""
from operator import attrgetter

from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.query.exceptions import TigerTypeError

__all__ = ["NodeVariable"]


class NodeVariable(str):
    """A node variable used in a TIGER query.
    
    
    *Properties*
     * `name`: the name of the variable (read-only)
     * `is_set`: `True` if the variable is a set,`False` otherwise (read-only)
     * `var_type`: the type of the variable, a member of nltk_contrib.tiger.graph.NodeType
                   `UNKNOWN` by default.
     """
    @classmethod
    def from_node(cls, variable):
        """Creates a new node variable from an AST node `variable`"""
        return cls(variable.name, variable.container is ast.ContainerTypes.Set)
    
    def __new__(cls, name, *args):
        return str.__new__(cls, name)
    
    def __init__(self, name, is_set, var_type = NodeType.UNKNOWN):
        super(self.__class__, self).__init__()
        self._name = name
        self._is_set = is_set
        self.var_type = var_type
        
    def __reduce__(self):
        return (NodeVariable, (self._name, self._is_set, self.var_type))
    
    def __repr__(self):
        return "nv(%s)" % (self._name, )

    def refine_type(self, new_type):
        """Tries to further specify the type of a node variable.
        
        If `new_type` is `NodeType.UNKNOWN` or the same as the current type of 
        the node variable, nothing is changed. If the type of the variable
        of `NodeType.UNKNOWN`, the variable is updated. Otherwise,
        a `TigerTypeError` is raised.
        """
        if new_type is NodeType.UNKNOWN or new_type is self.var_type:
            return
        elif self.var_type is NodeType.UNKNOWN:
            self.var_type = new_type
        else:
            raise TigerTypeError, self._name
            
    name = property(attrgetter("_name"), doc = "The name of the variable")
    is_set = property(attrgetter("_is_set"), 
                      doc = "`True` if the variable is a set, `False` otherwise.")
