from nltk.classify.api import ClassifierI
from nltk.probability import FreqDist
import math

class DecisionTreeClassifier(ClassifierI):
    """
    A decision tree classifier for text classification tasks.

    This classifier builds a decision tree based on the information gain
    of features in the training data.

    Parameters:
    -----------
    max_depth : int, optional (default=None)
        The maximum depth of the decision tree.
    """

    def __init__(self, max_depth=None):
        self.max_depth = max_depth
        self.tree = None

    def train(self, labeled_featuresets):
        """
        Train the decision tree classifier.

        Parameters:
        -----------
        labeled_featuresets : list of (dict, label) tuples
            The training data, where each tuple contains a feature dictionary
            and its corresponding label.
        """
        features = list(labeled_featuresets[0][0].keys())
        self.tree = self._build_tree(labeled_featuresets, features, 0)

    def _build_tree(self, data, features, depth):
        """
        Recursively build the decision tree.

        Parameters:
        -----------
        data : list of (dict, label) tuples
            The dataset to build the tree on.
        features : list of str
            The list of features to consider for splitting.
        depth : int
            The current depth of the tree.

        Returns:
        --------
        dict or str
            The decision tree (or leaf node) for the given data.
        """
        labels = [label for _, label in data]
        if len(set(labels)) == 1:
            return labels[0]
        if depth == self.max_depth or not features:
            return max(set(labels), key=labels.count)

        best_feature = max(features, key=lambda f: self._information_gain(data, f))
        tree = {best_feature: {}}

        for value in set(sample[0][best_feature] for sample in data):
            subset = [sample for sample in data if sample[0][best_feature] == value]
            new_features = [f for f in features if f != best_feature]
            tree[best_feature][value] = self._build_tree(subset, new_features, depth + 1)

        return tree

    def _information_gain(self, data, feature):
        """
        Calculate the information gain for a feature.

        Parameters:
        -----------
        data : list of (dict, label) tuples
            The dataset to calculate information gain on.
        feature : str
            The feature to calculate information gain for.

        Returns:
        --------
        float
            The information gain for the given feature.
        """
        def entropy(labels):
            freqdist = FreqDist(labels)
            probs = [count / len(labels) for count in freqdist.values()]
            return -sum(p * math.log2(p) for p in probs)

        labels = [label for _, label in data]
        feature_values = set(sample[0][feature] for sample in data)

        base_entropy = entropy(labels)
        weighted_feature_entropy = sum(
            len([sample for sample in data if sample[0][feature] == value]) / len(data) *
            entropy([sample[1] for sample in data if sample[0][feature] == value])
            for value in feature_values
        )

        return base_entropy - weighted_feature_entropy

    def classify(self, featureset):
        """
        Classify a single featureset.

        Parameters:
        -----------
        featureset : dict
            A dictionary of features to classify.

        Returns:
        --------
        str
            The predicted label for the given featureset.
        """
        def _classify(tree, featureset):
            if not isinstance(tree, dict):
                return tree
            feature = next(iter(tree))
            if featureset[feature] in tree[feature]:
                return _classify(tree[feature][featureset[feature]], featureset)
            return max(tree[feature].values(), key=lambda x: x if not isinstance(x, dict) else 0)

        return _classify(self.tree, featureset)

    def show_most_informative_features(self, n=10):
        """
        Show the n most informative features.

        Parameters:
        -----------
        n : int, optional (default=10)
            The number of features to show.

        Returns:
        --------
        list of tuple
            A list of (feature, information_gain) tuples, sorted by information gain.
        """
        # This method is left as an exercise. It should return the top n most informative features.
        pass