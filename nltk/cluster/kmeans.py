# Natural Language Toolkit: K-Means Clusterer
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import numpy
import random

from api import *
from util import *

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
                means.sort(cmp = _vector_compare)

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

                # recalculate cluster means by computing the centroid of each cluster
                new_means = map(self._centroid, clusters)

                # measure the degree of change from the previous step for convergence
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
        assert len(cluster) > 0
        centroid = copy.copy(cluster[0])
        for vector in cluster[1:]:
            centroid += vector
        return centroid / float(len(cluster))

    def __repr__(self):
        return '<KMeansClusterer means=%s repeats=%d>' % \
                    (self._means, self._repeats)

def _vector_compare(x, y):
    xs, ys = sum(x), sum(y)
    if xs < ys:     return -1
    elif xs > ys:   return 1
    else:           return 0

#################################################################################

def demo():
    # example from figure 14.9, page 517, Manning and Schutze

    from nltk import cluster

    vectors = [numpy.array(f) for f in [[2, 1], [1, 3], [4, 7], [6, 7]]]
    means = [[4, 3], [5, 5]]

    clusterer = cluster.KMeansClusterer(2, euclidean_distance, initial_means=means)
    clusters = clusterer.cluster(vectors, True, trace=True)

    print 'Clustered:', vectors
    print 'As:', clusters
    print 'Means:', clusterer.means()
    print

    vectors = [numpy.array(f) for f in [[3, 3], [1, 2], [4, 2], [4, 0], [2, 3], [3, 1]]]
    
    # test k-means using the euclidean distance metric, 2 means and repeat
    # clustering 10 times with random seeds

    clusterer = cluster.KMeansClusterer(2, euclidean_distance, repeats=10)
    clusters = clusterer.cluster(vectors, True)
    print 'Clustered:', vectors
    print 'As:', clusters
    print 'Means:', clusterer.means()
    print

    # classify a new vector
    vector = numpy.array([3, 3])
    print 'classify(%s):' % vector,
    print clusterer.classify(vector)
    print

if __name__ == '__main__':
    demo()

