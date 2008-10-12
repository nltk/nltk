# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module contains the node predicates that are supported in the query language.

Predicates are simple node filters, i.e. they evaluate to true or false for a given 
node id. They are implented by returning little SQL snippets that are added to the
``WHERE`` clause of the query that is used to retrieve all node ids that match
a given node predicate.

Predicates:
 - ``root``: true if a given node is the root of a graph
 - ``discontinuous``: true if the fringe of a node's subgraph does not have wholes, i.e. all 
   it's terminal successors are adjacent
 - ``continuous``: the negation of ``discontinuous.
 - ``token_arity(n, [m]): if the number of terminal children is ``n``, or between ``n`` and ``m``
 - ``arity(n, [m]): if the number of children is ``n``, or between ``n`` and ``m``

"""
from nltk_contrib.tiger.utils.factory import FactoryBase

from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.query.node_variable import NodeType
from nltk_contrib.tiger.query.exceptions import PredicateTypeError, UndefinedNameError
from nltk_contrib.tiger import index

__all__ = ["PredicateFactory", "NodeTypePredicate"]


class Predicate(object):
    """Base class for node predicates.
    
    Signatures
    ==========
    The signature of a predicate is defined in the attribute `__signature__`, which
    must be an iterable of `(ast_type, mandatory_argument)` tuples.
    
    Mandatory arguments must precede optional ones. To ensure this, use the function `signature`.
    
    The first member of a signature must be an `ast.VariableReference`, and a signature
    may only contain one variable reference. Other arguments should be literal values. However, the
    TSQL grammar currently only supports integer values, but is easily changed to support more 
    argument types.
    
    The attribute `__ref_types__` contains the set of allowable container types for the variable.
    
    Names
    =====
    The attribute `__names__` must be an iterable of strings that defines the different names
    a predicate can be used under.
    
    Creation
    ========
    Predicates are created using the function `create_from_ast`, which will first check the 
    argument types and then invoke the constructor. Subclasses constructors must take
    all their arguments as positional parameters. The first argument in the constructor
    call will be the name that was used in the query, to distinguish between different
    versions of the same predicate.
    """
    __signature__ = None
    __ref_types__ = None
    __names__ = None
    
    def __init__(self, name, ref):
        pass
    
    @classmethod
    def check_signature(cls, name, invocation_args):
        """Checks the argument list of a predicate against the signature of the class."""
        for idx, formal_arg in enumerate(cls.__signature__):
            expected_ast_type, mandatory = formal_arg
            try: 
                if invocation_args[idx].TYPE is not expected_ast_type:
                    raise PredicateTypeError, (
                        "Type Error in argument %i of '%s': Expected %s, got %s" % \
                        (idx, name, invocation_args[idx].TYPE, expected_ast_type))
            except IndexError:
                if mandatory:
                    raise PredicateTypeError, "Missing arguments for '%s'." % (name, )
                else:
                    break
        else:
            if idx + 1 != len(invocation_args):
                raise PredicateTypeError, "Too many arguments for predicate '%s'." % (name, )
        variable = invocation_args[0].variable
        if variable.container not in cls.__ref_types__:
            raise PredicateTypeError("Predicate '%s' not valid for container type '%s'." % (
                name, variable.container))
        return variable
    
    @classmethod
    def create_from_ast(cls, predicate_node):
        """Creates a predicate class `cls` from a predicate AST node."""
        assert predicate_node.name in cls.__names__
        variable = cls.check_signature(predicate_node.name, list(predicate_node))
        return variable, cls(predicate_node.name, *list(predicate_node))

    
    def __eq__(self, other): # pragma: nocover
        raise NotImplementedError

    def __ne__(self, other):
        return not self.__eq__(other)


class SetPredicate(Predicate):
    """Base class for set predicates."""
    def check_node_set(self, node_set): # pragma: nocover
        """Evaluates the predicate for a given node set.
        
        Returns a boolean. 
        
        Must be overridden in clients.
        """
        raise NotImplementedError

    FOR_NODE = False
    

class NodeQueryPredicate(Predicate):
    """Base class for predicates that modify the node query."""
    def get_query_fragment(self): # pragma: nocover
        """Returns the query fragment that should be added to the SQL query for retrieving node ids.
        
        The return value must be a correct and valid term to be used in a ``WHERE`` clause of an 
        SQL query. All fiels from the ``nodedata`` table may be used.
        
        Must be overridden in clients.
        """
        raise NotImplementedError

    FOR_NODE = True


def signature(*args):
    """Creates a signature list for the `__signature__` attribute in the `Predicate` class.
    
    If the last argument is a list, the members of this list are taken as optional arguments
    of the predicate.
    
    Example:
    >>> s = signature(ast.VariableReference, [ast.StringLiteral])
    >>> s == [(ast.VariableReference, True), (ast.StringLiteral, False)]
    """
    if isinstance(args[-1], (list, tuple)):
        args, optional = args[:-1], args[-1]
    else:
        optional = []
    return [(t, True) for t in args] + [(t, False) for t in optional]


class RootPredicate(NodeQueryPredicate):
    """Checks if a given node is the root of the graph.

    :Predicates: root
    """
    __names__ = ["root"]
    __signature__ = signature(ast.VariableReference)
    __ref_types__ = ast.ContainerTypes.enum_set()
    
    def get_query_fragment(self):
        """Checks if a node is a root by testing if the gorn address has zero length."""
        return "LENGTH(node_data.gorn_address) = 0"

    def __eq__(self, other):
        return self.__class__ is other.__class__
    

class ContinuityPredicate(NodeQueryPredicate):
    """Checks if a given node is continuous or not.
    
    :Predicates: continuous, discontinuous
    """
    __names__ = ["continuous", "discontinuous"]
    __signature__ = signature(ast.VariableReference)
    __ref_types__ = ast.ContainerTypes.enum_set()

    def __init__(self, name, ref):
        super(ContinuityPredicate, self).__init__(name, ref)
        self._continuity_type = (
            index.DISCONTINUOUS if name == "discontinuous" else index.CONTINUOUS)
        
    def get_query_fragment(self):
        """Checks (dis)continuity in the ``nodedata`` table."""
        return "node_data.continuity = %i" % (self._continuity_type,)
    
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._continuity_type == other._continuity_type


class XArityPredicate(NodeQueryPredicate):
    """Checks different arity predicates.
    
    :Predicates: arity, tokenarity
    """
    __names__ = ["arity", "tokenarity"]
    __signature__ = signature(ast.VariableReference, ast.IntegerLiteral, [ast.IntegerLiteral])
    __ref_types__ = ast.ContainerTypes.enum_set()
    
    def __init__(self, name, ref, lower, upper = None):
        super(XArityPredicate, self).__init__(self, ref)
        assert name in self.__names__
        self._field = name
        self._upper = upper.value if upper is not None else None
        self._lower = lower.value
        
    def get_query_fragment(self):
        """Checks token or child arity in the ``nodedata`` table."""
        if self._upper is None:
            return "node_data.%s = %i" % (self._field, self._lower)
        else:
            return "node_data.%s >= %i and node_data.%s <= %i" % \
                   (self._field, self._lower, self._field, self._upper)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._field == other._field and \
               self._lower == other._lower and self._upper == other._upper

    
class SetEmptyPredicate(SetPredicate):
    """Checks node sets for emptiness.
    
    :Predicates: empty, nonempty
    """
    __names__ = ["empty", "nonempty"]
    __signature__ = signature(ast.VariableReference)
    __ref_types__ = ast.ContainerTypes.Set.elem_set()
    
    def __init__(self, name, ref):
        super(self.__class__, self).__init__(name, ref)
        self._name = name
        self._has_elems = name == "nonempty"
    
    def check_node_set(self, node_set):
        """Checks if `node_set` matches the required emptiness state."""
        return bool(node_set) == self._has_elems

    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._name == other._name


# Special predicates
class NodeTypePredicate(NodeQueryPredicate):
    """A special non-user-constructible property for adding inferred node types."""
    def __init__(self, var_type):
        super(self.__class__, self).__init__(None, None)
        assert var_type is not NodeType.UNKNOWN
        self._var_type = var_type

    def get_query_fragment(self):
        """Adds a constraint on the node type."""
        if self._var_type is NodeType.TERMINAL:
            return "node_data.continuity = 0"
        else:
            return "node_data.continuity > 0"
    
    def __eq__(self, other):
        return self.__class__ is other.__class__ and self._var_type is other._var_type


class PredicateFactory(FactoryBase):
    """The factory class for predicates."""
    __classes__ = [RootPredicate, ContinuityPredicate, XArityPredicate, SetEmptyPredicate]
    
    def _get_class_switch(self, cls):
        """Uses the `__names__` as the list of type switches for `cls`."""
        return cls.__names__
    
    def _get_switch(self, pred_ast):
        """Returns the name of the predicate as the type switch."""
        return pred_ast.name
    
    def raise_error(self, pred_name):
        """Raises an `UndefinedNameError` for unknown predicates."""
        raise UndefinedNameError, (UndefinedNameError.PREDICATE, pred_name)
    
    def _create_instance(self, cls, pred_ast):
        """Creates a new predicate using the class factory method."""
        return cls.create_from_ast(pred_ast)
