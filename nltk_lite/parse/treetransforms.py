# Natural Language Toolkit: Tree Transformations
#
# Copyright (C) 2005 Oregon Graduate Institute
# Author: Nathan Bodenstab <bodenstab@cslu.ogi.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
A collection of methods for tree (grammar) transformations used
in parsing natural language.  

Although many of these methods are technically grammar transformations
(ie. Chomsky Norm Form), when working with treebanks it is much more
natural to visualize these modifications in a tree structure.  Hence,
we will do all transformation directly to the tree itself.
Transforming the tree directly also allows us to do parent annotation.
A grammar can then be simply induced from the modified tree.

The following is a short tutorial on the available transformations.

1) Chomsky Normal Form (binarization)

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
  the difference between them.

            Original       Right-Factored     Left-Factored

  Example:     A              A                      A 
             / | \          /   \                  /   \
            B  C  D   ==>  B    A|<C-D>   OR   A|<B-C>  D 
                                 /  \          /  \
                                C    D        B    C

2) Parent Annotation

  In addition to binarizing the tree, there are two standard
  modifications to node labels we can do in the same traversal: parent
  annotation and Markov order-N smoothing (or sibling smoothing).

  The purpose of parent annotation is to refine the probabilities of
  productions by adding a small amount of context.  With this simple
  addition, a CYK (inside-outside, dynamic programming chart parse)
  can improve from 74% to 79% accuracy.  A natural generalization from
  parent annotation is to grandparent annotation and beyond.  The
  tradeoff becomes accuracy gain vs. computational complexity.  We
  must also keep in mind data sparcity issues.

            Original       Parent Annotation 

  Example:     A                A^<?>            
             / | \             /   \            
            B  C  D   ==>  B^<A>    A|<C-D>^<?>     where ? is the parent of A
                                      /  \        
                                  C^<A>   D^<A>   


3) Markov order-N smoothing

  Markov smoothing combats data sparcity issues as well as decreasing
  computational requirements by limiting the number of children
  included in artificial nodes.  In practice, most people use an order
  2 grammar.

             Original          No Smoothing        Markov order 1     Markov order 2   etc...

  Example:       A                A                       A                A 
            /  / | \  \         /   \                   /   \            /   \
           B  C  D  E  F  ==>  B    A|<C-D-E-F>   ==>  B   A|<C>  ==>   B  A|<C-D>
                                      /   \                /   \            /   \
                                     C    ...             C    ...         C    ...

  Annotation decisions can be thought about in the vertical direction
  (parent, grandparent, etc) and the horizontal direction (number of
  siblings to keep).  Parameters to the following functions specify
  these values.  For more information see:

  Dan Klein and Chris Manning (2003) "Accurate Unlexicalized Parsing", ACL-03.
  http://www.aclweb.org/anthology/P03-1054
    
4) Unary Collapsing  

  Collapse unary productions (ie. subtrees with a single child) into a
  new non-terminal (Tree node).  This is useful when working with
  algorithms that do not allow unary productions, yet you do not wish
  to lose the parent information.

              A         
              |
  Example:    B   ==>   A+B
             / \        / \
            C   D      C   D    

"""

from nltk_lite.parse.tree import Tree

def chomskyNormalForm(tree, factor = "right", horzMarkov = None, vertMarkov = 0, childChar = "|", parentChar = "^"):
    """
    This method can modify a tree in three ways:
      1. Convert a tree into its Chomsky Normal Form (CNF) equivalent -- Every subtree
         has either two non-terminals or one terminal as its children.  This process
         requires the creation of more "artificial" non-terminal nodes.
      2. Markov (vertical) smoothing of children in new artificial nodes
      3. Horizontal (parent) annotation of nodes
      
      see documentation in code for more information
      
    @param tree: The Tree to be modified
    @type  tree: C{Tree}
    @param factor: Right or left factoring method (default = "right")
    @type  factor: C{string} = [left|right]
    @param horzMarkov: Markov order for sibling smoothing in artificial nodes (None (default) = include all siblings)
    @type  horzMarkov: C{int} | None
    @param vertMarkov: Markov order for parent smoothing (0 (default) = no vertical annotation)
    @type  vertMarkov: C{int} | None
    @param childChar: A string used in construction of the artificial nodes, separating the head of the
                      original subtree from the child nodes that have yet to be expanded (default = "|")
    @type  childChar: C{string}
    @param parentChar: A string used to separate the node representation from its vertical annotation
    @type  parentChar: C{string}
    """

    # assume all subtrees have homogeneous children
    # assume all terminals have no siblings
    
    # A semi-hack to have elegant looking code below.  As a result,
    # any subtree with a branching factor greater than 999 will be incorrectly truncated.
    if horzMarkov == None: horzMarkov = 999
    
    # Traverse the tree depth-first keeping a list of ancestor nodes to the root.
    # I chose not to use the tree.treepositions() method since it requires
    # two traversals of the tree (one to get the positions, one to iterate
    # over them) and node access time is proportional to the height of the node.
    # This method is 7x faster which helps when parsing 40,000 sentences.  

    nodeList = [(tree, [tree.node])]
    while nodeList != []:
        node, parent = nodeList.pop()
        if isinstance(node,Tree):
  
            # parent annotation
            parentString = ""
            originalNode = node.node
            if vertMarkov != 0 and node != tree and isinstance(node[0],Tree):
                parentString = "%s<%s>" % (parentChar, "-".join(parent))
                node.node += parentString
                parent = [originalNode] + parent[:vertMarkov - 1]
    
            # add children to the agenda before we mess with them
            for child in node:
                nodeList.append((child, parent))
           
            # chomsky normal form factorization
            if len(node) > 2:
                childNodes = [child.node for child in node]
                nodeCopy = node.copy()
                node[0:] = [] # delete the children
      
                curNode = node
                numChildren = len(nodeCopy)
                for i in range(1,numChildren - 1):
                    if factor == "right":
                        newHead = "%s%s<%s>%s" % (originalNode, childChar, "-".join(childNodes[i:min([i+horzMarkov,numChildren])]),parentString) # create new head
                        newNode = Tree(newHead, [])
                        curNode[0:] = [nodeCopy.pop(0), newNode]
                    else:
                        newHead = "%s%s<%s>%s" % (originalNode, childChar, "-".join(childNodes[max([numChildren-i-horzMarkov,0]):-i]),parentString)
                        newNode = Tree(newHead, [])
                        curNode[0:] = [newNode, nodeCopy.pop()]
        
                    curNode = newNode
      
                curNode[0:] = [child for child in nodeCopy]
        

def unChomskyNormalForm(tree, expandUnary = True, childChar = "|", parentChar = "^", unaryChar = "+"):
    """
    This method modifies the tree in three ways:
      1. Transforms a tree in Chomsky Normal Form back to its original structure (branching greater than two)
      2. Removes any parent annotation (if it exists)
      3. (optional) expands unary subtrees (if previously collapsed with collapseUnary(...) )
      
    @param tree: The Tree to be modified
    @type  tree: C{Tree}
    @param expandUnary: Flag to expand unary or not (default = True)
    @type  expandUnary: C{boolean}
    @param childChar: A string separating the head node from its children in an artificial node (default = "|")
    @type  childChar: C{string}
    @param parentChar: A sting separating the node label from its parent annotation (default = "^")
    @type  parentChar: C{string}
    @param unaryChar: A string joining two non-terminals in a unary production (default = "+")
    @type  unaryChar: C{string}  
    """
    
    # Traverse the tree-depth first keeping a pointer to the parent for modification purposes.
    nodeList = [(tree,[])]
    while nodeList != []:
        node,parent = nodeList.pop()
        if isinstance(node,Tree):
            # if the node contains the 'childChar' character it means that
            # it is an artificial node and can be removed, although we still need
            # to move its children to its parent
            childIndex = node.node.find(childChar)
            if childIndex != -1:
                nodeIndex = parent.index(node)
                parent.remove(parent[nodeIndex])
                # Generated node was on the left if the nodeIndex is 0 which
                # means the grammar was left factored.  We must insert the children
                # at the beginning of the parent's children
                if nodeIndex == 0:
                    parent.insert(0,node[0])
                    parent.insert(1,node[1])
                else:
                    parent.extend([node[0],node[1]])
                
                # parent is now the current node so the children of parent will be added to the agenda
                node = parent
            else:
                parentIndex = node.node.find(parentChar)
                if parentIndex != -1:
                    # strip the node name of the parent annotation
                    node.node = node.node[:parentIndex]
                  
                # expand collapsed unary productions
                if expandUnary == True:
                    unaryIndex = node.node.find(unaryChar)
                    if unaryIndex != -1:
                        newNode = Tree(node.node[unaryIndex + 1:], [i for i in node])
                        node.node = node.node[:unaryIndex]
                        node[0:] = [newNode]
                      
            for child in node:
                nodeList.append((child,node))


def collapseUnary(tree, collapsePOS = False, collapseRoot = False, joinChar = "+"):
    """
    Collapse subtrees with a single child (ie. unary productions)
    into a new non-terminal (Tree node) joined by 'joinChar'.
    This is useful when working with algorithms that do not allow
    unary productions, and completely removing the unary productions
    would require loss of useful information.  The Tree is modified 
    directly (since it is passed by reference) and no value is returned.
    
    @param tree: The Tree to be collapsed
    @type  tree: C{Tree}
    @param collapsePOS: 'False' (default) will not collapse the parent of leaf nodes (ie. 
                        Part-of-Speech tags) since they are always unary productions
    @type  collapsePOS: C{boolean}
    @param collapseRoot: 'False' (default) will not modify the root production
                         if it is unary.  For the Penn WSJ treebank corpus, this corresponds
                         to the TOP -> productions.
    @type collapseRoot: C{boolean}
    @param joinChar: A string used to connect collapsed node values (default = "+")
    @type  joinChar: C{string}
    """
    
    if collapseRoot == False and isinstance(tree, Tree) and len(tree) == 1:
        nodeList = [tree[0]]
    else:
        nodeList = [tree]

    # depth-first traversal of tree
    while nodeList != []:
        node = nodeList.pop()
        if isinstance(node,Tree):  
            if len(node) == 1 and isinstance(node[0], Tree) and (collapsePOS == True or isinstance(node[0,0], Tree)):
                node.node += joinChar + node[0].node
                node[0:] = [child for child in node[0]]
                # since we assigned the child's children to the current node, 
                # evaluate the current node again
                nodeList.append(node) 
            else:
                for child in node:
                    nodeList.append(child) 
          

def toTreebank(tree):
    """
    Convert a tree into its treebank-style bracketed equivalent.
    """
    return _toTreebank(tree).strip()

def _toTreebank(tree):
    s = " (%s" % tree.node
    for child in tree:
        if isinstance(child,Tree):
            s += _toTreebank(child)
        else:
            s += " " + child
    return s + ")"


#################################################################
# Demonstration
#################################################################

def demo():
    """
    A demonstration showing how each tree transform can be used.
    """  
      
    from nltk_lite.draw.tree import draw_trees
    from nltk_lite.parse import bracket_parse
    from copy import deepcopy
    
    # original tree from WSJ bracketed text
    sentence = "(TOP (S (S (VP (VBN Turned) (ADVP (RB loose)) (PP (IN in) (NP (NP (NNP Shane) (NNP Longman) (POS 's)) (NN trading) (NN room))))) (, ,) (NP (DT the) (NN yuppie) (NNS dealers)) (VP (AUX do) (NP (NP (RB little)) (ADJP (RB right)))) (. .)))"
    tree = bracket_parse(sentence)
    
    # collapse subtrees with only one child
    collapsedTree = deepcopy(tree)
    collapseUnary(collapsedTree)
    
    # convert the tree to CNF
    cnfTree = deepcopy(collapsedTree)
    chomskyNormalForm(cnfTree)
    
    # convert the tree to CNF with parent annotation (one level) and horizontal smoothing of order two
    parentTree = deepcopy(collapsedTree)
    chomskyNormalForm(parentTree, horzMarkov = 2, vertMarkov = 1)
    
    # convert the tree back to its original form (used to make CYK results comparable)
    original = deepcopy(parentTree)
    unChomskyNormalForm(original)
    
    # convert tree back to bracketed text
    sentence2 = toTreebank(original)
    print "Sentences the same? ", sentence == sentence2
    
    draw_trees(tree, collapsedTree, cnfTree, parentTree, original)

if __name__ == '__main__': demo()  
