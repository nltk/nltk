# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
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
parsers could be used to derive the morphological structure of the
morphemes that make up a word, or to derive the discourse structure of
a list of utterances.

Sometimes, a single piece of text can be represented by more than one
tree structure.  Texts represented by more than one tree structure are
called X{ambiguous} texts.  Note that there are actually two ways in
which a text can be ambiguous:

    - The text has multiple correct parses.
    - There is not enough information to decide which of several
      candidate parses is correct.

However, the parser module does I{not} distinguish these two types of
ambiguity.
"""

from nltk.tree import TreeToken
from nltk.cfg import Nonterminal, CFG, CFGProduction

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

    Parsing a text generates zero or more parses.  Abstractly, each of
    these parses has a X{quality} associated with it.  These quality
    ratings are used to decide which parses to return.  In particular,
    the C{parse} method returns the parse with the highest quality;
    and the C{parse_n} method returns a list of parses, sorted by
    their quality.

    If multiple parses have the same quality, then C{parse} and
    C{parse_n} can choose between them arbitrarily.  In particular,
    for some parsers, all parses have the same quality.  For these
    parsers, C{parse} returns a single arbitrary parse, and C{parse_n}
    returns an list of parses in arbitrary order.
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
            parses with the same quality is undefined.  I.e., the
            first parse in the list will have the highest quality; and
            each subsequent parse will have equal or lower quality.
            Note that the empty list will be returned if no parses
            were found.
        @rtype: C{list} of C{TreeToken}

        @param n: The number of parses to generate.  At most C{n}
            parses will be returned.  If C{n} is C{None}, return all
            parses. 
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
    Shift-reduce parser.

    Maintain two stacks: one for tokens, one for types/Nonterminals.
    Match the Nonterminals/types stack against the RHS of productions when
    trying to reduce.  Use the token stack to record the structures
    we've built so far.
    """
    def __init__(self, grammar, trace=0):
        """
        Construct a new C{SRParser}.
        """
        self._grammar = grammar
        self._trace = trace
        self.check_grammar()

    def _shift(self, token, stack, tokstack, remaining_text):
        """
        Push the next token onto the stack.
        """
        stack.append(token.type())
        tokstack.append(token)
        if self._trace: self._trace_shift(stack, remaining_text)

    def _reduce(self, stack, tokstack, remaining_text):
        # scan through the production set
        for production in self._grammar.productions():
            rhslen = len(production.rhs())
                
            # check if the RHS of a production matches the top of the stack
            if tuple(stack[-rhslen:]) == production.rhs():

                # replace the top of the stack with the LHS of the production
                stack[-rhslen:] = [production.lhs()]

                # combine the tree to reflect the reduction
                treetok = TreeToken(production.lhs().symbol(), *tokstack[-rhslen:])
                tokstack[-rhslen:] = [treetok]

                # We reduced something
                if self._trace:
                    self._trace_reduce(stack, production, remaining_text)
                return production

        # We didn't reduce anything
        return 0

    def parse(self, text):
        # Inherit documentation from ParserI.

        # initialize the stacks.
        stack = []
        tokstack = []

        # Trace output.
        remaining_text = text
        if self._trace: self._trace_stack(stack, remaining_text)

        # iterate through the text, pushing the token's type onto
        # the stack, then reducing the stack.
        for token in text:
            remaining_text = remaining_text[1:]
            self._shift(token, stack, tokstack, remaining_text)
            while self._reduce(stack, tokstack, remaining_text): pass

        # Did we reduce everything?
        if len(stack) != 1: return None

        # Did we end up with the right category?
        if stack[0] != self._grammar.start(): return None
        
        # We parsed successfully!
        return tokstack[0]

    def _trace_stack(self, stack, remaining_text, marker=' '):
        print ('  '+marker+' [' + ' '.join([`s` for s in stack])+' * '+
               ' '.join([`s.type()` for s in remaining_text]) + ']')

    def _trace_shift(self, stack, remaining_text):
        if self._trace > 2: print 'Shift %r:' % stack[0]
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'S')
        elif self._trace > 0: self._trace_stack(stack, remaining_text)

    def _trace_reduce(self, stack, production, remaining_text):
        if self._trace > 2:
            print 'Reduce %r <- %s' % (production.lhs(),
                                       ' '.join([`s` for s in production.rhs()]))
        if self._trace == 2: self._trace_stack(stack, remaining_text, 'R')
        elif self._trace > 1: self._trace_stack(stack, remaining_text)

    # Delegate to parse
    def parse_n(self, text):
        # Inherit documentation from ParserI; delegate to parse.
        treetok = self.parse(text)
        if treetok is None: return []
        else: return [treetok]

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

    def check_grammar(self):
        """
        Check that all the productions in the grammar are useful.
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

    A X{CFG expression} is a sequence of terminals and
    C{Nonterminal}s.

    To X{expand} an expression with a production is to replace a nonterminal
    with a CFG expression, using a production. (replace lhs with rhs)

    An X{expansion} *could* be just a CFG expression that's been
    expanded.  But then what do I call the lists of tokens &
    treetokens? 

    An X{partial parse} of a CFG expression is a sequence of C{Token}s
    and {TreeToken}s that stand in a 1-to-1 relationship to that
    expression: each C{Token} corresponds to a terminal and has the
    same type, and each C{TreeToken} corresponds to a nonterminal, and
    its node type matches the nonterminal's symbol.

    A partial parse X{covers} a text if the sequence of tokens and
    treetoken leaves is equal to the text.        
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace

    def parse(self, text):
        # Inherit docs from ProbabilisticParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

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

    def parse_n(self, text, n=None):
        # Inherit docs from ProbablisticParserI

        # Find anything with the right start symbol, beginning at the
        # start of the text.
        stack = (self._grammar.start(),)
        parses = [x[0] for x in self._expand_to_text(stack, text)]

        # Return the requested number of parses.
        if n is None: return parses
        else: return parses[:n]

    def _expand_to_text(self, expr, text, original_text=None):
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
        if original_text is None: original_text = text

        # If the expression and the text are both empty, then return a
        # single empty partial parse.
        if len(text) == 0 and len(expr) == 0:
            if self._trace: self._trace_stack(expr, text, original_text, 1)
            return [[]]
        else:
            if self._trace: self._trace_stack(expr, text, original_text, 0)

        # If the expression is empty, then we have text that we didn't
        # account for; return no partial parses.
        if len(expr) == 0: return []

        # Process the first element of the expression.
        if isinstance(expr[0], Nonterminal):
            # If it's a nonterminal, try expanding it with grammar productions.
            # (This may return no partial parses)
            pparses = []
            for production in self._grammar.productions():
                if production.lhs() == expr[0]:
                    pparses += self._expand_production(production, expr, text,
                                                 original_text)
            return pparses
        elif len(text) > 0 and expr[0] == text[0].type():
            # If it's a matching terminal, go on to the rest of the stack.
            pparses = self._expand_to_text(expr[1:], text[1:], original_text)
            return [ [text[0]] + e for e in pparses]
        else:
            # If it's a non-matching terminal, fail.
            return []

    def _expand_production(self, production, expr, text, original_text):
        """
        @return: all partial parses for the CFG expression C{expr}
            that cover C{text}, where the first element of C{expr} is
            expanded using C{production}.
        """
        # Expand expr[0] with production.
        expansion = production.rhs()+expr[1:]

        # Find partial parses for the expanded CFG expression.
        expansion_pparses = self._expand_to_text(expansion, text,
                                                 original_text)

        # For each partial parse, collect the elements generated by
        # the production into a single TreeToken.
        return [self._collect(production, e) for e in expansion_pparses]

    def _collect(self, production, pparse):
        """
        Collect the first C{production.rhs} elements of C{pparse} into a
        treetoken, with node C{production.lhs}; Return the resulting partial
        parse.
        """
        # Collect the children into a tree.
        rhs_len = len(production.rhs())
        children = pparse[:rhs_len]
        treetok = TreeToken(production.lhs(), *children)

        # Replace the children with the tree, and return it.
        return [treetok] + pparse[rhs_len:]

    def _trace_stack(self, expr, text, original_text, success):
        print '[',
        pos = len(original_text) - len(text)
        for tok in original_text[:pos]: print `tok.type()`,
        print '*',
        for elt in expr: print `elt`,
        if success: print ']     (good parse)'
        else: print ']'

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
        CFGProduction(VP, V, NP, PP, PP),
        CFGProduction(PP, P, NP),

        # Lexical Rules
        CFGProduction(NP, 'I'),   CFGProduction(Det, 'the'),
        CFGProduction(Det, 'a'),  CFGProduction(N, 'man'),
        CFGProduction(V, 'saw'),  CFGProduction(P, 'in'),
        CFGProduction(P, 'with'), CFGProduction(N, 'park'),
        CFGProduction(N, 'telescope')
        )

    grammar = CFG(S, productions)

    sent = 'I saw a man in the park with a telescope'
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
