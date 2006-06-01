# Contributed by Peter Wang

from nltk_lite import tokenize
from nltk_lite.contrib.featurechart import *
from nltk_lite.contrib.grammarfile import GrammarFile
from nltk_lite.draw.tree import draw_trees
from nltk_lite.parse import bracket_parse
from nltk_lite.parse import tree

"""
An implementation of the Hole Semantics model, following Blackburn and Bos,
Representation and Inference for Natural Language (CSLI, 2005).

The semantic representations are built by the grammar hole.cfg.
This module contains driver code to read in sentences and parse them
according to a hole semantics grammar.

After parsing, the semantic representation is in the form of an underspecified
representation that is not easy to read.  We use a "plugging" algorithm to
convert that representation into first-order logic formulas.  These can be
displayed textually or graphically.
"""

# Note that in this code there may be multiple types of trees being referred to:
#
# 1. parse trees
# 2. the underspecified representation
# 3. first-order logic formula trees
# 4. the search space when plugging (search tree)
#

class HoleSemantics:
    """
    This class holds the broken-down components of a hole semantics, i.e. it
    extracts the holes, labels, logic formula fragments and constraints out of
    a big conjunction of such as produced by the hole semantics grammar.  It
    then provides some operations on the semantics dealing with holes, labels
    and finding legal ways to plug holes with labels.
    """
    def __init__(self, usr):
        """
        Constructor.  `usr' is a tree of nodes that can take the forms:

            (and t t')
            (hole v)
            (label v)
            (: v phi)
            (leq v v)

        where
            t, t' are subtrees
            v is a variable
            phi is a formula fragment
        """
        self.holes = set()      # set of variables which were asserted hole(x)
        self.labels = set()     # set of variables which were asserted label(x)
        self.fragments = {}     # mapping of label -> formula fragment
        self.constraints = set() # set of Constraints
        self._break_down(usr)
        self.top_most_labels = self._find_top_most_labels()
        self.top_hole = self._find_top_hole()

    def is_label(self, x):
        """Return true if x is a label in this semantic representation."""
        return x in self.labels

    def is_hole(self, x):
        """Return true if x is a hole in this semantic representation."""
        return x in self.holes

    def is_node(self, x):
        """
        Return true if x is a node (label or hole) in this semantic
        representation.
        """
        return self.is_label(x) or self.is_hole(x)

    def _break_down(self, usr):
        """
        Extract holes, labels, formula fragments and constraints from the hole
        semantics underspecified representation (USR).
        """
        assert isinstance(usr, Tree)
        
        # (and X Y)
        if usr.node == 'and':
            self._break_down(usr[0])
            self._break_down(usr[1])

        # (hole H) -- H is a hole
        elif usr.node == 'hole':
            hole = usr[0]
            self.holes.add(hole)
            assert not self.is_label(hole)

        # (label L) -- L is a label
        elif usr.node == 'label':
            label = usr[0]
            self.labels.add(label)
            assert not self.is_hole(label)

        # (: L F)  -- a formula fragment F with label L
        elif usr.node == ':':
            label = usr[0]
            phi = usr[1]
            assert not self.fragments.has_key(label)
            self.fragments[label] = phi

        # (leq L N) -- a constraint between the label L and node N
        elif usr.node == 'leq':
            lhs = usr[0]
            rhs = usr[1]
            self.constraints.add(Constraint(lhs, rhs))

        else:
            raise ValueError(usr.node)

    def _find_top_most_labels(self):
        """
        Return the set of labels which are not referenced directly as part of
        another formula fragment.  These will be the top-most labels for the
        subtree that they are part of.
        """
        top_most_labels = self.labels.copy()
        for f in self.fragments.itervalues():
            for arg in f:
                if self.is_label(arg):
                    top_most_labels.discard(arg)
        return top_most_labels

    def _find_top_hole(self):
        """
        Return the hole that will be the top of the formula tree.
        """
        top_hole = self.holes.copy()
        for f in self.fragments.itervalues():
            for arg in f:
                if self.is_hole(arg):
                    top_hole.discard(arg)
        assert len(top_hole) == 1   # it must be unique
        return top_hole.pop()

    def pluggings(self):
        """
        Calculate and return all the legal pluggings (mappings of labels to
        holes) of this semantics given the constraints.
        """
        record = []
        self._plug_nodes([(self.top_hole, [])], self.top_most_labels, {},
                         record)
        return record

    def _plug_nodes(self, queue, potential_labels, plug_acc, record):
        """
        Plug the nodes in `queue' with the labels in `potential_labels'.

        Each element of `queue' is a tuple of the node to plug and the list of
        ancestor holes from the root of the graph to that node.

        `potential_labels' is a set of the labels which are still available for
        plugging.

        `plug_acc' is the incomplete mapping of holes to labels made on the
        current branch of the search tree so far.

        `record' is a list of all the complete pluggings that we have found in
        total so far.  It is the only parameter that is destructively updated.
        """
        assert queue != []
        (node, ancestors) = queue[0]
        if self.is_hole(node):
            # The node is a hole, try to plug it.
            self._plug_hole(node, ancestors, queue[1:], potential_labels,
                            plug_acc, record)
        else:
            assert self.is_label(node)
            # The node is a label.  Replace it in the queue by the holes and
            # labels in the formula fragment named by that label.
            phi = self.fragments[node]
            head = [(a, ancestors) for a in phi if self.is_node(a)]
            self._plug_nodes(head + queue[1:], potential_labels,
                             plug_acc, record)

    def _plug_hole(self, hole, ancestors0, queue, potential_labels0,
                   plug_acc0, record):
        """
        Try all possible ways of plugging a single hole.
        See _plug_nodes for the meanings of the parameters.
        """
        # Add the current hole we're trying to plug into the list of ancestors.
        assert hole not in ancestors0
        ancestors = [hole] + ancestors0

        # Try each potential label in this hole in turn.
        for l in potential_labels0:
            # Is the label valid in this hole?
            if self._violates_constraints(l, ancestors):
                continue

            plug_acc = plug_acc0.copy()
            plug_acc[hole] = l
            potential_labels = potential_labels0.copy()
            potential_labels.remove(l)

            if len(potential_labels) == 0:
                # No more potential labels.  That must mean all the holes have
                # been filled so we have found a legal plugging so remember it.
                #
                # Note that the queue might not be empty because there might
                # be labels on there that point to formula fragments with
                # no holes in them.  _sanity_check_plugging will make sure
                # all holes are filled.
                self._sanity_check_plugging(plug_acc, self.top_hole, [])
                record.append(plug_acc)
            else:
                # Recursively try to fill in the rest of the holes in the
                # queue.  The label we just plugged into the hole could have
                # holes of its own so at the end of the queue.  Putting it on
                # the end of the queue gives us a breadth-first search, so that
                # all the holes at level i of the formula tree are filled
                # before filling level i+1.
                # A depth-first search would work as well since the trees must
                # be finite but the bookkeeping would be harder.
                self._plug_nodes(queue + [(l, ancestors)], potential_labels,
                                 plug_acc, record)

    def _violates_constraints(self, label, ancestors):
        """
        Return True if the `label' cannot be placed underneath the holes given
        by the set `ancestors' because it would violate the constraints imposed
        on it.
        """
        for c in self.constraints:
            if c.lhs == label:
                if c.rhs not in ancestors:
                    return True
        return False

    def _sanity_check_plugging(self, plugging, node, ancestors):
        """
        Make sure that a given plugging is legal.  We recursively go through
        each node and make sure that no constraints are violated.
        We also check that all holes have been filled.
        """
        if self.is_hole(node):
            ancestors = [node] + ancestors
            label = plugging[node]
        else:
            label = node
        assert self.is_label(label)
        for c in self.constraints:
            if c.lhs == label:
                assert c.rhs in ancestors
        phi = self.fragments[label]
        for arg in phi:
            if self.is_node(arg):
                self._sanity_check_plugging(plugging, arg, [label] + ancestors)

    def formula_tree(self, plugging):
        """
        Return the first-order logic formula tree for this underspecified
        representation using the plugging given.
        """
        return self._formula_tree(plugging, self.top_hole)

    def _formula_tree(self, plugging, node):
        if node in plugging:
            return self._formula_tree(plugging, plugging[node])
        elif self.fragments.has_key(node):
            frag = self.fragments[node]
            children = [self._formula_tree(plugging, arg) for arg in frag]
            return FOLTree(frag.node, children)
        else:
            return node


class Constraint:
    """
    This class represents a constraint of the form (L =< N),
    where L is a label and N is a node (a label or a hole).
    """
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs
    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return self.lhs == other.lhs and self.rhs == other.rhs
        else:
            return False
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(repr(self))
    def __repr__(self):
        return '(%s =< %s)' % (self.lhs, self.rhs)


class FOLTree(Tree):
    """
    A Tree for first-order logic formulas that prints differently.  Nodes with
    operator names are printed in infix.  Nodes which have unrecognised names
    are assumed to be predicates.
    """
    def __str__(self):
        if self.node == 'ALL':
            var = self[0]
            st = self[1]
            return '(ALL %s %s)' % (var, st)
        elif self.node == 'SOME':
            var = self[0]
            st = self[1]
            return '(SOME %s %s)' % (var, st)
        elif self.node == 'AND':
            return '(%s /\ %s)' % (self[0], self[1])
        elif self.node == 'IMP':
            return '(%s -> %s)' % (self[0], self[1])
        # add more operators here
        else:
            # otherwise treat it as a predicate with arguments
            args = ', '.join([str(arg) for arg in self])
            return '%s(%s)' % (self.node, args)


def main():
    import sys
    from optparse import OptionParser, OptionGroup
    usage = """%%prog [options] [grammar_file]""" % globals()

    opts = OptionParser(usage=usage)
    opts.add_option("-c", "--components",
	action="store_true", dest="show_components", default=0,
	help="show hole semantics components")
    opts.add_option("-r", "--raw",
	action="store_true", dest="show_raw", default=0,
	help="show the raw hole semantics expression")
    opts.add_option("-d", "--drawtrees",
	action="store_true", dest="draw_trees", default=0,
	help="show formula trees in a GUI window")
    opts.add_option("-v", "--verbose",
	action="count", dest="verbosity", default=0,
	help="show more information during parse")

    (options, args) = opts.parse_args()

    if len(args) > 0:
        filename = args[0]
    else:
        filename = 'hole.cfg'

    print 'Reading grammar file', filename
    grammar = GrammarFile.read_file(filename)
    parser = grammar.earley_parser(trace=options.verbosity)

    # Prompt the user for a sentence.
    print 'Sentence: ',
    line = sys.stdin.readline()[:-1]

    # Parse the sentence.
    tokens = list(tokenize.whitespace(line))
    trees = parser.get_parse_list(tokens)
    print 'Got %d different parses' % len(trees)

    for tree in trees:
        # Get the semantic feature from the top of the parse tree.
        sem = tree[0].node['sem'].simplify()

        # Skolemise away all quantifiers.  All variables become unique.
        sem = sem.skolemise()

        # Reparse the semantic representation from its bracketed string format.
        # I find this uniform structure easier to handle.  It also makes the
        # code mostly independent of the lambda calculus classes.
        usr = bracket_parse(str(sem))

        # Break the hole semantics representation down into its components
        # i.e. holes, labels, formula fragments and constraints.
        hole_sem = HoleSemantics(usr)

        # Maybe print the raw semantic representation.
        if options.show_raw:
            print
            print 'Raw expression'
            print usr

        # Maybe show the details of the semantic representation.
        if options.show_components:
            print
            print 'Holes:       ', hole_sem.holes
            print 'Labels:      ', hole_sem.labels
            print 'Constraints: ', hole_sem.constraints
            print 'Top hole:    ', hole_sem.top_hole
            print 'Top labels:  ', hole_sem.top_most_labels
            print 'Fragments:'
            for (l,f) in hole_sem.fragments.items():
                print '\t%s: %s' % (l, f)

        # Find all the possible ways to plug the formulas together.
        pluggings = hole_sem.pluggings()

        # Build FOL formula trees using the pluggings.
        trees = map(hole_sem.formula_tree, pluggings)

        # Print out the formulas in a textual format.
        n = 1
        for tree in trees:
            print
            print '%d. %s' % (n, tree)
            n += 1

        # Maybe draw the formulas as trees.
        if options.draw_trees:
            draw_trees(*trees)

        print
        print 'Done.'

if __name__ == '__main__':
    main()

