# Natural Language Toolkit: Context Free Grammars
# + Lambda Semantics Interpreter by Ben Packer
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.token import *
from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
from nltk.cfg import *

#################################################################
# AugNonterminal
#################################################################

class AugNonterminal(Nonterminal):
    """
    An augmented non-terminal symbol for a context free grammar.
    C{Nonterminal} is a wrapper class for node values; it is used by
    C{CFGProduction}s to distinguish node values from leaf values.
    The node value that is wrapped by a C{Nonterminal} is known as its
    X{symbol}.  Symbols are typically strings representing phrasal
    categories (such as C{"NP"} or C{"VP"}).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two C{Nonterminal}s are considered equal if their
    symbols are equal.

    @see: L{CFG}
    @see: L{CFGProduction}
    @type _symbol: (any)
    @ivar _symbol: The node value corresponding to this
        C{Nonterminal}.  This value must be immutable and hashable. 
    """
    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        @type symbol: (any)
        @param symbol: The node value corresponding to this
            C{Nonterminal}.  This value must be immutable and
            hashable. 
        """
        self._symbol = symbol
        self._attrs = []
        self._triples = []

    def symbol(self):
        """
        @return: The node value corresponding to this C{Nonterminal}. 
        @rtype: (any)
        """
        return self._symbol

    def attrs(self):
        return self._attrs

    def add_attribute(self, attribute):
        self._attrs.append(attribute)

    def lambda_triples(self):
        return self._triples

    def add_triples(self, triples):
        assert(isinstance(triples, list))
        self._triples = triples

    def clone(self):
        return AugNonterminal(self._symbol)

    def __eq__(self, other):
        """
        @return: True if this non-terminal is equal to C{other}.  In
            particular, return true iff C{other} is a C{Nonterminal}
            and this non-terminal's symbol is equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and
                self._symbol == other._symbol)

    def __ne__(self, other):
        """
        @return: True if this non-terminal is not equal to C{other}.  In
            particular, return true iff C{other} is not a C{Nonterminal}
            or this non-terminal's symbol is not equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        return not (self==other)

    def __cmp__(self, other):
        if self == other: return 0
        else: return -1

    def __hash__(self):
        return hash(self._symbol)

    def __repr__(self):
        """
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{<M{s}>}.
        @rtype: C{string}
        """
        str = '<%s' % (self._symbol,)
        if len(self._attrs) > 0:
            str += ' ('
            for attr in self._attrs:
                str += '"%s", ' % attr
            str = str[0:len(str)-2]
            str += ')'
        if len(self._triples) > 0:
            str += ' ('
            for triple in self._triples:
                str += repr(triple) + ', '
            str = str[0:len(str)-2]
            str += ')'
        str += '>'
        return str

    def __str__(self):
        """
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{M{s}}.
        @rtype: C{string}
        """
        return '%s' % (self._symbol,)

    def __div__(self, rhs):
        """
        @return: A new nonterminal whose symbol is C{M{A}/M{B}}, where
            C{M{A}} is the symbol for this nonterminal, and C{M{B}}
            is the symbol for rhs.
        @rtype: L{Nonterminal}
        @param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        @type rhs: L{Nonterminal}
        """
        assert _chktype(1, rhs, Nonterminal)
        return Nonterminal('%s/%s' % (self._symbol, rhs._symbol))

class Lambda:
    def __init__(self, l_type, lamb):
        assert((l_type == 'A') | (l_type == 'B'))
        assert(isinstance(lamb, (str, type(lambda: None), tuple)))
        self._type = l_type
        if isinstance(lamb, (str, type(lambda: None))):
            self._triple = (lamb, None, [])
        elif len(lamb) == 2:
            self._triple = (lamb[0], lamb[1], [])
        else:
            self._triple = lamb
    def type(self):
        return self._type
    def triple(self):
        return self._triple
    def __repr__(self):
        rstr = '<' + self._type + ': '
        if isinstance(self._triple[0], str):
            rstr += str(self._triple[0]) + ', '
        else:
            rstr += '<lambda>, '
        rstr += str(self._triple[1]) + ', '
        rstr += '['
        for sto in self._triple[2]:
            rstr += '<lambda>, '
        if len(self._triple[2]) > 0:
            rstr = rstr[0:len(rstr)-2]
        rstr += ']>'
        return rstr

def augnonterminals(symbols):
    """
    Given a string containing a list of symbol names, return a list of
    C{Nonterminals} constructed from those symbols.  

    @param symbols: The symbol name string.  This string can be
        delimited by either spaces or commas.
    @type symbols: C{string}
    @return: A list of C{Nonterminals} constructed from the symbol
        names given in C{symbols}.  The C{Nonterminals} are sorted
        in the same order as the symbols names.
    @rtype: C{list} of L{Nonterminal}
    """
    if ',' in symbols: symbol_list = symbols.split(',')
    else: symbol_list = symbols.split()
    return [AugNonterminal(s.strip()) for s in symbol_list]

#################################################################
# ACFGProduction and CFG
#################################################################

from nltk.parser import *
from nltk.chktype import chktype as _chktype

class ACFGProduction(CFGProduction):
    """
    An augmented context-free grammar production.  Each production
    expands a single C{Nonterminal} (the X{left-hand side}) to a
    sequence of terminals and C{Nonterminals} (the X{right-hand
    side}).  X{terminals} can be any immutable hashable object that is
    not a C{Nonterminal}.  Typically, terminals are strings
    representing word types, such as C{"dog"} or C{"under"}.

    Abstractly, a CFG production indicates that the right-hand side is
    a possible X{instantiation} of the left-hand side.  CFG
    productions are X{context-free}, in the sense that this
    instantiation should not depend on the context of the left-hand
    side or of the right-hand side.

    @see: L{CFG}
    @see: L{Nonterminal}
    @type _lhs: L{Nonterminal}
    @ivar _lhs: The left-hand side of the production.
    @type _rhs: C{tuple} of (C{Nonterminal} and (terminal))
    @ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, rhs, anns=(), transrules=()):
        """
        Construct a new C{ACFGProduction}.

        @param lhs: The left-hand side of the new C{CFGProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{CFGProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        @param anns: A list of annotation Rules.
        @type anns: list of C{Rule}
        @param transrules: A list of translation Rules.
        @type transrules: list of C{Rule}
        """
        assert _chktype(1, lhs, Nonterminal)
        self._lhs = lhs
        self._rhs = rhs
        self._anns = anns;
        self._transrules = transrules;

    def add_annotation(self, ann):
        self._anns.append(ann)

    def add_translation(self, trans):
        self._transrules.append(trans)

    def lhs(self):
        """
        @return: the left-hand side of this C{CFGProduction}.
        @rtype: L{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{CFGProduction}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def anns(self):
        """
        @return: the annotations of this C{CFGProduction}.
        @rtype: list of C{Rule}
        """
        return self._anns

    def transrules(self):
        """
        @return: the translation rules of this C{CFGProduction}.
        @rtype: list of C{Rule}
        """
        return self._transrules

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{CFGProduction}.
        @rtype: C{string}
        """
        if isinstance(self._lhs, Nonterminal):
            str = '%s ->' % (self._lhs.symbol(),)
        else:
            str = '%r ->' % (self._lhs,)
        for elt in self._rhs:
            if isinstance(elt, Nonterminal):
                str += ' %s' % (elt.symbol(),)
            else:
                str += ' %r' % (elt,)
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the
            C{Production}. 
        @rtype: C{string}
        """
        return '[Production: %s]' % self

    def __eq__(self, other):
        """
        @return: true if this C{CFGProduction} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)

    def __ne__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        if not _classeq(self, other): return -1
        return cmp((self._lhs, self._rhs), (other._lhs, other._rhs))

    def __hash__(self):
        """
        @return: A hash value for the C{CFGProduction}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

class Rule:
    """
    A rule that an ACFGProduction carries for adding properties to
    AugNonterminals in the ACFGProduction
    """
    def __init__(self, action, premise=None):
        """
        Construct a new C{Rule}.

        @param action: The action to perform on the production's nonterminals.
        @type action: L{AnnotationBoolean} or L{Translation}
        @param premise: The premise that must be fulfilled to perform
        the action.
        @type premise: L{AnnotationBoolean} or None
        """
        assert(isinstance(action, AnnotationBoolean) | isinstance(action, Translation))
        if premise != None:
            assert(isinstance(premise, AnnotationBoolean))
        self._action = action
        self._premise = premise
    def action(self):
        return self._action
    def premise(self):
        return self._premise

class AnnotationBoolean:
    """
    A boolean expression concerning C{Annotation}s of C{AugNonterminal}s.
    C{AnnotationBoolean}s may be evaluated for their truth or executed to
    enforce their C{Annotation}s.
    """
    def __init__(self, op, anns):
        """
        Construct a new C{AnnotationBoolean}.

        @param op: The boolean operator.
        @type op: 'none', 'not', 'or', or 'and'
        @param anns: A tuple of the C{Annotation}s.
        @type anns: C{tuple} of L{Annotation}
        """
        assert((op == 'none') | (op == 'not') | (op == 'or') | (op == 'and'))
        assert(isinstance(anns, tuple))
        self._op = op
        self._anns = anns
    def op(self):
        return self._op
    def anns(self):
        return self._anns
    
class Annotation:
    """
    An annotation for a C{AugNonterminal}.
    """
    def __init__(self, attr, nonterm, n=1):
        assert(isinstance(attr, str))
        assert(isinstance(nonterm, str))
        assert(isinstance(n, int))
        self._attr = attr
        self._nonterm = nonterm
        self._n = n
    def attr(self):
        return self._attr
    def nonterm(self):
        return self._nonterm
    def n(self):
        return self._n

class Translation:
    """
    A translation of a C{AugNonterminal}.
    """
    def __init__(self, action, object, subject=None, n1=1, n2=1):
        assert((action == 'app') | (action == 'pull_s') | (action == 'pull_v') | (action == 'none'))
        assert(isinstance(object, (str, Lambda, Translation)))
        assert((isinstance(subject, (str, Translation))) | (subject == None))
        self._action = action
        self._object = object
        self._subject = subject
        self._n1 = n1
        self._n2 = n2
    def action(self):
        return self._action
    def object(self):
        return self._object
    def subject(self):
        return self._subject
    def n1(self):
        return self._n1
    def n2(self):
        return self._n2

class CFG:
    """
    A context-free grammar.  A CFG consists of a start state and a set
    of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.

    @see: L{CFGProduction}
    @see: L{Nonterminal}
    @see: L{nltk.parser}
    """
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{CFGProduction}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{CFGProduction}
        """
        assert _chktype(1, start, Nonterminal)
        assert _chktype(2, productions, (CFGProduction,), [CFGProduction])
        self._start = start
        self._productions = tuple(productions)

    def productions(self):
        return self._productions

    def start(self):
        return self._start

    def __repr__(self):
        return '<CFG with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'CFG with %d productions' % len(self._productions)
        str += ' (start state = %s)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        return str

#################################################################
# PCFGs and PCFG productions
#################################################################

from nltk.probability import ProbabilisticMixIn
class PCFGProduction(CFGProduction, ProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    C{PCFGProduction}s are essentially just C{CFGProduction}s that
    have probabilities associated with them.  These probabilities are
    used to record how likely it is that a given production will
    be used.  In particular, the probability of a C{PCFGProduction}
    records the likelihood that its right-hand side is the correct
    instantiation for any given occurance of its left-hand side.

    @see: L{CFGProduction}
    """
    def __init__(self, prob, lhs, *rhs):
        """
        Construct a new C{PCFGProduction}.

        @param prob: The probability of the new C{PCFGProduction}.
        @param lhs: The left-hand side of the new C{PCFGProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{PCFGProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        ProbabilisticMixIn.__init__(self, prob)
        CFGProduction.__init__(self, lhs, *rhs)

    def __str__(self):
        return CFGProduction.__str__(self) + ' (p=%s)' % self._prob

    def __eq__(self, other):
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self._prob == other._prob)

    def __hash__(self):
        return hash((self._lhs, self._rhs, self._prob))

class PCFG(CFG):
    """
    A probabilistic context-free grammar.  A PCFG consists of a start
    state and a set of productions.  The set of terminals and
    nonterminals is implicitly specified by the productions.

    PCFG productions should be C{PCFGProduction}s.  C{PCFG} imposes
    the constraint that the set of productions with any given
    left-hand-side must have probabilities that sum to 1.

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    @type EPSILON: C{float}
    @cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """
    EPSILON = 0.01
    
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{CFGProduction}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{PCFGProduction}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            PCFG.EPSILON of 1.
        """
        assert _chktype(1, start, Nonterminal)
        assert _chktype(2, productions, (PCFGProduction,), [PCFGProduction])
        CFG.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-PCFG.EPSILON) < p < (1+PCFG.EPSILON)):
                raise ValueError("CFGProductions for %r do not sum to 1" % lhs)

##//////////////////////////////////////////////////////
##  Recursive Descent Parser
##//////////////////////////////////////////////////////
class AugRecursiveDescentParser(ParserI):
    """
    A simple top-down CFG parser that parses texts by recursively
    expanding the fringe of a C{TreeToken}, and matching it against a
    text.

    C{RecursiveDescentParser} uses a list of tree locations called a
    X{frontier} to remember which subtrees have not yet been expanded
    and which leaves have not yet been matched against the text.  Each
    tree location consists of a list of child indices specifying the
    path from the root of the tree to a subtree or a leaf; see the
    reference documentation for C{TreeToken} for more information
    about tree locations.

    When the parser begins parsing a text, it constructs a tree
    containing only the start symbol, and a frontier containing the
    location of the tree's root node.  It then extends the tree to
    cover the text, using the following recursive procedure:

      - If the frontier is empty, and the text is covered by the tree,
        then return the tree as a possible parse.
      - If the frontier is empty, and the text is not covered by the
        tree, then return no parses.
      - If the first element of the frontier is a subtree, then
        use CFG productions to X{expand} it.  For each applicable
        production, add the expanded subtree's children to the
        frontier, and recursively find all parses that can be
        generated by the new tree and frontier.
      - If the first element of the frontier is a token, then X{match}
        it against the next token from the text.  Remove the token
        from the frontier, and recursively find all parses that can be
        generated by the new tree and frontier.

    @see: C{nltk.cfg}
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{RecursiveDescentParser}, that uses C{grammar}
        to parse texts.

        @type grammar: C{CFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        assert _chktype(1, grammar, CFG)
        assert _chktype(2, trace, types.IntType)
        self._grammar = grammar
        self._trace = trace

    def grammar(self):
        """
        @return: The grammar used to parse texts.
        @rtype: C{CFG}
        """
        return self._grammar

    def _find_production(self, productions, tree):
        children = tree.children()
        for production in productions:
            if production.lhs().symbol() == tree.node().symbol():
                rhs = production.rhs()
                i = 0
                confirmed = True
                for child in children:
                    if i > len(rhs)-1:
                        confirmed = False
                        break
                    elif (isinstance(rhs[i], Nonterminal) & isinstance(child, TreeToken)):
                        if rhs[i].symbol() == child.node().symbol():
                            i += 1
                            continue
                        else:
                            confirmed = False
                            break
                    elif (isinstance(rhs[i], str) & isinstance(child, Token)):
                        if rhs[i] == child.type():
                            i += 1
                            continue
                        else:
                            confirmed = False
                            break
                    else:
                        confirmed = False
                        break
                if confirmed == True:
                    return production
        return None
    
    def _do_properties(self, tree, cfg, r_type):
        assert(isinstance(tree, TreeToken))
        assert((r_type == 'ann') | (r_type == 'trans'))
        productions = cfg.productions()
        children = tree.children()
        production = self._find_production(productions, tree)
        if r_type == 'ann':
            rules = production.anns()
        elif r_type == 'trans':
            rules = production.transrules()
        for child in children:
            if isinstance(child, TreeToken):
                self._do_properties(child, cfg, r_type)
        if rules != ():
            i = 1
            for rule in rules:
                if self._do_annotation_boolean(rule.premise(), tree, 'eval'):
                    if r_type == 'ann':
                        self._do_annotation_boolean(rule.action(), tree, 'exec')
                    if r_type == 'trans':
                        results = self._perform_calculus(rule.action(), tree)
                        tree.node().add_triples(results)
                        break;
                i += 1

    def annotate(self, parses, cfg):
        for tree in parses:
            self._do_properties(tree, cfg, 'ann')

    def translate(self, parses, cfg):
        for tree in parses:
            self._do_properties(tree, cfg, 'trans')

    def _do_ann(self, ann, nodelist, type):
        assert(isinstance(ann, Annotation))
        count = 1
        attr = ann.attr()
        nonterm = ann.nonterm()
        n = ann.n()
        node = self._get_node(nonterm, nodelist, n)
        if type == 'eval':
            return node.attrs().count(attr) != 0
        elif type == 'exec':
            if node.attrs().count(attr) == 0:
                node.add_attribute(attr)
            return True
        return False

    def _get_node(self, symbol, nodelist, n=1):
        count = 1
        for node in nodelist:
            if node.symbol() == symbol:
                if count == n:
                    return node
                else:
                    count += 1
        return None

    def _get_nodelist(self, tree):
        assert(isinstance(tree, TreeToken))
        children = tree.children()
        nodelist = [tree.node()]
        for child in children:
            if isinstance(child, TreeToken):
                nodelist.append(child.node())
        return nodelist

    def _do_annotation_boolean(self, bool, tree, type):
        assert((bool == None) | (isinstance(bool, AnnotationBoolean)))
        assert(isinstance(tree, TreeToken))
        assert((type == 'eval') | (type == 'exec'))
        if bool == None:
            return True
        op = bool.op()
        anns = bool.anns()
        nodelist = self._get_nodelist(tree)
        if (op == 'none') | (op == 'not'):
            ann = anns[0]
            if op == 'none':
                return self._do_ann(ann, nodelist, type)
            elif type == 'eval':
                return not(self._do_ann(ann, nodelist, type))
        if op == 'and':
            for ann in anns:
                if isinstance(ann, Annotation):
                    if not(self._do_ann(ann, nodelist, type)):
                        return False
                elif isinstance(ann, AnnotationBoolean):
                    if not(self._do_annotation_boolean(ann, tree, type)):
                        return False
            return True
        if op == 'or':
            for ann in anns:
                if isinstance(ann, Annotation):
                    if self._do_ann(ann, nodelist, type):
                        return True
                elif isinstance(ann, AnnotationBoolean):
                    if self._do_annotation_boolean(ann, tree, type):
                        return True
            return False
        return False                

    def _triples_apply(self, objects, subjects, nodelist):
        assert(isinstance(objects, list))
        assert(isinstance(subjects, list))
        results = []
        for object in objects:
            for subject in subjects:
                assert(isinstance(object, Lambda))
                assert(isinstance(subject, Lambda))
                triple1 = object.triple()
                triple2 = subject.triple()
                if object.type() == 'A':
                    head = triple1[0](triple2[0])
                    if triple1[1] == None:
                        var = triple2[1]
                    else:
                        var = triple1[1]
                    sto = []
                    sto.extend(triple1[2])
                    sto.extend(triple2[2])
                if object.type() == 'B':
                    head = triple1[1]
                    var = triple2[1]
                    sto = [triple1[0](triple2[0])]
                    if len(triple1[2]) > 0:
                        sto.extend(triple1[2])
                    if len(triple2[2]) > 0:
                        sto.extend(triple2[2])
                results.append(Lambda('A',(head, var, sto)))
        return results

    def _triples_pull(self, objects, action):
        assert(isinstance(objects, list))
        assert(isinstance(action, str))
        results = []
        for object in objects:
            assert(isinstance(object, Lambda))
            assert((action == 'pull_s') | (action == 'pull_v'))
            triple = object.triple()
            if len(triple[2]) == 2:
                if action == 'pull_s':
                    head1 = triple[2][0](triple[0])
                    head2 = triple[2][1](triple[0])
                elif action == 'pull_v':
                    head1 = lambda x: triple[2][0](triple[0](x))
                    head2 = lambda x: triple[2][1](triple[0](x))
                var1 = triple[1]
                var2 = triple[1]
                sto1 = [triple[2][1]]
                sto2 = [triple[2][0]]
                results.extend(self._triples_pull([Lambda('A',(head1, var1, sto1))],
                                                  action))
                results.extend(self._triples_pull([Lambda('A',(head2, var2, sto2))],
                                                  action))
            if len(triple[2]) == 1:
                if action == 'pull_s':
                    head = triple[2][0](triple[0])
                elif action == 'pull_v':
                    head = lambda x: triple[2][0](triple[0](x))
                var = triple[1]
                sto = []
                results.append(Lambda('A',(head, var, sto)))
        return results

    def _get_trans(self, symbol, nodelist, n):
        assert(isinstance(symbol, str))
        assert(isinstance(nodelist, list))
        return self._get_node(symbol, nodelist, n).lambda_triples()

    def _perform_calculus(self, trans, tree):
        assert(isinstance(trans, Translation))
        assert(isinstance(tree, TreeToken))
        action = trans.action()
        object = trans.object()
        subject = trans.subject()
        n1 = trans.n1()
        n2 = trans.n2()
        nodelist = self._get_nodelist(tree)
        results = None
        if action == 'none':
            if isinstance(object, str):
                results = self._get_trans(object, nodelist, n1)
            elif isinstance(object, Lambda):
                results = [object]
        if action == 'app':
            if isinstance(object, Translation):
                objs_lambda = self._perform_calculus(object, tree)
            else:
                objs_lambda = self._get_trans(object, nodelist, n1)
            if isinstance(subject, Translation):
                subjs_lambda = self._perform_calculus(subject, tree)
            else:
                subjs_lambda = self._get_trans(subject, nodelist, n2)
            results = self._triples_apply(objs_lambda, subjs_lambda, nodelist)
        if (action == 'pull_s') | (action == 'pull_v'):
            if isinstance(object, Translation):
                objs_lambda = self._perform_calculus(object, tree)
            else:
                objs_lambda = self._get_trans(object, nodelist, n1)
            objs_lambda.extend(self._triples_pull(objs_lambda, action))
            results = objs_lambda
        return results

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.
        
        @param grammar: The new grammar.
        @type grammar: C{CFG}
        """
        assert _chktype(1, grammar, CFG)
        self._grammar = grammar

    def parse(self, text):
        # Inherit docs from ParserI; and delegate to parse_n
        assert _chktype(1, text, [Token], (Token))
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

    def parse_n(self, text, n=None):
        # Inherit docs from ParserI
        assert _chktype(1, text, [Token], (Token))
        assert _chktype(2, n, types.IntType, types.NoneType)

        # Start a recursive descent parse, with an initial tree
        # containing just the start symbol.
        initial_treetok = TreeToken(self._grammar.start().clone())
        frontier = [()]
        if self._trace:
            self._trace_start(initial_treetok, frontier, text)
        parses = self._parse(text, initial_treetok, frontier)

        # Return the requested number of parses.
        if n is None: return parses
        else: return parses[:n]

    def _parse(self, remaining_text, treetok, frontier):
        """
        Recursively expand and match each elements of C{treetok}
        specified by C{frontier}, to cover C{remaining_text}.  Return
        a list of all parses found.

        @return: A list of all parses that can be generated by
            matching and expanding the elements of C{treetok}
            specified by C{frontier}.
        @rtype: C{list} of C{TreeToken}
        @type treetok: C{TreeToken}
        @param treetok: A partial structure for the text that is
            currently being parsed.  The elements of C{treetok}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type remaining_text: C{list} of C{Token}s
        @param remaining_text: The portion of the text that is not yet
            covered by C{treetok}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{treetok} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.  This list sorted
            in left-to-right order of location within the tree.
        """
        # If the treetok covers the text, and there's nothing left to
        # expand, then we've found a complete parse; return it.
        if len(remaining_text) == 0 and len(frontier) == 0:
            if self._trace:
                self._trace_succeed(treetok, frontier)
            clonetok = TreeToken(treetok.node().clone(), *treetok.children())
            return [clonetok]

        # If there's still text, but nothing left to expand, we failed.
        elif len(frontier) == 0:
            if self._trace:
                self._trace_backtrack(treetok, frontier)
            return []

        # If the next element on the frontier is a tree, expand it.
        elif isinstance(treetok[frontier[0]], TreeToken):
            return self._expand(remaining_text, treetok, frontier)

        # If the next element on the frontier is a token, match it.
        else:
            return self._match(remaining_text, treetok, frontier)

    def _match(self, rtext, treetok, frontier):
        """
        @rtype: C{list} of C{TreeToken}
        @return: a list of all parses that can be generated by
            matching the first element of C{frontier} against the
            first token in C{rtext}.  In particular, if the first
            element of C{frontier} has the same type as the first
            token in C{rtext}, then substitute the token into
            C{treetok}; and return all parses that can be generated by
            matching and expanding the remaining elements of
            C{frontier}.  If the first element of C{frontier} does not
            have the same type as the first token in C{rtext}, then
            return empty list.

        @type treetok: C{TreeToken}
        @param treetok: A partial structure for the text that is
            currently being parsed.  The elements of C{treetok}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type rtext: C{list} of C{Token}s
        @param rtext: The portion of the text that is not yet
            covered by C{treetok}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{treetok} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """
        if (len(rtext) > 0 and treetok[frontier[0]].type() == rtext[0].type()):
            # If it's a terminal that matches text[0], then substitute
            # in the token, and continue parsing.
            newtreetok = treetok.with_substitution(frontier[0], rtext[0])
            if self._trace:
                self._trace_match(newtreetok, frontier[1:], rtext[0])
            return self._parse(rtext[1:], newtreetok, frontier[1:])
        else:
            # If it's a non-matching terminal, fail.
            if self._trace:
                self._trace_backtrack(treetok, frontier, rtext[:1])
            return []

    def _expand(self, remaining_text, treetok, frontier, production=None):
        """
        @rtype: C{list} of C{TreeToken}
        @return: A list of all parses that can be generated by
            expanding the first element of C{frontier} with
            C{production}.  In particular, if the first element of
            C{frontier} is a subtree whose node type is equal to
            C{production}'s left hand side, then add a child to that
            subtree for each element of C{production}'s right hand
            side; and return all parses that can be generated by
            matching and expanding the remaining elements of
            C{frontier}.  If the first element of C{frontier} is not a
            subtree whose node type is equal to C{production}'s left
            hand side, then return an empty list.  If C{production} is
            not specified, then return a list of all parses that can
            be generated by expanding the first element of C{frontier}
            with I{any} CFG production.
            
        @type treetok: C{TreeToken}
        @param treetok: A partial structure for the text that is
            currently being parsed.  The elements of C{treetok}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type remaining_text: C{list} of C{Token}s
        @param remaining_text: The portion of the text that is not yet
            covered by C{treetok}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{treetok} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """
        if production is None: productions = self._grammar.productions()
        else: productions = [production]
        
        parses = []
        for production in productions:
            if production.lhs().symbol() == treetok[frontier[0]].node().symbol():
                subtree = self._production_to_treetok(production)
                subtree = TreeToken(subtree.node().clone(),*subtree.children())
                newtreetok = treetok.with_substitution(frontier[0], subtree)
                new_frontier = [frontier[0]+(i,) for i in
                                range(len(production.rhs()))]
                if self._trace:
                    self._trace_expand(newtreetok, new_frontier, production)
                parses += self._parse(remaining_text, newtreetok,
                                      new_frontier + frontier[1:])
        return parses

    def _production_to_treetok(self, production):
        """
        @rtype: C{TreeToken}
        @return: The C{TreeToken} that is licensed by C{production}.
            In particular, given the production::

                C{[M{lhs} -> M{elt[1]} ... M{elt[n]}]}

            Return a tree token that has a node C{M{lhs}.symbol}, and
            C{M{n}} children.  For each nonterminal element
            C{M{elt[i]}} in the production, the tree token has a
            childless subtree with node value C{M{elt[i]}.symbol}; and
            for each terminal element C{M{elt[j]}}, the tree token has
            a leaf token with type C{M{elt[j]}}.

        @param production: The CFG production that licenses the tree
            token that should be returned.
        @type production: C{CFGProduction}
        """
        children = []
        for elt in production.rhs():
            if isinstance(elt, Nonterminal):
                children.append(TreeToken(elt))
            else:
                # New token's location = None
                children.append(Token(elt))
        return TreeToken(production.lhs(), *children)
    
    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        @type trace: C{int}
        @param trace: The trace level.  A trace level of C{0} will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        @rtype: C{None}
        """
        assert _chktype(1, trace, types.IntType)
        self._trace = trace

    def _trace_fringe(self, treetok, treeloc=None):
        """
        Print trace output displaying the fringe of C{treetok}.  The
        fringe of C{treetok} consists of all of its leaves and all of
        its childless subtrees.

        @rtype: C{None}
        """
        if treeloc == (): print "*",
        if isinstance(treetok, TreeToken):
            children = treetok.children()
            if len(children) == 0: print `treetok.node()`,
            for i in range(len(children)):
                if treeloc is not None and i == treeloc[0]:
                    self._trace_fringe(children[i], treeloc[1:])
                else:
                    self._trace_fringe(children[i])
        else:
            print `treetok.type()`,

    def _trace_treetok(self, treetok, frontier, operation):
        """
        Print trace output displaying the parser's current state.

        @param operation: A character identifying the operation that
            generated the current state.
        @rtype: C{None}
        """
        if self._trace == 2: print '  %c [' % operation,
        else: print '    [',
        if len(frontier) > 0: self._trace_fringe(treetok, frontier[0])
        else: self._trace_fringe(treetok)
        print ']'

    def _trace_start(self, treetok, frontier, text):
        print 'Parsing %r' % ' '.join([tok.type() for tok in text])
        if self._trace > 2: print 'Start:'
        if self._trace > 1: self._trace_treetok(treetok, frontier, ' ')
        
    def _trace_expand(self, treetok, frontier, production):
        if self._trace > 2: print 'Expand: %s' % production
        if self._trace > 1: self._trace_treetok(treetok, frontier, 'E')

    def _trace_match(self, treetok, frontier, tok):
        if self._trace > 2: print 'Match: %r' % tok
        if self._trace > 1: self._trace_treetok(treetok, frontier, 'M')

    def _trace_succeed(self, treetok, frontier):
        if self._trace > 2: print 'GOOD PARSE:'
        if self._trace == 1: print 'Found a parse:\n%s' % treetok
        if self._trace > 1: self._trace_treetok(treetok, frontier, '+')

    def _trace_backtrack(self, treetok, frontier, toks=None):
        if self._trace > 2:
            if toks: print 'Backtrack: %r match failed' % toks[0]
            else: print 'Backtrack'

def t_rule(symbol):
    return Rule(Translation('none', symbol))

def a_rule(ann, symbol, n=1, premise=None):
    return Rule(AnnotationBoolean('none', (Annotation(ann, symbol, n),)), premise)

def build_tuple(*args):
    result = []
    for arg in args:
	if isinstance(arg, tuple):
            result.extend(arg)
	else:
	    result.append(arg)
    return tuple(result)

def agree(symbol1, symbol2, attrs, n1=1, n2=1):
    rules = []
    for attr in attrs:
        ab1 = AnnotationBoolean('none', (Annotation(attr, symbol1, n1),))
        ab2 = AnnotationBoolean('none', (Annotation(attr, symbol2, n2),))
        rules.append(Rule(ab1, ab2))
        rules.append(Rule(ab2, ab1))
    return tuple(rules)

#################################################################
# Demonstration
#################################################################

from nltk.parser import *

def demo():
    A, AUXP, DDET, DET, DETP = augnonterminals('A, AUXP, DDET, DET, DETP')
    INF, NOM, NOMHD, NOUN, N = augnonterminals('INF, NOM, NOMHD, NOUN, N')
    NP, PRED, S, SDEC, V, VP = augnonterminals('NP, PRED, S, SDEC, V, VP')
    VPP, VPT, TENSE, TO = augnonterminals('VPP, VPT, TENSE, TO')

    ab1 = AnnotationBoolean('not',(Annotation('predicative','NP'),))
    ab2 = AnnotationBoolean('and',(AnnotationBoolean('not',
                                                     (Annotation('definite','NP'),
                                                      Annotation('predicative','NP'))),))
    ab3 = AnnotationBoolean('or',(Annotation('gappy','NP'),Annotation('gappy','PRED')))
    ab4 = AnnotationBoolean('and',(Annotation('gappy','SDEC'),Annotation('gappy','PRED')))
    ab5 = AnnotationBoolean('and',(Annotation('gappy','SDEC'),Annotation('gappy','NP')))
    ab6 = AnnotationBoolean('or',(Annotation('wh','NP'),Annotation('wh','PRED')))
    ab7 = AnnotationBoolean('and',(Annotation('wh','SDEC'),Annotation('wh','PRED')))
    ab8 = AnnotationBoolean('and',(Annotation('wh','SDEC'),Annotation('wh','NP')))
    ab9 = AnnotationBoolean('or',(Annotation('wh','NP'),Annotation('wh','INF')))
    ab10 = AnnotationBoolean('and',(Annotation('wh','NP'),Annotation('wh','VP')))
    ab11 = AnnotationBoolean('and',(Annotation('wh','VP'),Annotation('wh','INF')))

    productions = (ACFGProduction(AUXP, (TENSE,), (), (t_rule('TENSE'),)),
                   ACFGProduction(DDET, (DET,),
                                  (a_rule('definite','DDET'),),
                                  (t_rule('DET'),)),
                   ACFGProduction(DETP, (A,), (), (t_rule('A'),)),
                   ACFGProduction(DETP, (DDET,),
                                  build_tuple(agree('DETP','DDET',('definite',))),
                                  (t_rule('DDET'),)),
                   ACFGProduction(INF, (TO, VPP),
                                  build_tuple(agree('INF','VPP',('gappy','wh'))),
                                  (t_rule('VPP'),)),
                   ACFGProduction(NOM, (NOMHD,),
                                  build_tuple(agree('NOM','NOMHD',('gappy',))),
                                  (t_rule('NOMHD'),)),
                   ACFGProduction(NOMHD, (NOUN,), (), (t_rule('NOUN'),)),
                   ACFGProduction(NOUN, (N,), (), (t_rule('N'),)),
                   ACFGProduction(NP, (DETP, NOM),
                                  build_tuple(agree('NP','NOM',('gappy',)),
                                              agree('NP','DETP',('definite',))),
                                  (Rule(Translation('app','DETP','NOM'), ab1),
                                   Rule(Translation('none','NOM'), ab2))),
                   ACFGProduction(PRED, (AUXP, VPP),
                                  build_tuple(agree('PRED','VPP',('active','gappy','wh'))),
                                  (Rule(Translation('pull_v',
                                                    Translation('app','AUXP','VPP'))),)),
                   ACFGProduction(S, (SDEC,), (), (t_rule('SDEC'),)),
                   ACFGProduction(SDEC, (NP, PRED),
                                  (a_rule('gappy','SDEC',premise=ab3),
                                   a_rule('gappy','NP',premise=ab4),
                                   a_rule('gappy','PRED',premise=ab5),
                                   a_rule('wh','SDEC',premise=ab6),
                                   a_rule('wh','NP',premise=ab7),
                                   a_rule('wh','PRED',premise=ab8)),
                                  (Rule(Translation('pull_s',
                                                    Translation('app','PRED','NP'))),)),
                   ACFGProduction(VP, (VPT,),
                                  (a_rule('active','VPT'),a_rule('active','VP')),
                                  (t_rule('VPT'),)),
                   ACFGProduction(VP, (VPT, NP, INF),
                                  build_tuple(a_rule('takesinf','VPT'),
                                              a_rule('trans','VPT'),
                                              agree('VP','VPT','active'),
                                              a_rule('wh','VP',premise=ab9),
                                              a_rule('wh','INF',premise=ab10),
                                              a_rule('wh','NP',premise=ab11)),
                                  (Rule(Translation('app',
                                                    Translation('app','VPT','NP'),
                                                    'INF')),)),
                   ACFGProduction(VPP, (VP,),
                                  build_tuple(agree('VPP','VP',('gappy','wh')),
                                              a_rule('active','VP')),
                                  (t_rule('VP'),)),
                   ACFGProduction(VPT, (V,),
                                  build_tuple(agree('VPT','V',
                                                    ('active','trans','takesinf'))),
                                  (t_rule('V'),)),
                   ACFGProduction(N, ('man',), (),
                                  (t_rule(Lambda('A',lambda X: 'man ' + X)),)),
                   ACFGProduction(N, ('woman',), (),
                                  (t_rule(Lambda('A',lambda X: 'woman ' + X)),)),
                   ACFGProduction(DET, ('every',), (a_rule('definite','DET'),),
                                  (t_rule(Lambda('B',
                                                 (lambda P: lambda S:
                                                  '(every X1 (' + P('X1') + ') ' + S + ')',
                                                  'X1'))),)),
                   ACFGProduction(A, ('a',), (),
                                  (t_rule(Lambda('B',
                                                 (lambda P: lambda S:
                                                  '(some X2 (' + P('X2') + ') ' + S + ')',
                                                  'X2'))),)),
                   ACFGProduction(V, ('persuade',),
                                  (a_rule('trans','V'),a_rule('takesinf','V')),
                                  (t_rule(Lambda('A',
                                                 lambda X: lambda P: lambda Y:
                                                 'persuade '+Y+' '+X+' '+'('+P(X)+')')),)),
                   ACFGProduction(V, ('go',), (a_rule('active','V'),),
                                  (t_rule(Lambda('A',lambda X: 'go ' + X)),)),
                   ACFGProduction(TENSE, ('&past',), (),
                                  (t_rule(Lambda('A',
                                                 lambda P: lambda X:
                                                 'past (' + P(X) + ')')),)),
                   ACFGProduction(TO, ('to',), (), ()))
    grammar = CFG(S, productions)
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    print 'Grammar for parsing, annotation, and translation'
    print grammar

    # Tokenize a sample sentence.
    sent = 'every man &past persuade a woman to go'
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    print 'Sentence to parse, annotate, and translate:'
    print '\t' + sent
    from nltk.tokenizer import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    parser = AugRecursiveDescentParser(grammar)

    # Run the parser.
    #parser.trace()
    parses = parser.parse_n(tok_sent)
    parser.annotate(parses, grammar)
    parser.translate(parses, grammar)
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    print 'Annotated parse trees:'
    for p in parses: print p
    print '%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%'
    print 'Final translations:'
    translations = []
    for p in parses:
        for trans in p.node().lambda_triples():
            if (trans.triple()[1] == None) & (trans.triple()[2] == []):
                if translations.count(trans.triple()[0]) == 0:
                    print trans.triple()[0]
                    translations.append(trans.triple()[0])
    return parses


if __name__ == '__main__':
    demo()
