# -*- coding: utf-8 -*-
"""
This module implements the dependency parsing algorithm presented by Danqi Chen and
Christopher Manning at EMNLP 2014.

This implementation mostly follows the architecture and naming of the original Java implementation
provided in the CoreNLP suite.
"""

import timeit
from nltk.tag.perceptron import PerceptronTagger
import numpy as np
from numpy import random


class DependencyParser(object):
    """ This class implements the transition-based dependency parser described in [Chen and Manning 2014].
    The parser is based on the arc-standard transition system and uses a neural network for classifying transitions.

    The distinguishing features of this parser are:
    - the use of embeddings for part-of-speech tags and arc labels
    - cube activation function in the neural network classifier
    - pre-computation trick for speeding up parsing and training.

    More detailed description of the parser can be found in this paper:
    cs.stanford.edu/people/danqi/papers/emnlp2014.pdf

    To parse a part-of-speech tagged sentence, use method 'parse'. For parsing, a model file is required.
    The parser can be loaded directly from a model file using the 'load_from_model_file' method.
    If a part-of-speech tagger is available, the method can also parse a sentence that
    is not pos-tagged. The part-of-speech tagger should implement the TaggerI interface of module tag, and
    is set via the 'tagger' attribute of a class Config instance. The parser and the tagger should use
    the same tags for parts of speech.

    To train a parser model, use method 'train'. For training, a treebank in CoNLL-U format is needed as well as
    a word embeddings file. Training parameters can be set via class Config.

    To evaluate the parser's performance on sentences in CoNLL-U format, use method 'test_conll'.

    """

    def __init__(self, config=None):
        """
        Create a dependency parser, which can be used for training a model file.
        Before parsing sentences, it is necessary to either train the parser or load a pre-trained model.

        :param config: parser's parameters.
        :type config: Config
        """

        self.config = Config() if config is None else config
        self._knownWords = []  # the list of words with known embeddings
        self._knownPos = []  # the list of model's part-of-speech tags
        self._knownLabels = []  # the list of dependency labels
        self._wordIDs = {}  # IDs of known words
        self._posIDs = {}  # IDs of known part-of-speech tags
        self._labelIDs = {}  # IDs of known dependency labels
        self._system = None  # the parsing system
        self._classifier = None  # the neural network for classifying parsing system transitions
        self._preComputed = None  # IDs of input tokens for which pre-computation is done
        self._language = self.config.language

    @classmethod
    def load_from_model_file(cls, model_file, encoding='utf8', config=None):
        """
        Reads the pre-trained model file and returns a dependency parser with those parameters.
        Parameters specified in the model file override the overlapping ones from config.
        This method is compatible with models provided in the CoreNLP suite.

        :param model_file: the path to the model file
        :type model_file: str
        :param encoding: model file's encoding
        :type encoding: str
        :param config: parser's parameters
        :type config: Config
        :return: dependency parser
        :rtype: DependencyParser
        """

        parser = DependencyParser() if config is None else DependencyParser(config)
        parser.load_model_file(model_file, encoding=encoding, verbose=False)
        return parser

    def load_model_file(self, model_file, encoding='utf8', verbose=True):
        """
        Loads parser's parameters from the pre-trained model file. Parameters specified in the model file
        override the overlapping ones from config. This method is compatible with models provided in
        the CoreNLP suite.

        :param model_file: the path to the model file
        :type model_file: str
        :param encoding: model file's encoding
        :type encoding: str
        :param verbose: if True, prints parsing system's parameters.
        :type verbose: bool
        """

        print("Loading depparse model file: {0} ... ".format(model_file))
        with open(model_file, mode='r', encoding=encoding) as source:

            # read Config parameters at the beginning of the model file
            params = []
            for _ in range(7):
                s = source.readline()
                params.append(int(s[s.find("=") + 1:]))
            n_dict, n_pos, n_label, e_size, h_size, n_tokens, n_precomputed = params

            self._knownWords, self._knownPos, self._knownLabels = [], [], []
            self.config.embeddingSize = e_size
            self.config.hiddenSize = h_size
            self.config.numTokens = n_tokens
            self.config.numPreComputed = n_precomputed

            # read word, pos tag and arc label embeddings
            e = np.zeros((n_dict + n_pos + n_label, e_size))
            for k in range(n_dict + n_pos + n_label):
                splits = source.readline().split(" ")
                if k < n_dict:
                    self._knownWords.append(splits[0])
                elif k < n_dict + n_pos:
                    self._knownPos.append(splits[0])
                else:
                    self._knownLabels.append(splits[0])
                e[k] = list(map(float, splits[1:]))

            self._generate_IDs()

            # read classifier weights
            w1 = np.zeros((h_size, e_size * n_tokens))
            for j in range(len(w1[0])):
                splits = source.readline().split(" ")
                w1[:, j] = list(map(float, splits))

            splits = source.readline().split(" ")
            b1 = list(map(float, splits))

            w2 = np.zeros((n_label * 2 - 1, h_size))
            for j in range(len(w2[0])):
                splits = source.readline().split(" ")
                w2[:, j] = list(map(float, splits))

            # read precomputed values
            self._preComputed = []
            while len(self._preComputed) < n_precomputed:
                splits = source.readline().split()
                self._preComputed.extend(list(map(int, splits)))

            # initialize the classifier
            self._classifier = Classifier(self.config, None, e, w1, b1, w2, self._preComputed)

        self._initialize(verbose)

    def write_model_file(self, model_file, encoding='utf8'):
        """
        Saves the parser's parameters at 'model_file'. The following parameters are written in the file:
        - known words, part-of-speech tags, arc labels and their embeddings,
        - neural network's weights,
        - pre-computed values.

        :param model_file: the file, where the model is saved.
        :type model_file: str
        :param encoding: model file's encoding.
        :type encoding: str
        """

        w1 = self._classifier.W1
        b1 = self._classifier.b1
        w2 = self._classifier.W2
        e = self._classifier.E

        with open(model_file, 'w', encoding=encoding) as output:
            output.write("dict={0}\n".format(len(self._knownWords)))
            output.write("pos={0}\n".format(len(self._knownPos)))
            output.write("label={0}\n".format(len(self._knownLabels)))
            output.write("embeddingSize={0}\n".format(len(e[0])))
            output.write("hiddenSize={0}\n".format(len(b1)))
            output.write("numTokens={0}\n".format(int(len(w1[0]) / len(e[0]))))
            output.write("preComputed={0}\n".format(len(self._preComputed)))

            index = 0
            # write word / POS / label embeddings
            # each line starts with a word, tag or label, then followed by its representation.
            # values are separated with whitespace.
            for word in self._knownWords:
                output.write("{0} {1}\n".format(word, " ".join(map(str, e[index]))))
                index += 1

            for pos in self._knownPos:
                output.write("{0} {1}\n".format(pos, " ".join(map(str, e[index]))))
                index += 1

            for label in self._knownLabels:
                output.write("{0} {1}\n".format(label, " ".join(map(str, e[index]))))
                index += 1

            # write classifier weights
            for j in range(len(w1[0])):
                output.write("{0}\n".format(" ".join(map(str, w1[:, j]))))

            output.write("{0}\n".format(" ".join(map(str, b1))))

            for j in range(len(w2[0])):
                output.write("{0}\n".format(" ".join(map(str, w2[:, j]))))

            # write pre-computation info
            for i in range(len(self._preComputed)):
                output.write("{0}".format(self._preComputed[i]))
                if (i + 1) % 100 == 0 or i == len(self._preComputed) - 1:
                    output.write("\n")
                else:
                    output.write(" ")

    def train(self, train_file, dev_file, model_file, embed_file, tagger_file=None):
        """
        Trains a dependency parser model. For training, a treebank in CoNLL-U format is needed.
        The objective is to learn the neural network classifier's weights and word, tag, label embeddings that
        minimize the cross-entropy loss, using AdaGrad for optimization.

        Training parameters can be set via attribute 'config'. The trained model is saved in 'model_file'
        and can be loaded later for parsing. If tagger_loc is specified, the method also trains an averaged perceptron
        part-of-speech tagger.

        :param train_file: the file with training sentences in CoNLL-U format.
        :type train_file: str
        :param dev_file: the file with sentences in CoNLL-U format, on which the trained model's UAS is evaluated.
        :type dev_file: str
        :param model_file: the file where the trained model is saved.
        :type model_file: str
        :param embed_file: the file with word embeddings. Each line of the file starts with a word, followed by its
        whitespace-separated embedding values.
        :type embed_file: str
        :param tagger_file: the file where the part-of-speech tagger is saved. if None, pos-tagger is not trained.
        :type tagger_file: str
        """

        print("Train File: {0}".format(train_file))
        print("Dev File: {0}".format(dev_file))
        print("Model File: {0}".format(model_file))
        print("EmbeddingFile: {0}".format(embed_file))

        # retrieve train sentences and their parses from a conll-u file
        train_sents, train_trees = load_conll_file(train_file, self.config.unlabeled, self.config.cPOS)
        print_tree_stats("Train", train_trees)

        # retrieve development sentences and their parses from a conll-u file
        dev_sents, dev_trees = load_conll_file(dev_file, self.config.unlabeled, self.config.cPOS)
        print_tree_stats("Dev", dev_trees)

        # train an averaged perceptron part-of-speech tagger if tagger_file is specified
        if tagger_file is not None:

            print('Training averaged perceptron part-of-speech tagger...')
            tagger = PerceptronTagger(False)
            tagger.train(to_tagger_sents(train_sents), save_loc=tagger_file)
            print('Part-of-speech tagger model saved in file: {0}'.format(tagger_file))

            # evaluate and print trained tagger's accuracy on development sentences
            eval_sents = to_tagger_sents(dev_sents)
            print('Accuracy of the part-of-speech tagger on dev sents: {0}'.format(tagger.evaluate(eval_sents)))

            self.config.tagger = tagger

        # generate dictionaries of known words, tags and labels from train sentences
        self._gen_dictionaries(train_sents, train_trees)

        l_dict = list(self._knownLabels)  # create a copy of known labels dictionary for the parsing system
        l_dict.pop(0)  # remove the -NULL- label from known labels before passing them to the parsing system
        self._system = ArcStandard(self.config.punct_tags, l_dict, True)

        # setup the classifier
        self._setup_classifier_for_training(train_sents, train_trees, embed_file)
        print(self.config.SEPARATOR)
        self.config.print_parameters()

        best_uas = 0.0  # to store the best UAS observed during intermediate evaluations
        for i in range(self.config.maxIter):

            # compute weights' gradients
            correct = self._classifier.compute_gradients(self.config.batchSize, self.config.regParameter, self.config.dropProb)
            print("##### Iteration {0}. Correct transitions (%) = {1}".format(i, round(100 * correct, 2)))

            # update classifier's weights
            self._classifier.take_ada_gradient_step(self.config.adaAlpha, self.config.adaEps)

            # evaluate UAS
            if (i % self.config.evalPerIter) == 0:

                # compute hidden layer values for most common input features
                self._classifier.precompute()

                # predict dependency parses of sentences from development set
                predicted = [self._parse(s) for s in dev_sents]
                result = self._system.evaluate(dev_sents, predicted, dev_trees)

                # if noPunc is True, punctuation is ignored during evaluation
                uas = result["UASnoPunc"] if self.config.noPunc else result["UAS"]
                print("UAS: {0}".format(uas))

                if self.config.saveIntermediate and uas > best_uas:

                    print("Exceeds best previous UAS of {0}. Saving model file..".format(best_uas))
                    best_uas = uas
                    self.write_model_file(model_file)

            # clear gradient history
            if self.config.clearGradientPerIter > 0 and i % self.config.clearGradientPerIter == 0:

                print("Clearing gradient histories..")
                self._classifier.clearGradientHistories()

        # evaluate final model's UAS and save if it beats the best intermediate model's UAS

        # predict dependency parses of sentences from development set using final model
        predicted = [self._parse(s) for s in dev_sents]
        result = self._system.evaluate(dev_sents, predicted, dev_trees)

        # if noPunc is True, punctuation is ignored during evaluation
        uas = result["UASnoPunc"] if self.config.noPunc else result["UAS"]
        print("Final model UAS: {0}".format(uas))

        if uas > best_uas:

            print("Exceeds best previous UAS of {0}. Saving model file..".format(best_uas))
            self.write_model_file(model_file)

    def parse_sents(self, sentences, tagged=True):
        """
        Parse sentences. If the sentences are not part-of-speech tagged, a part-of-speech tagger must be provided
        via 'tagger' attribute of 'config'.

        :param sentences: the list of sentences to be parsed
        :type sentences: list(list((str, tag)) or list(list(str))
        :param tagged: indicates whether the sentences are part-of-speech tagged or not.
        :type tagged: bool
        :return: the dependency trees of parsed sentences.
        :rtype: list(DependencyTree)
        """
        return [self.parse(sent, tagged) for sent in sentences]

    def parse(self, sentence, tagged=True):
        """
        Parse a sentence. If the sentence is not part-of-speech tagged, a part-of-speech tagger must be provided
        via 'tagger' attribute of 'config'.

        :param sentence: the sentence to parse
        :type sentence: list of (word, tag) pairs if the sentence is tagged, otherwise list of words
        :param tagged: indicates whether the sentences are part-of-speech tagged or not.
        :return: the dependency tree of the parsed sentence.
        :rtype: DependencyTree
        """

        if not tagged:

            if self.config.tagger is None:
                raise ValueError("No part-of-speech tagger is provided. "
                                 "The parser needs a part-of-speech tagger if the sentence is not tagged.")
            # tag the sentence
            sentence = self.config.tagger.tag(sentence)

        sentence = [{"word": word, "pos": tag} for (word, tag) in sentence]
        return self._parse(sentence)

    def _parse(self, sentence):

        if self._system is None:
            raise ValueError("Parser has not been loaded and initialized; first load a model.")

        num_trans = self._system.num_transitions()
        c = self._system.initial_configuration(sentence)

        # apply transitions to the initial configuration until a terminal configuration is reached.
        while not self._system.is_terminal(c):

            # compute scores for all transitions
            scores = self._classifier.compute_scores(self.get_features(c))
            opt_score = -np.inf
            opt_trans = None
            for j in range(num_trans):

                # find the feasible transition with highest score
                if scores[j] > opt_score and self._system.can_apply(c, self._system.transitions[j]):

                    opt_score = scores[j]
                    opt_trans = self._system.transitions[j]

            # apply the transition with highest score
            self._system.apply(c, opt_trans)

        # the parsing system reached a terminal configuration,
        # which means the dependency parse is complete
        return c.tree

    def get_word_id(self, s):
        return self._wordIDs.get(s, self._wordIDs[Config.UNKNOWN])

    def get_pos_id(self, s):
        return self._posIDs.get(s, self._posIDs[Config.UNKNOWN])

    def get_label_id(self, s):
        return self._labelIDs.get(s)

    def get_features(self, c):
        """
        Extracts features from a parsing system configuration. The extracted features are the word, pos tag and
        arc labels of the following elements:
        - the top 3 words on the stack and buffer (arc labels for these elements are not included in the feature set),
        - the first and second leftmost, rightmost children of the top two words on the stack,
        - the leftmost of leftmost, rightmost of rightmost children of the top two words on the stack

        :param c: parsing system configuration
        :type c: Configuration
        :return: list of IDs of configuration's features (feature's ID is its index in the embeddings matrix,
        at which feature's value is stored)
        :rtype: list of ints
        """

        f_word, f_pos, f_label = [], [], []

        # extract features from the configuration stack's top 3 elements
        for j in [2, 1, 0]:
            index = c.get_stack(j)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))

        # extract features from the configuration buffer's top 3 elements
        for j in [0, 1, 2]:
            index = c.get_buffer(j)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))

        # extract features from stack's top 2 elements' children elements
        for j in [0, 1]:
            k = c.get_stack(j)

            # features from first leftmost child
            index = c.get_left_child(k)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

            # features from first rightmost child
            index = c.get_right_child(k)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

            # features from second leftmost child
            index = c.get_left_child(k, 2)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

            # features from second rightmost child
            index = c.get_right_child(k, 2)
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

            # features from leftmost child of stack element's leftmost child
            index = c.get_left_child(c.get_left_child(k))
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

            # features from rightmost child of stack element's rightmost child
            index = c.get_right_child(c.get_right_child(k))
            f_word.append(self.get_word_id(c.get_word(index)))
            f_pos.append(self.get_pos_id(c.get_pos(index)))
            f_label.append(self.get_label_id(c.get_label(index)))

        features = f_word + f_pos + f_label
        return features

    def gen_train_examples(self, sents, trees):
        """
        Generates training examples from sentences and their dependency trees. Each training example consists of
        features extracted from a parsing system configuration and labels of that parsing system's transitions.
        The label of the correct transition is 1, other feasible transitions have label 0, and the rest -1.

        :param sents: list of sentences. In a sentence, each token's value, pos tag, its head token's number and
        arc label are stored at keys "word", "pos", "head", "depType" respectively.
        :type sents: list(list(dict))
        :param trees: list of the sentences' dependency trees
        :type trees: list(DependencyTree)
        :return: training set
        :rtype: Dataset
        """

        num_trans = self._system.num_transitions()
        train_set = Dataset(self.config.numTokens, num_trans)

        tok_pos_count = {}  # to store IDs of most common input features, which are then selected for pre-computation
        print(self.config.SEPARATOR)
        print("Generate training examples...")

        # generate train examples from every sentence in tre training set
        # for i in range(len(sents)):
        for i, sent in enumerate(sents):

            if trees[i].is_projective():

                # extract training examples from parsing system's all configurations.
                # start from parsing system's initial configuration for the sentence,
                # and apply oracle transitions until a terminal configuration is reached.
                c = self._system.initial_configuration(sent)
                while not self._system.is_terminal(c):

                    # get oracle transition, i.e. the transition that leads to building the gold dependency tree
                    oracle = self._system.get_oracle(c, trees[i])

                    feature = self.get_features(c)  # extract configuration's features
                    label = []  # to store transitions' labels
                    for j in range(num_trans):
                        transition = self._system.transitions[j]
                        if transition == oracle:
                            # oracle transition's label is 1
                            label.append(1)
                        elif self._system.can_apply(c, transition):
                            # if the transition is feasible but not oracle, label 0
                            label.append(0)
                        else:
                            # if the transition cannot be applied to current configuration, label -1
                            label.append(-1)

                    train_set.add_example(feature, label)

                    for j in range(len(feature)):
                        # input feature's ID is composed from token's ID and its position
                        try:
                            tok_pos_count[feature[j] * len(feature) + j] += 1
                        except KeyError:
                            tok_pos_count[feature[j] * len(feature) + j] = 1

                    # transition the system into its next configuration
                    self._system.apply(c, oracle)

        print("#Train Examples: {0}".format(train_set.n))

        # sort feature IDs in the descending order of frequency
        sorted_tokens = sorted(tok_pos_count, key=lambda k: -tok_pos_count[k])

        # select most common feature IDs for pre-computation
        self._preComputed = sorted_tokens[:self.config.numPreComputed]

        return train_set

    def test_conll(self, test_file, out_file, verbose=True, tagged=True):
        """
        Evaluate the parser's performance on gold trees in CoNLL-U format from 'test_file' and save predicted trees
        in the same format at 'out_file'. If tagged is False, tags from the treebank are ignored and a part-of-speech
        tagger is used to tag sentences before parsing. 
		To get the desired results for evaluation without punctuation, edit config's and parsing system's punct_tags attribute.

        :param test_file: the file with gold sentences in CoNLL-U format.
        :type test_file: str
        :param out_file: the file, where predicted trees are saved.
        :type out_file: str
        :param verbose: if True, prints evaluation results.
        :type verbose: bool
        :param tagged: indicates whether to use gold part-of-speech tags or not.
        :return: the result of evaluation:
         - unlabeled attachment score ("UAS", "UASnoPunc"),
         - labeled attachment score ("LAS", "LASnoPunc"),
         - unlabeled exact match score ("UEM", "UEMnoPunc"),
         - percent of predicted trees with correct roots ("ROOT").
        :rtype: dict
        """

        test_sents, test_trees = load_conll_file(test_file, self.config.unlabeled, self.config.cPOS)
        start_time = timeit.default_timer()

        # predict the dependency parses of sentences
        if not tagged:
            predicted = [self.parse([token["word"] for token in sent], tagged=False) for sent in test_sents]
        else:
            predicted = [self._parse(sent) for sent in test_sents]

        seconds = timeit.default_timer() - start_time
        result = self._system.evaluate(test_sents, predicted, test_trees)

        if verbose:
            num_words, num_oov_words = 0, 0  # to store the counts of all words and words out of vocabulary
            num_sentences = len(test_sents)
            for test_sent in test_sents:
                num_words += len(test_sent)
                num_oov_words += len([token for token in test_sent if token["word"] not in self._wordIDs])
            wordspersec = num_words / seconds  # the number of words parsed per second
            sentspersec = num_sentences / seconds  # the number of sentences parsed per second
            print("Test File: {0}".format(test_file))
            print("OOV Words: {0} / {1} = {2}%".format(num_oov_words, num_words, num_oov_words * 100.0 / num_words))
            print("UAS = {0}%".format(result["UASnoPunc"] if self.config.noPunc else result["UAS"]))
            print("LAS = {0}%".format(result["LASnoPunc"] if self.config.noPunc else result["LAS"]))
            print("Dependency Parser parsed {0} words in {1} sentences in {2}s at {3} w/s, {4} sent/s.".format(
                num_words, num_sentences, seconds, wordspersec, sentspersec))

        if out_file is not None:  # saved predicted parses in conll-u format
            write_conll_file(out_file, test_sents, predicted)

        return result

    def _gen_dictionaries(self, sents, trees):

        words, tags, labels = [], [], []

        # extract words and pos tags
        for sent in sents:
            for token in sent:
                words.append(token["word"])
                tags.append(token["pos"])

        # extract root label and other dependency labels
        root_label = None
        for tree in trees:
            for i in range(1, tree.n + 1):
                if tree.get_head(i) == 0:
                    root_label = tree.get_label(i)
                else:
                    labels.append(tree.get_label(i))

        self._knownWords = generate_dict(words, self.config.wordCutOff)
        self._knownPos = generate_dict(tags)
        self._knownLabels = generate_dict(labels)
        self._knownLabels.insert(0, root_label)

        # avoid the case when root label equals to one of the other labels
        for k in range(1, len(self._knownLabels)):
            if self._knownLabels[k] == root_label:
                self._knownLabels.pop(k)
                break

        self._knownWords.insert(0, Config.UNKNOWN)
        self._knownWords.insert(1, Config.NULL)
        self._knownWords.insert(2, Config.ROOT)
        self._knownPos.insert(0, Config.UNKNOWN)
        self._knownPos.insert(1, Config.NULL)
        self._knownPos.insert(2, Config.ROOT)
        self._knownLabels.insert(0, Config.NULL)
        self._generate_IDs()

    def _generate_IDs(self):

        self._wordIDs = {}
        self._posIDs = {}
        self._labelIDs = {}

        index = 0
        for word in self._knownWords:
            self._wordIDs[word] = index
            index += 1
        for pos in self._knownPos:
            self._posIDs[pos] = index
            index += 1
        for label in self._knownLabels:
            self._labelIDs[label] = index
            index += 1

    def _setup_classifier_for_training(self, train_sents, train_trees, embed_file):

        # randomly initialize weight matrices
        init_range = self.config.initRange
        w1 = random.uniform(-init_range, init_range, (self.config.hiddenSize, self.config.embeddingSize * self.config.numTokens))
        b1 = random.uniform(-init_range, init_range, self.config.hiddenSize)
        w2 = random.uniform(-init_range, init_range, (self._system.num_transitions(), self.config.hiddenSize))

        # read embeddings
        embeddings, embed_id = self._read_embed_file(embed_file)

        # match embeddings with words in dictionary
        e = []
        for i in range(len(self._knownWords) + len(self._knownPos) + len(self._knownLabels)):
            index = -1
            if i < len(self._knownWords):
                word = self._knownWords[i]
                try:
                    index = embed_id[word]
                except KeyError:
                    index = embed_id.get(word.lower(), -1)
            if index >= 0:
                column = list(embeddings[index])
            else:
                # didn't find token's embedding, so initialize randomly
                column = random.uniform(-init_range, init_range, self.config.embeddingSize)
            e.append(column)

        train_set = self.gen_train_examples(train_sents, train_trees)
        self._classifier = Classifier(self.config, train_set, e, w1, b1, w2, self._preComputed)

    def _read_embed_file(self, embed_file, encoding='utf8'):

        embeddings = []  # to store word, tag, label embeddings
        embed_id = {}  # maps word, tag and label strings to their IDs, where ID is the index in embeddings

        with open(embed_file, 'r', encoding=encoding) as f:
            for i, line in enumerate(f):
                splits = line.split()
                dim = len(splits) - 1
                if dim != self.config.embeddingSize:
                    f.close()
                    raise ValueError('The dimension of embedding file does not match Config.embeddingSize. '
                                     'Given: {0}. Expected: {1}, line {2}'.format(dim, self.config.embeddingSize, i + 1))

                embed_id[splits[0]] = i
                embeddings.append(list(map(float, splits[1:])))

        return embeddings, embed_id

    def _initialize(self, verbose):
        # initializes the parsing system and precomputes hidden layer values for common features

        if self._knownLabels is None:
            raise ValueError("Model has not been loaded or trained")

        l_dict = list(self._knownLabels)
        l_dict.pop(0)

        self._system = ArcStandard(self.config.punct_tags, l_dict, verbose)

        if self.config.numPreComputed > 0:
            self._classifier.precompute()


class DependencyTree(object):
    """ 
    Represents a dependency parse tree. Stores a sentence's syntactic structure, but not its words.
    Dependency relations and their types are stored in attributes 'head' and 'label' respectively.
    """

    def __init__(self, tree=None):

        self.n = 0  # the number of tokens in the sentence

        # Numeration of sentence's tokens starts at 1, with the root element is at 0.
        self.head = []  # 'head' stores each token's head node's number.
        self.label = []  # 'label' stores each token's dependency type from its head node
        self._counter = None
        if tree is not None:
            self.n = tree.n
            self.head = tree.head
            self.label = tree.label
        else:
            self.head.append(Config.NONEXIST)
            self.label.append(Config.UNKNOWN)

    def add(self, head, label):
        """
        Adds a new node to the dependency tree, appending its head's number and dependency arc label to
        the dependency tree's 'head' and 'label' arrays.

        :param head: new node's head node number
        :type head: int
        :param label: the new node's dependency arc label from its head.
        :type label: str
        """
        self.n += 1
        self.head.append(head)
        self.label.append(label)

    def set(self, k, h, l):
        """
        Set the sentence's k-th token's head and arc label.

        :param k: token's number (0 for root)
        :param h: token's head's number (-1 for root)
        :param l: arc label
        """
        self.head[k] = h
        self.label[k] = l

    def get_head(self, k):
        """ Returns the number of sentence's k-th word's head. """
        if k <= 0 or k > self.n:
            return Config.NONEXIST
        else:
            return self.head[k]

    def get_label(self, k):
        """ Returns the label of sentence's k-th word from its head. """
        if k <= 0 or k > self.n:
            return Config.NULL
        else:
            return self.label[k]

    def get_root(self):
        """ Returns the root node's index. """
        for k in range(1, self.n + 1):
            if self.get_head(k) == 0:
                return k
        return 0

    def is_single_root(self):
        """ Checks if the tree has only one root. """
        roots = 0
        for k in range(1, self.n + 1):
            if self.get_head(k) == 0:
                roots += 1
        return roots == 1

    def is_tree(self):
        """ Checks if the dependency parse is a tree. """
        h = [-1] * (self.n + 1)
        for i in range(1, self.n + 1):
            if self.get_head(i) < 0 or self.get_head(i) > self.n:
                return False
            k = i
            while k > 0:
                if h[k] == i:
                    return False
                h[k] = i
                k = self.get_head(k)
        return True

    def is_projective(self):
        """ Checks if the dependency tree is projective. """
        if not self.is_tree():
            return False
        self._counter = -1
        return self._visit_tree(0)

    def _visit_tree(self, w):
        """
        Traverses the dependency tree to check if it's projective. Recursively visits the tree's nodes,
        and if finds a node, for which the number of visited nodes is not equal to its index, returns False.
        Otherwise, returns True.
        """
        for i in range(1, w):
            if self.get_head(i) == w and not self._visit_tree(i):
                return False
        self._counter += 1
        if w != self._counter:
            return False
        for i in range(w + 1, self.n + 1):
            if self.get_head(i) == w and not self._visit_tree(i):
                return False
        return True

    def equal(self, tree):
        """
        :param tree: dependency tree.
        :type tree: DependencyTree
        :return: True, if the trees are identical.
        """
        if tree.n != self.n:
            return False
        for i in range(1, self.n + 1):
            if self.get_head(i) != tree.get_head(i) or self.get_label(i) != tree.get_label(i):
                return False
        return True

    @classmethod
    def to_conll(cls, tagged_sentence, tree):
        """
        Takes a part-of-speech tagged sentence and its dependency parse, and returns in CoNLL-U format.

        :param tagged_sentence: part-of-speech tagged sentence
		:type tagged_sentence: list of (word, tag) pairs where both word and tag are str
        :param tree: the sentence's dependency tree
        :type tree: DependencyTree
        :rtype: str
        """
        conll = ""
        for i, token in enumerate(tagged_sentence):
            conll += "{0}\t{1}\t_\t{2}\t{3}\t_\t{4}\t{5}\t_\t_\n".format(i + 1, token[0], token[1], token[1], tree.get_head(i + 1), tree.get_label(i + 1))
        return conll


class Classifier(object):
    """ This class implements a feed-forward neural network classifier for a transition-based dependency parser.

    The neural network has 3 fully connected layers:
    - an input layer taking word, pos tag and arc label embeddings
    - a hidden layer with cube activation function
    - a softmax output layer
    The classification result is the softmax probabilities for all possible transitions of the parsing system.

    The optimization objective during training is to minimize the cross-entropy loss among feasible transitions.
    The network also learns the embeddings for words, pos tags and arc labels.

    The learning rate, dropout probability and classifier's other parameters can be set via class Config.
    """

    def __init__(self, config, dataset, e, w1, b1, w2, precomputed):
        """
        :param config: classifier's parameters
        :type config: Config
        :param dataset: training examples
        :type dataset: Dataset
        :param e: embeddings matrix
        :param w1: weights from input layer to hidden layer
        :param b1: weights of input layer's bias unit
        :param w2: weights from hidden layer to output layer
        :param precomputed: IDs of precomputed features from the training set
        """

        self.config = config  # classifier's parameters
        self.dataset = dataset  # training set
        self.E = np.array(e)  # embeddings
        self.W1 = np.array(w1)  # weights from input layer to hidden layer
        self.b1 = np.array(b1)  # weights of input layer's bias unit
        self.W2 = np.array(w2)  # weights from hidden layer to output layer
        self.eg2W1 = None  # to store gradient histories of weights in W1
        self.eg2W2 = None  # to store gradient histories of weights in W2
        self.eg2E = None  # to store gradient histories of embeddings
        self.eg2b1 = None  # to store gradient histories of weights in b1
        self.saved = None  # to store precomputed values
        self.init_gradient_histories()
        self.numLabels = len(w2)
        self.preMap = {}
        for i in range(min(len(precomputed), config.numPreComputed)):
            self.preMap[precomputed[i]] = i
        self.gradW1 = None
        self.gradb1 = None
        self.gradW2 = None
        self.gradE = None
        self.percentCorrect = 0

    def get_to_precompute(self, examples):
        """
        Returns the IDs of precomputed features from the training examples.

        :param examples: training examples
        :type examples: list
        """

        featureIDs = set()
        for ex in examples:
            feature = ex.feature
            for j in range(self.config.numTokens):
                tok = feature[j]
                index = tok * self.config.numTokens + j
                if index in self.preMap:
                    featureIDs.add(index)

        return featureIDs

    # def compute_cost_function(self, batch_size, reg_parameter, dropout_prob):
    def compute_gradients(self, batch_size, reg_parameter, dropout_prob):
        """
        Computes gradients of weights. The training error derivatives are backpropagated to embeddings.

        :param batch_size: the number of training examples
        :param reg_parameter: regularization weight
        :param dropout_prob: dropout probability of hidden layer's neurons
        :return: percent of correctly classified examples
        """

        # select mini-batch for training
        examples = random.choice(self.dataset.examples, min(batch_size, len(self.dataset.examples)), False)

        # precompute hidden layer for common features
        to_precompute = self.get_to_precompute(examples)
        self.precompute(to_precompute)

        # pass training examples forward and backward through the network
        correct = self._process(examples, dropout_prob)
        self._add_l2_regularization(reg_parameter)
        return correct

    def take_ada_gradient_step(self, ada_alpha, ada_eps):
        """
        Updates neural network's weights, embeddings and gradient histories
        based on latest backpropagation results.

        :param ada_alpha: AdaGrad learning rate
        :param ada_eps: a small number added to denominators for numerical stability
        """

        self.eg2W1 += self.gradW1 * self.gradW1
        self.W1 -= ada_alpha * self.gradW1 / np.sqrt(self.eg2W1 + ada_eps)

        self.eg2b1 += self.gradb1 * self.gradb1
        self.b1 -= ada_alpha * self.gradb1 / np.sqrt(self.eg2b1 + ada_eps)

        self.eg2W2 += self.gradW2 * self.gradW2
        self.W2 -= ada_alpha * self.gradW2 / np.sqrt(self.eg2W2 + ada_eps)

        self.eg2E += self.gradE * self.gradE
        self.E -= ada_alpha * self.gradE / np.sqrt(self.eg2E + ada_eps)

    def init_gradient_histories(self):

        self.eg2E = np.zeros(self.E.shape)
        self.eg2W1 = np.zeros(self.W1.shape)
        self.eg2b1 = np.zeros(self.b1.shape)
        self.eg2W2 = np.zeros(self.W2.shape)

    def clear_gradient_histories(self):
        """ Clears previous gradient histories and initializes them with zeros. """

        self.init_gradient_histories()

    def precompute(self, to_precompute=None):
        """
        Computes and saves hidden layer's values (before activation) for given features.

        :param to_precompute: IDs of features
        """

        if to_precompute is None:
            to_precompute = self.preMap.keys()

        self.saved = np.zeros([len(self.preMap), self.config.hiddenSize])

        for x in to_precompute:
            map_x = self.preMap[x]
            tok = int(x / self.config.numTokens)  # get token's ID
            offset = (x % self.config.numTokens) * self.config.embeddingSize  # get token's position in feature vector
            self.saved[map_x] += self.W1[:, offset:offset + self.config.embeddingSize].dot(self.E[tok])

    def compute_scores(self, feature, pre_map=None):
        """
        Computes the transitions' scores for the given feature vector by feeding it forward through the neural network.
        The higher transition's score is, the more probable it is.

        :param feature: feature vector (each value is an index into the embedding matrix)
        :param pre_map: precomputed values
        :return: transitions' scores
        """

        if pre_map is None:
            pre_map = self.preMap

        hidden = np.zeros(self.config.hiddenSize)
        offset = 0
        for j in range(len(feature)):
            tok = feature[j]
            index = tok * self.config.numTokens + j

            if index in pre_map:
                # hidden layer is precomputed for this feature
                _id = pre_map[index]
                hidden += self.saved[_id]
            else:
                # compute hidden layer
                hidden += self.W1[:, offset:offset + self.config.embeddingSize].dot(self.E[tok])
            offset += self.config.embeddingSize

        # apply cube activation
        hidden = (hidden + self.b1) ** 3

        # compute and return the output layer
        return np.dot(self.W2, hidden)

    def _process(self, examples, dropout_prob):
        """
        Calculates the training error derivatives and returns the percent of correctly predicted transitions.

        :param examples: training examples
        :param dropout_prob: dropout probability of hidden layer nodes
        :return: percent of correctly classified examples
        """

        batch_size = len(examples)
        self.gradW1 = np.zeros(self.W1.shape)
        self.gradb1 = np.zeros(self.b1.shape)
        self.gradW2 = np.zeros(self.W2.shape)
        self.gradE = np.zeros(self.E.shape)

        correct = 0.0  # to store percent of correctly classified examples
        e_size = self.config.embeddingSize  # size of embedding vectors
        h_size = self.config.hiddenSize  # hidden layer's size

        for ex in examples:
            feature = ex.feature
            label = ex.label

            hidden = np.zeros(h_size)
            hidden3 = np.zeros(h_size)

            # randomly drop some hidden layer units. 'ls' contains the indices of those units which are still active
            ls = np.random.choice(range(h_size), int(h_size * (1 - dropout_prob)), False)

            # feed the example forward through the network
            offset = 0
            for j in range(len(feature)):
                tok = feature[j]
                index = tok * self.config.numTokens + j

                if index in self.preMap:
                    _id = self.preMap[index]
                    hidden[ls] += self.saved[_id][ls]
                else:
                    hidden[ls] += self.W1[ls, offset:offset + e_size].dot(self.E[tok])
                offset += e_size

            hidden[ls] += self.b1[ls]
            hidden3[ls] = hidden[ls] ** 3
            scores = np.dot(self.W2[:, ls], hidden3[ls])

            opt_label = -1
            for i in range(self.numLabels):
                if label[i] >= 0 and (opt_label < 0 or scores[i] > scores[opt_label]):
                    opt_label = i

            # compute softmax probabilities for feasible transitions
            sum1, sum2 = 0.0, 0.0
            max_score = scores[opt_label]
            for i in range(self.numLabels):
                if label[i] >= 0:
                    scores[i] = np.exp(scores[i] - max_score)
                    if label[i] == 1:
                        sum1 += scores[i]
                    sum2 += scores[i]

            if label[opt_label] == 1:
                correct += 1.0 / batch_size

            # compute gradients
            grad_hidden3 = np.zeros(h_size)
            for i in range(self.numLabels):
                if label[i] >= 0:
                    delta = -(label[i] - scores[i] / sum2) / batch_size
                    self.gradW2[i][ls] += delta * hidden3[ls]
                    grad_hidden3[ls] += delta * self.W2[i][ls]

            grad_hidden = np.zeros(h_size)
            grad_hidden[ls] = grad_hidden3[ls] * 3 * hidden[ls] * hidden[ls]
            self.gradb1[ls] += grad_hidden[ls]

            offset = 0
            for j in range(self.config.numTokens):
                tok = feature[j]
                self.gradW1[ls, offset:offset + e_size] += np.outer(grad_hidden[ls], self.E[tok])
                self.gradE[tok] += np.dot(grad_hidden, self.W1[:, offset:offset + e_size])
                offset += e_size

        return correct

    def _add_l2_regularization(self, regularization_weight):
        """ Adds l2 regularization to the cost. """

        self.gradW1 += regularization_weight * self.W1
        self.gradb1 += regularization_weight * self.b1
        self.gradW2 += regularization_weight * self.W2
        self.gradE += regularization_weight * self.E


class ParsingSystem(object):
    """ A transition system for dependency parsing. """

    def __init__(self, punct_tags, labels, verbose):
        self.rootLabel = labels[0]  # the root dependency's label
        self.labels = list(labels)  # labels of all dependencies
        self.transitions = None  # to store all possible transitions
        self.punct_tags = punct_tags  # part-of-speech tags of punctuation symbols
        self.make_transitions()

        if verbose:
            print(Config.SEPARATOR)
            print("#Transitions: {0}".format(self.num_transitions()))
            print("#Labels: {0}".format(len(self.labels)))
            print("ROOTLABEL: {0}".format(self.rootLabel))

    def make_transitions(self):
        """ Generate all possible transitions and assign the list to 'transitions'. """
        raise NotImplementedError()

    def can_apply(self, c, t):
        """
        Checks whether the transition can be applied to the parsing system configuration.

        :param c: configuration
        :param t: transition
        """
        raise NotImplementedError()

    def apply(self, c, t):
        """
        Applies the transition to the parsing system configuration.

        :param c: configuration
        :param t: transition
        """
        raise NotImplementedError()

    def get_oracle(self, c, tree):
        """
        Returns the oracle transition that if applied to the configuration
        leads to the building of the provided dependency tree.

        :param c: configuration
        :param tree: dependency tree
        """
        raise NotImplementedError()

    def is_oracle(self, c, t, tree):
        """
        Checks whether the transition is oracle, i.e. will lead to the building of the provided
        dependency tree if applied to the configuration .

        :param c: configuration
        :param t: transition
        :param tree: dependency tree
        """
        raise NotImplementedError()

    def initial_configuration(self, sentence):
        """ Builds the parsing system's initial configuration for the sentence. """
        raise NotImplementedError()

    def is_terminal(self, c):
        """
        Checks whether the configuration is terminal, i.e. the parsing has finished.

        :param c: configuration
        """
        raise NotImplementedError()

    def num_transitions(self):
        """ Returns the number of possible transitions. """
        return len(self.transitions)

    def evaluate(self, sentences, trees, gold_trees):
        """
        Evaluates the accuracy of predicted dependency trees against gold trees for the provided sentences.

        :param sentences: the sentences that were parsed. In a sentence, each token's value, pos tag, its head token's
        number and arc label are stored at keys "word", "pos", "head", "depType" respectively.
        :type sentences: list(list(dict))
        :param trees: predicted dependency trees of the sentences
        :type trees: list(DependencyTree)
        :param gold_trees: gold dependency trees of the sentences
        :type gold_trees: list(DependencyTree)
        :return: the result of evaluation:
         - unlabeled attachment score ("UAS", "UASnoPunc"),
         - labeled attachment score ("LAS", "LASnoPunc"),
         - unlabeled exact match score ("UEM", "UEMnoPunc"),
         - percent of predicted trees with correct roots ("ROOT").
        :rtype: dict
        """
        if len(trees) != len(gold_trees):  # checks that the number of predicted and gold trees are equal
            print("ERROR: Incorrect number of trees.")
            return None

        correct_arcs = correct_arcs_no_punc = 0  # to store the number of correctly predicted arcs
        correct_heads = correct_heads_no_punc = 0  # to store the number of correctly predicted arcs (ignoring labels)
        correct_trees = correct_trees_no_punc = 0  # to store the number of correctly predicted trees
        sum_arcs = sum_arcs_no_punc = 0  # to store the overall number of dependency arcs with / without punctuation
        correct_root = 0  # to store the number of correctly predicted root elements

        for i, tree in enumerate(trees):
            if tree.n != gold_trees[i].n:
                print("ERROR: Tree {0} has incorrect number of nodes.".format(i + 1))
                return None
            if not tree.is_tree():
                print("ERROR: Tree {0} is not valid.".format(i + 1))
                return None

            sum_arcs += tree.n
            n_correct_head, n_correct_head_no_punc, n_no_punc = 0, 0, 0
            for j in range(1, tree.n + 1):
                if tree.get_head(j) == gold_trees[i].get_head(j):
                    correct_heads += 1
                    n_correct_head += 1
                    correct_arcs += tree.get_label(j) == gold_trees[i].get_label(j)

                tag = sentences[i][j - 1]["pos"]
                if tag not in self.punct_tags:  # check if this is a punctuation symbol
                    sum_arcs_no_punc += 1
                    n_no_punc += 1
                    if tree.get_head(j) == gold_trees[i].get_head(j):
                        correct_heads_no_punc += 1
                        n_correct_head_no_punc += 1
                        correct_arcs_no_punc += tree.get_label(j) == gold_trees[i].get_label(j)

            correct_trees += n_correct_head == tree.n
            correct_trees_no_punc += n_correct_head_no_punc == n_no_punc
            correct_root += tree.get_root() == gold_trees[i].get_root()

        result = {}
        result["UAS"] = correct_heads * 100.0 / sum_arcs
        result["UASnoPunc"] = correct_heads_no_punc * 100.0 / sum_arcs_no_punc
        result["LAS"] = correct_arcs * 100.0 / sum_arcs
        result["LASnoPunc"] = correct_arcs_no_punc * 100.0 / sum_arcs_no_punc
        result["UEM"] = correct_trees * 100.0 / len(trees)
        result["UEMnoPunc"] = correct_trees_no_punc * 100.0 / len(trees)
        result["ROOT"] = correct_root * 100.0 / len(trees)
        return result


class ArcStandard(ParsingSystem):
    """ Implementation of Arc-Standard transition system for dependency parsing. """

    def __init__(self, tlp, labels, verbose):
        super().__init__(tlp, labels, verbose)
        self._singleRoot = True

    def is_terminal(self, c):
        return len(c.stack) == 1 and len(c.buffer) == 0

    def make_transitions(self):
        self.transitions = []
        for label in self.labels:
            self.transitions.append("L(" + label + ")")
        for label in self.labels:
            self.transitions.append("R(" + label + ")")
        self.transitions.append("S")

    def initial_configuration(self, s):
        c = Configuration.from_sentence(s)
        length = len(s)

        for i in range(1, length + 1):
            c.tree.add(Config.NONEXIST, Config.UNKNOWN)
            c.buffer.append(i)

        c.stack.append(0)
        return c

    def can_apply(self, c, t):
        if t.startswith("L") or t.startswith("R"):
            label = t[2:- 1]
            h = c.get_stack(0) if t.startswith("L") else c.get_stack(1)
            if h < 0:
                return False
            if h == 0 and label != self.rootLabel:
                return False

        n_stack = len(c.stack)
        n_buffer = len(c.buffer)

        if t.startswith("L"):
            return n_stack > 2
        elif t.startswith("R"):
            if self._singleRoot:
                return n_stack > 2 or (n_stack == 2 and n_buffer == 0)
            else:
                return n_stack >= 2
        else:
            return n_buffer > 0

    def apply(self, c, t):
        w1 = c.get_stack(1)
        w2 = c.get_stack(0)

        if t.startswith("L"):
            c.add_arc(w2, w1, t[2:-1])
            c.remove_second_top_stack()
        elif t.startswith("R"):
            c.add_arc(w1, w2, t[2:-1])
            c.remove_top_stack()
        else:
            c.shift()

    def get_oracle(self, c, tree):
        w1 = c.get_stack(1)
        w2 = c.get_stack(0)

        if w1 > 0 and tree.get_head(w1) == w2:
            return "L(" + tree.get_label(w1) + ")"
        elif w1 >= 0 and tree.get_head(w2) == w1 and not c.has_other_child(w2, tree):
            return "R(" + tree.get_label(w2) + ")"
        else:
            return "S"

    def can_reach(self, c, tree):
        n = c.get_sentence_size()
        for i in range(1, n + 1):
            if c.get_head(i) != Config.NONEXIST and c.get_head(i) != tree.get_head(i):
                return False

        in_buffer = [False] * (n + 1)
        dep_in_list = [False] * (n + 1)

        left_l = [0] * (n + 2)
        right_l = [0] * (n + 2)

        for v in c.buffer:
            in_buffer[v] = True

        n_left = len(c.stack)
        for i in range(0, n_left):
            x = c.stack[i]
            left_l[n_left - i] = x
            if x > 0:
                dep_in_list[tree.get_head(x)] = True

        n_right = 1
        right_l[n_right] = left_l[1]
        for i in range(0, len(c.buffer)):
            x = c.buffer[i]
            if not in_buffer[tree.get_head(x)] or dep_in_list[x]:
                n_right += 1
                right_l[n_right] = x
                dep_in_list[tree.get_head(x)] = True

        g = np.zeros((n_left + 1, n_right + 1))
        g[1:, 1:] = -1

        g[1][1] = left_l[1]
        for i in range(1, n_left + 1):
            for j in range(1, n_right + 1):
                if g[i][j] != -1:
                    x = g[i][j]
                    if j < n_right and tree.get_head(right_l[j + 1]) == x:
                        g[i][j + 1] = x
                    if j < n_right and tree.get_head(x) == right_l[j + 1]:
                        g[i][j + 1] = right_l[j + 1]
                    if i < n_left and tree.get_head(left_l[i + 1]) == x:
                        g[i + 1][j] = x
                    if i < n_left and tree.get_head(x) == left_l[i + 1]:
                        g[i + 1][j] = left_l[i + 1]

        return g[n_left][n_right] != -1

    def is_oracle(self, c, t, tree):
        if not self.can_apply(c, t):
            return False

        if t.startswith("L") and tree.get_label(c.get_stack(1)) != t[2:-1]:
            return False

        if t.startswith("R") and tree.get_label(c.get_stack(0)) != t[2:-1]:
            return False

        ct = Configuration.from_configuration(c)
        self.apply(ct, t)
        return self.can_reach(ct, tree)


class Configuration(object):
    """ This class describes a parsing system configuration.
    In this class, the index of zero refers to the ROOT node and actual word indices begin at one.
    """

    def __init__(self, stack, buffer, tree, sentence):
        self.stack = stack
        self.buffer = buffer
        self.tree = tree
        self.sentence = sentence

    @classmethod
    def from_configuration(cls, c):
        return Configuration(c.stack, c.buffer, c.tree, c.sentence)

    @classmethod
    def from_sentence(cls, sentence):
        return Configuration([], [], DependencyTree(), sentence)

    def shift(self):
        k = self.get_buffer(0)
        if k == Config.NONEXIST:
            return False
        self.buffer.pop(0)
        self.stack.append(k)
        return True

    def remove_second_top_stack(self):
        if len(self.stack) < 2:
            return False
        self.stack.pop(len(self.stack) - 2)
        return True

    def remove_top_stack(self):
        if len(self.stack) < 1:
            return False
        self.stack.pop(len(self.stack) - 1)
        return True

    def get_sentence_size(self):
        return len(self.sentence)

    def get_head(self, k):
        return self.tree.get_head(k)

    def get_label(self, k):
        return self.tree.get_label(k)

    def get_stack(self, k):
        n_stack = len(self.stack)
        if 0 <= k < n_stack:
            return self.stack[n_stack - 1 - k]
        else:
            return Config.NONEXIST

    def get_buffer(self, k):
        if 0 <= k < len(self.buffer):
            return self.buffer[k]
        else:
            return Config.NONEXIST

    def get_word(self, k):
        if k == 0:
            return Config.ROOT

        k -= 1
        if k < 0 or k >= len(self.sentence):
            return Config.NULL
        else:
            return self.sentence[k]["word"]

    def get_pos(self, k):
        if k == 0:
            return Config.ROOT

        k -= 1
        if k < 0 or k >= len(self.sentence):
            return Config.NULL
        else:
            return self.sentence[k]["pos"]

    def add_arc(self, h, t, l):
        self.tree.set(t, h, l)

    def get_left_child(self, k, cnt=1):
        if k < 0 or k > self.tree.n:
            return Config.NONEXIST

        c = 0
        for i in range(1, k):
            if self.tree.get_head(i) == k:
                c += 1
                if c == cnt:
                    return i
        return Config.NONEXIST

    def get_right_child(self, k, cnt=1):
        if k < 0 or k > self.tree.n:
            return Config.NONEXIST

        c = 0
        for i in range(self.tree.n, k, -1):
            if self.tree.get_head(i) == k:
                c += 1
                if c == cnt:
                    return i
        return Config.NONEXIST

    def has_other_child(self, k, gold_tree):
        for i in range(1, self.tree.n + 1):
            if gold_tree.get_head(i) == k and self.tree.get_head(i) != k:
                return True
        return False


class Dataset(object):
    """ Defines a set of training or test examples for multi-class classification. """

    def __init__(self, num_features, num_labels):
        self.n = 0
        self.numFeatures = num_features
        self.numLabels = num_labels
        self.examples = []

    def add_example(self, feature, label):
        data = Example(feature, label)
        self.n += 1
        self.examples.append(data)


class Example(object):

    def __init__(self, feature, label):

        self.feature = feature
        self.label = label


class Config(object):
    """ This class configures the parameters of a dependency parser.  """

    UNKNOWN = "-UNKNOWN-"
    ROOT = "-ROOT-"
    NULL = "-NULL-"
    NONEXIST = -1
    SEPARATOR = "###################"
    numTokens = 48

    def __init__(self,
                 language="en",
                 word_cut_off=1,
                 init_range=0.01,
                 max_iter=20000,
                 batch_size=10000,
                 ada_eps=1e-6,
                 ada_alpha=0.01,
                 reg_parameter=1e-8,
                 drop_prob=0.5,
                 hidden_size=200,
                 embedding_size=50,
                 num_precomputed=100000,
                 eval_per_iter=100,
                 clear_gradient_per_iter=0,
                 save_intermediate=True,
                 unlabeled=False,
                 cPOS=False,
                 no_punc=False,
                 punct_tags={"``", "''", ".", ",", ":"},
                 tagger=None
                 ):
        self.language = language  # the language the parser is intended for
        self.wordCutOff = word_cut_off  # words with a frequency lower than cutoff are not included in the dictionary of known words
        self.initRange = init_range  # initialization range of classifier's weights and unknown words' embeddings
        self.maxIter = max_iter  # the number of neural network classifier's training iterations
        self.batchSize = batch_size  # the number of training examples used during a training iteration
        self.adaEps = ada_eps  # a number added to the denominator of the AdaGrad expression for numerical stability
        self.adaAlpha = ada_alpha  # initial learning rate for AdaGrad training
        self.regParameter = reg_parameter  # the l2-regularization weight
        self.dropProb = drop_prob  # dropout probability of network's hidden layer's neurons
        self.hiddenSize = hidden_size  # the number of neurons in the hidden layer of the neural network
        self.embeddingSize = embedding_size  # the size of vector
        self.numPreComputed = num_precomputed  # the number of input tokens for which hidden-layer unit activations are computed
        self.evalPerIter = eval_per_iter  # compute UAS after every specified number of training iterations
        self.clearGradientPerIter = clear_gradient_per_iter  # clear gradient histories after every specified number of training iterations
        self.saveIntermediate = save_intermediate  # save a model file during training when UAS is improved
        self.unlabeled = unlabeled  # train a labeled parser unlabeled is False
        self.cPOS = cPOS  # usa coarse part-of-speech tags if cPOS is True
        self.noPunc = no_punc  # if True, punctuation is ignored during evaluation
        self.punct_tags = punct_tags  # part of speech tags of punctuation symbols
        self.tagger = tagger  # a part-of-speech tagger to tag sentences during parsing (should implement the TaggerI interface)

    def print_parameters(self):
        parameters = vars(self)
        for var in parameters:
            print('{0} = {1}'.format(var, parameters[var]))


def load_conll_file(conll_file, unlabeled, cPOS, encoding='utf-8'):
    """
    Read sentences and their dependency parses from CoNLL-U file.

    :param conll_file: path to the CoNLL-U file
    :param unlabeled: indicates whether to read dependency types (if True) or not
    :param cPOS: if True, reads coarse part-of-speech tags
    :param encoding: file's encoding
    :return: sentences and their dependency trees from the file
    """

    sents, trees = [], []
    with open(conll_file, 'r', encoding=encoding) as f:
        sentence_tokens = []
        tree = DependencyTree()
        for line in f:
            line = line.rstrip('\r\n')
            splits = line.split("\t")
            if len(splits) < 10:
                trees.append(tree)
                sents.append(sentence_tokens)
                tree = DependencyTree()
                sentence_tokens = []
            else:
                word = splits[1]
                pos = splits[3] if cPOS else splits[4]
                dep_type = splits[7]
                head = int(splits[6])
                token = {
                    "word": word,
                    "pos": pos,
                    "head": head,
                    "depType": dep_type}
                sentence_tokens.append(token)

                if not unlabeled:
                    tree.add(head, dep_type)
                else:
                    tree.add(head, Config.UNKNOWN)

    return sents, trees


def write_conll_file(out_file, sentences, trees, encoding='utf8'):
    """
    Writes sentences and their dependency parse to a file in CoNLL-U format.

    :param out_file: output file
    :param sentences: the sentences to write
    :param trees: dependency trees of the sentences
    :type trees: list(DependencyTree)
    :param encoding: output file's encoding
    """
    with open(out_file, 'w', encoding=encoding) as output:
        for i in range(len(sentences)):
            sentence = sentences[i]
            tree = trees[i]
            # tokens = []

            for j in range(1, len(sentence) + 1):
                token = sentence[j - 1]
                output.write("{0}\t{1}\t_\t{2}\t{3}\t_\t{4}\t{5}\t_\t_\n"
                             .format(j, token["word"], token["pos"], token["pos"],
                                     tree.get_head(j), tree.get_label(j)))
            output.write('\n')


def generate_dict(strings, cutoff=1):
    freq = {}
    for string in strings:
        try:
            freq[string] += 1
        except KeyError:
            freq[string] = 1

    keys = sorted(freq, key=lambda k: -freq[k])
    d = []
    for word in keys:
        if freq[word] >= cutoff:
            d.append(word)

    return d


def print_tree_stats(message, trees):
    print("{0} {1}".format(Config.SEPARATOR, message))
    n_trees = len(trees)
    non_tree = 0
    multi_root = 0
    non_projective = 0
    for tree in trees:
        if not tree.is_tree():
            non_tree += 1
        else:
            if not tree.is_projective():
                non_projective += 1
            if not tree.is_single_root():
                multi_root += 1

    print("#Trees: {0}".format(n_trees))
    print("{0} tree(s) are illegal {1}".format(non_tree, non_tree * 100.0 / n_trees))
    print("{0} tree(s) are legal but have multiple roots {1}".format(multi_root, multi_root * 100.0 / n_trees))
    print("{0} tree(s) are legal but not projective {1}".format(non_projective, non_projective * 100.0 / n_trees))


def to_tagger_sents(train_sents):
    sents = []
    for train_sent in train_sents:
        sents.append([(token["word"], token["pos"]) for token in train_sent])
    return sents


def demo():
    """   
    Setup part-of-speech tagger:
    
    # >>> tagger = PerceptronTagger(False)
    # >>> tagger.load('averaged_perceptron_tagger_ud_ru.pickle')
    
    Setup parser:
    
    # >>> parser = DependencyParser.load_from_model_file('nn_dependency_parser_ud_ru.nndp')
    # >>> parser.config.tagger = tagger
      
    Setup example sentences:
    
    # >>> raw_sentence = ['Илья', 'оторопел', 'и', 'дважды', 'перечитал', 'бумажку', '.']
    # >>> tagged_sentence = tagger.tag(raw_sentence)
    
    Parse a tagged sentence:
    
    # >>> dependency_parse1 = parser.parse(tagged_sentence)
    # >>> print(dependency_parse1.head)  # [-1, 2, 0, 2, 5, 2, 5, 2]
    # >>> print(dependency_parse1.label) # ['-UNKNOWN-', 'nsubj', 'root', 'cc', 'advmod', 'conj', 'dobj', 'punct']
    
    Parse a raw sentence:
    
    # >>> dependency_parse2 = parser.parse(raw_sentence, tagged=False)
    # >>> print(dependency_parse2.head)  # [-1, 2, 0, 2, 5, 2, 5, 2]
    # >>> print(dependency_parse2.label) # ['-UNKNOWN-', 'nsubj', 'root', 'cc', 'advmod', 'conj', 'dobj', 'punct']
    """
