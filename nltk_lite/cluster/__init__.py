# Natural Language Toolkit: Clusterers
#
# Copyright (C) 2004-2006 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# Porting: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module contains a number of basic clustering algorithms. Clustering
describes the task of discovering groups of similar items with a large
collection. It is also describe as unsupervised machine learning, as the data
from which it learns is unannotated with class information, as is the case for
supervised learning.  Annotated data is difficult and expensive to obtain in
the quantities required for the majority of supervised learning algorithms.
This problem, the knowledge acquisition bottleneck, is common to most natural
language processing tasks, thus fueling the need for quality unsupervised
approaches.

This module contains a k-means clusterer, E-M clusterer and a group average
agglomerative clusterer (GAAC). All these clusterers involve finding good
cluster groupings for a set of vectors in multi-dimensional space.

The K-means clusterer starts with k arbitrary chosen means then allocates each
vector to the cluster with the closest mean. It then recalculates the means of
each cluster as the centroid of the vectors in the cluster. This process
repeats until the cluster memberships stabilise. This is a hill-climbing
algorithm which may converge to a local maximum. Hence the clustering is
often repeated with random initial means and the most commonly occurring
output means are chosen.

The GAAC clusterer starts with each of the M{N} vectors as singleton clusters.
It then iteratively merges pairs of clusters which have the closest centroids.
This continues until there is only one cluster. The order of merges gives rise
to a dendogram - a tree with the earlier merges lower than later merges. The
membership of a given number of clusters M{c}, M{1 <= c <= N}, can be found by
cutting the dendogram at depth M{c}.

The Gaussian EM clusterer models the vectors as being produced by a mixture
of k Gaussian sources. The parameters of these sources (prior probability,
mean and covariance matrix) are then found to maximise the likelihood of the
given data. This is done with the expectation maximisation algorithm. It
starts with k arbitrarily chosen means, priors and covariance matrices. It
then calculates the membership probabilities for each vector in each of the
clusters - this is the 'E' step. The cluster parameters are then updated in
the 'M' step using the maximum likelihood estimate from the cluster membership
probabilities. This process continues until the likelihood of the data does
not significantly increase.

They all extend the ClusterI interface which defines common operations
available with each clusterer. These operations include.
   - cluster: clusters a sequence of vectors
   - classify: assign a vector to a cluster
   - classification_probdist: give the probability distribution over cluster memberships

The current existing classifiers also extend cluster.VectorSpace, an
abstract class which allows for singular value decomposition (SVD) and vector
normalisation. SVD is used to reduce the dimensionality of the vector space in
such a manner as to preserve as much of the variation as possible, by
reparameterising the axes in order of variability and discarding all bar the
first d dimensions. Normalisation ensures that vectors fall in the unit
hypersphere.

Usage example (see also demo())::
    vectors = [array(f) for f in [[3, 3], [1, 2], [4, 2], [4, 0]]]
    
    # initialise the clusterer (will also assign the vectors to clusters)
    clusterer = cluster.KMeans(2, euclidean_distance)
    clusterer.cluster(vectors, True)

    # classify a new vector
    print clusterer.classify(array([3, 3]))

Note that the vectors must use numarray array-like
objects. nltk_contrib.unimelb.tacohn.SparseArrays may be used for
efficiency when required.
"""

from nltk_lite.probability import DictionaryProbDist
import copy, numarray, math, random, sys, types
from numarray import array, linear_algebra

#======================================================================
# Generic interfaces
#======================================================================

class ClusterI:
    """
    Interface covering basic clustering functionality.
    """

    def cluster(self, vectors, assign_clusters=False):
        """
        Assigns the vectors to clusters, learning the clustering parameters
        from the data. Returns a cluster identifier for each vector.
        """
        raise AssertionError()

    def classify(self, token):
        """
        Classifies the token into a cluster, setting the token's CLUSTER
        parameter to that cluster identifier.
        """
        raise AssertionError()

    def likelihood(self, vector, label):
        """
        Returns the likelihood (a float) of the token having the
        corresponding cluster.
        """
        if self.classify(vector) == label:
            return 1.0
        else:
            return 0.0

    def classification_probdist(self, vector):
        """
        Classifies the token into a cluster, returning
        a probability distribution over the cluster identifiers.
        """
        likelihoods = {}
        sum = 0.0
        for cluster in self.cluster_names():
            likelihoods[cluster] = self.likelihood(vector, cluster)
            sum += likelihoods[cluster] 
        for cluster in self.cluster_names():
            likelihoods[cluster] /= sum
        return DictionaryProbDist(likelihoods)

    def num_clusters(self):
        """
        Returns the number of clusters.
        """
        raise AssertError()

    def cluster_names(self):
        """
        Returns the names of the clusters.
        """
        return range(self.num_clusters())

    def cluster_name(self, index):
        """
        Returns the names of the cluster at index.
        """
        return index

class VectorSpace(ClusterI):
    """
    Abstract clusterer which takes tokens and maps them into a vector space.
    Optionally performs singular value decomposition to reduce the
    dimensionality.
    """
    def __init__(self, normalise=False, svd_dimensions=None):
        """
        @param normalise:       should vectors be normalised to length 1
        @type normalise:        boolean
        @param svd_dimensions:  number of dimensions to use in reducing vector
                                dimensionsionality with SVD
        @type svd_dimensions:   int 
        """
        self._Tt = None
        self._should_normalise = normalise
        self._svd_dimensions = svd_dimensions
    
    def cluster(self, vectors, assign_clusters=False, trace=False):
        assert len(vectors) > 0

        # normalise the vectors
        if self._should_normalise:
            vectors = map(self._normalise, vectors)

        # use SVD to reduce the dimensionality
        if self._svd_dimensions and self._svd_dimensions < len(vectors[0]):
            [u, d, vt] = linear_algebra.singular_value_decomposition(
                            numarray.transpose(array(vectors)))
            S = d[:self._svd_dimensions] * \
                numarray.identity(self._svd_dimensions, numarray.Float64)
            T = u[:,:self._svd_dimensions]
            Dt = vt[:self._svd_dimensions,:]
            vectors = numarray.transpose(numarray.matrixmultiply(S, Dt))
            self._Tt = numarray.transpose(T)
            
        # call abstract method to cluster the vectors
        self.cluster_vectorspace(vectors, trace)

        # assign the vectors to clusters
        if assign_clusters:
            print self._Tt, vectors
            return [self.classify(vector) for vector in vectors]

    def cluster_vectorspace(self, vectors, trace):
        """
        Finds the clusters using the given set of vectors.
        """
        raise AssertionError()

    def classify(self, vector):
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = numarray.matrixmultiply(self._Tt, vector)
        cluster = self.classify_vectorspace(vector)
        return self.cluster_name(cluster)

    def classify_vectorspace(self, vector):
        """
        Returns the index of the appropriate cluster for the vector.
        """
        raise AssertionError()

    def likelihood(self, vector, label):
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = numarray.matrixmultiply(self._Tt, vector)
        return self.likelihood_vectorspace(vector, label)

    def likelihood_vectorspace(self, vector, cluster):
        """
        Returns the likelihood of the vector belonging to the cluster.
        """
        predicted = self.classify_vectorspace(vector)
        if cluster == predicted: return 1.0
        else:                    return 0.0

    def vector(self, vector):
        """
        Returns the vector after normalisation and dimensionality reduction
        """
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = numarray.matrixmultiply(self._Tt, vector)
        return vector

    def _normalise(self, vector):
        """
        Normalises the vector to unit length.
        """
        return vector / math.sqrt(numarray.dot(vector, vector))

class _DendogramNode:
    """ Tree node of a dendogram. """

    def __init__(self, value, *children):
        self._value = value
        self._children = children

    def leaves(self, values=True):
        if self._children:
            leaves = []
            for child in self._children:
                leaves.extend(child.leaves(values))
            return leaves
        elif values:
            return [self._value]
        else:
            return [self]

    def groups(self, n):
        queue = [(self._value, self)]

        while len(queue) < n:
            priority, node = queue.pop()
            if not node._children:
                queue.push((priority, node))
                break
            for child in node._children:
                if child._children:
                    queue.append((child._value, child))
                else:
                    queue.append((0, child))
            # makes the earliest merges at the start, latest at the end
            queue.sort()

        groups = []
        for priority, node in queue:
            groups.append(node.leaves())
        return groups

class Dendogram:
    """
    Represents a dendogram, a tree with a specified branching order.  This
    must be initialised with the leaf items, then iteratively call merge for
    each branch. This class constructs a tree representing the order of calls
    to the merge function.
    """

    def __init__(self, items=[]):
        """
        @param  items: the items at the leaves of the dendogram
        @type   items: sequence of (any)
        """
        self._items = [_DendogramNode(item) for item in items]
        self._original_items = copy.copy(self._items)
        self._merge = 1

    def merge(self, *indices):
        """
        Merges nodes at given indices in the dendogram. The nodes will be
        combined which then replaces the first node specified. All other nodes
        involved in the merge will be removed.

        @param  indices: indices of the items to merge (at least two)
        @type   indices: seq of int
        """
        assert len(indices) >= 2
        node = _DendogramNode(self._merge, *[self._items[i] for i in indices])
        self._merge += 1
        self._items[indices[0]] = node
        for i in indices[1:]:
            del self._items[i]

    def groups(self, n):
        """
        Finds the n-groups of items (leaves) reachable from a cut at depth n.
        @param  n: number of groups
        @type   n: int
        """
        if len(self._items) > 1:
            root = _DendogramNode(self._merge, *self._items)
        else:
            root = self._items[0]
        return root.groups(n)

    def show(self):
        """
        Print the dendogram in ASCII art to standard out.
        """

        # ASCII rendering characters
        JOIN, HLINK, VLINK = '+', '-', '|'

        # find the root (or create one)
        if len(self._items) > 1:
            root = _DendogramNode(self._merge, *self._items)
        else:
            root = self._items[0]
        leaves = self._original_items
        
        # find the bottom row and the best cell width
        last_row = [str(leaf._value) for leaf in leaves]
        width = max(map(len, last_row)) + 1
        lhalf = width / 2
        rhalf = width - lhalf - 1

        # display functions
        def format(centre, left=' ', right=' '):
            return '%s%s%s' % (lhalf*left, centre, right*rhalf)
        def display(str):
            sys.stdout.write(str)

        # for each merge, top down
        queue = [(root._value, root)]
        verticals = [ format(' ') for leaf in leaves ]
        while queue:
            priority, node = queue.pop()
            child_left_leaf = map(lambda c: c.leaves(False)[0], node._children)
            indices = map(leaves.index, child_left_leaf)
            if child_left_leaf:
                min_idx = min(indices)
                max_idx = max(indices)
            for i in range(len(leaves)):
                if leaves[i] in child_left_leaf:
                    if i == min_idx:    display(format(JOIN, ' ', HLINK))
                    elif i == max_idx:  display(format(JOIN, HLINK, ' '))
                    else:               display(format(JOIN, HLINK, HLINK))
                    verticals[i] = format(VLINK)
                elif min_idx <= i <= max_idx:
                    display(format(HLINK, HLINK, HLINK))
                else:
                    display(verticals[i])
            display('\n')
            for child in node._children:
                if child._children:
                    queue.append((child._value, child))
            queue.sort()

            for vertical in verticals:
                display(vertical)
            display('\n')

        # finally, display the last line
        display(''.join([item.center(width) for item in last_row]))
        display('\n')
        
    def __repr__(self):
        if len(self._items) > 1:
            root = _DendogramNode(self._merge, *self._items)
        else:
            root = self._items[0]
        leaves = root.leaves(False)
        return '<Dendogram with %d leaves>' % len(leaves)

########################################################################

from kmeans import *
from gaac import *
from em import *
