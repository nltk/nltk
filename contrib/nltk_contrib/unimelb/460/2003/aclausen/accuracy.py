import classifier
import mailtokenizer
import modelclassifier

import nltk.corpus

import cPickle
import getopt
import sys

# in-place list set subtraction
def merge_purge(xs, ys):
	xs.sort()
	ys.sort()
	i = len(xs) - 1
	j = len(ys) - 1
	while i >= 0 and j >= 0:
		if xs[i] == ys[j]:
			del xs[i]
			j -= 1
		i -= 1

# TestingCorpusReader is a SubCorpusReader that used for testing
# accuracy of a classifier.

class TestingCorpusReader(classifier.SubCorpusReader):
	def __init__(self, parent_corpus,
		     groups=None, avoid_items=[], default_tokenizer=None):
		all_items = []
		for group in parent_corpus.groups():
			all_items += parent_corpus.items(group)
		merge_purge(all_items, avoid_items)
		classifier.SubCorpusReader.__init__(self, parent_corpus,
			groups=groups, items=all_items,
			default_tokenizer=default_tokenizer)

general_help = \
	'use: accuracy [<options>] <classifier> { <group> }+\n'\
	'options:\n'\
	'-a, --avoid-training	don\'t test on training data\n'\
	'-n n, --corpus-size n  maxmimum number of items to use from corpus\n'\
	'-t, --test-training	test on training data\n'

try:
	(options, parameters) = getopt.getopt(sys.argv[1:], "an:t",
		["avoid-training", "corpus-size", "test-training"])
	if len(parameters) < 1:
		raise getopt.GetoptError('Not enough arguments', '')
except getopt.GetoptError:
	print general_help
	sys.exit(1)

# process options
opt_avoid_training = 1
opt_max_corpus_size = 100000
for (option, argument) in options:
	if option in ["-a", "--avoid-training"]:
		opt_avoid_training = 1
	elif option in ["-n", "--corpus-size"]:
		opt_max_corpus_size = int(argument)
	elif option in ["-t", "--test-training"]:
		opt_avoid_training = 0

classifier_file_name = parameters[0]
groups = parameters[1:]

print 'loading classifier...'
(classifier_obj, (training_items, is_male_female)) = \
	cPickle.load(file(classifier_file_name, 'r'))

# set items to avoid in training, allows for testing from 
# the same newsgroup as training data.
if opt_avoid_training:
	avoid_items = training_items
else:
	avoid_items = []
mail_tokenizer = mailtokenizer.MailCleanTokenizer(mailtokenizer.frequent_words)

# Make a testing corpus
corpus = TestingCorpusReader(
		nltk.corpus.twenty_newsgroups,
		groups=tuple(groups),
		avoid_items=avoid_items,
		default_tokenizer=mail_tokenizer)

# multiple classifications 
if is_male_female:
	corpus = classifier.MFCorpusReader(corpus)
	corpus = classifier.QuotientCorpusReader(
			corpus,
			lambda(gender, group): gender)

first_items = []
for group in corpus.groups():
	first_items += list(corpus.items(group))[:opt_max_corpus_size]
corpus = classifier.SubCorpusReader(corpus, items=first_items)

tester = classifier.ClassifierTester(corpus)
tester.test(classifier_obj)

