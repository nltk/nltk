#
# AdaBoost.MH - based on:
#
# ``The Boosting Approach to Machine Learning: An Overview'',
# Robert E. Schapire, MSRI Workshop on Nonlinear Estimation and
# Classification, 2002
#
# ``Improved Boosting Algorithms using Confidence Rated Predictions'',
# Robert E. Schapire and Yoram Singer, Machine Learning 34(3), 1999.
#

from nltk_contrib.unimelb.tacohn.classifier import *
from nltk_contrib.unimelb.tacohn.classifier.feature import *
from nltk_contrib.unimelb.tacohn.classifier.naivebayes import *
from nltk.corpus import senseval
from nltk.probability import *
from nltk.chktype import type_safety_level
import math, sys
from Numeric import *

class WeightedVoteClassifier(ClassifierI):
    def __init__(self, labels, classifiers, weights):
        self._classifiers = classifiers
        self._weights = weights
        self._labels = labels

    def fv_list_likelihood(self, fv_list, label):
        val = total = 0
        for j in range(len(self._labels)):
            sum = 0
            for classifier, weight in zip(self._classifiers, self._weights):
                p = classifier[j].fv_list_prob(fv_list, 'positive')
                sum += (p * 2.0 - 1.0) * weight

            if label == self._labels[j]:
                val = (sum + 1) / 2.0
            total += (sum + 1) / 2.0
        return val / total

    def fv_list_probdist(self, fv_list):
        total = 0
        counts = {}
        for j in range(len(self._labels)):
            sum = 0
            for classifier, weight in zip(self._classifiers, self._weights):
                p = classifier[j].fv_list_prob(fv_list, 'positive')
                sum += p * weight
            total += sum
            counts[self._labels[j]] = sum

        for label in self.labels():
            counts[label] /= float(total)

        return DictionaryProbDist(counts)

    def classify(self, unlabeled_token):
        old_tsl = type_safety_level(0)
        labels = []
        for j in range(len(self._labels)):
            sum = 0
            for classifier, weight in zip(self._classifiers, self._weights):
                p = classifier[j].prob(Token(LabeledText(unlabeled_token.type(),
                                       'positive'), unlabeled_token.loc()))
                sum += (p * 2.0 - 1.0) * weight

            labels.append((sum, self._labels[j]))

        labels.sort()
        best = labels[-1][1]

        type_safety_level(old_tsl)
        return Token(LabeledText(unlabeled_token.type(), (labels[-1][1],)),
                     unlabeled_token.loc())

    def classify_multilabel(self, unlabeled_token):
        old_tsl = type_safety_level(0)
        labels = []
        for j in range(len(self._labels)):
            sum = 0
            for classifier, weight in zip(self._classifiers, self._weights):
                p = classifier[j].prob(Token(LabeledText(unlabeled_token.type(),
                                       self._labels[j]), unlabeled_token.loc()))
                sum += (p * 2.0 - 1.0) * weight

            if sum >= 0:
                labels.append(self._labels[j])

        type_safety_level(old_tsl)
        return Token(LabeledText(unlabeled_token.type(), tuple(labels)),
                     unlabeled_token.loc())

    def labels(self):
        return self._labels

    # other ClassifierI methods... FIXME

class AdaBoostClassifierTrainer(ClassifierTrainerI):
    def __init__(self, classifier_trainer, max_iterations, trace=False):
        self._inducer = classifier_trainer
        self._max_iterations = max_iterations
        self._trace = trace

    def train(self, labeled_tokens):
        fv_lists = map(lambda t: self._inducer._fd_list.detect(t.type().text()),
                       labeled_tokens)
        labels = map(lambda t: t.type().label(), labeled_tokens)
        return self.train_fv_lists(fv_lists, labels)

    def train_fv_lists(self, fv_lists, labels):
        m = len(fv_lists)
        label_set = {}
        for ls in labels:
            for l in ls:
                label_set[l] = 1
        label_set = label_set.keys()
        k = len(label_set)

        if self._trace:
            print 'ABC - training with', m, 'instances', k, 'labels'

        ys = zeros((m, k)) - 1
        for i in range(m):
            for label in labels[i]:
                li = label_set.index(label)
                ys[i, li] = 1

        D = ones((m, k), 'd') / (m * k)

        hs = []
        as = []
        for t in range(self._max_iterations):
            if self._trace:
                print 'ABC iteration', t, '- inducing classifier'

            classifier, predictions = self._train_and_test_classifier(D,
                zip(fv_lists, labels), label_set)
            hs.append(classifier)
            if self._trace:
                print 'ABC - h', classifier

            r = 0
            for i in range(m):
                for j in range(k):
                    r += D[i, j] * ys[i, j] * predictions[i, j]

            if r == 1:
                as.append(1)
                return WeightedVoteClassifier(label_set, hs, as)
                
            a = 0.5 * math.log((1 + r) / (1 - r))
            as.append(a)
            if self._trace:
                print 'ABC - a', a

            Z = 0
            zs = zeros((m, k), 'd')
            for i in range(m):
                for j in range(k):
                    z = D[i, j] * math.exp(-a * ys[i, j] * predictions[i, j])
                    zs[i, j] = z
                    Z += z

            if self._trace:
                print 'ABC - Z', Z, 'zs', str(zs)[:40], '...'

            for i in range(m):
                for j in range(k):
                    D[i, j] = zs[i, j] / Z

        return WeightedVoteClassifier(label_set, hs, as)

    def _train_and_test_classifier(self, D, instances, labels):
        cs = []
        ps = zeros((len(instances), len(labels)), 'd')
        for j in range(len(labels)):
            fvls, ls = self._filter_tokens(instances, labels[j])
            classifier = self._inducer.train_fv_lists_weights(fvls, ls, D[:, j])
            for i in range(len(instances)):
                p = classifier.fv_list_prob(fvls[i], 'positive')
                ps[i, j] = p * 2.0 - 1.0 # normalise between -1 and +1
            cs.append(classifier)
        return cs, ps

    def _filter_tokens(self, instances, label):
        fvls = []
        labels = []
        for fv_list, ls in instances:
            fvls.append(fv_list)
            if label in ls:
                labels.append('positive')
            else:
                labels.append('negative')
        return fvls, labels

def demo_nb(W, N):
    print 'Loading SENSEVAL interest corpus'
    labeled_tokens = senseval.tokenize('interest.pos')

    print 'Filtering using %d window' % W
    filtered = []
    words = {}
    for token in labeled_tokens:
        #if token.type().label()[0] in ['interest_1', 'interest_4']:
        if True:
            labeled_text = token.type()
            head = labeled_text.headIndex()
            trimmed = labeled_text.text()[head - W : head + W + 1]

            filtered.append(Token(LabeledText(trimmed, labeled_text.label()),
                                  token.loc()))

            for word_token in trimmed:
                words[word_token.type()] = 1

    words = words.keys()
    #words = words.keys()[:200] # otherwise a bit over 8000

    print 'Creating NB trainer, with %d words' % len(words)
    fd_list = FilteredFDList(
                ArrayFunctionFilter(lambda tk: tk.type().base()),
                BagOfWordsFDList(words))
    nbt = NBClassifierTrainer(fd_list, estimator=('Lidstone', 0.0001))

    print 'Training AdaBoost with %d iterations' % N
    abt = AdaBoostClassifierTrainer(nbt, N, trace=True)
    classifier = abt.train(filtered[100:])

    print 'Testing'
    test_multi_label(classifier, filtered[:100], fd_list)

    print 'NB - benchmark'
    test_multi_label(nbt.train(filtered[100:]), filtered[:100], fd_list)

def test_multi_label(classifier, tests, fd_list):
    correct = 0
    for i in range(len(tests)):
        test = tests[i]
        pdist = classifier.fv_list_probdist(fd_list.detect(test.type()))
        #pred = classifier.classify(Token(test.type().text(), test.loc()))
        pred = pdist.max()
        #print 'test', i, 'pred', pred.type().label(), 'actual', test.type().label()
        print 'test', i, 'pred', pred, 'actual', test.type().label()
        for l in pdist.samples():
            print '%s/%f' % (l, pdist.prob(l)),
        print 
        if pred == test.type().label() or pred == test.type().label()[0]:
            correct += 1
    
    print 'accuracy', (correct / float(len(tests)))

def load_senseval():
    print 'Loading SENSEVAL interest corpus'
    labeled_tokens = nltk.corpus.senseval.tokenize('interest.pos')

    print 'Filtering'
    filtered = []
    words = {}
    tags = {}
    for token in labeled_tokens:
        if token.type().label() in ['interest_1', 'interest_4']:
            labeled_text = token.type()
            head = labeled_text.headIndex()
            text = labeled_text.text()
            reordered = text[head:] + text[:head]
            #reordered = text[head:] + [None] + text[:head]

            filtered.append(Token(LabeledText(reordered, labeled_text.label()),
                                  token.loc()))

            for word_token in text:
                words[word_token.type().base()] = 1 # or could include the tag
                tags[word_token.type().tag()] = 1

    return words.keys(), tags.keys(), filtered

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print >>sys.stderr, 'Must supply <window size> and <iterations>'
        sys.exit()
    demo_nb(int(sys.argv[1]), int(sys.argv[2]))
    #words, tokens = load_senseval()
    #demo_singlefeature(words, tokens)
