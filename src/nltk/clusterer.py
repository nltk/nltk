# Natural Language Toolkit: Clusterers
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

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

They all extend the ClustererI interface which defines common operations
available with each clusterer. These operations include.
   - cluster: clusters a sequence of tokens
   - classify: assign a token to a cluster
   - classification_probdist: give the probability distribution over cluster memberships

The current existing classifiers also extend VectorSpaceClusterer, an
abstract class which allows for singular value decomposition (SVD) and vector
normalisation. SVD is used to reduce the dimensionality of the vector space in
such a manner as to preserve as much of the variation as possible, by
reparameterising the axes in order of variability and discarding all bar the
first d dimensions. Normalisation ensures that vectors fall in the unit
hypersphere.

Usage example (see also demo())::
    tokens = [Token(FEATURES=Numeric.array([3, 3])),
              Token(FEATURES=Numeric.array([1, 2])),
              Token(FEATURES=Numeric.array([4, 2])),
              Token(FEATURES=Numeric.array([4, 0]))]
    
    # initialise the clusterer (will also assign the tokens to clusters)
    clusterer = KMeansClusterer(2, euclidean_distance)
    clusterer.cluster(tokens, True)

    # classify a new token
    token = Token(FEATURES=Numeric.array([3, 3]))
    clusterer.classify(token)
    print token

Note that the tokens must have FEATURE attributes with Numeric array-like
objects. nltk_contrib.unimelb.tacohn.SparseArrays may be used for efficiency
when required.
"""

from nltk.chktype import chktype
from nltk.probability import DictionaryProbDist
from nltk.token import Token
import copy, LinearAlgebra, Numeric, math, random, sys, types

# Common functions

_dot = Numeric.dot
# _dot = nltk_contrib.unimelb.tacohn.sparsearray.dot

#======================================================================
# Generic interfaces
#======================================================================

class ClustererI:
    """
    Interface covering basic clustering functionality.
    """

    def cluster(self, tokens, assign_clusters=False):
        """
        Assigns the tokens to clusters, learning the clustering parameters
        from the data. Can assign a cluster identifier to each token's CLUSTER
        parameter. 
        """
        raise AssertionError()

    def classify(self, token):
        """
        Classifies the token into a cluster, setting the token's CLUSTER
        parameter to that cluster identifier.
        """
        raise AssertionError()

    def likelihood(self, labelled_token):
        """
        Returns the likelihood (a float) of the token having the
        corresponding cluster.
        """
        assert chktype(1, labelled_token, Token)
        assert labelled_token.has('CLUSTER')
        token = labelled_token.exclude('CLUSTER')
        self.classify(token)
        if token == labelled_token:
            return 1.0
        else:
            return 0.0

    def classification_probdist(self, token):
        """
        Classifies the token into a cluster, setting the token's
        CLUSTER_PROBDIST parameter to a probability distribution over the
        cluster identifiers.
        """
        assert chktype(1, token, Token)
        likelihoods = {}
        sum = 0.0
        for cluster in self.cluster_names():
            #new_token = token.copy()
            token['CLUSTER'] = cluster
            likelihoods[cluster] = self.likelihood(token)
            sum += likelihoods[cluster] 
        del token['CLUSTER']
        for cluster in self.cluster_names():
            likelihoods[cluster] /= sum
        token['CLUSTER_PROBDIST'] = DictionaryProbDist(likelihoods)

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

#======================================================================
# Vector space abstract class
#======================================================================

class VectorSpaceClusterer(ClustererI):
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
        assert chktype(1, normalise, bool)
        assert chktype(2, svd_dimensions, int, types.NoneType)
        self._Tt = None
        self._should_normalise = normalise
        self._svd_dimensions = svd_dimensions
    
    def cluster(self, tokens, assign_clusters=False, trace=False):
        assert chktype(1, tokens, [Token])
        assert chktype(2, assign_clusters, bool)
        assert chktype(3, trace, bool)
        assert len(tokens) > 0
        vectors = map(lambda tk: tk['FEATURES'], tokens)

        # normalise the vectors
        if self._should_normalise:
            vectors = map(self._normalise, vectors)

        # use SVD to reduce the dimensionality
        if self._svd_dimensions and self._svd_dimensions < len(vectors[0]):
            [u, d, vt] = LinearAlgebra.singular_value_decomposition(
                            Numeric.transpose(Numeric.array(vectors)))
            S = d[:self._svd_dimensions] * \
                Numeric.identity(self._svd_dimensions, Numeric.Float64)
            T = u[:,:self._svd_dimensions]
            Dt = vt[:self._svd_dimensions,:]
            vectors = Numeric.transpose(Numeric.matrixmultiply(S, Dt))
            self._Tt = Numeric.transpose(T)
            
        # call abstract method to cluster the vectors
        self.cluster_vectorspace(vectors, trace)

        # assign the tokens to clusters
        if assign_clusters:
            for token in tokens:
                self.classify(token)

    def cluster_vectorspace(self, vectors, trace):
        """
        Finds the clusters using the given set of vectors.
        """
        raise AssertionError()

    def classify(self, token):
        assert chktype(1, token, Token)
        vector = token['FEATURES']
        #assert chktype('features', vector, Numeric.array([]), SparseArray)
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = Numeric.matrixmultiply(self._Tt, vector)
        cluster = self.classify_vectorspace(vector)
        token['CLUSTER'] = self.cluster_name(cluster)

    def classify_vectorspace(self, vector):
        """
        Returns the index of the appropriate cluster for the vector.
        """
        raise AssertionError()

    def likelihood(self, labelled_token):
        assert chktype(1, labelled_token, Token)
        vector = labelled_token['FEATURES']
        #assert chktype('features', vector, Numeric.array([]), SparseArray)
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = Numeric.matrixmultiply(self._Tt, vector)
        return self.likelihood_vectorspace(vector, labelled_token['CLUSTER'])

    def likelihood_vectorspace(self, vector, cluster):
        """
        Returns the likelihood of the vector belonging to the cluster.
        """
        #assert chktype(1, vector, Numeric.array([]), SparseArray)
        predicted = self.classify_vectorspace(vector)
        if cluster == predicted: return 1.0
        else:                    return 0.0

    def vector(self, token):
        """
        Returns the vector after normalisation and dimensionality reduction
        for the given token's FEATURES.
        """
        assert chktype(1, token, Token)
        vector = token['FEATURES']
        #assert chktype('features', vector, Numeric.array([]), SparseArray)
        if self._should_normalise:
            vector = self._normalise(vector)
        if self._Tt != None:
            vector = Numeric.matrixmultiply(self._Tt, vector)
        return vector

    def _normalise(self, vector):
        """
        Normalises the vector to unit length.
        """
        #assert chktype(1, vector, Numeric.array([]), SparseArray)
        return vector / math.sqrt(_dot(vector, vector))

#======================================================================
# K-Means clusterer
#======================================================================

class KMeansClusterer(VectorSpaceClusterer):
    """
    The K-means clusterer starts with k arbitrary chosen means then allocates
    each vector to the cluster with the closest mean. It then recalculates the
    means of each cluster as the centroid of the vectors in the cluster. This
    process repeats until the cluster memberships stabilise. This is a
    hill-climbing algorithm which may converge to a local maximum. Hence the
    clustering is often repeated with random initial means and the most
    commonly occuring output means are chosen.
    """

    def __init__(self, num_means, distance, repeats=1,
                       conv_test=1e-6, initial_means=None,
                       normalise=False, svd_dimensions=None,
                       rng=None):
        """
        @param  num_means:  the number of means to use (may use fewer)
        @type   num_means:  int
        @param  distance:   measure of distance between two vectors
        @type   distance:   function taking two vectors and returing a float
        @param  repeats:    number of randomised clustering trials to use
        @type   repeats:    int
        @param  conv_test:  maximum variation in mean differences before
                            deemed convergent
        @type   conv_test:  number
        @param  initial_means: set of k initial means
        @type   initial_means: sequence of vectors
        @param  normalise:  should vectors be normalised to length 1
        @type   normalise:  boolean
        @param svd_dimensions: number of dimensions to use in reducing vector
                               dimensionsionality with SVD
        @type svd_dimensions: int 
        @param  rng:        random number generator (or None)
        @type   rng:        Random
        """
        assert chktype(1, num_means, int)
        #assert chktype(2, distance, ...)
        assert chktype(3, repeats, int)
        assert chktype(4, conv_test, int, float)
        #assert chktype(5, initial_means, [Numeric.array([])], [SparseArray])
        assert chktype(6, normalise, bool)
        assert chktype(7, svd_dimensions, int, types.NoneType)
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._num_means = num_means
        self._distance = distance
        self._max_difference = conv_test
        assert not initial_means or len(initial_means) == num_means
        self._means = initial_means
        assert repeats >= 1
        assert not (initial_means and repeats > 1)
        self._repeats = repeats
        if rng: self._rng = rng
        else:   self._rng = random.Random()

    def cluster_vectorspace(self, vectors, trace=False):
        if self._means and self._repeats > 1:
            print 'Warning: means will be discarded for subsequent trials'

        meanss = []
        for trial in range(self._repeats):
            if trace: print 'k-means trial', trial
            if not self._means or trial > 1:
                self._means = self._rng.sample(vectors, self._num_means)
            self._cluster_vectorspace(vectors, trace)
            meanss.append(self._means)

        if len(meanss) > 1:
            # sort the means first (so that different cluster numbering won't
            # effect the distance comparison)
            for means in meanss:
                means.sort()

            # find the set of means that's minimally different from the others
            min_difference = min_means = None
            for i in range(len(meanss)):
                d = 0
                for j in range(len(meanss)):
                    if i != j:
                        d += self._sum_distances(meanss[i], meanss[j])
                if min_difference == None or d < min_difference:
                    min_difference, min_means = d, meanss[i]

            # use the best means
            self._means = min_means

    def _cluster_vectorspace(self, vectors, trace=False):
        if self._num_means < len(vectors):
            # perform k-means clustering
            converged = False
            while not converged:
                # assign the tokens to clusters based on minimum distance to
                # the cluster means
                clusters = [[] for m in range(self._num_means)]
                for vector in vectors:
                    index = self.classify_vectorspace(vector)
                    clusters[index].append(vector)

                if trace: print 'iteration'
                #for i in range(self._num_means):
                    #print '  mean', i, 'allocated', len(clusters[i]), 'vectors'

                # recalcluate the cluster means by computing the centroid of
                # each cluster
                new_means = map(self._centroid, clusters)

                # measure the degree of change in the means from the previous
                # step for convergence
                difference = self._sum_distances(self._means, new_means)
                if difference < self._max_difference:
                    converged = True

                # remember the new means
                self._means = new_means

    def classify_vectorspace(self, vector):
        # finds the closest cluster centroid
        # returns that cluster's index
        best_distance = best_index = None
        for index in range(len(self._means)):
            mean = self._means[index]
            dist = self._distance(vector, mean)
            if best_distance == None or dist < best_distance:
                best_index, best_distance = index, dist
        return best_index

    def num_clusters(self):
        if self._means:
            return len(self._means)
        else:
            return self._num_means

    def means(self):
        """
        The means used for clustering.
        """
        return self._means

    def _sum_distances(self, vectors1, vectors2):
        difference = 0.0
        for u, v in zip(vectors1, vectors2):
            difference += self._distance(u, v) 
        return difference

    def _centroid(self, cluster):
        assert chktype(1, cluster, [])
        assert len(cluster) > 0
        centroid = copy.copy(cluster[0])
        for vector in cluster[1:]:
            centroid += vector
        return centroid / float(len(cluster))

    def __repr__(self):
        return '<KMeansClusterer means=%s repeats=%d>' % \
                    (self._means, self._repeats)

#======================================================================
# Group average agglomerative clusterer
#======================================================================

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
    Represents a dendogram, a tree with a speficied branching order.  This
    must be initialised with the leaf items, then iteratively call merge for
    each branch. This class constructs a tree representing the order of calls
    to the merge function.
    """

    def __init__(self, items=[]):
        """
        @param  items: the items at the leaves of the dendogram
        @type   items: sequence of (any)
        """
        assert chktype(1, items, [])
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
        assert chktype(1, indices, [int], (int,))
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
        assert chktype(1, n, int)
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

class GroupAverageAgglomerativeClusterer(VectorSpaceClusterer):
    """
    The GAAC clusterer starts with each of the N vectors as singleton
    clusters. It then iteratively merges pairs of clusters which have the
    closest centroids.  This continues until there is only one cluster. The
    order of merges gives rise to a dendogram - a tree with the earlier merges
    lower than later merges. The membership of a given number of clusters c, 1
    <= c <= N, can be found by cutting the dendogram at depth c.

    This clusterer uses the cosine similarity metric only, which allows for
    efficient speed-up in the clustering process. 
    """

    def __init__(self, num_clusters=1, normalise=True, svd_dimensions=None):
        assert chktype(1, num_clusters, int)
        assert chktype(2, normalise, bool)
        assert chktype(3, svd_dimensions, int, types.NoneType)
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._num_clusters = num_clusters
        self._dendogram = None
        self._groups_values = None

    def cluster(self, tokens, assign_clusters=False, trace=False):
        # stores the merge order
        self._dendogram = Dendogram([Numeric.array(tk['FEATURES'],
        Numeric.Float64) for tk in tokens])
            
        return VectorSpaceClusterer.cluster(self, tokens,
                                            assign_clusters, trace)

    def cluster_vectorspace(self, vectors, trace=False):
        # create a cluster for each vector
        clusters = [[vector] for vector in vectors]

        # the sum vectors
        vector_sum = copy.copy(vectors)

        while len(clusters) > max(self._num_clusters, 1):
            # find the two best candidate clusters to merge, based on their
            # S(union c_i, c_j)
            best = None
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    sim = self._average_similarity(
                                vector_sum[i], len(clusters[i]),
                                vector_sum[j], len(clusters[j]))
                    if not best or sim > best[0]:
                        best = (sim, i, j)

            # merge them and replace in cluster list
            i, j = best[1:]
            sum = clusters[i] + clusters[j]
            if trace: print 'merging %d and %d' % (i, j)

            clusters[i] = sum
            del clusters[j]
            vector_sum[i] = vector_sum[i] + vector_sum[j]
            del vector_sum[j]

            self._dendogram.merge(i, j)

        self.update_clusters(self._num_clusters)

    def update_clusters(self, num_clusters):
        clusters = self._dendogram.groups(num_clusters)
        self._centroids = []
        for cluster in clusters:
            assert len(cluster) > 0
            if self._should_normalise:
                centroid = self._normalise(cluster[0])
            else:
                centroid = Numeric.array(cluster[0])
            for vector in cluster[1:]:
                if self._should_normalise:
                    centroid += self._normalise(vector)
                else:
                    centroid += vector
            centroid /= float(len(cluster))
            self._centroids.append(centroid)
        self._num_clusters = len(self._centroids)

    def classify_vectorspace(self, vector):
        best = None
        for i in range(self._num_clusters):
            centroid = self._centroids[i]
            sim = self._average_similarity(vector, 1, centroid, 1)
            if not best or sim > best[0]:
                best = (sim, i)
        return best[1]

    def dendogram(self):
        """
        @return: The dendogram representing the current clustering
        @rtype:  Dendogram
        """
        return self._dendogram

    def num_clusters(self):
        return self._num_clusters

    def _average_similarity(self, v1, l1, v2, l2):
        sum = v1 + v2
        length = l1 + l2
        return (_dot(sum, sum) - length) / (length * (length - 1))

    def __repr__(self):
        return '<GroupAverageAgglomerativeClusterer n=%d>' % self._num_clusters

class ExpectationMaximizationClusterer(VectorSpaceClusterer):
    """
    The Gaussian EM clusterer models the vectors as being produced by a
    mixture of k Gaussian sources. The parameters of these sources (prior
    probability, mean and covariance matrix) are then found to maximise the
    likelihood of the given data. This is done with the expectation
    maximisation algorithm. It starts with k arbitrarily chosen means, priors
    and covariance matrices. It then calculates the membership probabilities
    for each vector in each of the clusters - this is the 'E' step. The
    cluster parameters are then updated in the 'M' step using the maximum
    likelihood estimate from the cluster membership probabilities. This
    process continues until the likelihood of the data does not significantly
    increase.
    """

    def __init__(self, initial_means, priors=None, covariance_matrices=None,
                       conv_threshold=1e-6, bias=0.1, normalise=False,
                       svd_dimensions=None):
        """
        Creates an EM clusterer with the given starting parameters,
        convergence threshold and vector mangling parameters.

        @param  initial_means: the means of the gaussian cluster centers
        @type   initial_means: [seq of] Numeric array or seq of SparseArray
        @param  priors: the prior probability for each cluster
        @type   priors: Numeric array or seq of float
        @param  covariance_matrices: the covariance matrix for each cluster
        @type   covariance_matrices: [seq of] Numeric array 
        @param  conv_threshold: maximum change in likelihood before deemed
                    convergent
        @type   conv_threshold: int or float
        @param  bias: variance bias used to ensure non-singular covariance
                      matrices
        @type   bias: float
        @param  normalise:  should vectors be normalised to length 1
        @type   normalise:  boolean
        @param  svd_dimensions: number of dimensions to use in reducing vector
                               dimensionsionality with SVD
        @type   svd_dimensions: int 
        """
        #assert chktype(1, initial_means, [])
        #assert chktype(2, priors, [], types.NoneType)
        #assert chktype(3, covariance_matrices, [], types.NoneType)
        assert chktype(4, conv_threshold, float, int)
        assert chktype(6, normalise, bool)
        assert chktype(7, svd_dimensions, int, types.NoneType)
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._means = Numeric.array(initial_means, Numeric.Float64)
        self._num_clusters = len(initial_means)
        self._conv_threshold = conv_threshold
        self._covariance_matrices = covariance_matrices
        self._priors = priors
        self._bias = bias

    def num_clusters(self):
        return self._num_clusters
        
    def cluster_vectorspace(self, vectors, trace=False):
        assert len(vectors) > 0

        # set the parameters to initial values
        dimensions = len(vectors[0])
        means = self._means
        priors = self._priors
        if not priors:
            priors = self._priors = Numeric.ones(self._num_clusters,
                                        Numeric.Float64) / self._num_clusters
        covariances = self._covariance_matrices 
        if not covariances:
            covariances = self._covariance_matrices = \
                [ Numeric.identity(dimensions, Numeric.Float64) 
                  for i in range(self._num_clusters) ]
            
        # do the E and M steps until the likelihood plateaus
        lastl = self._loglikelihood(vectors, priors, means, covariances)
        converged = False

        while not converged:
            if trace: print 'iteration; loglikelihood', lastl
            # E-step, calculate hidden variables, h[i,j]
            h = Numeric.zeros((len(vectors), self._num_clusters),
                Numeric.Float64)
            for i in range(len(vectors)):
                for j in range(self._num_clusters):
                    h[i,j] = priors[j] * self._gaussian(means[j],
                                               covariances[j], vectors[i])
                h[i,:] /= sum(h[i,:])

            # M-step, update parameters - cvm, p, mean
            for j in range(self._num_clusters):
                covariance_before = covariances[j]
                new_covariance = Numeric.zeros((dimensions, dimensions),
                            Numeric.Float64)
                new_mean = Numeric.zeros(dimensions, Numeric.Float64)
                sum_hj = 0.0
                for i in range(len(vectors)):
                    delta = vectors[i] - means[j]
                    new_covariance += h[i,j] * \
                        Numeric.multiply.outer(delta, delta)
                    sum_hj += h[i,j]
                    new_mean += h[i,j] * vectors[i]
                covariances[j] = new_covariance / sum_hj
                means[j] = new_mean / sum_hj
                priors[j] = sum_hj / len(vectors)

                # bias term to stop covariance matrix being singular
                covariances[j] += self._bias * \
                    Numeric.identity(dimensions, Numeric.Float64)

            # calculate likelihood - FIXME: may be broken
            l = self._loglikelihood(vectors, priors, means, covariances)

            # check for convergence
            if abs(lastl - l) < self._conv_threshold:
                converged = True
            lastl = l

    def classify_vectorspace(self, vector):
        best = None
        for j in range(self._num_clusters):
            p = self._priors[j] * self._gaussian(self._means[j],
                                    self._covariance_matrices[j], vector)
            if not best or p > best[0]:
                best = (p, j)
        return best[1]

    def likelihood_vectorspace(self, vector, cluster):
        cid = self.cluster_names().index(cluster)
        return self._priors[cluster] * self._gaussian(self._means[cluster],
                                self._covariance_matrices[cluster], vector)

    def _gaussian(self, mean, cvm, x):
        m = len(mean)
        assert cvm.shape == (m, m), \
            'bad sized covariance matrix, %s' % str(cvm.shape)
        try:
            det = LinearAlgebra.determinant(cvm)
            inv = LinearAlgebra.inverse(cvm)
            a = det ** -0.5 * (2 * Numeric.pi) ** (-m / 2.0) 
            dx = x - mean
            b = -0.5 * Numeric.matrixmultiply( \
                    Numeric.matrixmultiply(dx, inv), dx)
            return a * Numeric.exp(b) 
        except OverflowError:
            # happens when the exponent is negative infinity - i.e. b = 0
            # i.e. the inverse of cvm is huge (cvm is almost zero)
            return 0

    def _loglikelihood(self, vectors, priors, means, covariances):
        llh = 0.0
        for vector in vectors:
            p = 0
            for j in range(len(priors)):
                p += priors[j] * \
                         self._gaussian(means[j], covariances[j], vector)
            llh += Numeric.log(p)
        return llh

    def __repr__(self):
        return '<ExpectionMaximizationClusterer means=%s>' % list(self._means)

def euclidean_distance(u, v):
    """
    Returns the euclidean distance between vectors u and v. This is equivalent
    to the length of the vector (u - v).
    """
    diff = u - v
    return math.sqrt(_dot(diff, diff))

def cosine_distance(u, v):
    """
    Returns the cosine of the angle between vectors v and u. This is equal to
    u.v / |u||v|.
    """
    return _dot(u, v) / (math.sqrt(_dot(u, u)) * math.sqrt(_dot(v, v)))

def demo():
    """
    Non-interactive demonstration of the clusterers with simple 2-D data.
    """
    # use a set of tokens with 2D indices
    tokens = [Token(FEATURES=Numeric.array([3, 3])),
              Token(FEATURES=Numeric.array([1, 2])),
              Token(FEATURES=Numeric.array([4, 2])),
              Token(FEATURES=Numeric.array([4, 0])),
              Token(FEATURES=Numeric.array([2, 3])),
              Token(FEATURES=Numeric.array([3, 1]))]
    
    # test k-means using the euclidean distance metric, 2 means and repeat
    # clustering 10 times with random seeds
    clusterer = KMeansClusterer(2, euclidean_distance, repeats=10)
    clusterer.cluster(tokens, True)
    print 'using clusterer', clusterer
    print 'clustered', str(tokens)[:60], '...'
    # classify a new token
    token = Token(FEATURES=Numeric.array([3, 3]))
    print 'classify(%s)' % token,
    clusterer.classify(token)
    print token

    # test the GAAC clusterer with 4 clusters
    clusterer = GroupAverageAgglomerativeClusterer(4)
    print 'using clusterer', clusterer
    clusterer.cluster(tokens, True)
    #print 'clustered', str(tokens)[:60], '...'
    print 'clustered', tokens
    # show the dendogram
    clusterer.dendogram().show()
    # classify a new token
    token = Token(FEATURES=Numeric.array([3, 3]))
    print 'classify(%s)' % token,
    clusterer.classify(token)
    print token
    print

    # test the EM clusterer with means given by k-means (2) and
    # dimensionality reduction
    clusterer = KMeansClusterer(2, euclidean_distance, svd_dimensions=1)
    clusterer.cluster(tokens)
    means = clusterer.means()
    clusterer = ExpectationMaximizationClusterer(means, svd_dimensions=1)
    clusterer.cluster(tokens, True)
    print 'using clusterer', clusterer
    print 'clustered', str(tokens)[:60], '...'
    # classify a new token
    token = Token(FEATURES=Numeric.array([3, 3]))
    print 'classify(%s)' % token,
    clusterer.classify(token)
    print token
    # show the classification probabilities
    token = Token(FEATURES=Numeric.array([2.2, 2]))
    print 'classification_probdist(%s)' % token
    clusterer.classification_probdist(token)
    for sample in token['CLUSTER_PROBDIST'].samples():
        print '%s => %.0f%%' % (sample,
                    token['CLUSTER_PROBDIST'].prob(sample) *100)

def demo_kmeans():
    # example from figure 14.9, page 517, Manning and Schutze
    tokens = [Token(FEATURES=Numeric.array(f))
              for f in [[2, 1], [1, 3], [4, 7], [6, 7]]]
    means = [[4, 3], [5, 5]]

    clusterer = KMeansClusterer(2, euclidean_distance, initial_means=means)
    clusterer.cluster(tokens, True, trace=True)

    print 'clustered', tokens
    print 'means', clusterer.means()

def demo_em():
    # example from figure 14.10, page 519, Manning and Schutze
    tokens = [Token(FEATURES=Numeric.array(f))
              for f in [[0.5, 0.5], [1.5, 0.5], [1, 3]]]
    means = [[4, 2], [4, 2.01]]

    clusterer = ExpectationMaximizationClusterer(means, bias=0.1)
    clusterer.cluster(tokens, True, trace=True)

    print 'clustered', tokens
    for c in range(2):
        print 'cluster %d' % c
        print 'prior', clusterer._priors[c]
        print 'mean ', clusterer._means[c]
        print 'covar', clusterer._covariance_matrices[c]

    # classify a new token
    token = Token(FEATURES=Numeric.array([2, 2]))
    print 'classify(%s)' % token,
    clusterer.classify(token)
    print token

    # show the classification probabilities
    token = Token(FEATURES=Numeric.array([2, 2]))
    print 'classification_probdist(%s)' % token
    clusterer.classification_probdist(token)
    for sample in token['CLUSTER_PROBDIST'].samples():
        print '%s => %.0f%%' % (sample,
                    token['CLUSTER_PROBDIST'].prob(sample) *100)

if __name__ == '__main__':
    demo()
    #demo_em()
    #demo_kmeans()
