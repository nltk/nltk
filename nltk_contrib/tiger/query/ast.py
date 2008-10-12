# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""This module defines all nodes in the abstract syntax trees (ASTs) of TIGERSearch queries.

AST node types
==============

AST node types can be checked using the attribute `TYPE`, i. e.

>>> n.TYPE is ast.Conjunction

In the current implementation, `n.TYPE` is a shorthand for `n.__class__`. However,
clients must not rely on the `TYPE` attribute being any particular object. The only
operations that can be done with this property is equality and identity checking.


Attributes
==========

The attributes of AST nodes are defined in the `__slot__` variable of the class
and set via introspection by the base class constructor. Please see the documentation
of the individual nodes for the semantics of the attributes.


Equality
========

Since all attributes are known, AST trees support equality checks, i.e.

>>> n == Conjunction([StringLiteral("a"), StringLiteral("b")])

works intuitively. Note however, that partial matching is not supported, i.e. both
trees need to be completely specified.


`__repr__`
=========
`__repr__` is implemented in such a way that the whole tree will be printed out
(not pretty-printed!). The usual contract

>>> query_ast == eval(repr(query_ast))

holds.


Iteration
=========

If a node is not a leaf node (i.e. when the method `is_leaf` returns `True`,
it supports two forms of iteration:

 * Standard iteration via `__iter__`
    All attributes of the node that are also nodes will be produced
 * Iteration with `named_iter`
    Along with the child nodes, the names of the child nodes will be returned.
    No assumptions may be made on the types of the names, they can only be used
    to replace an existing child node via `set_child`.
"""
from operator import attrgetter
from itertools import izip
from nltk_contrib.tiger.utils.enum import Enum, enum_member

# TODO: figure out how to support slots in class hierarchies. Currently, 
# the slot "children" from _Composite needs to be duplicated in Predicate.

class VariableTypes(Enum):
    """This enumeration defines all types of variables that can be defined
    in TIGERSearch queries.

    See the documentation of `nltk_contrib.tiger.query.tsqlparser` which parts of the
    grammar use which variable types.
    """
    FeatureValue = enum_member()
    FeatureDescription = enum_member()
    NodeIdentifier = enum_member()

    
class ContainerTypes(Enum):
    Single = enum_member()
    Set = enum_member()
    

# abstract node base classes
class _Node(object):
    """The abstract base class of all AST nodes.

    All *magic* features, like equality checks, `__repr__`, automatic
    setting of attributes, iteration and child replacemnt are implemented
    in this class.

    This class cannot be instantiated.

    *Attributes*: none
    """
    __slots__ = ()

    TYPE = property(lambda self: self.__class__)

    def __new__(cls, *args, **kwargs):
        if cls._is_abstract(cls.__name__):
            raise TypeError, "cannot instantiate abstract class '%s'." % (cls, )
        else:
            return object.__new__(cls)

    def __init__(self, *args):
        assert len(args) == len(self.__slots__), \
               (self.__class__.__name__, args, self.__slots__)
        for name, value in izip(self.__slots__, args):
            setattr(self, name, value)

    @staticmethod
    def _is_abstract(classname):
        """Returns `True` if a class is understood to be an abstract class.

        The names of abstract classes start with an underscore (``_``).
        """
        return classname.startswith("_")

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        if isinstance(other, _Node) and self.TYPE == other.TYPE:
            for name in self.__slots__:
                if getattr(self, name) != getattr(other, name):
                    return False
            return True
        else:
            return False

    def __repr__(self):
        return u"%s(%s)" % (self.__class__.__name__,
                            ",".join(repr(getattr(self, v)) for v in self.__slots__))

    def __iter__(self):
        for v in self.__slots__:
            obj = getattr(self, v)
            if isinstance(obj, _Node):
                yield obj

    def named_iter(self):
        """Returns a tuple `(name_tag, child_node)` for all child nodes."""
        for v in self.__slots__:
            obj = getattr(self, v)
            if isinstance(obj, _Node):
                yield v, obj

    @staticmethod
    def is_leaf():
        """Returns `True` if the node is a leaf node, `False` otherwise."""
        return False

    def set_child(self, name_tag, new_child):
        """Replaces a child node with another AST node `new_child`.

        Children are specified using `name_tag` returned by `named_iter`.

        `new_child` must be a subclass of `_Node`.
        """
        if self.is_leaf():
            raise TypeError, "cannot set children on leaf nodes"
        else:
            assert isinstance(getattr(self, name_tag), _Node)
            assert isinstance(new_child, _Node)
            setattr(self, name_tag, new_child)


class _LeafNode(_Node):
    """The base class for all leaf nodes."""

    @staticmethod
    def is_leaf():
        """Returns `True` if the node is a leaf node, `False` otherwise."""
        return True


class _CompositeNode(_Node):
    """The base class of all composite nodes, i.e. nodes with a possibly
    unbounded number of other children, using for grouping (logic operations etc).

    *Attributes*:
      - `children`: the child nodes
    """
    __slots__ = ("children", )

    def __init__(self, *args):
        assert len(args[-1]) > -1
        _Node.__init__(self, *args)

    def __iter__(self):
        return iter(self.children)

    def named_iter(self):
        """Returns a tuple `(name_tag, child_node)` for all child nodes."""
        return enumerate(self.children)

    def set_child(self, name, new_child):
        """Replaces a child node with another AST node `new_child`.

        Children are specified using `name_tag` returned by `named_iter`.

        `new_child` must be a subclass of `_Node`.
        """
        assert isinstance(new_child, _Node)
        self.children[name] = new_child

    def apply_associativity(self):
        """Applies the law of associativity to the composite node.

        After this operation, all the children of child nodes with the same
        type as this node will be inlined.

        Example:

        >>> n = Conjunction([StringLiteral("a"),
        ...                  Conjunction([StringLiteral("b"), StringLiteral("c")])])
        >>> n.apply_associativity()
        >>> n == Conjunction([StringLiteral("a"), StringLiteral("b"), StringLiteral("c")
        """
        nc = []
        for c in self.children:
            if self.TYPE is c.TYPE:
                nc.extend(c.children)
            else:
                nc.append(c)
        self.children = nc


class _NodeRelationOperator(_Node):
    """The base class for all node relation operators.

    *Attributes*:
      - `left_operand`: the node (in the TIGERSearch meaning) operand on the left side
      - `right_operand`: the node on the right right of the operator
      - `modifiers`: the operator modifiers, as specified by the grammar and the classes.
      
    *Special class attributes*:
      - `modifiers`: a dictionary of all modifiers with their default values
      - `converters`: a dictionary that contains converter functions for all modifiers
                      these converter functions are used in the `create` method. For the 
                      modifier `negated`, no converter has to be defined.
    """
    __slots__ = ("left_operand", "right_operand", "modifiers")
    __modifiers__ = {}

    def __init__(self, left_operand, right_operand, **kwargs):
        modifiers = self.__modifiers__.copy()
        modifiers.update(kwargs)

        _Node.__init__(self, left_operand, right_operand, modifiers)

    def __repr__(self):
        return u"%s(%s, %s, **%s)" % (self.__class__.__name__,
                                      self.left_operand, self.right_operand, self.modifiers)
    
    @classmethod
    def create(cls, parse_result):
        """Creates an operator AST node from a parse result."""
        cls.__converters__["negated"] = lambda o: o.negated != ""
        modifiers = dict(
            (name, cls.__converters__[name](parse_result.operator))
            for name in cls.__modifiers__)
            
        return cls(parse_result.leftOperand, parse_result.rightOperand, **modifiers)
        
    @staticmethod
    def _get_label(operator):
        """Returns the label modifier from an operator parse result, or `None` if not defined."""
        return None if len(operator.label) == 0 else operator.label

    @staticmethod
    def _get_range(operator):
        """Returns the range modifier from an operator parse result."""
        if operator.indirect == "*":
            return (1, )
        elif operator.mindist != "":
            return (int(operator.mindist), int(operator.maxdist or operator.mindist))
        else: 
            return (1, 1)


## Actual node classes

class Conjunction(_CompositeNode):
    """A class that represents a conjunction of terms.

    *Attributes*: see `_CompositeNode`
    """
    def __invert__(self):
        return Disjunction([Negation(c) for c in self])


class Disjunction(_CompositeNode):
    """A class that represents a disjunction of terms.

    *Attributes*: see `_CompositeNode`
    """
    def __invert__(self):
        return Conjunction([Negation(c) for c in self])


class PrecedenceOperator(_NodeRelationOperator):
    """A class that represents the precedence operator ``.``.

    *Attributes*: see `_NodeRelationOperator`
    :Modifiers:
     - `range`: a tuple, `(minimum, maximum)` reach of the precedence constraint
     - `negated`: if `True`, the constraint is negated
    """

    __modifiers__ = {
        "range" : (1, 1),
        "negated" : False }
    
    __converters__ = {
        "range": _NodeRelationOperator._get_range,
    }
    

class DominanceOperator(_NodeRelationOperator):
    """A class that represents the dominance operator ``>``.

    Note that corner dominance is handled by a separate operator.

    *Attributes*: see `_NodeRelationOperator`
    :Modifiers:
     - `range`: a tuple, `(minimum, maximum)` reach of the dominance constraint.
     - `label`: the label string for labeled dominance, or `None`
     - `negated`: if `True`, the constraint is negated
    """
    __modifiers__ = {
        "range" : (1, 1),
        "label" : None,
        "negated" : False }
    __converters__ = {
        "range": _NodeRelationOperator._get_range,
        "label": _NodeRelationOperator._get_label
    }
    

class CornerOperator(_NodeRelationOperator):
    """A class that represents the corner dominance operator ``>@``.

    *Attributes*: see `_NodeRelationOperator`
    :Modifiers:
     - `corner`: ``"r"`` or ``"l"``, depending on the specified corner
     - `negated`: if `True`, the constraint is negated
    """
    __modifiers__ = {
        "corner" : "",
        "negated": False }
    
    __converters__ = {
        "corner": attrgetter("corner")
    }
    

class SecEdgeOperator(_NodeRelationOperator):
    """A class that represents the secondary edge dominance operator ``>~``.

    *Attributes*: see `_NodeRelationOperator`
    :Modifiers:
     - `label`: the label string for labeled secondary edge dominance, or `None`
     - `negated`: if `True`, the constraint is negated
    """
    __modifiers__ = {
        "label" : None,
        "negated" : False }
    
    __converters__ = {
        "label": _NodeRelationOperator._get_label
    }


class SiblingOperator(_NodeRelationOperator):
    """A class that represents the sibling operator operator ``$``.

    *Attributes*: see `_NodeRelationOperator`
    :Modifiers:
     - `ordered`: if `True`, the left operand should precede the right one
     - `negated`: if `True`, the constraint is negated
    """
    __modifiers__ = {
        "negated" : False,
        "ordered" : False }

    __converters__ = {
        "ordered": lambda o: o.ordered != "",
    }


class Negation(_Node):
    """A class that represents the negation of a term.

    *Attributes*:
     - 'expression': the negated expression
    """
    __slots__ = ("expression", )


    def __invert__(self):
        return self.expression


class NodeDescription(_Node):
    """A class that represents a node description.

    Please see the grammar for the child nodes that can be contained
    in a node description.

    *Attributes*:
     - `expression`: the node description expression, a boolean expression
                     of feature constraints
    """
    __slots__ = ("expression", )


class VariableDefinition(_Node):
    """A class that represents a variable definition.

    *Attributes*:
     - `variable`: the variable, a `Variable` node
     - `expression`: the referent of the variable, a node description, feature value or constraint
    """
    __slots__ = ("variable", "expression")

    
class TsqlExpression(_Node):
    """The toplevel root node for TIGERSearch queries.

    *Attributes*:
     - `expression`: the query, either a single term or a conjunction of terms
    """
    __slots__ = ("expression", )

    
class Predicate(_CompositeNode):
    """A class that represents a node predicate.

    Currently, the only argument types allowed by the grammer are nodes or
    integer literals. This may change in the future.

    The function `apply_associativity` doesn't do anything useful for this node,
    because predicates cannot be nested.
    
    *Attributes*:
     - `name`: the name of the predicate
     - `children`: the list of arguments, a list of AST nodes
    """
    __slots__ = ("name", "children")


class FeatureConstraint(_Node):
    """A class that represents a featur constraint.

    *Attributes*:
     - `feature`: the feature name
     - `expression`: a boolean expression for the feature value
    """
    __slots__ = ("feature", "expression")


class StringLiteral(_LeafNode):
    """A class that represents a string literal.

    *Attributes*:
     - `string`: the string literal
    """
    __slots__ = ("string", )


class RegexLiteral(_LeafNode):
    """A class that represents a regex literal.

    *Attributes*:
     - `regex`: the regular expression
    """
    __slots__ = ("regex", )


class IntegerLiteral(_LeafNode):
    """A class that represents an integer literal.

    *Attributes*:
     - `value`: the integer value
    """
    __slots__ = ("value", )


class FeatureRecord(_LeafNode):
    """A class that represents a feature record.

    *Attributes*:
     - `type`: a member of `nltk_contrib.tiger.graph.NodeType`
    """
    __slots__ = ("type",)

    def __invert__(self):
        return FeatureRecord(~self.type)


class Variable(_LeafNode):
    """A class that represents a variable.

    *Attributes*:
     - `name`: the variable name
     - `type`: the variable type, an enum value of `VariableTypes`
     - `container`: the container type, an enum value of `ContainerTypes`
    """
    __slots__ = ("name", "type", "container")


class VariableReference(_LeafNode):
    """A class that represents a variable reference.

    *Attributes*:
     - `variable`: the actual variable
    """
    __slots__ = ("variable",)


class Nop(_LeafNode):
    """A node that represents an empty tree."""
