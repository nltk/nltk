# Natural Language Toolkit: Group Average Agglomerative Clusterer
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import numpy
import copy

from nltk.cluster.util import VectorSpaceClusterer, Dendrogram

class GAAClusterer(VectorSpaceClusterer):
    """
    The Group Average Agglomerative starts with each of the N vectors as singleton
    clusters. It then iteratively merges pairs of clusters which have the
    closest centroids.  This continues until there is only one cluster. The
    order of merges gives rise to a dendrogram: a tree with the earlier merges
    lower than later merges. The membership of a given number of clusters c, 1
    <= c <= N, can be found by cutting the dendrogram at depth c.

    This clusterer uses the cosine similarity metric only, which allows for
    efficient speed-up in the clustering process.
    """

    def __init__(self, num_clusters=1, normalise=True, svd_dimensions=None):
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._num_clusters = num_clusters
        self._dendrogram = None
        self._groups_values = None

    def cluster(self, vectors, assign_clusters=False, trace=False):
        # stores the merge order
        self._dendrogram = Dendrogram(
            [numpy.array(vector, numpy.float64) for vector in vectors])
        return VectorSpaceClusterer.cluster(self, vectors, assign_clusters, trace)

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

            self._dendrogram.merge(i, j)

        self.update_clusters(self._num_clusters)

    def update_clusters(self, num_clusters):
        clusters = self._dendrogram.groups(num_clusters)
        self._centroids = []
        for cluster in clusters:
            assert len(cluster) > 0
            if self._should_normalise:
                centroid = self._normalise(cluster[0])
            else:
                centroid = numpy.array(cluster[0])
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

    def dendrogram(self):
        """
        :return: The dendrogram representing the current clustering
        :rtype:  Dendrogram
        """
        return self._dendrogram

    def num_clusters(self):
        return self._num_clusters

    def _average_similarity(self, v1, l1, v2, l2):
        sum = v1 + v2
        length = l1 + l2
        return (numpy.dot(sum, sum) - length) / (length * (length - 1))

    def __repr__(self):
        return '<GroupAverageAgglomerative Clusterer n=%d>' % self._num_clusters

def demo():
    """
    Non-interactive demonstration of the clusterers with simple 2-D data.
    """

    from nltk.cluster import GAAClusterer

    # use a set of tokens with 2D indices
    vectors = [numpy.array(f) for f in [[3, 3], [1, 2], [4, 2], [4, 0], [2, 3], [3, 1]]]

    # test the GAAC clusterer with 4 clusters
    clusterer = GAAClusterer(4)
    clusters = clusterer.cluster(vectors, True)

    print 'Clusterer:', clusterer
    print 'Clustered:', vectors
    print 'As:', clusters
    print

    # show the dendrogram
    clusterer.dendrogram().show()

    # classify a new vector
    vector = numpy.array([3, 3])
    print 'classify(%s):' % vector,
    print clusterer.classify(vector)
    print


if __name__ == '__main__':
    demo()
