# Natural Language Toolkit: Test Code for Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.tree}.

@todo: Test L{nltk.tree.ProbabilisticTreeToken}
@todo: Test L{nltk.tree.parse_treebank}
"""

from nltk.tree import *
from nltk.tokenizer import WhitespaceTokenizer
from nltk.tokenreader import TreebankTokenReader

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////


def test_Tree(): r"""
Unit test cases for L{tree.Tree}.

C{Trees} are used to encode hierarchical structures.  Each C{Tree}
object encodes a single grouping in the hierarchy.  A C{Tree} is
actually a specialized subclass of C{list} that:

  - Adds a new attribute, the C{node} value.

  - Conceptually divides its children into two groups: C{Tree}
    children (called \"subtrees\") and non-C{Tree} children (called
    \"leaves\").

  - Adds several tree-specific operations.

  - Adds a new tree-specific indexing scheme.

Trees are created from a node and a list (or any iterable) of
children:

    >>> Tree(1, [2, 3, 4])
    (1: 2 3 4)
    >>> Tree('S', [Tree('NP', ['I']), 
    ...            Tree('VP', [Tree('V', ['saw']),
    ...                        Tree('NP', ['him'])])])
    (S: (NP: 'I') (VP: (V: 'saw') (NP: 'him')))

One exception to \"any iterable\": in order to avoid confusion,
strings are I{not} accepted as children lists:

    >>> Tree('NP', 'Bob')
    Traceback (most recent call last):
      ...
    TypeError: children should be a list, not a string

A single level can contain both leaves and subtrees:

    >>> Tree(1, [2, Tree(3, [4]), 5])
    (1: 2 (3: 4) 5)

Some trees to run tests on:

    >>> dp1 = Tree('dp', [Tree('d', ['the']), Tree('np', ['dog'])])
    >>> dp2 = Tree('dp', [Tree('d', ['the']), Tree('np', ['cat'])])
    >>> vp = Tree('vp', [Tree('v', ['chased']), dp2])
    >>> tree = Tree('s', [dp1, vp])
    >>> print tree
    (s:
      (dp: (d: the) (np: dog))
      (vp: (v: chased) (dp: (d: the) (np: cat))))

The node value is stored using the C{node} attribute:

    >>> dp1.node, dp2.node, vp.node, tree.node
    ('dp', 'dp', 'vp', 's')

This attribute can be modified directly:

    >>> dp1.node = 'np'
    >>> dp2.node = 'np'
    >>> print tree
    (s:
      (np: (d: the) (np: dog))
      (vp: (v: chased) (np: (d: the) (np: cat))))

Children can be accessed with indexing, just as with normal lists:

    >>> tree[0]
    (np: (d: 'the') (np: 'dog'))
    >>> tree[1][1]
    (np: (d: 'the') (np: 'cat'))

Children can be modified directly, as well:

    >>> tree[0], tree[1][1] = tree[1][1], tree[0]
    >>> print tree
    (s:
      (np: (d: the) (np: cat))
      (vp: (v: chased) (np: (d: the) (np: dog))))

The C{Tree} class adds a new method of indexing, using tuples rather
than ints.  C{t[a,b,c]} is equivalant to C{t[a][b][c]}.  The sequence
C{(a,b,c)} is called a \"tree path\".

    >>> print tree[1,1][0]
    (d: the)

    >>> # Switch the cat & dog back the way they were.
    >>> tree[1,1], tree[0] = tree[0], tree[1,1]
    >>> print tree
    (s:
      (np: (d: the) (np: dog))
      (vp: (v: chased) (np: (d: the) (np: cat))))

    >>> path = (1,1,1,0)
    >>> print tree[path]
    cat

The length of a tree is the number of children it has.

    >>> len(tree), len(dp1), len(dp2), len(dp1[0])
    (2, 2, 2, 1)
    >>> len(Tree('x', []))
    0

The current repr for trees looks like this:

    >>> print repr(tree)
    (s: (np: (d: 'the') (np: 'dog')) (vp: (v: 'chased') (np: (d: 'the') (np: 'cat'))))

But this might change in the future.  Similarly, the current str looks
like:

    >>> print str(tree)
    (s:
      (np: (d: the) (np: dog))
      (vp: (v: chased) (np: (d: the) (np: cat))))
    
(Note line-wrapping).  But the details of both reprs might change.

The C{leaves} method returns a list of a trees leaves:

    >>> print tree.leaves()
    ['the', 'dog', 'chased', 'the', 'cat']

The C{height} method returns the height of the tree.  A tree with no
children is considered to have a height of 1; a tree with only
children is considered to have a height of 2; and any other tree's
height is one plus the maximum of its children's heights:

    >>> print tree.height()
    5
    >>> print tree[1,1,1].height()
    2
    >>> print tree[0].height()
    3

The C{treepositions} method returns a list of the tree positions of
subtrees and leaves in a tree.  By default, it gives the position of
every tree, subtree, and leaf, in prefix order:

    >>> print tree.treepositions()
    [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0), (1,), (1, 0), (1, 0, 0), (1, 1), (1, 1, 0), (1, 1, 0, 0), (1, 1, 1), (1, 1, 1, 0)]

The order can also be specified explicitly.  Four orders are currently
supported:

    # Prefix order
    >>> print tree.treepositions('preorder')
    [(), (0,), (0, 0), (0, 0, 0), (0, 1), (0, 1, 0), (1,), (1, 0), (1, 0, 0), (1, 1), (1, 1, 0), (1, 1, 0, 0), (1, 1, 1), (1, 1, 1, 0)]

    # Postfix order
    >>> print tree.treepositions('postorder')
    [(0, 0, 0), (0, 0), (0, 1, 0), (0, 1), (0,), (1, 0, 0), (1, 0), (1, 1, 0, 0), (1, 1, 0), (1, 1, 1, 0), (1, 1, 1), (1, 1), (1,), ()]
    
    # Both prefix & postfix order (subtrees listed twice, leaves once)
    >>> print tree.treepositions('bothorder')
    [(), (0,), (0, 0), (0, 0, 0), (0, 0), (0, 1), (0, 1, 0), (0, 1), (0,), (1,), (1, 0), (1, 0, 0), (1, 0), (1, 1), (1, 1, 0), (1, 1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 1, 1, 0), (1, 1, 1), (1, 1), (1,), ()]
    
    # Leaves only (in order)
    >>> print tree.treepositions('leaves')
    [(0, 0, 0), (0, 1, 0), (1, 0, 0), (1, 1, 0, 0), (1, 1, 1, 0)]

C{treepositions} can be useful for modifying a tree.  For example, we
could upper-case all leaves with:

    >>> for pos in tree.treepositions('leaves'):
    ...     tree[pos] = tree[pos].upper()
    >>> print tree
    (s:
      (np: (d: THE) (np: DOG))
      (vp: (v: CHASED) (np: (d: THE) (np: CAT))))

In addition to C{str} and C{repr}, several methods exist to convert a
tree object to one of several standard tree encodings:

    >>> print tree.pp_treebank()
    (s (np (d THE) (np DOG)) (vp (v CHASED) (np (d THE) (np CAT))))
    >>> print tree.pp_latex_qtree()
    \Tree [.s
            [.np [.d THE ] [.np DOG ] ]
            [.vp [.v CHASED ] [.np [.d THE ] [.np CAT ] ] ] ]

Trees can be parsed from treebank strings with the static
C{Tree.parse} method:

    >>> tree2 = Tree.parse('(S (NP I) (VP (V enjoyed) (NP my cookie)))')
    >>> print tree2
    (S: (NP: I) (VP: (V: enjoyed) (NP: my cookie)))

Trees can be compared for equality:

    >>> tree == Tree.parse(tree.pp_treebank())
    True
    >>> tree2 == Tree.parse(tree2.pp_treebank())
    True
    >>> tree == tree2
    False
    >>> tree == Tree.parse(tree2.pp_treebank())
    False
    >>> tree2 == Tree.parse(tree.pp_treebank())
    False

    >>> tree != Tree.parse(tree.pp_treebank())
    False
    >>> tree2 != Tree.parse(tree2.pp_treebank())
    False
    >>> tree != tree2
    True
    >>> tree != Tree.parse(tree2.pp_treebank())
    True
    >>> tree2 != Tree.parse(tree.pp_treebank())
    True
    
    >>> tree < tree2 or tree > tree2
    True
"""

def test_TreebankTokenReader(): r"""
Unit tests for L{TreebankTokenReader}.

The treebank token reader reads a treebank-style tree into a single
token, with the TREE and WORDS properties:

    >>> s = '(S (NP I) (VP (V enjoyed) (NP my cookie)))'
    >>> treetok = TreebankTokenReader(SUBTOKENS='WORDS').read_token(s)
    >>> print treetok.properties()
    ['TREE', 'WORDS']
    >>> print treetok['TREE']
    (S: (NP: <I>) (VP: (V: <enjoyed>) (NP: <my> <cookie>)))
    >>> print treetok['WORDS']
    [<I>, <enjoyed>, <my>, <cookie>]

With an optional argument (C{add_subtoks}), the token reader constructor
can be told not to include the WORDS property:

    >>> treetok = TreebankTokenReader(add_subtoks=False).read_token(s)
    >>> print treetok.properties()
    ['TREE']

Another optional argument (C{add_locs}), can be used to tell the token
reader constructor to add LOC properties to each leaf:
    
    >>> treetok = TreebankTokenReader(add_locs=True, SUBTOKENS='WORDS').read_token(s)
    >>> print treetok['TREE']
    (S:
      (NP: <I>@[7:8c])
      (VP: (V: <enjoyed>@[17:24c]) (NP: <my>@[30:32c] <cookie>@[33:39c])))
    >>> print treetok['WORDS']
    [<I>@[7:8c], <enjoyed>@[17:24c], <my>@[30:32c], <cookie>@[33:39c]]
    >>> loc = treetok['WORDS'][1]['LOC']
    >>> print loc.select(s)
    enjoyed

Another optional argument (C{add_contexts}), can be used to tell the
token reader constructor to add LOC properties to each leaf:
    
    >>> treetok = TreebankTokenReader(add_contexts=True).read_token(s)
    >>> # [XX] Finish this test!
"""

#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite(reload_module=False):
    import doctest, nltk.test.tree
    if reload_module: reload(nltk.test.tree)
    return doctest.DocTestSuite(nltk.test.tree)

def test(verbosity=2, reload_module=False):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite(reload_module))

if __name__ == '__main__':
    test(reload_module=True)
