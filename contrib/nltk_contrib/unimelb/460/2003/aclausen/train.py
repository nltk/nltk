import classifier
import mailtokenizer
import modelclassifier
import progress

import nltk.corpus

import email
import cPickle
import getopt
import sys

def print_sizes(corpus):
	groups = corpus.groups()
	groups.sort()
	for group in groups:
		print str(group), len(corpus.items(group))
	print ''

general_help = \
	'use: train [<options>] <output-classifier> { <group> }+\n'\
	'options:\n'\
	'-c n, --context n      maximum context size (default 3)\n'\
	'-t n, --top n          top n words allowed context (default 500)\n'\
	'-n n, --corpus-size n  maxmimum number of items to use from corpus\n'\
	'-m, --male-female	build a male/female classifier\n'\
	'-r, --rel-entropy	use relative entropy for classification\n'\
	'-i, --min-info		use min. information for classification\n'

try:
	(options, parameters) = getopt.getopt(sys.argv[1:], "c:t:n:mri", [
		"context=", "top=", "corpus-size=", "male-female", 
		"rel-entropy", "min-info"])
	if len(parameters) < 2:
		raise getopt.GetoptError('Not enough arguments', '')
except getopt.GetoptError:
	print general_help
	sys.exit(1)

# process options
opt_context = 3
opt_top = 500
opt_max_corpus_size = 100000
opt_male_female = 0
opt_rel_entropy = 0
for (option, argument) in options:
	if option in ["-c", "--context"]:
		opt_context = int(argument)
	elif option in ["-t", "--top"]:
		opt_top = int(argument)
	elif option in ["-n", "--corpus-size"]:
		opt_max_corpus_size = int(argument)
	elif option in ["-m", "--male-female"]:
		opt_male_female = 1
	elif option in ["-r", "--rel-entropy"]:
		opt_rel_entropy = 1
	elif option in ["-i", "--min-info"]:
		opt_rel_entropy = 0
 
# process other parameters
classifier_file_name = parameters[0]
groups = parameters[1:]

# construct the corpus
# Looks a bit ad-hoc.. it is essentially constructing an relation algebra
# query from the command line arguments.  Perhaps it would be more elegant
# expressed that way...
mail_tokenizer = mailtokenizer.MailCleanTokenizer(mailtokenizer.frequent_words)
corpus = classifier.SubCorpusReader(
		nltk.corpus.twenty_newsgroups,
		groups=tuple(groups),
		default_tokenizer=mail_tokenizer)

if opt_male_female:
	corpus = classifier.MFCorpusReader(corpus)

print_sizes(corpus)

first_items = []
for group in corpus.groups():
	first_items += list(corpus.items(group))[:opt_max_corpus_size]
corpus = classifier.SubCorpusReader(corpus, items=first_items)

if opt_male_female:
	corpus = classifier.QuotientCorpusReader(
			corpus,
			lambda(gender, group): gender)
	print 'male:', len(corpus.items('male'))
	print 'female:', len(corpus.items('female'))

# Construct the classifier
if opt_rel_entropy:
 	trainer = modelclassifier.RelEntClassifier(corpus, opt_context)
else:
	trainer = modelclassifier.MinInfoClassifier(corpus, opt_context, opt_top)

# Pickle the classifier
cPickle.dump((trainer, (first_items, opt_male_female)),
	     file(classifier_file_name, 'w'),
	     1)

