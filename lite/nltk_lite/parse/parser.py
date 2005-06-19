# Natural Language Toolkit: Parsers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for producing tree structures that represent
the internal organization of a text.  This task is known as X{parsing}
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

@group Interfaces: ParserI
@group Parsers: ShiftReduceParser, SteppingShiftReduceParser,
       RecursiveDescentParser, SteppingRecursiveDescentParser
@sort: ParserI, ShiftReduceParser, SteppingShiftReduceParser,
       RecursiveDescentParser, SteppingRecursiveDescentParser, 
       demo, chart, chunk, probabilistic
@see: C{nltk.cfg}
"""

from cfg import Nonterminal, CFG, CFGProduction, nonterminals
from tree import *
from nltk_lite import tokenize
from types import *

##//////////////////////////////////////////////////////
##  Parser Interface
##//////////////////////////////////////////////////////
class ParserI:
    """
    A processing class for deriving trees that represent possible
    structures for a sequence of tokens.  These tree structures are
    known as X{parses}.  Typically, parsers are used to derive syntax
    trees for sentences.  But parsers can also be used to derive other
    kinds of tree structure, such as morphological trees and discourse
    structures.
    
    """
    def parse(self, sent):
        """
        Derive a parse tree that represents the structure of the given
        sentences words, and return a Tree.  If no parse is found,
        then output C{None}.  If multiple parses are found, then
        output the best parse.

        The parsed trees derive a structure for the subtokens, but do
        not modify them.  In particular, the leaves of the subtree
        should be equal to the list of subtokens.

        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        """
        raise NotImplementedError()

    def get_parse(self, sent):
        """
        @return: A parse tree that represents the structure of the
        sentence.  If no parse is found, then return C{None}.

        @rtype: L{Tree}
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        """

    def get_parse_list(self, sent):
        """
        @return: A list of the parse trees for the sentence.  When possible,
        this list should be sorted from most likely to least likely.

        @rtype: C{list} of L{Tree}
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        """

    def get_parse_probs(self, sent):
        """
        @return: A probability distribution over the parse trees for the sentence.

        @rtype: L{ProbDistI}
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        """

    def get_parse_list(self, sent):
        """
        @return: A dictionary mapping from the parse trees for the
        sentence to numeric scores.

        @rtype: C{dict}
        @param sent: The sentence to be parsed
        @type sent: L{list} of L{string}
        """

##//////////////////////////////////////////////////////
##  Abstract Base Class for Parsers
##//////////////////////////////////////////////////////
class AbstractParser(ParserI):
    """
    An abstract base class for parsers.  C{AbstractParser} provides
    a default implementation for:

      - L{parse} (based on C{get_parse})
      - L{get_parse_list} (based on C{get_parse})
      - L{get_parse} (based on C{get_parse_list})

    Note that subclasses must override either C{get_parse} or
    C{get_parse_list} (or both), to avoid infinite recursion.
    """
    def __init__(self):
        """
        Construct a new parser.
        """
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractParser:
            raise AssertionError, "Abstract classes can't be instantiated"

    def parse(self, token):
        return self.get_parse(token)

    def grammar(self):
        return self._grammar

    def get_parse(self, token):
        trees = self.get_parse_list(token)
        if len(trees) == 0: return None
        else: return trees[0]
    
    def get_parse_list(self, token):
        tree = self.get_parse(token)
        if tree is None: return []
        else: return [tree]

##//////////////////////////////////////////////////////
##  Shift/Reduce Parser
##//////////////////////////////////////////////////////
class ShiftReduceParser(AbstractParser):
    """
    A simple bottom-up CFG parser that uses two operations, "shift"
    and "reduce", to find a single parse for a text.

    C{ShiftReduceParser} maintains a stack, which records the
    structure of a portion of the text.  This stack is a list of
    C{Token}s and C{Tree}s that collectively cover a portion of
    the text.  For example, while parsing the sentence "the dog saw
    the man" with a typical grammar, C{ShiftReduceParser} will produce
    the following stack, which covers "the dog saw"::

       [(NP: (Det: <'the'>) (N: <'dog'>)), (V: <'saw'>)]

    C{ShiftReduceParser} attempts to extend the stack to cover the
    entire text, and to combine the stack elements into a single tree,
    producing a complete parse for the sentence.

    Initially, the stack is empty.  It is extended to cover the text,
    from left to right, by repeatedly applying two operations:

      - X{shift} moves a token from the beginning of the text to the
        end of the stack.
      - X{reduce} uses a CFG production to combine the rightmost stack
        elements into a single C{Tree}.

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

    @see: C{nltk.cfg}
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
        AbstractParser.__init__(self)
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

        @type stack: C{list} of C{Token} and C{Tree}
        @param stack: A list of C{Token}s and C{Tree}s, encoding
            the structure of the text that has been parsed so far.
        @type remaining_text: C{list} of C{Token}
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
            matches any C{Token} whose type is equal to the terminal.
        @type rhs: C{list} of (terminal and C{Nonterminal})
        @param rhs: The right hand side of a CFG production.
        @type rightmost_stack: C{list} of (C{Token} and C{Tree})
        @param rightmost_stack: The rightmost elements of the parser's
            stack.
        """
        
        if len(rightmost_stack) != len(rhs): return 0
        for i in range(len(rightmost_stack)):
            if isinstance(rightmost_stack[i], Tree):
                if not isinstance(rhs[i], Nonterminal): return 0
                if rightmost_stack[i].node != rhs[i].symbol(): return 0
            else:
                if isinstance(rhs[i], Nonterminal): return 0
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

        @rtype: C{CFGProduction} or C{None}
        @return: If a reduction is performed, then return the CFG
            production that the reduction is based on; otherwise,
            return false.
        @type stack: C{list} of C{Token} and C{Tree}
        @param stack: A list of C{Token}s and C{Tree}s, encoding
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
                str += `Nonterminal(elt.node)` + ' '
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
##  Recursive Descent Parser
##//////////////////////////////////////////////////////
class RecursiveDescentParser(AbstractParser):
    """
    A simple top-down CFG parser that parses texts by recursively
    expanding the fringe of a C{Tree}, and matching it against a
    text.

    C{RecursiveDescentParser} uses a list of tree locations called a
    X{frontier} to remember which subtrees have not yet been expanded
    and which leaves have not yet been matched against the text.  Each
    tree location consists of a list of child indices specifying the
    path from the root of the tree to a subtree or a leaf; see the
    reference documentation for C{Tree} for more information
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
        self._grammar = grammar
        self._trace = trace
        AbstractParser.__init__(self)

    def get_parse_list(self, tokens):
        # Inherit docs from ParserI

        # Start a recursive descent parse, with an initial tree
        # containing just the start symbol.
        start = self._grammar.start().symbol()
        initial_tree = Tree(start, [])
        frontier = [()]
        if self._trace:
            self._trace_start(initial_tree, frontier, tokens)
        parses = self._parse(tokens, initial_tree, frontier)

        # Return the parses.
        return parses

    def _parse(self, remaining_text, tree, frontier):
        """
        Recursively expand and match each elements of C{tree}
        specified by C{frontier}, to cover C{remaining_text}.  Return
        a list of all parses found.

        @return: A list of all parses that can be generated by
            matching and expanding the elements of C{tree}
            specified by C{frontier}.
        @rtype: C{list} of C{Tree}
        @type tree: C{Tree}
        @param tree: A partial structure for the text that is
            currently being parsed.  The elements of C{tree}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type remaining_text: C{list} of C{Token}s
        @param remaining_text: The portion of the text that is not yet
            covered by C{tree}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{tree} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.  This list sorted
            in left-to-right order of location within the tree.
        """
        # If the tree covers the text, and there's nothing left to
        # expand, then we've found a complete parse; return it.
        if len(remaining_text) == 0 and len(frontier) == 0:
            if self._trace:
                self._trace_succeed(tree, frontier)
            return [tree]

        # If there's still text, but nothing left to expand, we failed.
        elif len(frontier) == 0:
            if self._trace:
                self._trace_backtrack(tree, frontier)
            return []

        # If the next element on the frontier is a tree, expand it.
        elif isinstance(tree[frontier[0]], Tree):
            return self._expand(remaining_text, tree, frontier)

        # If the next element on the frontier is a token, match it.
        else:
            return self._match(remaining_text, tree, frontier)

    def _match(self, rtext, tree, frontier):
        """
        @rtype: C{list} of C{Tree}
        @return: a list of all parses that can be generated by
            matching the first element of C{frontier} against the
            first token in C{rtext}.  In particular, if the first
            element of C{frontier} has the same type as the first
            token in C{rtext}, then substitute the token into
            C{tree}; and return all parses that can be generated by
            matching and expanding the remaining elements of
            C{frontier}.  If the first element of C{frontier} does not
            have the same type as the first token in C{rtext}, then
            return empty list.

        @type tree: C{Tree}
        @param tree: A partial structure for the text that is
            currently being parsed.  The elements of C{tree}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type rtext: C{list} of C{Token}s
        @param rtext: The portion of the text that is not yet
            covered by C{tree}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{tree} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """

        tree_leaf = tree[frontier[0]]
        if (len(rtext) > 0 and tree_leaf == rtext[0]):
            # If it's a terminal that matches text[0], then substitute
            # in the token, and continue parsing.
            newtree = tree.copy(deep=True)
            newtree[frontier[0]] = rtext[0]
            if self._trace:
                self._trace_match(newtree, frontier[1:], rtext[0])
            return self._parse(rtext[1:], newtree, frontier[1:])
        else:
            # If it's a non-matching terminal, fail.
            if self._trace:
                self._trace_backtrack(tree, frontier, rtext[:1])
            return []

    def _expand(self, remaining_text, tree, frontier, production=None):
        """
        @rtype: C{list} of C{Tree}
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
            
        @type tree: C{Tree}
        @param tree: A partial structure for the text that is
            currently being parsed.  The elements of C{tree}
            that are specified by C{frontier} have not yet been
            expanded or matched.
        @type remaining_text: C{list} of C{Token}s
        @param remaining_text: The portion of the text that is not yet
            covered by C{tree}.
        @type frontier: C{list} of C{tuple} of C{int}
        @param frontier: A list of the locations within C{tree} of
            all subtrees that have not yet been expanded, and all
            leaves that have not yet been matched.
        """
        
        if production is None: productions = self._grammar.productions()
        else: productions = [production]
        
        parses = []
        for production in productions:
            lhs = production.lhs().symbol()
            if lhs == tree[frontier[0]].node:
                subtree = self._production_to_tree(production)
                if frontier[0] == ():
                    newtree = subtree
                else:
                    newtree = tree.copy(deep=True)
                    newtree[frontier[0]] = subtree
                new_frontier = [frontier[0]+(i,) for i in
                                range(len(production.rhs()))]
                if self._trace:
                    self._trace_expand(newtree, new_frontier, production)
                parses += self._parse(remaining_text, newtree,
                                      new_frontier + frontier[1:])
        return parses

    def _production_to_tree(self, production):
        """
        @rtype: C{Tree}
        @return: The C{Tree} that is licensed by C{production}.
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
                children.append(Tree(elt.symbol(), []))
            else:
                # This will be matched.
                children.append(elt)
        return Tree(production.lhs().symbol(), children)
    
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

    def _trace_fringe(self, tree, treeloc=None):
        """
        Print trace output displaying the fringe of C{tree}.  The
        fringe of C{tree} consists of all of its leaves and all of
        its childless subtrees.

        @rtype: C{None}
        """
        
        if treeloc == (): print "*",
        if isinstance(tree, Tree):
            if len(tree) == 0: print `Nonterminal(tree.node)`,
            for i in range(len(tree)):
                if treeloc is not None and i == treeloc[0]:
                    self._trace_fringe(tree[i], treeloc[1:])
                else:
                    self._trace_fringe(tree[i])
        else:
            print `tree`,

    def _trace_tree(self, tree, frontier, operation):
        """
        Print trace output displaying the parser's current state.

        @param operation: A character identifying the operation that
            generated the current state.
        @rtype: C{None}
        """
        if self._trace == 2: print '  %c [' % operation,
        else: print '    [',
        if len(frontier) > 0: self._trace_fringe(tree, frontier[0])
        else: self._trace_fringe(tree)
        print ']'

    def _trace_start(self, tree, frontier, text):
        print 'Parsing %r' % ' '.join(text)
        if self._trace > 2: print 'Start:'
        if self._trace > 1: self._trace_tree(tree, frontier, ' ')
        
    def _trace_expand(self, tree, frontier, production):
        if self._trace > 2: print 'Expand: %s' % production
        if self._trace > 1: self._trace_tree(tree, frontier, 'E')

    def _trace_match(self, tree, frontier, tok):
        if self._trace > 2: print 'Match: %r' % tok
        if self._trace > 1: self._trace_tree(tree, frontier, 'M')

    def _trace_succeed(self, tree, frontier):
        if self._trace > 2: print 'GOOD PARSE:'
        if self._trace == 1: print 'Found a parse:\n%s' % tree
        if self._trace > 1: self._trace_tree(tree, frontier, '+')

    def _trace_backtrack(self, tree, frontier, toks=None):
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
    @see: C{nltk.cfg}
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace
        self._stack = None
        self._remaining_text = None
        self._history = []
        AbstractParser.__init__(self)

    def get_parse_list(self, token):
        self.initialize(token)
        while self.step(): pass
        
        return self.parses()

    def stack(self):
        """
        @return: The parser's stack.
        @rtype: C{list} of C{Token} and C{Tree}
        """
        return self._stack

    def remaining_text(self):
        """
        @return: The portion of the text that is not yet covered by the
            stack.
        @rtype: C{list} of C{Token}
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
        @rtype: C{CFGProduction} or C{boolean}
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
        
        @rtype: C{CFGProduction} or C{None}
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
        @rtype: C{list} of C{Tree}
        """
        if len(self._remaining_text) != 0: return []
        if len(self._stack) != 1: return []
        if self._stack[0].node != self._grammar.start().symbol():
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
    @see: C{nltk.cfg}
    """
    def __init__(self, grammar, trace=0):
        self._grammar = grammar
        self._trace = trace
        self._rtext = None
        self._tree = None
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []
        AbstractParser.__init__(self)

    # [XX] TEMPORARY HACK WARNING!  This should be replaced with
    # something nicer when we get the chance.
    def _freeze(self, tree):
        c = tree.copy()
#        for pos in c.treepositions('leaves'):
#            c[pos] = c[pos].freeze()
        return ImmutableTree.convert(c)
    
    def get_parse_list(self, tokens):
        self.initialize(tokens)
        while self.step() is not None: pass

        return self.parses()
        
    def initialize(self, tokens):
        """
        Start parsing a given text.  This sets the parser's tree to
        the start symbol, its frontier to the root node, and its
        remaining text to C{token['SUBTOKENS']}.
        """

        self._rtext = tokens
        start = self._grammar.start().symbol()
        self._tree = Tree(start, [])
        self._frontier = [()]
        self._tried_e = {}
        self._tried_m = {}
        self._history = []
        self._parses = []
        if self._trace:
            self._trace_start(self._tree, self._frontier, self._rtext)
    
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
        @rtype: C{Tree}
        """
        return self._tree

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
            if token is not None: return token

        # Try expanding.
        production = self.expand()
        if production is not None: return production
            
        # Try backtracking
        if self.backtrack():
            self._trace_backtrack(self._tree, self._frontier)
            return 1

        # Nothing left to do.
        return None

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
           return C{None}.
        @rtype: C{CFGProduction} or C{None}
        """

        # Make sure we *can* expand.
        if len(self._frontier) == 0:
            return None
        if not isinstance(self._tree[self._frontier[0]], Tree):
            return None

        # If they didn't specify a production, check all untried ones.
        if production is None:
            productions = self.untried_expandable_productions()
        else: productions = [production]

        parses = []
        for prod in productions:
            # Record that we've tried this production now.
            self._tried_e.setdefault(self._freeze(self._tree), []).append(prod)

            # Try expanding.
            if self._expand(self._rtext, self._tree, self._frontier, prod):
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
        self._tried_m.setdefault(self._freeze(self._tree), []).append(tok)

        # Make sure we *can* match.
        if len(self._frontier) == 0:
            return None
        if isinstance(self._tree[self._frontier[0]], Tree):
            return None

        if self._match(self._rtext, self._tree, self._frontier):
            # Return the token we just matched.
            return self._history[-1][0][0]
        else:
            return None

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
        (self._rtext, self._tree, self._frontier) = self._history.pop()
        return 1

    def expandable_productions(self):
        """
        @return: A list of all the productions for which expansions
            are available for the current parser state.
        @rtype: C{list} of C{CFGProduction}
        """
        # Make sure we *can* expand.
        if len(self._frontier) == 0: return []
        frontier_child = self._tree[self._frontier[0]]
        if (len(self._frontier) == 0 or
            not isinstance(frontier_child, Tree)):
            return []

        return [p for p in self._grammar.productions()
                if p.lhs().symbol() == frontier_child.node]

    def untried_expandable_productions(self):
        """
        @return: A list of all the untried productions for which
            expansions are available for the current parser state.
        @rtype: C{list} of C{CFGProduction}
        """
        
        tried_expansions = self._tried_e.get(self._freeze(self._tree), [])
        return [p for p in self.expandable_productions()
                if p not in tried_expansions]

    def untried_match(self):
        """
        @return: Whether the first element of the frontier is a token
            that has not yet been matched.
        @rtype: C{boolean}
        """
        
        if len(self._rtext) == 0: return 0
        tried_matches = self._tried_m.get(self._freeze(self._tree), [])
        return (self._rtext[0] not in tried_matches)

    def currently_complete(self):
        """
        @return: Whether the parser's current state represents a
            complete parse.
        @rtype: C{boolean}
        """
        return (len(self._frontier) == 0 and len(self._rtext) == 0)

    def _parse(self, remaining_text, tree, frontier):
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
        self._history.append( (self._rtext, self._tree, self._frontier) )
        self._rtext = remaining_text
        self._tree = tree
        self._frontier = frontier

        # Is it a good parse?  If so, record it.
        if (len(frontier) == 0 and len(remaining_text) == 0):
            self._parses.append(tree)
            self._trace_succeed(self._tree, self._frontier)
        
        return [1]

    def parses(self):
        """
        @return: A list of the parses that have been found by this
            parser so far.
        @rtype: C{list} of C{Tree}
        """
        return self._parses

##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration of the parsers defined by nltk.parser.  The user
    is prompted to select which parser to run, and that parser is run
    on an example sentence with a simple grammar.
    """
    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define a grammar.
    productions = (
        # Syntactic Productions
        CFGProduction(S, [NP, 'saw', NP]),
        CFGProduction(S, [NP, VP]),
        CFGProduction(NP, [Det, N]),
        CFGProduction(VP, [V, NP, PP]),
        CFGProduction(NP, [Det, N, PP]),
        CFGProduction(PP, [P, NP]),

        # Lexical Productions
        CFGProduction(NP, ['I']),   CFGProduction(Det, ['the']),
        CFGProduction(Det, ['a']),  CFGProduction(N, ['man']),
        CFGProduction(V, ['saw']),  CFGProduction(P, ['in']),
        CFGProduction(P, ['with']), CFGProduction(N, ['park']),
        CFGProduction(N, ['dog']),  CFGProduction(N, ['telescope'])
        )
    grammar = CFG(S, productions)

    # Tokenize a sample sentence.
    sent = list(tokenize.whitespace('I saw a man in the park'))

    # Define a list of parsers.
    parsers = [ShiftReduceParser(grammar),
               RecursiveDescentParser(grammar),
               SteppingShiftReduceParser(grammar),
               SteppingRecursiveDescentParser(grammar)]

    # Ask the user to choose a parser.
    import sys
    print 'Choose a parser:'
    for i in range(len(parsers)):
        print '  %d. %s' % (i+1, parsers[i].__class__.__name__)
    print '=> ',
    try: parser = parsers[int(sys.stdin.readline())-1]
    except: print 'Bad input'; return

    # Run the parser.
    parser.trace()
    for p in parser.get_parse_list(sent):
        print p

if __name__ == '__main__': demo()
