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

    def distribution_dictionary(self, unlabeled_token):
        total = 0
        counts = {}
        for j in range(len(self._labels)):
            labeled_token = Token(
                LabeledText(unlabeled_token.type(), 'positive'),
                unlabeled_token.loc())
            sum = 0
            for classifier, weight in zip(self._classifiers, self._weights):
                p = classifier[j].prob(labeled_token)
                sum += p * weight
            total += sum
            counts[self._labels[j]] = sum

        for label in self.labels():
            counts[label] /= float(total)

        return counts

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
        labels = [t.type().label() for t in labeled_tokens]

        m = len(labeled_tokens)
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
                labeled_tokens, label_set)
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

    def _train_and_test_classifier(self, D, labeled_tokens, labels):
        cs = []
        ps = zeros((len(labeled_tokens), len(labels)), 'd')
        for j in range(len(labels)):
            labeled_texts = self._filter_tokens(labeled_tokens, labels[j])
            classifier = self._inducer.train(labeled_texts, weights = D[:, j])
            for i in range(len(labeled_texts)):
                p = classifier.prob(Token(
                        LabeledText(labeled_texts[i].type().text(), 'positive'),
                        labeled_texts[i].loc()))
                ps[i, j] = p * 2.0 - 1.0 # normalise between -1 and +1
            cs.append(classifier)
        return cs, ps

    def _filter_tokens(self, labeled_tokens, label):
        labeled_texts = []
        for token in labeled_tokens:
            l = 'negative'
            if label in token.type().label():
                l = 'positive'
            labeled_texts.append(
                Token(LabeledText(token.type().text(), l), token.loc()))
        return labeled_texts

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
                words[word_token.type().base()] = 1

    words = words.keys()
    #words = words.keys()[:200] # otherwise a bit over 8000

    training = filtered[100:]
    testing = filtered[:100]

    print 'Creating NB trainer, with %d words' % len(words)
    ffd_list = FilteredFDList(ArrayFunctionFilter(lambda tk: tk.type().base()),
                              BagOfWordsFDList(words))
    fd_list = MemoizedFDList(ffd_list, [tk.type().text() for tk in training])

    nbt = NBClassifierTrainer(fd_list, estimator=('Lidstone', 0.0001))

    print 'Training AdaBoost with %d iterations' % N
    abt = AdaBoostClassifierTrainer(nbt, N, trace=True)
    classifier = abt.train(training)

    print 'Testing'
    test_multi_label(classifier, testing)

    print 'NB - benchmark'
    test_multi_label(nbt.train(training), testing)

def test_multi_label(classifier, tests):
    correct = 0
    for i in range(len(tests)):
        test = tests[i]
        dd = classifier.distribution_dictionary(
            Token(test.type().text(), test.loc()))
        pred = None
        for label, prob in dd.items():
            if not pred or prob > pred[0]:
                pred = (prob, label)
        pred = pred[1]
        #print 'test', i, 'pred', pred.type().label(), 'actual', test.type().label()
        print 'test', i, 'pred', pred, 'actual', test.type().label()
        for label, prob in dd.items():
            print '%s/%f' % (label, prob),
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
