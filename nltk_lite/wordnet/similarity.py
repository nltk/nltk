
from nltk_lite.wordnet import *

class SimilarityI(object):

    def get_similarity(self, word1, word2):
        """
        Calculate the similarity of the two Words using some similarity metric
        e.g. path distance in Wordnet. Note that both Words must be the same
        part of speech e.g. both Nouns.

        @return: An integer denoting how similar the two words are. -1 will be returned in the event of an error.
    @rtype: L{int}

        @param word1: The first word to be compared
        @type word1: L{Wordnet Sense}

        @param word2: The second word to be compared
        @type word2: L{Wordnet Sense}
        """
        raise NotImplementedError()

class PathDistanceSimilarity(SimilarityI):

    def get_similarity(self, word1, word2):

        synset1 = word1.synset
        synset2 = word2.synset

        if synset1 == synset2: return 1

        hypernym_tree1 = build_hypernym_tree(synset1, 0)
        hypernym_tree2 = build_hypernym_tree(synset2, 0)

        # The maximum path distance connecting the two synsets is equal to the
        # the sum of the heights of the two trees.
        path_distance = hypernym_tree1.height() + hypernym_tree2.height()

        # It is possible that no matches will be found (i.e. if a noun and a
        # verb are compared); we need to keep track of this.
        match_found = False

        hypernyms = hypernym_tree2.to_list()

        for hypernym in hypernyms:
            matches = search_hypernym_tree(hypernym_tree1, hypernym.synset)
            matches.sort()

            if len(matches) > 0:
                match_found = True

                if matches[0].depth + hypernym.depth < path_distance:
                    path_distance = matches[0].depth + hypernym.depth

        return 1.0 / (path_distance + 1)

def build_hypernym_tree(synset, depth):

    hypernyms = synset.getPointerTargets("hypernym")

    node = Tree(SynsetNodeValue(synset, depth))

    for hypernym in hypernyms:
         node.add_child(build_hypernym_tree(hypernym, depth+1))

    return node

# Search recursively in a tree for the supplied synset. Return a list of the
# depths in the tree where this synset is found. Note that this involves a full
# tree traversal in order to find _all_ matching synsets.

def search_hypernym_tree(node, synset):

    value = node.value

    if value.synset == synset:
        matches = [value]

    else:
        matches = []

    for child in node.children:
        matches.extend(search_hypernym_tree(child, synset))

    return matches

class SynsetNodeValue:

    def __init__(self, synset, depth):
        self.synset = synset
        self.depth = depth

    def __cmp__(self, other):
        if not isinstance(other, SynsetNodeValue):
            raise TypeError, "SynsetNodeValues can only be compared with other SynsetNodeValues"

        return cmp(self.depth, other.depth)

    def __repr__(self):
        return `(self.synset, self.depth)`

class Tree(object):

    def __init__(self, value, children=None):
        self.value = value

        if children is None:
            self.children = []
        else:
            self.children = children

    def add_child(self, child):
        self.children.append(child)

    def to_list(self):
        list = [self.value]

        if len(self.children) > 0:

            for child in self.children:
                list.extend(child.to_list())

        return list

    def size(self):
        size = 1

        for child in self.children:
            size += child.size()

        return size

    def height(self):

        height = 0
        max_height = 0

        for child in self.children:
            height = child.height()

            if (height > max_height):
                max_height = height

        return max_height + 1
