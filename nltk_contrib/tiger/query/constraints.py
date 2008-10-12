# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Contains the classes for constraint checking.

The code and the interfaces of this module are still subject to change. Please refer to the
inline comments for more information.
"""
from __future__ import with_statement

from nltk_contrib.tiger.query.exceptions import UndefinedNameError
from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.index import ID, EDGE_LABEL, CONTINUITY, LEFT_CORNER, RIGHT_CORNER, TOKEN_ORDER, GORN_ADDRESS
from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.utils.enum import Enum, enum_member
from nltk_contrib.tiger.utils.factory import FactoryBase

DEFAULT_TYPES = (NodeType.UNKNOWN, NodeType.UNKNOWN)

# WARNING: This module is still subject to heavy change!
# FIXME: while the code is correct (well, the tests run through), it's 
#        also quite convoluted. There should be an easier way to do this,
#        ideally one that allows to combine constraints over the same 
#        pair of nodes.

# This is also the reason why this code is not properly documented.
# the short story:
# A constraint must implement the class method setup_context, which will 
# be called exactly once for each corpus, and may only be used for setting
# data in the evaluator context, which will also be handed into the
# from_op method.

# The plan is to rewrite this that each constraint takes a node and a list of nodes
# and returns those nodes that fulfill the constraint. This way, constraints
# can take advantage of natural ordering in some cases


# For evaluation, the check method will be called. For speed reasons,
# the check methods should not contain any branches.

class Direction(Enum):
    LEFT_TO_RIGHT = enum_member()
    RIGHT_TO_LEFT = enum_member()
    NONE = enum_member()
    BOTH = enum_member()
    

class Constraint(object):
    __converters__ = {}

    
    @classmethod
    def setup_context(cls, context):
        pass

    @classmethod
    def from_op(cls, op_node, var_types, ctx):
        kwargs = {}
        for modifier_name in cls.__attributes__:
            conv = cls.__converters__.get(modifier_name, lambda *x: x[0])
            kwargs[modifier_name] = conv(op_node.modifiers[modifier_name], cls, ctx)
            kwargs["types"] = var_types
        return cls(**kwargs)
    
    def __init__(self, types, *args):
        self._types = types
        self._modifiers = args
        
    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        return self.__class__ is other.__class__ and \
               self._modifiers == other._modifiers
    
    def get_complement(self):
        assert self.__attributes__[-1] == "negated"
        args = list(self._modifiers)
        args[-1] = not args[-1]
        return self.__class__(self._types, *args)
    
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, ", ".join(str(x) for x in self._modifiers))

    def get_predicates(self, left, right):
        return [], []
    
    def get_node_variable_types(self):
        return NodeType.UNKNOWN, NodeType.UNKNOWN
    
    def get_singlematch_direction(self):
        return Direction.NONE


class PrecedenceConstraint(Constraint):
    __attributes__ = ("range", "negated")
    
    def __init__(self, types = DEFAULT_TYPES, range = (1, 1), negated = False):
        super(PrecedenceConstraint, self).__init__(types, range, negated)
        self._negated = not negated
        self._direction = Direction.NONE
        
        if range == (1, 1):
            if types == (NodeType.TERMINAL, NodeType.TERMINAL):
                self.check = self.check_immedidate_tt
                if self._negated:
                    self._direction = Direction.BOTH
            else:
                self.check = self.check_immediate

        elif range == (1, ):
            self.check = self.check_general
        else:
            self._min, self._max = range
            self.check = self.ranged_check

    def ranged_check(self, left_op, right_op, qc):
        l = left_op if left_op[CONTINUITY] == 0 else qc.get_node(left_op[LEFT_CORNER])
        r = right_op if right_op[CONTINUITY] == 0 else qc.get_node(right_op[LEFT_CORNER])
        return (self._min <= r[TOKEN_ORDER] - l[TOKEN_ORDER] <= self._max) is self._negated

    def check_general(self, left_op, right_op, qc):
        l = left_op if left_op[CONTINUITY] == 0 else qc.get_node(left_op[LEFT_CORNER])
        r = right_op if right_op[CONTINUITY] == 0 else qc.get_node(right_op[LEFT_CORNER])
        return (l[TOKEN_ORDER] < r[TOKEN_ORDER]) is self._negated
    
    def check_immediate(self, left_op, right_op, qc):
        l = left_op if left_op[CONTINUITY] == 0 else qc.get_node(left_op[LEFT_CORNER])
        r = right_op if right_op[CONTINUITY] == 0 else qc.get_node(right_op[LEFT_CORNER])
        return (l[TOKEN_ORDER] == r[TOKEN_ORDER] - 1) is self._negated
    
    def check_immedidate_tt(self, left_op, right_op, qc):
        return (left_op[TOKEN_ORDER] == right_op[TOKEN_ORDER] - 1) is self._negated

    def get_singlematch_direction(self):
        return self._direction
    

class SiblingConstraint(Constraint):
    __attributes__ = ("ordered", "negated")

    def __init__(self, types = DEFAULT_TYPES, ordered = False, negated = False):
        assert not (negated and ordered)
        super(SiblingConstraint, self).__init__(types, ordered, negated)
        if ordered:
            self.check = self.check_ordered
        elif negated:
            self.check = self.check_negated
        else:
            self.check = self.check_normal
    
    def check_negated(self, left_op, right_op, qc):
        return len(left_op[GORN_ADDRESS]) != len(right_op[GORN_ADDRESS]) \
               or left_op[GORN_ADDRESS][:-1] != right_op[GORN_ADDRESS][:-1]

    def check_normal(self, left_op, right_op, qc):
        return len(left_op[GORN_ADDRESS]) == len(right_op[GORN_ADDRESS]) \
               and left_op[GORN_ADDRESS][:-1] == right_op[GORN_ADDRESS][:-1]

    def check_ordered(self, left_op, right_op, qc):
        if len(left_op[GORN_ADDRESS]) == len(right_op[GORN_ADDRESS]) \
           and left_op[GORN_ADDRESS][:-1] == right_op[GORN_ADDRESS][:-1]:
            l = left_op if left_op[CONTINUITY] == 0 else qc.get_node(left_op[LEFT_CORNER])
            r = right_op if right_op[CONTINUITY] == 0 else qc.get_node(right_op[LEFT_CORNER])
            return l[TOKEN_ORDER] < r[TOKEN_ORDER]
        else:
            return False


def guarded(func, exc_type, new_exc_factory, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except exc_type, e:
        raise new_exc_factory(e)
    
from contextlib import contextmanager

@contextmanager
def convert_exception(exc_type, new_exc_type, args = lambda exc: exc.args):
    try:
        yield
    except exc_type, e:
        raise new_exc_type, args(e)
    
def _get_label_id(label, dct, domain):
    with convert_exception(KeyError, UndefinedNameError, lambda exc: (domain, exc.args[0])):
        return dct[label]

class DominanceConstraint(Constraint):
    class ChildrenTypePredicate(object):
        def get_query_fragment(self):
            return "node_data.token_order > 1"
    
        def __eq__(self, other):
            return self.__class__ is other.__class__

        def __ne__(self, other):
            return not self.__eq__(other)
    
        FOR_NODE = True
    
    class EdgeLabelPredicate(object):
        def __init__(self, label_id):
            self._label_id = label_id
        
        def get_query_fragment(self):
            return "edge_label = %i" % (self._label_id)
        
        def __eq__(self, other):
            return self.__class__ == other.__class__ and self._label_id == other._label_id
        
        def __ne__(self, other):
            return not self.__eq__(other)
        
        FOR_NODE = True

    __attributes__ = ("label", "range", "negated")
    __converters__ = {
        "label": lambda l, cls, ctx: _get_label_id(l, ctx.edge_label_map, 
                                                   UndefinedNameError.EDGELABEL)
    }

    
    @classmethod
    def setup_context(cls, context):
        context.edge_label_map = dict(context.db.execute("SELECT label, id FROM edge_labels"))
        context.edge_label_map[None] = None

    def __init__(self, types = DEFAULT_TYPES, label = None, range = (1, 1), negated = False):
        super(DominanceConstraint, self).__init__(types, label, range, negated)
        self._lbl = label
        self._negated = not negated
        self._direction = Direction.NONE
        if range == (1, 1):
            if self._negated:
                self._direction = Direction.RIGHT_TO_LEFT
            if self._lbl is None:
                self.check = self.check_immediate
            else:
                self.check = self.check_immediate_lbl
                
        elif range == (1, ):
            assert label is None
            if negated:
                self.check = self.check_general_ngt
            else:
                self.check = self.check_general
        else:
            assert label is None
            self._min, self._max = range
            self.check = self.ranged_check
        
    def ranged_check(self, left_op, right_op, qc):
        l = len(left_op[GORN_ADDRESS])
        r = len(right_op[GORN_ADDRESS])
        return (self._min <= r - l <= self._max and 
                buffer(right_op[GORN_ADDRESS][:l]) == left_op[GORN_ADDRESS]) is self._negated

    def check_general_ngt(self, left_op, right_op, qc):
        l = len(left_op[GORN_ADDRESS])
        r = len(right_op[GORN_ADDRESS])
        return not (r - l > 0 and buffer(right_op[GORN_ADDRESS][:l]) == left_op[GORN_ADDRESS])

    def check_general(self, left_op, right_op, qc):
        l = len(left_op[GORN_ADDRESS])
        r = len(right_op[GORN_ADDRESS])
        return (r - l > 0 and buffer(right_op[GORN_ADDRESS][:l]) == left_op[GORN_ADDRESS])

    def check_immediate(self, left_op, right_op, qc):
        l = len(left_op[GORN_ADDRESS])
        r = len(right_op[GORN_ADDRESS])
        return (r - l == 1 and buffer(right_op[GORN_ADDRESS][:l]) == left_op[GORN_ADDRESS]) \
               is self._negated

    def check_immediate_lbl(self, left_op, right_op, qc):
        l = len(left_op[GORN_ADDRESS])
        r = len(right_op[GORN_ADDRESS])
        return (r - l == 1 and buffer(right_op[GORN_ADDRESS][:l]) == left_op[GORN_ADDRESS] \
                and right_op[EDGE_LABEL] == self._lbl) is self._negated

    def get_predicates(self, left, right):
        l = []
        if right.var_type is NodeType.NONTERMINAL:
            l.append(self.ChildrenTypePredicate())
        return l, [self.EdgeLabelPredicate(self._lbl)] if self._lbl is not None else []
            
    def get_node_variable_types(self):
        return NodeType.NONTERMINAL, NodeType.UNKNOWN
    
    def get_singlematch_direction(self):
        return self._direction


class SecEdgeConstraint(Constraint):
    class SecEdgePredicate(object):
        # secedges.label_id is not indexed, therefore it is cheaper to load 
        # all secedges and then check for the correct labels later
        ORIGIN = 0
        TARGET = 1
        _ID_NAMES = ["origin_id", "target_id"]
        
        def __init__(self, node):
            self._node = node
            
        def get_query_fragment(self):
            return "(SELECT COUNT(*) FROM secedges WHERE secedges.%s = node_data.id) > 0" % (
                self._ID_NAMES[self._node], )
        
        def __eq__(self, other):
            return self.__class__ == other.__class__ and self._node == other._node
        
        def __ne__(self, other):
            return not self.__eq__(other)
        
        FOR_NODE = True
        
    __attributes__ = ("label", "negated")
    __converters__ = {
        "label": lambda l, cls, ctx: _get_label_id(l, ctx.secedge_label_map, 
                                                   UndefinedNameError.SECEDGELABEL)
    }
    
    @classmethod
    def setup_context(cls, ev_context):
        ev_context.secedge_label_map = \
                  dict(ev_context.db.execute("SELECT label, id FROM secedge_labels"))
        ev_context.secedge_label_map[None] = None

    def __init__(self, types = DEFAULT_TYPES, label = None, negated = False):
        super(SecEdgeConstraint, self).__init__(types, label, negated)
        self._lbl = label
        self._neg = negated

    def check(self, left_op, right_op, query_context):
        if self._lbl is not None:
            query_context.cursor.execute(
                """SELECT origin_id FROM secedges
                WHERE origin_id = ? AND target_id = ? AND label_id = ?""",
                (left_op[ID], right_op[ID], self._lbl))

        else:
            query_context.cursor.execute("""SELECT origin_id FROM secedges
            WHERE origin_id = ? AND target_id = ?""", (left_op[ID], right_op[ID]))
        return (query_context.cursor.fetchone() is None) is self._neg

    def get_predicates(self, left, right):
        return ([self.SecEdgePredicate(self.SecEdgePredicate.ORIGIN)],
                [self.SecEdgePredicate(self.SecEdgePredicate.TARGET)])


class CornerConstraint(Constraint):
    _IDX = {"l": LEFT_CORNER,
            "r": RIGHT_CORNER}

    __attributes__ = ("corner", "negated")
    __converters__ = {
        "corner": lambda c, cls, ctx: cls._IDX[c]
    }

    def __init__(self, types, corner, negated = False):
        super(CornerConstraint, self).__init__(types, corner, negated)
        if negated:
            self.check = lambda l, r, qc: l[corner] != r[ID] and not (r[ID] == l[ID] and \
                                                                      l[CONTINUITY] == 0)
        else:
            self.check = lambda l, r, qc: l[corner] == r[ID] or r[ID] == l[ID] and\
                l[CONTINUITY] == 0

    def get_node_variable_types(self):
        return NodeType.UNKNOWN, NodeType.TERMINAL


class ConstraintFactory(FactoryBase):
    __classes__ = {
        ast.SiblingOperator: SiblingConstraint,
        ast.PrecedenceOperator: PrecedenceConstraint,
        ast.CornerOperator: CornerConstraint,
        ast.SecEdgeOperator: SecEdgeConstraint,
        ast.DominanceOperator: DominanceConstraint
        }

    def _create_instance(self, cls, op_node, var_types, context):
        return cls.from_op(op_node, var_types, context)

    def _get_switch(self, op_node, var_types, context):
        return op_node.TYPE

