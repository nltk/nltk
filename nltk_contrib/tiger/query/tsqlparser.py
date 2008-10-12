# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Defines the grammar and parser class for the TigerSearch query language.

For a complete description, see the `TigerSearch Manual`_.

The grammar will create an abstract syntax tree from a TigerSearch query.

Please see the unit test and the `nltk_contrib.tiger.query.ast` module for 
the nodes and the structure of the ASTs.

If applicable, all fragments contain information about their respective AST node type, 
some example strings and the named results introduced by the fragment in question. This 
is not the full list of named results returned by the fragment, which can be obtained 
by examining which fragments are used in the expression builder in question.

The grammar does not check semantic correctness of the query, e.g. : 
 * valid predicate names
 * correct parameter types for predicates, as long as they are a node operand or 
   an integer literal.
 * type-correctness for variable references
 * conflicts in feature constraints (e.g. ``[cat="NP"&"NN"]``)
 * conflicts in relations (e.g. ``#a > #b & #b > #a``)
 * nonsensical distance modifiers (e.g. ``#a >5,1 #b``)
 
All these checks are done by the query builder and evaluator functions. 

The only normalization done in the parser is that ``cat!="NE"``
is turned into ``cat=!"NE"``.

.. _`TigerSearch Manual` : http://tinyurl.com/2jm24u
"""
import pyparsing

from nltk_contrib.tiger.graph import NodeType
from nltk_contrib.tiger.query import ast
from nltk_contrib.tiger.query.exceptions import TigerSyntaxError
__all__ = ["TsqlParser"]

# enable memoizing support in parser (speeds up parsing)
pyparsing.ParserElement.enablePackrat()

# convenience functions

NUMBER = pyparsing.Word(pyparsing.nums)
WORD = pyparsing.Word(pyparsing.alphas)

def single_value_holder(cls, conv = lambda n: n):
    """Creates a parse action that invokes `cls` with the first parse result.
    
    `conv` can be used to convert the parse result before invoking `cls`.
    """
    return lambda s, l, t: cls(conv(t[0]))


def suppressed_literal(s):
    """Creates a suppressed literal string `s`."""
    return pyparsing.Literal(s).suppress()


def boolean_expr(atom):
    """Creates a boolean expression grammar out of an expression `atom`.
    
    A boolean expression can contain the following operators, ordered by binding power:
     * negation: ``!term``
     * conjunction: ``term & term``
     * disjunction: ``term | term``
     
    and can have parentheses for grouping. 
    """
    ops = [
        (suppressed_literal(u"!"), 1, pyparsing.opAssoc.RIGHT,
         lambda s, l, t: ast.Negation(t[0][0])),

        (suppressed_literal(u"&"), 2, pyparsing.opAssoc.LEFT,
         lambda s, l, t: ast.Conjunction(t.asList()[0])),

        (suppressed_literal(u"|"), 2, pyparsing.opAssoc.LEFT,
         lambda s, l, t: ast.Disjunction(t.asList()[0]))]
    return pyparsing.operatorPrecedence(atom, ops)


def surround(left, expr, right):
    """Circumfixes the expression `expr` with `left` and `right`.
    
    Both `left` and `right` will be turned into suppressed literals.
    
    *Parameters*:
     `left`
        the left part of the circumfix
     `expr`
        the grammar expression to be circumfixed
     `right`
       the right part of the circumfix
    """
    return suppressed_literal(left) + expr + suppressed_literal(right)



def integer_literal():
    """Defines an expression for an integer literals.
    
    :AST Node: `IntegerLiteral`
    :Example: ``12345``
    """
    return NUMBER.setParseAction(single_value_holder(ast.IntegerLiteral, int))


def string_literal():
    """Defines an expression for string literals.
    
    A string literal can be enclosed in single (') or double (") quotes and can contain
    escaped characters using "\\".

    :AST Node: `StringLiteral`
    :Example: ``"word"``
    """
    string = (pyparsing.QuotedString("'", escChar = "\\") | 
              pyparsing.QuotedString('"', escChar = "\\"))
    return string.setParseAction(single_value_holder(ast.StringLiteral))  


def regex_literal():
    """"Defines an expression for regular expression literals.
    
    :AST Node: `RegexLiteral`
    :Example: ``/a+b+/``
    """
    regex = pyparsing.QuotedString("/")
    return regex.setParseAction(single_value_holder(ast.RegexLiteral))


def variable_name(type_prefixes):
    """Defines a reusable expression for all variable names.

    A variable name can only contain ASCII alphanumeric characters and the 
    underscore character, and must start with one of the characters listed in 
    in the dictionary `type_prefixes` (by default only "#"). The value in 
    `type_prefixes` determines the container type of the variable.
    
    :Named Results:
     - `varname`: the variable name
    """
    assert all(len(pfx) == 1 for pfx in type_prefixes), "prefix list may only contain characters"
    
    v_expr = pyparsing.Combine(pyparsing.oneOf(type_prefixes.keys()) + 
                               pyparsing.Word(pyparsing.alphanums + "_")).setResultsName("varname")
    v_expr.type_map = type_prefixes
    return v_expr


def variable_reference(variable_expr, variable_type):
    """Defines an expression for variable references of type `variable_type`.
    
    See `nltk_contrib.tiger.query.ast.VariableTypes` for the list of variable types.
    
    :AST Node: `VariableReference`
    :Example: ``#a``
    """
    return variable_expr.setParseAction(
        lambda s, l, t: ast.VariableReference(ast.Variable(
            t.varname, variable_type, variable_expr.type_map[t.varname[0]])))


def variable_definition(variable_expr, variable_type, right_hand):
    """Defines an expression for variable definitions of type `variable_type`.
    
    The referent expression is `right_hand`, and `variable_expr` contains the expression
    for variable names.
    
    :AST Node: `Variable`
    :Example: ``#a:...``
    :Named Results:
     - `expr`: the right-hand side of the definition
    """
    definition = (variable_expr + suppressed_literal(u":") + 
                  right_hand.setResultsName("expr"))
    return definition.setParseAction(
        lambda s, l, t: ast.VariableDefinition(
            ast.Variable(t.varname, variable_type, variable_expr.type_map[t.varname[0]]), t.expr))


def feature_value():
    """Defines an expression for the right hand side in feature constraints.
    
    A feature constraint can be a boolean expression of string and regex literals.
    
    :Example: ``"NE"``, ``"NE"|"NN"``, ``/h.*/ & !"haus"``
    """
    return boolean_expr(string_literal() | regex_literal())

FEATURE_VALUE = feature_value()

VAR_PREFIXES = {"#": ast.ContainerTypes.Single}

def feature_record():
    """Defines an expression for feature records.
    
    Valid feature records:
     * ``T``: all terminals
     * ``NT``: all nonterminals
     
    :AST Node: `FeatureRecord:
    :Example: ``T``, ``NT``
    """
    return pyparsing.oneOf("T NT").setParseAction(
        single_value_holder(ast.FeatureRecord, lambda v: NodeType.fromkey(v[0])))


def feature_constraint():
    """Defines a boolean expression for feature constraint.
    
    A feature constraint is a feature name, a match operator and a 
    feature value expression.
    
    Match operators:
     * ``=`?` (equality)
     * ``!=`` (inequality)
    
    If the match operator is `!=`, the feature value expression will be wrapped inside
    a `Negation` AST node.
    
    :AST Node: `FeatureConstraint`
    :Example: ``cat="NP"``, ``pos!=/N+/``, ``word="safe" & pos="NN"``
    """
    op = pyparsing.oneOf(u"= !=")
    v = FEATURE_VALUE
    
    constraint = (WORD + op + v)
    constraint.setParseAction(lambda s, l, t: ast.FeatureConstraint(t[0], t[2]) if t[1] == "=" 
                                              else ast.FeatureConstraint(t[0], ast.Negation(t[2])))
    return boolean_expr(constraint | feature_record())

FEATURE_CONSTRAINT = feature_constraint()


def node_description(): 
    """Defines an expression for node descriptions.
    
    Node descriptions can either be a boolean expression of  list of constraints, a 
    feature constraint variable definition or reference or a feature record.
    
    :AST Node: `NodeDescription`
    :Example: ``[pos="PREP" & word=("vor"|"vorm")]``, ``[T]``, ``[#a:(word = "safe")]``, ``[#b]``
    """
    node_desc = surround(u"[", FEATURE_CONSTRAINT, u"]")
    return node_desc.setParseAction(single_value_holder(ast.NodeDescription))

NODE_DESCRIPTION = node_description()

NODE_VAR_PREFIXES = {"#": ast.ContainerTypes.Single,
                     "%": ast.ContainerTypes.Set }


def node_variable_def():
    """Defines an expression for node variable definitions. 
    
    Node variables have the type `VariableTypes.NodeIdentifier`

    :AST Node: `VariableReference`
    :Example: ``#n1:[pos = "PREP" & word = ("vor", "vorm")]``
    """
    return variable_definition(variable_name(NODE_VAR_PREFIXES), 
                               ast.VariableTypes.NodeIdentifier, NODE_DESCRIPTION)


def node_variable_ref():
    """Defines an expression for node variable references. 
    
    Node variables have the type `VariableTypes.NodeIdentifier`
    
    :AST Node: `VariableReference`
    :Example: ``#n1``
    """
    return variable_reference(variable_name(NODE_VAR_PREFIXES), ast.VariableTypes.NodeIdentifier)


def node_operand():
    """Defines an expression for node operands in predicate functions or constraints.
    
    An operand can be a node variable definition, reference or a node description itself.
    """
    return (node_variable_def() | node_variable_ref() | NODE_DESCRIPTION)

NODE_OPERAND = node_operand()


class ConstraintModifiers(object):
    """A class that contains all possible constraint modifiers.
    
    Each modifier `MOD` is stored as a named result `res`.
    
    Modifiers:
     `NEGATION` : `negated`
       the ! symbol before a constraint operator
     `TRANSITIVE` : `indirect`
       the * symbol after an operator
     `DISTANCE` : `mindist` and `maxdist`
       a single or a pair of integers after an operator
     `EDGE_LABEL` : `label`
       a string after a dominance operator
    """
    NEGATION = pyparsing.Optional(pyparsing.Literal("!")).setResultsName("negated")
    TRANSITIVE = pyparsing.Literal("*").setResultsName("indirect")
    DISTANCE = (NUMBER("mindist") + pyparsing.Optional(suppressed_literal(",") + NUMBER("maxdist")))
    EDGE_LABEL = WORD("label")

    
def operator_symbol(s, ast_node_class):
    """Defines an operator symbol `s`.
    
    :Named Results:
     - `op_class`: the AST class of the operator
    """
    return pyparsing.Literal(s).setResultsName("op_class")\
                               .setParseAction(lambda s, l, t: ast_node_class)


def dominance_operator():
    """Defines an expression for dominance operators.

    All variantes of the dominance operator can be negated.
    
    :AST Node: `DominanceOperator`
    :Example: ``>``, ``>*``, ``>L``, ``>n``, ``>n,m``
    """
    return (ConstraintModifiers.NEGATION +
            operator_symbol(">", ast.DominanceOperator) +
            pyparsing.Optional(ConstraintModifiers.EDGE_LABEL | 
                               ConstraintModifiers.TRANSITIVE |
                               ConstraintModifiers.DISTANCE))


def corner_operator():
    """Defines an expression for left- and rightmost terminal successors (corners).

    All variants of the corner dominance operator can be negated.
    
    :AST Node: `CornerDominance`
    :Example: ``>@l``, ``>@r``
    :Named Results:
     - `corner`: the corner, either ``l`` or ``r``
    """
    return (ConstraintModifiers.NEGATION + 
            operator_symbol(">@", ast.CornerOperator) +
            pyparsing.oneOf("l r").setResultsName("corner"))


def precedence_operator():
    """Defines an expression for precendence operators.
    
    All variants can be negated.
    
    :AST Node: `PrecedenceOperator`
    :Example: ``.``, ``.*``, ``.n``, ``.n,m``
    """
    return (ConstraintModifiers.NEGATION +
            operator_symbol(".", ast.PrecedenceOperator) + 
            pyparsing.Optional(ConstraintModifiers.TRANSITIVE | 
                               ConstraintModifiers.DISTANCE))


def sec_edge_operator():
    """Defines an expression for secondary edge dominance operators.
    
    All variants can be negated.
    
    :AST Node: `SecEdgeOperator`
    :Example: ``>~``, ``>~L``
    """
    return (ConstraintModifiers.NEGATION + 
            operator_symbol(">~", ast.SecEdgeOperator) + 
            pyparsing.Optional(ConstraintModifiers.EDGE_LABEL))


def sibling_operator():
    """Defines an expression for sibling operators.
    
    The ``$.*`` operator for siblings with precendence cannot be negated.
    
    :AST Node: `SiblingOperator`
    :Example: ``$.*``, ``$``
    """
    return ((operator_symbol("$", ast.SiblingOperator) + 
             pyparsing.Optional(pyparsing.Literal(".*").setResultsName("ordered"))) | 
            (ConstraintModifiers.NEGATION + operator_symbol("$", ast.SiblingOperator)))


def node_relation_constraint():
    """Defines an expression for node relation constraints.
    
    Please see the documentation of the operator AST nodes.
    
    :Example: ``[cat="NP"] > #a``
    :Named Results:
     - `leftOperand`: the node operand on the left side
     - `operator` the operator symbol, without modifiers
     - `rightOperand` the node operand on the right side
    """
    constraint_op = pyparsing.Group(sec_edge_operator() | corner_operator() | dominance_operator() |
                                    precedence_operator() | sibling_operator())
    
    constraint = (NODE_OPERAND.setResultsName("leftOperand") + 
                  constraint_op.setResultsName("operator") +
                  NODE_OPERAND.setResultsName("rightOperand"))
    return constraint.setParseAction(lambda s, l, t: t.operator.op_class.create(t))


def node_predicate():
    """Defines an expression for node predicates.
    
    A node predicate is a function name and a parenthesized list of node operands or 
    integer literals. The list of supported predicates is not part of the parser.
    
    :AST Node: `Predicate`
    :Example: ``root(#a)``, ``arity([cat="NP", 5)``
    :Named Results:
     - `pred`: the name of the predicate
     - `args`: the list of arguments, either node operands or integer literals
    """
    arg = (NODE_OPERAND | integer_literal()).setResultsName("args", listAllMatches = True)
    identifier = WORD("pred")
    
    return (identifier + surround(u"(", pyparsing.delimitedList(arg), u")")
            ).setParseAction(lambda s, l, t: ast.Predicate(t.pred, t.args.asList()))
    

# the complete query language
def tsql_grammar():
    """Defines the expression for the complete TigerSearch query language.
    
    A query term is either a node operand, a node relation constraint or node predicate. An
    expression can be a single term or a conjunction of terms.
    
    Toplevel disjunctions are not currently not supported, toplevel disjunction is not supported,
    because it can always be represented by negations in the relations and node descriptions.
    
    The returned expression must match the whole input string.
    
    :AST Node: `TsqlExpression`
    :Example: ``#a:[cat="NP"] & root(#a) and #a > [word="safe"]``
    """
    atom = (node_predicate() | node_relation_constraint() | NODE_OPERAND)
    
    expr = pyparsing.Group(atom + pyparsing.OneOrMore(suppressed_literal(u"&") + atom)
                           ).setParseAction(lambda s, l, t: ast.Conjunction(t.asList()[0])) | atom
    
    expr.setParseAction(single_value_holder(ast.TsqlExpression))
    return expr + pyparsing.StringEnd()


class TsqlParser(object):
    """A simple façade for the PyParsing TSQL grammar."""
    def __init__(self):
        self._g = tsql_grammar()
    
    def parse_query(self, query_string):
        """Parses a query string and returns the AST.
        
        If the string cannot be parsed, a `TigerSyntaxError` will be raised.
        """
        try:
            return self._g.parseString(query_string)[0]
        except pyparsing.ParseException, e:
            raise TigerSyntaxError, e
