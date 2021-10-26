# Natural Language Toolkit: Tree Transformations
#
# Copyright (C) 2005-2007 Oregon Graduate Institute
# Author: Nathan Bodenstab <bodenstab@cslu.ogi.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
A collection of methods for tree (grammar) transformations used
in parsing natural language.

Although many of these methods are technically grammar transformations
(ie. Chomsky Norm Form), when working with treebanks it is much more
natural to visualize these modifications in a tree structure.  Hence,
we will do all transformation directly to the tree itself.
Transforming the tree directly also allows us to do parent annotation.
A grammar can then be simply induced from the modified tree.

The following is a short tutorial on the available transformations.

 1. Chomsky Normal Form (binarization)

    It is well known that any grammar has a Chomsky Normal Form (CNF)
    equivalent grammar where CNF is defined by every production having
    either two non-terminals or one terminal on its right hand side.
    When we have hierarchically structured data (ie. a treebank), it is
    natural to view this in terms of productions where the root of every
    subtree is the head (left hand side) of the production and all of
    its children are the right hand side constituents.  In order to
    convert a tree into CNF, we simply need to ensure that every subtree
    has either two subtrees as children (binarization), or one leaf node
    (non-terminal).  In order to binarize a subtree with more than two
    children, we must introduce artificial nodes.

    There are two popular methods to convert a tree into CNF: left
    factoring and right factoring.  The following example demonstrates
    the difference between them.  Example::

     Original       Right-Factored     Left-Factored

          A              A                      A
        / | \          /   \                  /   \
       B  C  D   ==>  B    A|<C-D>   OR   A|<B-C>  D
                            /  \          /  \
                           C    D        B    C

 2. Parent Annotation

    In addition to binarizing the tree, there are two standard
    modifications to node labels we can do in the same traversal: parent
    annotation and Markov order-N smoothing (or sibling smoothing).

    The purpose of parent annotation is to refine the probabilities of
    productions by adding a small amount of context.  With this simple
    addition, a CYK (inside-outside, dynamic programming chart parse)
    can improve from 74% to 79% accuracy.  A natural generalization from
    parent annotation is to grandparent annotation and beyond.  The
    tradeoff becomes accuracy gain vs. computational complexity.  We
    must also keep in mind data sparcity issues.  Example::

     Original       Parent Annotation

          A                A^<?>
        / | \             /   \
       B  C  D   ==>  B^<A>    A|<C-D>^<?>     where ? is the
                                 /  \          parent of A
                             C^<A>   D^<A>


 3. Markov order-N smoothing

    Markov smoothing combats data sparcity issues as well as decreasing
    computational requirements by limiting the number of children
    included in artificial nodes.  In practice, most people use an order
    2 grammar.  Example::

      Original       No Smoothing       Markov order 1   Markov order 2   etc.

       __A__            A                      A                A
      / /|\ \         /   \                  /   \            /   \
     B C D E F  ==>  B    A|<C-D-E-F>  ==>  B   A|<C>  ==>   B  A|<C-D>
                            /   \               /   \            /   \
                           C    ...            C    ...         C    ...



    Annotation decisions can be thought about in the vertical direction
    (parent, grandparent, etc) and the horizontal direction (number of
    siblings to keep).  Parameters to the following functions specify
    these values.  For more information see:

    Dan Klein and Chris Manning (2003) "Accurate Unlexicalized
    Parsing", ACL-03.  https://www.aclweb.org/anthology/P03-1054

 4. Unary Collapsing

    Collapse unary productions (ie. subtrees with a single child) into a
    new non-terminal (Tree node).  This is useful when working with
    algorithms that do not allow unary productions, yet you do not wish
    to lose the parent information.  Example::

       A
       |
       B   ==>   A+B
      / \        / \
     C   D      C   D

"""

from nltk.internals import deprecated
from nltk.tree.transforms import chomsky_normal_form as cnf
from nltk.tree.transforms import collapse_unary as cu
from nltk.tree.transforms import un_chomsky_normal_form as ucnf


@deprecated("Import using `from nltk.tree import chomsky_normal_form` instead.")
def chomsky_normal_form(
    tree, factor="right", horzMarkov=None, vertMarkov=0, childChar="|", parentChar="^"
):
    return cnf(
        tree,
        factor=factor,
        horzMarkov=horzMarkov,
        vertMarkov=vertMarkov,
        childChar=childChar,
        parentChar=parentChar,
    )


@deprecated("Import using `from nltk.tree import un_chomsky_normal_form` instead.")
def un_chomsky_normal_form(
    tree, expandUnary=True, childChar="|", parentChar="^", unaryChar="+"
):
    return ucnf(
        tree,
        expandUnary=expandUnary,
        childChar=childChar,
        parentChar=parentChar,
        unaryChar=unaryChar,
    )


@deprecated("Import using `from nltk.tree import collapse_unary` instead.")
def collapse_unary(tree, collapsePOS=False, collapseRoot=False, joinChar="+"):
    """
    Collapse subtrees with a single child (ie. unary productions)
    into a new non-terminal (Tree node) joined by 'joinChar'.
    This is useful when working with algorithms that do not allow
    unary productions, and completely removing the unary productions
    would require loss of useful information.  The Tree is modified
    directly (since it is passed by reference) and no value is returned.

    :param tree: The Tree to be collapsed
    :type  tree: Tree
    :param collapsePOS: 'False' (default) will not collapse the parent of leaf nodes (ie.
                        Part-of-Speech tags) since they are always unary productions
    :type  collapsePOS: bool
    :param collapseRoot: 'False' (default) will not modify the root production
                         if it is unary.  For the Penn WSJ treebank corpus, this corresponds
                         to the TOP -> productions.
    :type collapseRoot: bool
    :param joinChar: A string used to connect collapsed node values (default = "+")
    :type  joinChar: str
    """

    return cu(
        tree, collapsePOS=collapsePOS, collapseRoot=collapseRoot, joinChar=joinChar
    )


__all__ = ["chomsky_normal_form", "un_chomsky_normal_form", "collapse_unary"]
