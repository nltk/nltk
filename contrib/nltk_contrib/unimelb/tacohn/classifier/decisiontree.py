# Natural Language Toolkit: Decision tree
#
# Copyright (C) 2001 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Decision tree classifier using the flip-flop algorithm - based on [1,2]. This
algorithm choses the feature which offers the most informative split to create
the current node in the decision tree. The instances are then split using this
feature and the process repeated using the remaining features. When the
instances have only one label or there are no features left, a leaf node is
created. This method could probably benefit from pruning with held-out test
data.

[1] Brown 1991: Brown, Peter F., Pietra, Stephen A. Della, Pietra, Vincent
J.  Della, and Mercer, Robert L., "Word-Sense Disambiguation Using
Statistical Methods," in: Proceedings of the 29th Conference of the
Association for Computational Linguistics, pp. 264-270, Berkeley, CA, June
1991.  http://citeseer.nj.nec.com/brown91wordsense.html

[2] Arthur Nadas, David Nahamoo, Michael A. Picheny, and Jeffrey Powell. An
iterative "flip-flop" approximation of the most informative split in the
construction of decision trees. In Proceedings of the IEEE International
Conference on Acoustics, Speech and Signal Processing, Toronto, Canada, May
1991.
"""

import math, random, operator
from nltk.probability import *
from nltk.token import Token
from nltk_contrib.unimelb.tacohn.classifier import ClassifierTrainerI, LabeledText
from nltk_contrib.unimelb.tacohn.classifier.feature import *
from nltk_contrib.unimelb.tacohn.classifier.featureselection import SelectedFDList
from nltk.set import MutableSet, Set

class _DecisionNode:
    """
    Internal node in a decision tree (i.e. not a leaf). Characterised by a
    range of feature numbers, and two sets of feature numbers corresponding to
    the left and right sub-trees. When classifying an instance, the tree is
    traversed by following the sub-tree based on the activated features -- if
    there is an activated value in the left set, then go left; similar for
    right. If there is no value in either set a random decision is made
    weighted for the number of training instances in each subtree.
    """

    LEFT =  1
    RIGHT = 2
    def __init__(self, fn_range, fl, fr, left = None, right = None):
        """
        Create a node with the given range, left and right feature number sets
        and the left and right sub-trees. These may be None if they are to be
        filled in at a later time using add_child.
        """
        self.fn_range = fn_range
        self.fnum_dict = {}
        for fnum in fl:
            self.fnum_dict[fnum] = self.LEFT
        for fnum in fr:
            self.fnum_dict[fnum] = self.RIGHT
        self.left_fnum = fl
        self.right_fnum = fr
        self.left_node = left
        self.right_node = right

    def traverse(self, fnums):
        """
        Traverse to a leaf node of the tree using the list of activated
        feature numbers.  The left or right sub-tree is chosen based on the
        activated features -- if there is an activated value in the left set,
        then go left; similar for right. If there is no value in either set
        a random decision is made weighted for the number of training
        instances in each subtree. The leaf node will be returned.
        """
        relevant = filter(lambda x, r=self.fn_range: x in r, fnums)
        irrelevant = filter(lambda x, r=self.fn_range: x not in r, fnums)

        for fnum in relevant:
            direction = self.fnum_dict.get(fnum)
            if direction == self.LEFT:
                return self.left_node.traverse(irrelevant)
            elif direction == self.RIGHT:
                return self.right_node.traverse(irrelevant)

        if random.random() < self.left_skew:
            return self.left_node.traverse(irrelevant)
        else:
            return self.right_node.traverse(irrelevant)

    def count(self):
        """
        Returns a count of the number of training instances represented by
        this sub-tree.
        """
        return self.left_node.count() + self.right_node.count()

    def labels(self):
        """
        Returns a set of labels possible for this sub-tree.
        """
        ls = Set(*self.left_node.labels()).union(Set(*self.right_node.labels()))
        return ls.elements()

    def add_child(self, node):
        """
        Adds a child to the next free node. This node can only hold two
        children, and the left child is filled before the right. It is an
        error to add a child to an already full node.
        """
        if not self.left_node:
            self.left_node = node
        elif not self.right_node:
            self.right_node = node
        else:
            raise AssertionError('Cannot add child to full node')

    def compile(self):
        """
        Compiles the left skew parameter. Entire tree must be defined.
        """
        if self.left_node and self.right_node:
            self.left_node.compile()
            self.right_node.compile()
            self.left_skew = self.left_node.count() / \
                float(self.left_node.count() + self.right_node.count())

    def __repr__(self):
        if not self.fn_range:
            return '<Fake root>'
        else:
            return '<Node %d-%d children=%s>' % (self.fn_range[0],
                self.fn_range[-1], repr([self.left_node, self.right_node]))

class _DecisionLeaf:
    """
    A leaf (external node) in a decision tree. The leaf simply holds a
    frequency distribution over all labels.
    """
    def __init__(self, label_fdist):
        """
        Create a leaf with the given label frequency distribution.
        """
        self._label_fdist = label_fdist

    def count(self):
        """
        Returns a count of the number of training instances represented by the
        leaf.
        """
        return self._label_fdist.N()

    def label(self):
        """
        Returns the most probable label for this leaf.
        """
        return self._label_fdist.max()

    def labels(self):
        """
        Returns the set of possible labels for this leaf.
        """
        return self._label_fdist.samples()

    def traverse(self, fnums):
        """
        Returns self, to provide base case for recursion.
        """
        return self

    def prob(self, label):
        """
        Returns the probability of the given label.
        """
        return self._label_fdist.freq(label)

    def compile(self):
        return

    def __repr__(self):
        return '<Leaf ' + ' '.join(['%s:%.2f' % (l, self._label_fdist.freq(l))
                                   for l in self._label_fdist.samples()]) + '>'

class DecisionTreeClassifier(AbstractFeatureClassifier):
    """
    A decision tree classifier. This class provides the basic classifier
    interface wrapping the capabilities of the _DecisionNode and _DecisionLeaf
    classes. Instances are classified based on their feature values. At each
    level in the tree, instances are split into two base on the value for the
    instance of the current level's feature. This process continues until a
    leaf is reached. This leaf contains a frequency distribution of labels,
    which is used for chosing the most probable label and determining the
    probability of being given alternative labels.
    """
    def __init__(self, fd_list, root):
        """
        Create a decision tree classifier using the feature detector list and
        the root decision node.
        """
        AbstractFeatureClassifier.__init__(self, fd_list, root.labels())
        self._root = root

    def classify(self, unlabeled_token):
        # inherit doco
        fv_list = self._fd_list.detect(unlabeled_token.type())
        fnums = map(lambda x: x[0], fv_list.assignments())
        leaf = self._root.traverse(fnums)
        label = leaf.label()
        return Token(LabeledText(unlabeled_token.type(), label),
                     unlabeled_token.loc())

    def fv_list_likelihood(self, fv_list, label):
        # inherit doco
        fnums = map(lambda x: x[0], fv_list.assignments())
        leaf = self._root.traverse(fnums)
        return leaf.prob(label)

    def likelihood(self, labeled_token):
        # inherit doco
        fv_list = self._fd_list.detect(labeled_token.type())
        return self.fv_list_likelihood(fv_list, labeled_token.type().label())

    def distribution_list(self, unlabeled_token):
        # inherit doco
        fv_list = self._fd_list.detect(unlabeled_token.type())
        fnums = map(lambda x: x[0], fv_list.assignments())
        leaf = self._root.traverse(fnums)
        return [leaf.prob(label) for label in self.labels()]

    def __repr__(self):
        return '<DecisionTreeClassifier %s>' % repr(self._root)

class DecisionTreeClassifierTrainer(ClassifierTrainerI):
    """
    Trainer class for a decision tree classifier using the flip-flop - based
    on [1,2]. This algorithm choses the feature which offers the most
    informative split to create the current node in the decision tree. The
    instances are then split using this feature and the process repeated using
    the remaining features. When the instances have only one label or there
    are no features left, a leaf node is created. This method could probably
    benefit from pruning with held-out test data.
    
    [1] 'Word-Sense Disambiguation using Statistical Methods', Brown et al 
    [2] 'An iterative "Flip-Flop" approximation of the most informatve split
    in the construction of Decision Trees', Nadas et al.
    """
    def __init__(self, fd_list, trace=False):
        """
        Create the trainer using the feature detector list and trace
        parameter.
        """
        self._fd_list = fd_list
        self._trace = trace

    def train(self, training_tokens):
        """
        Train the decision tree. The algorithm is as follows:

        a) create fv_lists for all instances -> V = [(fv_list, label)]
        b) push (V, P, F) onto the stack
           (F = set of distinct features, P = placeholder parent node)
        c) while stack is not empty, pop V, P, F:
            if all v in V share common label or F is empty:
                create leaf node(label) as child of P
            else:
                find optimal partition, (L, R) using f in F
                F = F \ f
                VL = v in V where f(v) in L
                VR = v in V where f(v) in R
                N = node(f, L, R)
                push (F, N, VL) onto stack
                push (F, N, VR) onto stack
        d) done - tree is in P

        The optimal partitioning is done with the flip-flop algorithm.
        """
        
        # step A
        ranges = self._fd_list.ranges()
        F = range(len(ranges))
        root = P = _DecisionNode([], [], [], None, None)
        V = []
        # don't process a node covering few examples - make it a leaf
        min_instances = len(training_tokens) / 50
        # if the primary label accounts for so many samples, accept
        min_skew = 0.90

        # some precomputation helps ;)
        cooccurrence_fd = ConditionalFreqDist()
        senses = {}
        for token in training_tokens:
            lt = token.type()
            senses[lt.label()] = 1
            fv_list = self._fd_list.detect(lt.text())
            V.append((fv_list, lt.label()))
            assignments = fv_list.assignments()
            for rid in F:
                for id, value in assignments:
                    if id in ranges[rid]: # could be done more effic. with dict
                        cooccurrence_fd[rid].inc((id, lt.label()))
        cooccurrence_pd = ConditionalProbDist(cooccurrence_fd, MLEProbDist)

        if len(senses) == 1:
            # create dumb classifier that always returns the dominant (only)
            # sense as seen in the training data
            return DefaultClassifier(senses.keys()[0])

        # step B
        stack = []
        stack.append((V, P, F))

        # step C
        while stack:
            V, P, F = stack.pop()

            # check for triviality
            label_fdist = FreqDist()
            for fv_list, label in V:
                label_fdist.inc(label)

            if self._trace:
                print 'DTCT - processing %d instances' % len(V)
                for s in label_fdist.samples():
                    print 'DTCT - sample: %s => %.2f (%d)' \
                        % (s, label_fdist.freq(s), label_fdist.count(s))
                print 'DTCT - P', P
                print 'DTCT - F', F

            if not F or label_fdist.B() == 1 \
                     or len(V) <= min_instances \
                     or label_fdist.freq(label_fdist.max()) >= min_skew:
                leaf = _DecisionLeaf(label_fdist)
                P.add_child(leaf)
            else:
                # find optimal partition
                part = self._optimal_part(V, F, ranges,
                                          cooccurrence_pd, label_fdist)

                # can sometimes fail to classify one instance...
                if not part:
                    leaf = _DecisionLeaf(label_fdist)
                    P.add_child(leaf)
                else:
                    f, L, R = part

                    # modify the features and instances & push onto stack
                    new_F = F[:]
                    new_F.remove(f)
                    VL, VR = self._split_instances(V, ranges[f], L, R)

                    if VL and VR:
                        # create the node
                        N = _DecisionNode(ranges[f], L, R)
                        P.add_child(N)

                        # ensures left is popped first
                        stack.append((VR, N, new_F))
                        stack.append((VL, N, new_F)) 
                    else:
                        # this should never happen...
                        stack.append((V, P, new_F))

        # step D
        tree = root.left_node
        tree.compile()
        return DecisionTreeClassifier(self._fd_list, tree)

    def _optimal_part(self, instances, range_ids, ranges,
                      cooccurrence_pd, label_fdist):
        """
        Finds the optimal partition, using one of the list of range_ids to
        index the ranges list of feature numbers. The range_id used to
        partition is returned, along with the list of left and right feature
        numbers.
        """
        if self._trace:
            print 'DTCT - finding optimal partition'
            print 'DTCT - range_ids', range_ids
            print 'DTCT - %d instances' % len(instances)

        max = None
        for rid in range_ids:
            try:
                if self._trace:
                    print 'DTCT - flipping for', rid

                (divisions, I) = self._flip_flop(cooccurrence_pd[rid],
                                                 label_fdist.samples())
                if self._trace:
                    print 'DTCT - division for', rid, 'has', I
                    print 'DTCT - division is', divisions

                if max == None or I > max[2]:
                    max = (rid, divisions, I)
            except ValueError:
                pass # no samples for that range... odd?

        if self._trace:
            print 'DTCT - complete, maximal partition is', max

        if max == None:
            return None

        # do we need to flip sx and sy? or doesn't it matter?
        (sx, nsx), (sy, nsy) = max[1]
        return max[0], sx, nsx

    def _split_instances(self, instances, fnum_range, left_fnums, right_fnums):
        """
        Splits the sequence instances of (fv_list, label) pairs into two
        parts. The first (left) part contains those instances with non-zero
        feature value for one or more feature numbers in left_fnums, and the
        second (right) part contains the same for right_fnums. Note that no
        instance can be in both lists and that instances in neither will be
        discarded.
        """
        left_instances = []
        right_instances = []
        homeless_instances = []
        for fv_list, label in instances:
            done = False
            for fnum in left_fnums:
                if fv_list[fnum]:
                    left_instances.append((fv_list, label))
                    done = True
                    break
            if not done:
                for fnum in right_fnums:
                    if fv_list[fnum]:
                        right_instances.append((fv_list, label))
                        done = True
                        break
            if not done:
                homeless_instances.append((fv_list, label))

        left_instances  += homeless_instances
        right_instances += homeless_instances

        return left_instances, right_instances

    # ahh now for the flip flop!
    def _flip_flop(self, pdist, labels):
        # find the set of features
        features = MutableSet()
        for id, label in pdist.samples():
            features.insert(id)
        features = features.elements()

        # create an arbitrary split
        left, right = cleave(features, len(features) / 2)

        # now flip!
        return self._flip(left, right, features, labels, pdist, None)
        
    def _flip(self, sx, nsx, xs, ys, prob, last = None):
        if self._trace: print 'flip', sx, nsx, last, ys
        table = []
        for y in ys:
            p1y = self._sum_probs(prob, sx, [y])
            p2y = self._sum_probs(prob, nsx, [y])
            if p1y + p2y != 0:
                table.append((p1y / (p1y + p2y), y))
            else:
                table.append((0, y))

        table.sort()
        if self._trace: print 'flip -- table', table
        max = None
        for i in range(1, len(table)):
            sy = map(lambda x: x[1], table[:i])
            nsy = map(lambda x: x[1], table[i:])
            sy.sort()
            nsy.sort()
            
            I = self._mutual_information(sx, sy, nsx, nsy, prob)
            if max == None or I > max[0]:
                    max = (I, (sy, nsy))

        if self._trace: print 'flip -- max', max
        if max == None:
            return (((sx, nsx), (ys, [])), 0.0)

        if last != None and math.fabs(max[0] - last) < 1e-6:
            return (((sx, nsx), max[1]), max[0])
        else:
            return self._flop(max[1][0], max[1][1], xs, ys, prob, max[0])

    def _flop(self, sy, nsy, xs, ys, prob, last = None):
        if self._trace: print 'flop', sy, nsy, last, xs
        table = []
        for x in xs:
            px1 = self._sum_probs(prob, [x], ys)
            px2 = self._sum_probs(prob, [x], nsy)
            if px1 + px2 != 0:
                table.append((px1 / (px1 + px2), x))
            else:
                table.append((0, x))

        table.sort()
        if self._trace: print 'flop -- table', table
        max = None
        for i in range(1, len(table)):
            sx = map(lambda x: x[1], table[:i])
            nsx = map(lambda x: x[1], table[i:])
            sx.sort()
            nsx.sort()
            
            I = self._mutual_information(sx, sy, nsx, nsy, prob)
            if max == None or I > max[0]:
                max = (I, (sx, nsx))

        if self._trace: print 'flop -- max', max
        if max == None:
            return (((xs, []), (sy, nsy)), 0.0)

        if last != None and math.fabs(max[0] - last) < 1e-6:
            return ((max[1], (sy, nsy)), max[0])
        else:
            return self._flip(max[1][0], max[1][1], xs, ys, prob, max[0])

    def _mutual_information(self, sx, sy, nsx, nsy, prob):
        q11 = self._sum_probs(prob, sx, sy)
        q12 = self._sum_probs(prob, sx, nsy)
        q21 = self._sum_probs(prob, nsx, sy)
        q22 = self._sum_probs(prob, nsx, nsy)

        # using 0 log 0 = 0
        I = 0
        if q11 != 0: I += q11 * math.log(q11 / ((q11 + q21) * (q11 + q12))) 
        if q12 != 0: I += q12 * math.log(q12 / ((q12 + q22) * (q11 + q12))) 
        if q21 != 0: I += q21 * math.log(q21 / ((q11 + q21) * (q21 + q22))) 
        if q22 != 0: I += q22 * math.log(q22 / ((q12 + q22) * (q21 + q22)))
        I = I / math.log(2)

        return I

    def _sum_probs(self, pdist, xs, ys):
        sum = 0
        for x in xs:
            for y in ys:
                sum += pdist.prob((x, y))
        return sum

def cleave(sequence, index):
    """
    Cleaves a sequence in two, returning a pair of items before the index and
    items at and after the index.
    """
    return sequence[:index], sequence[index:]


def demo():
    instances = [['bank', 'river'], ['bank', 'swim'], # river
                 ['banks', 'swim'], ['bank', 'visit'], # river
                 ['banks', 'charge'], ['bank', 'interest'], # finance
                 ['bank', 'visit'], ['banking', 'internet'], # finance
                 ['bank', 'with'], # finance
                 ['bank', 'on'], ['bank', 'with']] # depend
    labels = ['river', 'river', 'river', 'river',
              'finance', 'finance', 'finance', 'finance', 'finance',
              'depend', 'depend']
    lts = map(LabeledText, instances, labels)
    tts = map(Token, lts)

    ws = reduce(operator.add, instances)
    words = Set(*reduce(operator.add, instances)).elements() + ['foo']
    print zip(range(len(words)), words)

    first_word = FilteredFDList(lambda seq: seq[0:1], BagOfWordsFDList(words), 'first word is')
    second_word = FilteredFDList(lambda seq: seq[1:2], BagOfWordsFDList(words), 'second word is')
    fd_list = first_word + second_word

    for i in range(len(fd_list)):
        print i, '=>', fd_list.describe(i)

    print 'training...'
    trainer = DecisionTreeClassifierTrainer(fd_list, trace=False)
    classifier = trainer.train(tts)
    print 'classifier ', classifier

    tests = map(Token,
                [['banks', 'visit'],
                 ['bank', 'with'],
                 ['bank', 'swim'],
                 ['banks', 'swim'],
                 ['banks', 'swim'],
                 ['banks', 'charge'],
                 ['banks', 'on'],
                 ['banking', 'with'],
                 ['banking', 'internet'],
                 ['banking', 'foo'],
                 ['bank', 'charge']])

    print 'testing...'
    for test in tests:
        print 'classify(%s) = %s' % (test, classifier.classify(test))
        print 'dist_dict(%s) = %s' % (test, classifier.distribution_dictionary(test))
            

if __name__ == '__main__':
    demo()
