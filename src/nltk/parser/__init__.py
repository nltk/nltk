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
from nltk.token import Token
from nltk.cfg import Nonterminal, CFG, CFGProduction

__all__ = (
    'ParserI',
    'ShiftReduceParser', 'SteppingShiftReduceParser',
    'RecursiveDescentParser', 'SteppingRecursiveDescentParser',
    'demo',
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
        @return: A list of the C{n} best parses for the given text,
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
        Create a new C{ShiftReduceParser}, that uses C{grammar} to
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
    
    def parse_n(self, text, n=None):
        # Inherit documentation from ParserI; delegate to parse.
        if n == 0: return []
        treetok = self.parse(text)
        if treetok is None: return []
        else: return [treetok]

    def parse(self, text):
        # Inherit documentation from ParserI.

        # initialize the stack.
        stack = []
        remaining_text = text[:]
        
        # Trace output.
        if self._trace:
            print 'Parsing %r' % ' '.join([tok.type() for tok in text])
            self._trace_stack(stack, remaining_text)

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

    def _match_rhs(self, rhs, rightmost_stack):
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

    def _reduce(self, stack, remaining_text, production=None):
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
        if production is None: productions = self._grammar.productions()
        else: productions = [production]
        
        # Try each production, in order.
        for production in productions:
            rhslen = len(production.rhs())
                
            # check if the RHS of a production matches the top of the stack
            if self._match_rhs(production.rhs(), stack[-rhslen:]):

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
        # Inherit docs from ParserI; and delegate to parse_n
        final_trees = self.parse_n(text, 1)
        if len(final_trees) == 0: return None
        else: return final_trees[0]

    def parse_n(self, text, n=None):
        # Inherit docs from ParserI

        # Start a recursive descent parse, with an initial tree
        # containing just the start symbol.
        initial_treetok = TreeToken(self._grammar.start().symbol())
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
            return [treetok]

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
            if production.lhs().symbol() == treetok[frontier[0]].node():
                subtree = self._production_to_treetok(production)
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
                children.append(TreeToken(elt.symbol()))
            else:
                # New token's location = None
                children.append(Token(elt))
        return TreeToken(production.lhs().symbol(), *children)
    
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
            if len(children) == 0: print `Nonterminal(treetok.node())`,
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

    @ivar _history: A list of C{(stack, remaining_text)} pairs,
        containing all of the previous states of the parser.  This
        history is used to implement the C{undo} operation.
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace
        self._stack = None
        self._remaining_text = None
        self._history = []

    def parse(self, text):
        # Inherit docs
        self.initialize(text)
        while self.step(): pass
        parses = self.parses()
        if len(parses) == 0: return None
        else: return parses[0]

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
        self._history.append( (self._stack[:], self._remaining_text[:]) )
        self._shift(self._stack, self._remaining_text)
        return 1
        
    def reduce(self, production=None):
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
        @rtype: C{list} of C{CFGProduction}
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
        @rtype: C{list} of C{TreeToken}
        """
        if len(self._remaining_text) != 0: return []
        if len(self._stack) != 1: return []
        if self._stack[0].node() != self._grammar.start().symbol():
            return []
        return self._stack
    
##//////////////////////////////////////////////////////
##  Stepping Recursive Descent Parser
##//////////////////////////////////////////////////////
class SteppingRecursiveDescentParser(RecursiveDescentParser):
    """
    A C{RecursiveDescentParser} that allows you to step through the
    parsing process, performing a single operation at a time.

    The C{initialize} method is used to start parsing a text.
    C{expand} expands the first element on the frontier using a single
    CFG production, and C{match} matches the first element on the
    frontier against the next text token. C{backtrack} undoes the most
    recent expand or match operation.  C{step} performs a single
    expand, match, or backtrack operation.  C{parses} returns the set
    of parses that have been found by the parser.
    
    @ivar _history: A list of C{(rtext, tree, frontier)} tripples,
        containing the previous states of the parser.  This history is
        used to implement the C{backtrack} operation.
    @ivar _tried_e: A record of all productions that have been tried
        for a given tree.  This record is used by C{expand} to perform
        the next untried production.
    @ivar _tried_m: A record of what tokens have been matched for a
        given tree.  This record is used by C{step} to decide whether
        or not to match a token.
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace
        self._rtext = None
        self._treetok = None
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []
    
    def parse_n(self, text, n=None):
        self.initialize(text)
        while self.step(): pass
        if n is None: return self.parses()
        else: return self.parses()[:n]
        
    def initialize(self, text):
        """
        Start parsing a given text.  This sets the parser's tree to
        the start symbol, its frontier to the root node, and its
        remaining text to C{text}.

        @param text: The text to start parsing.
        @type text: C{list} of C{Token}
        """
        self._rtext = text
        self._treetok = TreeToken(self._grammar.start().symbol())
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []
        if self._trace:
            self._trace_start(self._treetok, self._frontier, text)
    
    def remaining_text(self):
        """
        @return: The portion of the text that is not yet covered by the
            tree.
        @rtype: C{list} of C{Token}
        """
        return self._rtext

    def frontier(self):
        """
        @return: A list of the tree locations of all subtrees that
            have not yet been expanded, and all leaves that have not
            yet been matched.
        @rtype: C{list} of C{tuple} of C{int}
        """
        return self._frontier

    def tree(self):
        """
        @return: A partial structure for the text that is
            currently being parsed.  The elements specified by the
            frontier have not yet been expanded or matched.
        @rtype: C{TreeToken}
        """
        return self._treetok

    def step(self):
        """
        Perform a single parsing operation.  If an untried match is
        possible, then perform the match, and return the matched
        token.  If an untried expansion is possible, then perform the
        expansion, and return the production that it is based on.  If
        backtracking is possible, then backtrack, and return 1.
        Otherwise, return 0.

        @return: 0 if no operation was performed; a token if a match
            was performed; a production if an expansion was performed;
            and 1 if a backtrack operation was performed.
        @rtype: C{CFGProduction} or C{Token} or C{boolean}
        """
        # Try matching (if we haven't already)
        if self.untried_match():
            token = self.match()
            if token: return token

        # Try expanding.
        production = self.expand()
        if production: return production
            
        # Try backtracking
        if self.backtrack():
            self._trace_backtrack(self._treetok, self._frontier)
            return 1

        # Nothing left to do.
        return 0

    def expand(self, production=None):
        """
        Expand the first element of the frontier.  In particular, if
        the first element of the frontier is a subtree whose node type
        is equal to C{production}'s left hand side, then add a child
        to that subtree for each element of C{production}'s right hand
        side.  If C{production} is not specified, then use the first
        untried expandable production.  If all expandable productions
        have been tried, do nothing.

        @return: The production used to expand the frontier, if an
           expansion was performed.  If no expansion was performed,
           return C{None}
        @rtype: C{CFGProduction} or C{None}
        """
        # Make sure we *can* expand.
        if (len(self._frontier) == 0 or
            not isinstance(self._treetok[self._frontier[0]], TreeToken)):
            return None

        # If they didn't specify a production, check all untried ones.
        if production is None:
            productions = self.untried_expandable_productions()
        else: productions = [production]

        parses = []
        for prod in productions:
            # Record that we've tried this production now.
            self._tried_e.setdefault(self._treetok.type(), []).append(prod)

            # Try expanding.
            if self._expand(self._rtext, self._treetok, self._frontier, prod):
                return prod

        # We didn't expand anything.
        return None

    def match(self):
        """
        Match the first element of the frontier.  In particular, if
        the first element of the frontier has the same type as the
        next text token, then substitute the text token into the tree.

        @return: The token matched, if a match operation was
            performed.  If no match was performed, return C{None}
        @rtype: C{Token} or C{None}
        """
        # Record that we've tried matching this token.
        tok = self._rtext[0]
        self._tried_m.setdefault(self._treetok.type(), []).append(tok)

        # Make sure we *can* match.
        if (len(self._frontier) == 0 or
            isinstance(self._treetok[self._frontier[0]], TreeToken)):
            return None

        if self._match(self._rtext, self._treetok, self._frontier):
            # Return the token we just matched.
            return self._history[-1][0][0]
        else:
            return 0

    def backtrack(self):
        """
        Return the parser to its state before the most recent
        match or expand operation.  Calling C{undo} repeatedly return
        the parser to successively earlier states.  If no match or
        expand operations have been performed, C{undo} will make no
        changes.

        @return: true if an operation was successfully undone.
        @rtype: C{boolean}
        """
        if len(self._history) == 0: return 0
        (self._rtext, self._treetok, self._frontier) = self._history.pop()
        return 1

    def expandable_productions(self):
        """
        @return: A list of all the productions for which expansions
            are available for the current parser state.
        @rtype: C{list} of C{CFGProduction}
        """
        # Make sure we *can* expand.
        if (len(self._frontier) == 0 or
            not isinstance(self._treetok[self._frontier[0]], TreeToken)):
            return []

        return [p for p in self._grammar.productions()
                if p.lhs().symbol() == self._treetok[self._frontier[0]].node()]

    def untried_expandable_productions(self):
        """
        @return: A list of all the untried productions for which
            expansions are available for the current parser state.
        @rtype: C{list} of C{CFGProduction}
        """
        tried_expansions = self._tried_e.get(self._treetok.type(), [])
        return [p for p in self.expandable_productions()
                if p not in tried_expansions]

    def untried_match(self):
        """
        @return: Whether the first element of the frontier is a token
            that has not yet been matched.
        @rtype: C{boolean}
        """
        if len(self._rtext) == 0: return 0
        tried_matches = self._tried_m.get(self._treetok.type(), [])
        return (self._rtext[0] not in tried_matches)

    def currently_complete(self):
        """
        @return: Whether the parser's current state represents a
            complete parse.
        @rtype: C{boolean}
        """
        return (len(self._frontier) == 0 and len(self._rtext) == 0)

    def _parse(self, remaining_text, treetok, frontier):
        """
        A stub version of C{_parse} that sets the parsers current
        state to the given arguments.  In C{RecursiveDescentParser},
        the C{_parse} method is used to recursively continue parsing a
        text.  C{SteppingRecursiveDescentParser} overrides it to
        capture these recursive calls.  It records the parser's old
        state in the history (to allow for backtracking), and updates
        the parser's new state using the given arguments.  Finally, it
        returns C{[1]}, which is used by C{match} and C{expand} to
        detect whether their operations were successful.

        @return: C{[1]}
        @rtype: C{list} of C{int}
        """
        self._history.append( (self._rtext, self._treetok, self._frontier) )
        self._rtext = remaining_text
        self._treetok = treetok
        self._frontier = frontier

        # Is it a good parse?  If so, record it.
        if (len(frontier) == 0 and len(remaining_text) == 0):
            self._parses.append(treetok)
            self._trace_succeed(self._treetok, self._frontier)
        
        return [1]

    def parses(self):
        """
        @return: A list of the parses that have been found by this
            parser so far.
        @rtype: C{list} of C{TreeToken}
        """
        return self._parses

##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    productions = (
        # Syntactic Rules
        CFGProduction(S, NP, 'saw', NP),
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

    # tokenize the sentence
    from nltk.token import WSTokenizer
    tok_sent = WSTokenizer().tokenize(sent)

    parsers = [ShiftReduceParser(grammar),
               RecursiveDescentParser(grammar),
               SteppingShiftReduceParser(grammar),
               SteppingRecursiveDescentParser(grammar)]

    import sys
    print 'Choose a parser:'
    for i in range(len(parsers)):
        print '  %d. %s' % (i+1, parsers[i].__class__.__name__)
    print '=> ',
    try: parser = parsers[int(sys.stdin.readline())-1]
    except: print 'Bad input'; return
        
    parser.trace()
    for p in parser.parse_n(tok_sent): print p

if __name__ == '__main__': demo()
