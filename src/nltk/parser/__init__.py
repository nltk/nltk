# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu>
#         Scott Currie <sccurrie@seas.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces for producing tree structures that represent
the internal organziation of a text.  This task is known as X{parsing}
the text, and the resulting tree structures are called the text's
X{parses}.  Typically, the text is a single sentence, and the tree
structure represents the syntactic structure of the sentence.
However, parsers can also be used in other domains.  For example,
parsers can be used to derive the morphological structure of the
morphemes that make up a word, or to derive the discourse structure
for a set of utterances.

Sometimes, a single piece of text can be represented by more than one
tree structure.  Texts represented by more than one tree structure are
called X{ambiguous} texts.  Note that there are actually two ways in
which a text can be ambiguous:

    - The text has multiple correct parses.
    - There is not enough information to decide which of several
      candidate parses is correct.

However, the parser module does I{not} distinguish these two types of
ambiguity.

The parser module defines C{ParserI}, a standard interface for parsing
texts; and two simple implementations of that interface,
C{ShiftReduceParser} and C{RecursiveDescentParser}.  It also contains
three sub-modules for specialized kinds of parsing:

  - C{nltk.parser.chart} defines chart parsing, which uses dynamic
    programming to efficiently parse texts.
  - C{nltk.parser.chunk} defines chunk parsing, which identifies
    non-overlapping linguistic groups in a text.
  - C{nltk.parser.probabilistic} defines probabilistic parsing, which
    associates a probability with each parse.
"""

from nltk.tree import TreeToken
from nltk.cfg import Nonterminal, CFG, CFGProduction

__all__ = (
    'ParserI',
    'ShiftReduceParser', 'SteppingShiftReduceParser',
    'RecursiveDescentParser', 'demo',
    'chart', 'chunk', 'probabilistic',
    )

##//////////////////////////////////////////////////////
##  Parser Interface
##//////////////////////////////////////////////////////
class ParserI:
    """
    A processing interface for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as X{parses}.  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.

    A parse for a text assigns a tree structure to that text, but does
    not modify the text itself.  In particular, if M{t} is a text,
    then the leaves of any parse of M{t} should be M{t}.

    Parsing a text produces zero or more parses.  Abstractly, each
    of these parses has a X{quality} associated with it.  These
    quality ratings are used to decide which parses to return.  In
    particular, the C{parse} method returns the parse with the highest
    quality; and the C{parse_n} method returns a list of parses,
    sorted by their quality.

    If multiple parses have the same quality, then C{parse} and
    C{parse_n} can choose between them arbitrarily.  In particular,
    for some parsers, all parses are assigned the same quality.  For
    these parsers, C{parse} returns a single arbitrary parse, and
    C{parse_n} returns a list of parses in arbitrary order.
    """
    def __init__(self):
        """
        Construct a new C{Parser}.
        """
        assert 0, "ParserI is an abstract interface"

    def parse(self, text):
        """
        Return the best parse for the given text, or C{None} if no
        parses are available.
        
        @return: The highest-quality parse for the given text.  If
            multiple parses are tied for the highest quality, then
            choose one arbitrarily.  If no parse is available for the
            given text, return C{None}.
        @rtype: C{TreeToken} or C{None}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

    def parse_n(self, text, n=None):
        """
        @return: a list of the C{n} best parses for the given text,
            sorted in descending order of quality (or all parses, if
            the text has less than C{n} parses).  The order among
            parses with the same quality is undefined.  In other
            words, the first parse in the list will have the highest
            quality; and each subsequent parse will have equal or
            lower quality.  Note that the empty list will be returned
            if no parses were found.
        @rtype: C{list} of C{TreeToken}

        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is not specified, return
            all parses.
        @type n: C{int}
        @param text: The text to be parsed.  This text consists
            of a list of C{Tokens}, ordered by their C{Location}.
        @type text: C{list} of C{Token}
        """
        assert 0, "ParserI is an abstract interface"

##//////////////////////////////////////////////////////
##  Shift/Reduce Parser
##//////////////////////////////////////////////////////
class ShiftReduceParser(ParserI):
    """
    A simple bottom-up CFG parser that uses two operations, "shift"
    and "reduce", to find a single parse for a text.

    C{ShiftReduceParser} maintains a stack, which records the
    structure of a portion of the text.  This stack is a list of
    C{Token}s and C{TreeToken}s that collectively cover a portion of
    the text.  For example, while parsing the sentence "the dog saw
    the man" with a typical grammar, C{ShiftReduceParser} will produce
    the following stack, which covers "the dog saw"::

       [('NP': ('Det': 'the') ('N': 'dog'))@[0w:2w], ('V': 'saw')@[2w]]

    C{ShiftReduceParser} attempts to extend the stack to cover the
    entire text, and to combine the stack elements into a single tree,
    producing a complete parse for the sentence.

    Initially, the stack is empty.  It is extended to cover the text,
    from left to right, by repeatedly applying two operations:

      - X{shift} moves a token from the beginning of the text to the
        end of the stack.
      - X{reduce} uses a CFG production to combine the rightmost stack
        elements into a single C{TreeToken}.

    Often, more than one operation can be performed on a given stack.
    In this case, C{ShiftReduceParser} uses the following heuristics
    to decide which operation to perform:

      - Only shift if no reductions are available.
      - If multiple reductions are available, then apply the reduction
        whose CFG production is listed earliest in the grammar.

    Note that these heuristics are not guaranteed to choose an
    operation that leads to a parse of the text.  Also, if multiple
    parses exists, C{ShiftReduceParser} will return at most one of
    them.
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{ShiftReduceParser}, that uses {grammar} to
        parse texts.

        @type grammar: C{CFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        self._grammar = grammar
        self._trace = trace
        self._check_grammar()

    def grammar(self):
        """
        @return: The grammar used to parse texts.
        @rtype: C{CFG}
        """
        return self._grammar

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.
        
        @param grammar: The new grammar.
        @type grammar: C{CFG}
        """
        return self._grammar
    
    def parse_n(self, text):
        # Inherit documentation from ParserI; delegate to parse.
        treetok = self.parse(text)
        if treetok is None: return []
        else: return [treetok]

    def parse(self, text):
        # Inherit documentation from ParserI.

        # initialize the stack.
        stack = []
        remaining_text = text[:]
        
        # Trace output.
        if self._trace: self._trace_stack(stack, remaining_text)

        # iterate through the text, pushing the token's type onto
        # the stack, then reducing the stack.
        while len(remaining_text) > 0:
            self._shift(stack, remaining_text)
            while self._reduce(stack, remaining_text): pass

        # Did we reduce everything?
        if len(stack) != 1: return None

        # Did we end up with the right category?
        if stack[0].node() != self._grammar.start().symbol():
            return None
        
        # We parsed successfully!
        return stack[0]

    def _shift(self, stack, remaining_text):
        """
        Move a token from the beginning of C{remaining_text} to the
        end of C{stack}.

        @type stack: C{list} of C{Token} and C{TreeToken}
        @param stack: A list of C{Token}s and C{TreeToken}s, encoding
            the structure of the text that has been parsed so far.
        @type remaining_text: C{list} of C{Token}
        @param remaining_text: The portion of the text that is not yet
            covered by C{stack}.
        @rtype: C{None}
        """
        stack.append(remaining_text[0])

        # These are equivalant; the second is more efficient, but
        # probably harder to read.  So just use the 1st for now.
        remaining_text.remove(remaining_text[0])
        #remaining_text[:1] = []  # delete the 1st element
        
        if self._trace: self._trace_shift(stack, remaining_text)

    def _match(self, rhs, rightmost_stack):
        """
        @rtype: C{boolean}
        @return: true if the right hand side of a CFG production
            matches the rightmost elements of the stack.  C{rhs}
            matches C{rightmost_stack} if they are the same length,
            and each element of C{rhs} matches the corresponding
            element of C{rightmost_stack}.  A nonterminal element of
            C{rhs} matches any C{TreeToken} whose node value is equal
            to the nonterminal's symbol.  A terminal element of C{rhs}
            matches any C{Token} whose type is equal to the terminal.
        @type rhs: C{list} of (terminal and C{Nonterminal})
        @param rhs: The right hand side of a CFG production.
        @type rightmost_stack: C{list} of (C{Token} and C{TreeToken})
        @param rightmost_stack: The rightmost elements of the parser's
            stack.
        """
        if len(rightmost_stack) != len(rhs): return 0
        for i in range(len(rightmost_stack)):
            if isinstance(rightmost_stack[i], TreeToken):
                if not isinstance(rhs[i], Nonterminal): return 0
                if rightmost_stack[i].node() != rhs[i].symbol(): return 0
            else:
                if isinstance(rhs[i], Nonterminal): return 0
                if rightmost_stack[i].type() != rhs[i]: return 0
        return 1

    def _reduce(self, stack, remaining_text):
        """
        Find a CFG production whose right hand side matches the
        rightmost stack elements; and combine those stack elements
        into a single C{TreeToken}, with the node specified by the
        production's left-hand side.  If more than one CFG production
        matches the stack, then use the production that is listed
        earliest in the grammar.  The new C{TreeToken} replaces the
        elements in the stack.

        @rtype: C{CFGProduction} or C{boolean}
        @return: If a reduction is performed, then return the CFG
            production that the reduction is based on; otherwise,
            return false.
        @type stack: C{list} of C{Token} and C{TreeToken}
        @param stack: A list of C{Token}s and C{TreeToken}s, encoding
            the structure of the text that has been parsed so far.
        @type remaining_text: C{list} of C{Token}
        @param remaining_text: The portion of the text that is not yet
            covered by C{stack}.
        """
        # Try each production, in order.
        for production in self._grammar.productions():
            rhslen = len(production.rhs())
                
            # check if the RHS of a production matches the top of the stack
            if self._match(production.rhs(), stack[-rhslen:]):

                # combine the tree to reflect the reduction
                treetok = TreeToken(production.lhs().symbol(),
                                    *stack[-rhslen:])
                stack[-rhslen:] = [treetok]

                # We reduced something
                if self._trace:
                    self._trace_reduce(stack, production, remaining_text)
                return production

        # We didn't reduce anything
        return 0

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
        self._trace = trace

    def _trace_stack(self, stack, remaining_text, marker=' '):
        """
        Print trace output displaying the given stack and text.
        
        @rtype: C{None}
        @param marker: A character that is printed to the left of the
            stack.  This is used with trace level 2 to print 'S'
            before shifted stacks and 'R' before reduced stacks.
        """
        str = '  '+marker+' [ '
        for tok in stack:
            if isinstance(tok, TreeToken):
                str += `Nonterminal(tok.node())` + ' '
            else:
                str += `tok.type()` + ' '
        str += '* ' + ' '.join([`s.type()` for s in remaining_text]) + ']'
        print str

    def _trace_shift(self, stack, remaining_text):
        """
        Print trace output displaying that a token has been shifted.
        
        @rtype: C{None}
        """
        if self._trace > 2: print 'Shift %r:' % stack[-1]
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'S')
        elif self._trace > 0: self._trace_stack(stack, remaining_text)

    def _trace_reduce(self, stack, production, remaining_text):
        """
        Print trace output displaying that C{production} was used to
        reduce C{stack}.
        
        @rtype: C{None}
        """
        if self._trace > 2:
            rhs = ' '.join([`s` for s in production.rhs()])
            print 'Reduce %r <- %s' % (production.lhs(), rhs)
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'R')
        elif self._trace > 1: self._trace_stack(stack, remaining_text)

    def _check_grammar(self):
        """
        Check to make sure that all of the CFG productions are
        potentially useful.  If any productions can never be used,
        then print a warning.

        @rtype: C{None}
        """
        productions = self._grammar.productions()

        # Any production whose RHS is an extension of another production's RHS
        # will never be used. 
        for i in range(len(productions)):
            for j in range(i+1, len(productions)):
                rhs1 = productions[i].rhs()
                rhs2 = productions[j].rhs()
                if rhs1[:len(rhs2)] == rhs2:
                    print 'Warning: %r will never be used' % productions[i]

##//////////////////////////////////////////////////////
##  Recursive Descent Parser
##//////////////////////////////////////////////////////
class RecursiveDescentParser(ParserI):
    """
    A simple top-down CFG parser that parses texts by recursively
    expanding a CFG expression.  A X{CFG expression} is a sequence of
    terminals and C{Nonterminal}s.

    Terminology:
      - An X{partial parse} of a CFG expression is a sequence of
        C{Token}s and {TreeToken}s that stand in a 1-to-1
        relationship to that expression: each C{Token} corresponds
        to a terminal and has the same type, and each C{TreeToken}
        corresponds to a nonterminal, and its node type matches the
        nonterminal's symbol.
      - A partial parse X{covers} a text if the sequence of tokens
        and treetoken leaves is equal to the text.
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace

    def grammar(self):
        """
        @return: The grammar used to parse texts.
        @rtype: C{CFG}
        """
        return self._grammar

    def set_grammar(self, grammar):
        """
        Change the grammar used to parse texts.
        
        @param grammar: The new grammar.
        @type grammar: C{CFG}
        """
        return self._grammar
    
    def parse(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

    def parse_n(self, text, n=None):
        # Inherit docs from ProbablisticParserI

        # Find anything with the right start symbol, beginning at the
        # start of the text.
        stack = (self._grammar.start(),)
        parses = [x[0] for x in self._expand_to_text(stack, text)]

        # Return the requested number of parses.
        if n is None: return parses
        else: return parses[:n]

    def _expand_to_text(self, expr, text, original_text=None, depth=1):
        """
        Find all partial parses for the CFG expression C{expr} that
        cover C{text}, and return them as a list.  
        
        @return: all candidate partial parses for the CFG expression
            C{expr} that cover C{text}.
        @rtype: C{list} of (C{list} of (C{Token} and C{TreeToken}))

        @type expr: sequence of (C{Terminal} and nonterminal)
        @param expr: The CFG expression that should be expanded to
            cover C{text}.
            
        @type text: C{list} of C{Token}
        @param text: The text that should be covered by the partial
            parses of C{expr}.
        @type original_text: C{list} of C{Token}
        @param original_text: The text that was originally given to
            the parser.  This is only used for producing trace output. 
        """
        if original_text is None:
            original_text = text
            if self._trace:
                self._trace_stack(expr, text, original_text, 0, 'Start')

        # If the expression and the text are both empty, then return a
        # single empty partial parse.
        if len(text) == 0 and len(expr) == 0:
            if self._trace:
                self._trace_stack(expr, text, original_text, depth, 'SUCCEED')
            return [[]]

        # If the expression is empty, then we have text that we didn't
        # account for; return no partial parses.
        if len(expr) == 0: 
            if self._trace:
                self._trace_stack(expr, text, original_text, depth, 'Fail')

        # Process the first element of the expression.
        if isinstance(expr[0], Nonterminal):
            # If it's a nonterminal, try expanding it with grammar productions.
            # (This may return no partial parses)
            pparses = []
            for production in self._grammar.productions():
                if production.lhs() == expr[0]:
                    pparses += self._expand_production(production, expr, text,
                                                       original_text, depth)
            return pparses
        elif len(text) > 0 and expr[0] == text[0].type():
            if self._trace:
                self._trace_stack(expr[1:], text[1:], original_text,
                                  depth, 'Shift')
            # If it's a matching terminal, go on to the rest of the stack.
            pparses = self._expand_to_text(expr[1:], text[1:],
                                           original_text, depth)
            return [ [text[0]] + e for e in pparses]
        else:
            if self._trace:
                self._trace_stack(expr, text, original_text, depth, 'Fail')
            # If it's a non-matching terminal, fail.
            return []

    def _expand_production(self, production, expr, text,
                           original_text, depth):
                           
        """
        @return: all partial parses for the CFG expression C{expr}
            that cover C{text}, where the first element of C{expr} is
            expanded using C{production}.
        @rtype: C{list} of (C{list} of (C{Token} and C{TreeToken}))
        """
        # Expand expr[0] with production.
        expansion = production.rhs()+expr[1:]

        # Trace output
        if self._trace:
            self._trace_stack(expansion, text, original_text, depth, 'Expand')
            
        # Find partial parses for the expanded CFG expression.
        expansion_pparses = self._expand_to_text(expansion, text,
                                                 original_text, depth+1)

        # For each partial parse, collect the elements generated by
        # the production into a single TreeToken.
        return [self._collect(production, e) for e in expansion_pparses]

    def _collect(self, production, pparse):
        """
        Collect the first C{production.rhs} elements of C{pparse} into a
        treetoken, with node C{production.lhs}; Return the resulting partial
        parse.

        @type production: C{CFGProduction}
        @type pparse: C{list} of (C{list} of (C{Token} and C{TreeToken}))
        @rtype: C{list} of (C{list} of (C{Token} and C{TreeToken}))
        """
        # Collect the children into a tree.
        rhs_len = len(production.rhs())
        children = pparse[:rhs_len]
        treetok = TreeToken(production.lhs(), *children)

        # Replace the children with the tree, and return it.
        return [treetok] + pparse[rhs_len:]

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
        self._trace = trace

    def _trace_stack(self, expr, text, original_text, depth, marker=' '):
        if self._trace > 3: print '%-40s[' % ('  '*depth+marker),
        elif self._trace == 3: print '[%2s] %-8s[' % (depth, marker),
        else: print '%-8s[' % marker, 
            
        pos = len(original_text) - len(text)
        for tok in original_text[:pos]: print `tok.type()`,
        print '*',
        for elt in expr: print `elt`,
        print ']'

##//////////////////////////////////////////////////////
##  Stepping Shift/Reduce Parser
##//////////////////////////////////////////////////////
class SteppingShiftReduceParser(ShiftReduceParser):
    """
    A C{ShiftReduceParser} that allows you to setp through the parsing
    process, performing a single operation at a time.  It also allows
    you to change the parser's grammar midway through parsing a text.

    The C{initialize} method is used to start parsing a text.
    C{shift} performs a single shift operation, and C{reduce} performs
    a single reduce operation.  C{step} will perform a single reduce
    operation if possible; otherwise, it will perform a single shift
    operation.  C{parses} returns the set of parses that have been
    found by the parser.
    """
    def __init__(self, grammar, trace=0):
        ShiftReduceParser.__init__(self, grammar, trace)
        self._stack = None
        self._remaining_text = None

    def stack(self):
        """
        @return: The parser's stack.
        @rtype: C{list} of C{Token} and C{TreeToken}
        """
        return self._stack

    def remaining_text(self):
        """
        @return: The portion of the text that is not yet covered by the
            stack.
        @rtype: C{list} of C{Token}
        """
        return self._remaining_text
        
    def initialize(self, text):
        """
        Start parsing a given text.  This sets the parser's stack to
        C{[]} and sets its remaining text to C{text}.

        @param text: The text to start parsing.
        @type text: C{list} of C{Token}
        """
        self._stack = []
        self._remaining_text = text[:]

    def step(self):
        """
        Perform a single parsing operation.  If a reduction is
        possible, then perform that reduction, and return the
        production that it is based on.  Otherwise, if a shift is
        possible, then perform it, and return 1.  Otherwise, return
        0. 

        @return: 0 if no operation was performed; 1 if a shift was
            performed; and the CFG production used to reduce if a
            reduction was performed.
        @rtype: C{CFGProduction} or C{boolean}
        """
        return self.reduce() or self.shift()

    def shift(self):
        """
        Move a token from the beginning of the remaining text to the
        end of the stack.

        @rtype: C{None}
        """
        if len(self._remaining_text) == 0: return 0
        self._shift(self._stack, self._remaining_text)
        return 1
        
    def reduce(self):
        return self._reduce(self._stack, self._remaining_text)

    def parses(self):
        if len(self._remaining_text) != 0: return []
        if len(self._stack) != 1: return []
        if self._stack[0].node() != self._grammar.start().symbol():
            return []
        return self._stack
    
##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    productions = (
        # Syntactic Rules
        CFGProduction(S, NP, VP),
        CFGProduction(NP, Det, N),
        CFGProduction(VP, V, NP, PP),
        CFGProduction(NP, Det, N, PP),
        CFGProduction(PP, P, NP),

        # Lexical Rules
        CFGProduction(NP, 'I'),   CFGProduction(Det, 'the'),
        CFGProduction(Det, 'a'),  CFGProduction(N, 'man'),
        CFGProduction(V, 'saw'),  CFGProduction(P, 'in'),
        CFGProduction(P, 'with'), CFGProduction(N, 'park'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'telescope')
        )

    grammar = CFG(S, productions)

    sent = 'I saw a man in the park'
    print "Sentence:\n", sent

    # tokenize the sentence
    from nltk.token import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    srparser = ShiftReduceParser(grammar)
    rdparser = RecursiveDescentParser(grammar)

    srparser.trace()
    rdparser.trace()

    for p in srparser.parse_n(tok_sent): print p
    for p in rdparser.parse_n(tok_sent): print p

if __name__ == '__main__': demo()
