# Natural Language Toolkit: Shift-Reduce Parser
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from tree import *
from nltk_lite import tokenize
from nltk_lite.parse import AbstractParse, cfg
from types import *

##//////////////////////////////////////////////////////
##  Shift/Reduce Parser
##//////////////////////////////////////////////////////
class ShiftReduce(AbstractParse):
    """
    A simple bottom-up CFG parser that uses two operations, "shift"
    and "reduce", to find a single parse for a text.

    C{ShiftReduce} maintains a stack, which records the
    structure of a portion of the text.  This stack is a list of
    C{String}s and C{Tree}s that collectively cover a portion of
    the text.  For example, while parsing the sentence "the dog saw
    the man" with a typical grammar, C{ShiftReduce} will produce
    the following stack, which covers "the dog saw"::

       [(NP: (Det: 'the') (N: 'dog')), (V: 'saw')]

    C{ShiftReduce} attempts to extend the stack to cover the
    entire text, and to combine the stack elements into a single tree,
    producing a complete parse for the sentence.

    Initially, the stack is empty.  It is extended to cover the text,
    from left to right, by repeatedly applying two operations:

      - X{shift} moves a token from the beginning of the text to the
        end of the stack.
      - X{reduce} uses a CFG production to combine the rightmost stack
        elements into a single C{Tree}.

    Often, more than one operation can be performed on a given stack.
    In this case, C{ShiftReduce} uses the following heuristics
    to decide which operation to perform:

      - Only shift if no reductions are available.
      - If multiple reductions are available, then apply the reduction
        whose CFG production is listed earliest in the grammar.

    Note that these heuristics are not guaranteed to choose an
    operation that leads to a parse of the text.  Also, if multiple
    parses exists, C{ShiftReduce} will return at most one of
    them.

    @see: C{nltk.cfg}
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{ShiftReduce}, that uses C{grammar} to
        parse texts.

        @type grammar: C{Grammar}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        self._grammar = grammar
        self._trace = trace
        AbstractParse.__init__(self)
        self._check_grammar()

    def get_parse(self, tokens):

        # initialize the stack.
        stack = []
        remaining_text = tokens
        
        # Trace output.
        if self._trace:
            print 'Parsing %r' % ' '.join(tokens)
            self._trace_stack(stack, remaining_text)

        # iterate through the text, pushing the token onto
        # the stack, then reducing the stack.
        while len(remaining_text) > 0:
            self._shift(stack, remaining_text)
            while self._reduce(stack, remaining_text): pass

        # Did we reduce everything?
        if len(stack) != 1: return None

        # Did we end up with the right category?
        if stack[0].node != self._grammar.start().symbol():
            return None
        
        # We parsed successfully!
        return stack[0]

    def _shift(self, stack, remaining_text):
        """
        Move a token from the beginning of C{remaining_text} to the
        end of C{stack}.

        @type stack: C{list} of C{String} and C{Tree}
        @param stack: A list of C{String}s and C{Tree}s, encoding
            the structure of the text that has been parsed so far.
        @type remaining_text: C{list} of C{String}
        @param remaining_text: The portion of the text that is not yet
            covered by C{stack}.
        @rtype: C{None}
        """
        stack.append(remaining_text[0])
        remaining_text.remove(remaining_text[0])
        if self._trace: self._trace_shift(stack, remaining_text)

    def _match_rhs(self, rhs, rightmost_stack):
        """
        @rtype: C{boolean}
        @return: true if the right hand side of a CFG production
            matches the rightmost elements of the stack.  C{rhs}
            matches C{rightmost_stack} if they are the same length,
            and each element of C{rhs} matches the corresponding
            element of C{rightmost_stack}.  A nonterminal element of
            C{rhs} matches any C{Tree} whose node value is equal
            to the nonterminal's symbol.  A terminal element of C{rhs}
            matches any C{String} whose type is equal to the terminal.
        @type rhs: C{list} of (terminal and C{Nonterminal})
        @param rhs: The right hand side of a CFG production.
        @type rightmost_stack: C{list} of (C{String} and C{Tree})
        @param rightmost_stack: The rightmost elements of the parser's
            stack.
        """
        
        if len(rightmost_stack) != len(rhs): return 0
        for i in range(len(rightmost_stack)):
            if isinstance(rightmost_stack[i], Tree):
                if not isinstance(rhs[i], cfg.Nonterminal): return 0
                if rightmost_stack[i].node != rhs[i].symbol(): return 0
            else:
                if isinstance(rhs[i], cfg.Nonterminal): return 0
                if rightmost_stack[i] != rhs[i]: return 0
        return 1

    def _reduce(self, stack, remaining_text, production=None):
        """
        Find a CFG production whose right hand side matches the
        rightmost stack elements; and combine those stack elements
        into a single C{Tree}, with the node specified by the
        production's left-hand side.  If more than one CFG production
        matches the stack, then use the production that is listed
        earliest in the grammar.  The new C{Tree} replaces the
        elements in the stack.

        @rtype: C{Production} or C{None}
        @return: If a reduction is performed, then return the CFG
            production that the reduction is based on; otherwise,
            return false.
        @type stack: C{list} of C{String} and C{Tree}
        @param stack: A list of C{String}s and C{Tree}s, encoding
            the structure of the text that has been parsed so far.
        @type remaining_text: C{list} of C{String}
        @param remaining_text: The portion of the text that is not yet
            covered by C{stack}.
        """
        if production is None: productions = self._grammar.productions()
        else: productions = [production]
        
        # Try each production, in order.
        for production in productions:
            rhslen = len(production.rhs())
                
            # check if the RHS of a production matches the top of the stack
            if self._match_rhs(production.rhs(), stack[-rhslen:]):

                # combine the tree to reflect the reduction
                tree = Tree(production.lhs().symbol(), stack[-rhslen:])
                stack[-rhslen:] = [tree]

                # We reduced something
                if self._trace:
                    self._trace_reduce(stack, production, remaining_text)
                return production

        # We didn't reduce anything
        return None

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
        # 1: just show shifts.
        # 2: show shifts & reduces
        # 3: display which tokens & productions are shifed/reduced
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
        for elt in stack:
            if isinstance(elt, Tree):
                str += `cfg.Nonterminal(elt.node)` + ' '
            else:
                str += `elt` + ' '
        str += '* ' + ' '.join(remaining_text) + ']'
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
            rhs = ' '.join(production.rhs())
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
##  Stepping Shift/Reduce Parser
##//////////////////////////////////////////////////////
class SteppingShiftReduce(ShiftReduce):
    """
    A C{ShiftReduce} that allows you to setp through the parsing
    process, performing a single operation at a time.  It also allows
    you to change the parser's grammar midway through parsing a text.

    The C{initialize} method is used to start parsing a text.
    C{shift} performs a single shift operation, and C{reduce} performs
    a single reduce operation.  C{step} will perform a single reduce
    operation if possible; otherwise, it will perform a single shift
    operation.  C{parses} returns the set of parses that have been
    found by the parser.

    @ivar _history: A list of C{(stack, remaining_text)} pairs,
        containing all of the previous states of the parser.  This
        history is used to implement the C{undo} operation.
    @see: C{nltk.cfg}
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace
        self._stack = None
        self._remaining_text = None
        self._history = []
        AbstractParse.__init__(self)

    def get_parse_list(self, token):
        self.initialize(token)
        while self.step(): pass
        
        return self.parses()

    def stack(self):
        """
        @return: The parser's stack.
        @rtype: C{list} of C{String} and C{Tree}
        """
        return self._stack

    def remaining_text(self):
        """
        @return: The portion of the text that is not yet covered by the
            stack.
        @rtype: C{list} of C{String}
        """
        return self._remaining_text
        
    def initialize(self, token):
        """
        Start parsing a given text.  This sets the parser's stack to
        C{[]} and sets its remaining text to C{token['SUBTOKENS']}.
        """
        self._stack = []
        self._remaining_text = token
        self._history = []

    def step(self):
        """
        Perform a single parsing operation.  If a reduction is
        possible, then perform that reduction, and return the
        production that it is based on.  Otherwise, if a shift is
        possible, then perform it, and return 1.  Otherwise,
        return 0. 

        @return: 0 if no operation was performed; 1 if a shift was
            performed; and the CFG production used to reduce if a
            reduction was performed.
        @rtype: C{Production} or C{boolean}
        """
        return self.reduce() or self.shift()

    def shift(self):
        """
        Move a token from the beginning of the remaining text to the
        end of the stack.  If there are no more tokens in the
        remaining text, then do nothing.

        @return: True if the shift operation was successful.
        @rtype: C{boolean}
        """
        if len(self._remaining_text) == 0: return 0
        self._history.append( (self._stack[:], self._remaining_text[:]) )
        self._shift(self._stack, self._remaining_text)
        return 1
        
    def reduce(self, production=None):
        """
        Use C{production} to combine the rightmost stack elements into
        a single C{Tree}.  If C{production} does not match the
        rightmost stack elements, then do nothing.

        @return: The production used to reduce the stack, if a
            reduction was performed.  If no reduction was performed,
            return C{None}.
        
        @rtype: C{Production} or C{None}
        """
        self._history.append( (self._stack[:], self._remaining_text[:]) )
        return_val = self._reduce(self._stack, self._remaining_text,
                                  production)

        if not return_val: self._history.pop()
        return return_val

    def undo(self):
        """
        Return the parser to its state before the most recent
        shift or reduce operation.  Calling C{undo} repeatedly return
        the parser to successively earlier states.  If no shift or
        reduce operations have been performed, C{undo} will make no
        changes.

        @return: true if an operation was successfully undone.
        @rtype: C{boolean}
        """
        if len(self._history) == 0: return 0
        (self._stack, self._remaining_text) = self._history.pop()
        return 1

    def reducible_productions(self):
        """
        @return: A list of the productions for which reductions are
            available for the current parser state.
        @rtype: C{list} of C{Production}
        """
        productions = []
        for production in self._grammar.productions():
            rhslen = len(production.rhs())
            if self._match_rhs(production.rhs(), self._stack[-rhslen:]):
                productions.append(production)
        return productions

    def parses(self):
        """
        @return: A list of the parses that have been found by this
            parser so far.
        @rtype: C{list} of C{Tree}
        """
        if len(self._remaining_text) != 0: return []
        if len(self._stack) != 1: return []
        if self._stack[0].node != self._grammar.start().symbol():
            return []
        return self._stack
    
##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration of the shift-reduce parser.
    """

    from nltk_lite.parse import cfg

    # Define some nonterminals
    S, VP, NP, PP = cfg.nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = cfg.nonterminals('V, N, P, Name, Det')

    # Define a grammar.
    productions = (
        # Syntactic Productions
        cfg.Production(S, [NP, 'saw', NP]),
        cfg.Production(S, [NP, VP]),
        cfg.Production(NP, [Det, N]),
        cfg.Production(VP, [V, NP, PP]),
        cfg.Production(NP, [Det, N, PP]),
        cfg.Production(PP, [P, NP]),

        # Lexical Productions
        cfg.Production(NP, ['I']),   cfg.Production(Det, ['the']),
        cfg.Production(Det, ['a']),  cfg.Production(N, ['man']),
        cfg.Production(V, ['saw']),  cfg.Production(P, ['in']),
        cfg.Production(P, ['with']), cfg.Production(N, ['park']),
        cfg.Production(N, ['dog']),  cfg.Production(N, ['telescope'])
        )
    grammar = cfg.Grammar(S, productions)

    # Tokenize a sample sentence.
    sent = list(tokenize.whitespace('I saw a man in the park'))

    parser = ShiftReduce(grammar)
    parser.trace()
    for p in parser.get_parse_list(sent):
        print p

if __name__ == '__main__': demo()
