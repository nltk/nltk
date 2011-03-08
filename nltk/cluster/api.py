# Natural Language Toolkit: Clusterer Interfaces
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# Porting: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.probability import DictionaryProbDist

class ClusterI(object):
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

