# Discourse Representation Theory Implementation
# Author: Edward Ivanovic
# Date: 2004/1/2

from nltk.parser import *
from nltk.cfg import *
from nltk.tree import *
from nltk.tokenizer import WhitespaceTokenizer
import random
from nltk.corpus import gutenberg
from nltk.probability import *
from nltk_contrib.mit.rspeer.parser import parser
from nltk_contrib.mit.rspeer.parser.feature import *

# Define some global nonterminals.
# These are used to build the trigger trees. The string names here
# must match the string names in the external grammar file.
S, VP1, VP, NP, PP, Pro = nonterminals('S, VP1, VP, NP, PP, Pro')
V, N, P, Name, Det, Aux = nonterminals('V, N, P, PN, Det, Aux')

# Global variable to keep track of what the next referent letter should be.
# Make it global to ensure subordinate DRSs don't repreat the same letters
# as any other DRSs.
next_letter = 'a'

class Operation:
    """
    Defines an operation used by the construction algorithm (Kamp & Reyle, 1993)
    
    This class acts as an abstract base class for all construction operations.
    Operations all reside in a list that is searched when attempting to
    reduce a node from a CFG <S> tree.
    """

    def __init__(self, name):
        """
        name is the name of this operation, e.g. "CR.ID"
        searchPath is used to store the path taken to find the target tree
        (subtree) in the matchTrees() method. It's defined as a local
        variable because of the recursive algorithm used - we don't want to
        overwrite the data wnen we recurse.
        """
        self.name = name
        self.searchPath = []

    def canReduce(self, tree):
        """
        tests whether the tree passed in can be reduced. Uses getNodeToReduce()
        to do the test - returns the depth of the first trigger tree found
        within tree, otherwise returns None.
        """
        searchPath = self.getNodeToReduce(tree)
        if searchPath is not None:
            return len(searchPath)  # return the search depth
        else:
            return None             # this operation can't reduce the tree

    def getSubtree(self, tree, path):
        """
        Returns the subtree from tree as specified by path.
        path is a list of integers specifying the node index to follow to the
        subtree. E.g. path = [0,0,1] get tree[0,0,1]
        """
        thisTree = tree
        for p in path:
            thisTree = thisTree[p]

        return thisTree

    def reduce(self, tree, drs):
        """
        Abstract method. The subclass should implement this method to perform
        the actual reduction for this operation.
        """
        None

    def matchTrees(self, tree, subtree, isRoot):
        """
        Attempts to find subtree within tree.
        Recursively calls itself for each node to compare building the
        locally-stored tree path as it goes. The trees may contain
        referents or strings as leaves (or just regular nodes).
        
        isRoot lets us know if we're still trying to find subtree's root
        (head node) within tree. If so, we can traverse tree and not change
        subtree, otherwise we must traverse and compare both at the same time
        to ensure there are no gaps in the matching trees.
        """
        if isinstance(subtree, Referent):
            return isinstance(tree.type(), Referent)

        if not isinstance(tree, AbstractTree):
            return tree.type() == subtree   # string == string

        if not isinstance(subtree, Nonterminal):
            toMatch = subtree.node().symbol()
        else:   # this must be a leaf, not a node. do the comparison & return
            toMatch = subtree.symbol()
            if tree.node().symbol() == toMatch:
                return True
            elif not isRoot:
                return False

        if(isRoot and tree.node().symbol() != toMatch):
            # recurse through the children until we find a match
            # for the root node...
            for i in range(0, len(tree)):
                self.searchPath.append(i)
                if self.matchTrees(tree[i], subtree, True):
                    return True
                else:
                    self.searchPath.pop()

            return False    # no matches

        elif(tree.node().symbol() == toMatch):
            # compare the children
            if len(tree) == len(subtree):
                for i in range (0, len(subtree)):
                    if not self.matchTrees(tree[i], subtree[i], False):
                        return False
                return True

        return False

    def getNodeToReduce(self, tree):
        """
        Find the matching tree pattern. returns 'None' if no
        match found, otherwise returns the path to the first 
        *target* tree found _within_ the trigger tree.
        """

        triggerTrees = self.getTriggerTrees()
        target = self.getTargetTree()

        self.searchPath = []

        for subtree in triggerTrees:
            if self.matchTrees(tree, subtree, True):
                # we have the path to the trigger tree - now continue to get
                # the target tree out of it
                newtree = self.getSubtree(tree, self.searchPath)
                self.matchTrees(newtree, target, True)  # assume this will succeed
                return self.searchPath

        return None


class OperID(Operation):
    """
    Indefinate Description Operator
    From Kamp & Reyle, 1993 pp. 84:
        1. Introduce a new discourse referent.
        2. Introduce the result of substituting this discourse referent
           for the NP-constituent in the syntactic structure to which the rule
           is being applied.
        3. Introduce a condition obtained by placing the discourse referent
           in parentheses behind the top node of the N-constituent.
    """

    def __init__(self):
        Operation.__init__(self, "CR.ID")

    def getTargetTree(self):
        tree = Tree(NP, Det, N)
        return tree

    def getTriggerTrees(self):
        """
        The trigger tree and target tree are the same in this case.
        """
        tree = self.getTargetTree()
        return [tree]

    def reduce(self, tree, drs):
        treePath = self.getNodeToReduce(tree)   # path to target tree w/i tree
        newTree = tree
        if treePath != None:    # treePath should never be None by here...but check anyway
            npNode = self.getSubtree(tree, treePath)    # the target tree w/ tree's continuing nodes & leaves
            newRef = drs.introduceReferent(npNode[1].node())
            newTree = tree.with_substitution(treePath, Token(newRef))   # reduce tree here
            npNode.draw()       # some FYIs for interest
            newTree.draw()
            cond = Condition(npNode[1][0].type())   #we have a Det, N, so do [1] to get to the N then [0] to get to the Token object, finally type() to get the text out of the token
            cond.addReferent(newRef)
            drs.addCondition(cond)

        return newTree  # the new reduced tree


class OperPRO(Operation):
    """
    Pronoun Operator
    From page 70:
        1. Introduce a new discourse referent.
        2. Introduce a condition obtained by substituting this referent for
           the NP-node of the local configuration that triggers the rule
           application and delete that syntactic structure.
        3. Add a condition of the form a=b where a is a new discourse ref.
           and b is a /suitable/ discourse referent chosen from the universe
           of the DRS.
    """

    def __init__(self):
        Operation.__init__(self, "CR.PRO")

    def getTargetTree(self):
        tree = Tree(NP, Pro)
        return tree

    def getTriggerTrees(self):
        """
        We can have two trigger trees for this one.
        """
        target = self.getTargetTree()
        tree1 = Tree(S, target, VP1)
        tree2 = Tree(VP, V, target)
        return [tree1, tree2]

    def reduce(self, tree, drs):
        treePath = self.getNodeToReduce(tree)
        newTree = tree
        if treePath != None:
            targetTree = self.getSubtree(tree, treePath)
            newRef = drs.introduceReferent(targetTree[0].node())
            newTree = tree.with_substitution(treePath, Token(newRef))    # delete the NP node

            # add a new equality condition - match it with a 'suitable' referent
            cond = EqCondition(newRef)
            refs = []
            if drs.parentDRS != None:
                refs = drs.parentDRS.referents + [] # deep copy

            if len(drs.accessible) > 0: # this must be the b in if a then b (a=>b), hence access a's referents
                for d in drs.accessible:
                    refs += d.referents

            refs += drs.referents

            refs.reverse()  # start looking from the one added last as it's more
                            # likely to be the correct match if there are more
                            # than one suiable matches.
            
            # look for the suitable match here.  return the first one found
            # even though there might be a better match. This works well
            # for the type of sentences and rules curently implemeted.
            # If more rules are implemented to handle more complex setences
            # then we should store and return the highest match score.
            for ref in refs[1:]:    # skip the first one as it's the one we just added
                if newRef.getMatchScore(ref) > 0:   # find a suitable match
                    cond.addReferent(ref)
                    break;

            drs.addCondition(cond)

        return newTree


class OperPN(Operation):
    """
    Proper name - process described on page 65 (Kamp & Reyle, 1993).
    """

    def __init__(self):
        Operation.__init__(self, "CR.PN")

    def getTargetTree(self):
        tree = Tree(NP, Name)
        return tree

    def getTriggerTrees(self):
        target = self.getTargetTree()
        tree1 = Tree(S, target, VP1)
        tree2 = Tree(VP, V, target)
        return [tree1, tree2]

    def reduce(self, tree, drs):
        treePath = self.getNodeToReduce(tree)
        newTree = tree
        if treePath != None:
            targetTree = self.getSubtree(tree, treePath)
            # ensure we add any referents/conditions to the parent DRS if a
            # parent DRS exists. This allows us to perform correct
            # anaphoric resolution with the CR.COND operator (and some others).
            # See Kamp & Reyle for more information.
            if drs.parentDRS != None:
                thisDrs = drs.parentDRS
            else:
                thisDrs = drs

            newRef = thisDrs.introduceReferent(targetTree[0].node())
            newTree = tree.with_substitution(treePath, Token(newRef))    # delete the PN node
            cond = Condition(targetTree.leaves()[0].type())   # get the first leaf - must be the name
            cond.addReferent(newRef)
            thisDrs.addCondition(cond)

        return newTree


class OperNEG(Operation):
    """
    Negation - process described on page 99.
    """

    def __init__(self):
        Operation.__init__(self, "CR.NEG")

    def getTargetTree(self):
        return VP

    def getTriggerTrees(self):
        target = self.getTargetTree()
        tree = Tree(S, Referent('?', None), Tree(VP1, Aux, 'not', target))
        return [tree]

    def reduce(self, tree, drs):
        treePath = self.getNodeToReduce(tree)
        newTree = tree
        if treePath != None:
            targetTree = self.getSubtree(tree, treePath)

            # major transformation to the tree...
            newTree = tree.with_substitution([0,1], TreeToken(VP1, targetTree))    # delete the PN node

            childDRS = DRS(drs)
            childDRS.isNeg = True
            newTree = childDRS.parseTree(newTree)   # newTree is usually empty when this returns
            drs.addChild(childDRS)

        return newTree

class OperCOND(Operation):
    """
    Connective Operator - process described on page 156.
    """

    def __init__(self):
        Operation.__init__(self, "CR.COND")

    def getTargetTree(self):
        return S

    def getTriggerTrees(self):
        """
        This is a special case where there is one trigger tree but two
        target trees which are both the same: 'S'. Actually makes it really
        easy to reduce...
        """
        target = self.getTargetTree()
        tree = Tree(S, 'if', target, 'then', target)
        return [tree]

    def reduce(self, tree, drs):
        """
        An easy reduction for something that seems much more complicated.
        Break up the 2 [S] trees from tree then give them to 2 invididual
        DRSs to processes. Tell them they're related with a [S1]=>[S2],
        add then to this (main) DRS and we're done.
        We can safely hard-code the trigger tree indexes because its head will
        always be tree.
        """
        S1 = tree[0,1]
        S2 = tree[0,3]
        drs1 = DRS(drs)
        drs2 = DRS(drs)
        drs2.addAccessible(drs1)    # drs1 is accessible to drs2 since we have drs1 => drs2
        drs1.parseTree(S1)
        newTree = drs2.parseTree(S2)
        drs.addChild(drs1)
        drs.addChild(drs2)

        return newTree

# store the list of operations to search through here. If adding more operations
# then add them to this list to be picked up by the DRS processing.
operations = [OperID(), OperPRO(), OperPN(), OperNEG(), OperCOND()]

class Referent:
    """
    Represents a discourse referent. A DRS generally has many referents.
    """
    equality = []

    def __init__(self, symb, category):
        """
        symb is the symbol to use, such as x, y, z to denote this reference
        when printing it out.
        category stores the features that apply to this referent for
        anaphoric resolution. Features such as gender, plurality, etc. are
        stored within it.
        """
        self.symbol = symb
        self.cat = category
        if symb not in self.equality:
            self.equality.append(symb)

    def __str__(self):
        result = self.symbol
        for symb in self.equality:
            result += '\n' + self.symbol + '=' + symb

        return result

    def getMatchScore(self, ref):
        """
        Returns a score indicating the suitability of ref to this referent.
        The score is an integer from 0 and up based on agreement factors
        provided in the two referents (ref and self).  The higher the score
        the better the match is. A score of 0 indicates that no agreements
        were found.
        """

        if self.cat is None:
            return 0
        
        numMatched = 0

        for featurename in self.cat._dict.keys() + ref.cat._dict.keys():
            if self.cat._dict.has_key(featurename):
				feature = self.cat._dict[featurename]
            else:
				isRequired = ref.cat._dict[featurename].isRequired()
				if isRequired: value = NullCategory()
				else: value = StarCategory()
				feature = Feature(featurename, value, isRequired)
				
            a = ref.cat.match_feature(feature)
            if a == None:
                return 0    # don't continue - can't match these
            else:   # consider this a match
                numMatched += 1

        return numMatched


class Condition:
    """
    Represents a discourse condition. A DRS generally has many conditions.
    A condition always has at least 1 referent.
    """
    def __init__(self, cond_name):
        self.referent = []
        self.name = cond_name

    def __str__(self):
        result = self.name + '('
        for ref in self.referent:
            result += ref.symbol + ', '
        result += ')'

        return result

    def addReferent(self, ref):
        assert(isinstance(ref, Referent), 'Only Referent objects may be added to a Condition')
        self.referent.append(ref)


class EqCondition(Condition):
    """
    Represents an equality condition. e.g. x=y rather than the normal condition
    car(x) or likes(y, z)
    """
    def __str__(self):
        result = self.name.symbol + '='
        for ref in self.referent:
            result += ref.symbol + ' '

        return result

def getNextLetter():
    """
    Return the next letter for a discourse referent. Global to ensure DRSs
    don't use existing letters to introduce referents.
    """
    global next_letter
    letter = next_letter
    next_letter = chr(ord(next_letter) + 1)
    return letter


class DRS:
    """
    Represents a DRS - the 'language' of DRT.
    Basically stores conditions and referents and relationships between other
    DRSs, i.e. whether this has a parent, an accessible DRS (if a then b( a=>b))
    or this has any children (or a combination).
    """
    def __init__(self, parent=None):
        self.parentDRS = parent
        self.referents = []
        self.conditions = []
        self.childrenDRS = []
        self.isNeg = False
        self.accessible = []

    def numReferents(self):
        return len(self.referents)

    def numConditions(self):
        return len(self.conditions)

    def addAccessible(self, drs):
        """
        Store the accessible referents here - use them when doing anaphoric
        resolution. This is only used for if...then sentences. Accessibility
        for a negation child is automatic through the parentDRS pointer.
        """
        self.accessible.append(drs)

    def addChild(self, drs):
        self.childrenDRS.append(drs)

    def introduceReferent(self, category):
        """
        A referent is produced from a Category which contains information
        about the properties of the referent. These properties are then used
        to find a suitable match for the referent using feature grammar and
        other agreement factors.
        """
        if not isinstance(category, Category):
            print 'Must pass in a Category type.', category.__class__, ' passed instead!'
            raise TypeError
        else:
            letter = getNextLetter()
            ref = Referent(letter, category)
            self.referents.append(ref)
            return ref

    def addCondition(self, cond):
        self.conditions.append(cond)

    def complete(self, tree):
        # tidy up and colapse any V branches for a neater DRS
        tempReferents = []
        verb = ''
        for leaf in tree.leaves():
            if leaf.loc() is None:  # distinguish referents as they don't have a location (cleaner way of doing this?)
                # store the referent
                tempReferents.append(leaf.type())
            else:
                verb = leaf.type()     # assume 1 verb per irreducible tree for now

        tree = None # nothing left in this tree
        cond = Condition(verb)
        for ref in tempReferents:
            cond.addReferent(ref)

        self.addCondition(cond)
        
        return tree # None


    def parseTree(self, tree):
        """
        The main parsing algorithm. We get here once we have a parse tree to
        work with from the sentence passed in.
        Keep on looping through the registered operations reducing the tree
        with the operation that can reduce the highest tree first. Exit the
        loop once no operation can reduce the tree.
        """
        tree.draw()
        mayReduce = True

        while mayReduce:
            mayReduce = False
            nextOper = None
            minDepth = 500  # start at a very unlikely large depth to get the min

            for oper in operations:
                depth = oper.canReduce(tree)
                if (depth != None and depth < minDepth):
                    nextOper = oper
                    minDepth = depth

            if nextOper != None:
                tree = nextOper.reduce(tree, self)
                if tree != None:
                    mayReduce = True    # loop again as there may be more reductions

        if tree != None:
            tree = self.complete(tree) # collapse the trees - usually only verbs & DRs left
        return tree


    def parse(self, sent):
        # Get the grammar and parse the sentence into a tree. Then pass it to
        # parseTree for DRS analysis and reduction.

		filename = 'grammar.txt'
		grammar = parser.parseFile(filename)

        # tokenize the sentence
		tok_sent = WhitespaceTokenizer().tokenize(sent)

		ep = parser.IncrementalEarleyParser(grammar, parser.earleyStrategy)

		tree = ep.parse_n(tok_sent, 1)

		if len(tree) > 0:
		    self.parseTree(tree[0])
		else:
		    print 'No parses found for', sent


    def __str__(self):
        if self.isNeg:
            result = '\n+++++++ NOT +++++++++\n'
        else:
            result = '\n' + ('+' * 20) + '\n'

        for ref in self.referents:
            result += ref.symbol + ', '
            
        result += '\n' + ('-' * 30)
        for condition in self.conditions:
            result += '\n' + condition.__str__()

        for child in self.childrenDRS:
            result += child.__str__()

        result += '\n' + ('_' * 20) + '\n'
        return result


if __name__ == '__main__':
    #sentences = ["Jones does not own Ulysses", "he likes it"]
    #sentences = ["Jones does not own a Porsche", "he likes it"]
    #sentences = ["Jones owns a Porsche", "it fascinates him"]
    #sentences = ["Jones owns a Porsche", "he does not like it"]
    sentences = ["if Jones owns a Porsche then he likes it"]
    #sentences = ["a woman snorts", "she collapses"]
    drs = DRS()
    for sentence in sentences:
        drs.parse(sentence)

    print drs
