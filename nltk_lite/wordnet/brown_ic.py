
import sys

from itertools import islice

from nltk_lite.corpora import brown
from nltk_lite.probability import *
from nltk_lite.tokenize import *
from nltk_lite.wordnet.wntools import *

def substr_binary_search(item, list):

	low = 0
	high = len(list) - 1
	mid = high / 2

	while list[mid].find(item) < 0:

		if mid >= high or mid <= low: return False

		elif list[mid] > item:
			high = mid
			mid -= (high - low) / 2

		elif list[mid] < item:
			low = mid
			mid += (high - low) / 2
			
	return list[mid].split(':')[1]

def generate_compound_list(filename=None):

	dictionaries = [N, V]
	compound_types = ['nc', 'vbc']

	if filename: outfile = open(filename, 'w')
	else: outfile = sys.stdout

	for dict, type in zip(dictionaries, compound_types):

		for term in dict:
			term = term.form

			if ' ' in term: outfile.write("%s:%s\n" % (term, type))

def read_compound_list(filename):

	compound_list = []
	infile = open(filename, 'r')

	for line in infile:
		line = line.rstrip()
		compound_list.append(line)

	compound_list.sort()

	return compound_list

def get_roots(dictionary):

	roots = []

	for word in dictionary:

		for sense in word:

			synset = sense.synset
			hypernyms = set(synset.getPointerTargets("hypernym")) | set(synset.getPointerTargets("hypernym (instance)"))

			if len(hypernyms) == 0: roots.append(synset)

	return roots

def propogate_frequencies(freq_dist, node):

	hyponyms = set(node.getPointerTargets("hyponym")) | set(node.getPointerTargets("hyponym (instance)"))

	for hyponym in hyponyms:
		freq_dist.inc(node, propogate_frequencies(freq_dist, hyponym))

	return freq_dist.count(node)

def brown_information_content(compounds_filename, output_filename):

	noun_tags = [ 
		'nn',		# N. sing. common (burden)
#		'nn$',		# N. sing. common, genetive (company's)
#		'nn+bez',	# N. sing. common + 'to be' pres. 3rd pers sing. (wife's)
#		'nn+hvd',	# N. sing. common + 'to have' past (James'd)
#		'nn+hvz',	# N. sing. common + 'to have' pres. 3rd pers sing. (guy's)	
#		'nn+in',	# N. sing. common + prep. (buncha)
#		'nn+md',	# N. sing. common + modal aux. (sun'll)
#		'nn+nn',	# N. sing. common, hyphenated pair (stomach-belly)
		'nns',		# N. plu. common (burdens)
#		'nns$',		# N. plu. common genetive (companies')
#		'nns+md',	# N. plu. common + modal aux. (cowboys'll)
		'np',		# N. sing. proper (September)
#		'np$',		# N. sing. proper genetive (William's)
#		'np+bez',	# N. sing. proper + 'to be' pres. 3rd pers sing. (Rob's)
#		'np+hvd',	# N. sing. proper + 'to have' past (James'd)
#		'np+hvz',	# N. sing. proper + 'to have' pres. 3rd pers sing. (Bill's)	
#		'np+md',	# N. sing. proper + modal aux. (John'll)
		'nps',		# N. plu. proper (Catholics)
#		'nps$',		# N. plu. proper, genetive (Republicans')
		'nr',		# N. sing. adverbial (today, Saturday, East)
#		'nr$',		# N. sing. adverbial, genetive (Saturday's)
#		'nr+md'		# N. sing. adverbial + modal aux. (today'll)
		'nrs',		# N. plu. adverbial (Sundays)
		'nc',		# N. compound (jigsaw puzzle, egg cup)
	]

	verb_tags = [
		'vb',		# V. base: pres. imp. or inf. (find, act)
#		'vb+at',	# V. base: pres. or inf. + article (wanna)
#		'vb+in',	# V. base: pres. imp. or inf. + prep. (lookit)
#		'vb+jj',	# V. base: pres. imp. or inf. + adj. (die-dead)
#		'vb+ppo',	# V. pres. + pronoun, personal, acc. (let's)
#		'vb+rp',	# V. imperative + adverbial particle (g'ahn, c'mon)
#		'vb+vb',	# V. base: pres. imp. or inf. hyphenated pair (say-speak)
		'vbd',		# V. past (said, produced)
		'vbg',		# V. pres. part./gerund (keeping, attending)
#		'vbg+to',	# V. pres part. + infinitival to (gonna)
		'vbn',		# V. past part. (conducted, adopted)
#		'vbn+to',	# V. past part. + infinitival to (gotta)
		'vbz',		# V. pres. 3rd pers. sing. (deserves, seeks)
		'vbc'		# V. compound (band together, run over)
	]

	compounds = read_compound_list(compounds_filename)
	outfile = open(output_filename, "w")

	noun_freq_dist = FreqDist()
	verb_freq_dist = FreqDist()

	count = 0
	increment = 10000

	sys.stdout.write('Building initial frequency distributions')

	for sentence in islice(brown.tagged(), 1000):

		# Greedily search for compound nouns/verbs. The search is naive and
		# doesn't account for inflected words within the compound (so
		# variant forms of the compound will not be identified e.g. the
		# compound 'abdominal cavities' will not be recognised as the plural of
		# 'abdominal cavity'); this is in keeping with the current Pedersen
		# implementation. Rectifying this is mildy tricky in that some compound
		# constituents are expected to be inflected e.g. 'abandoned ship' so
		# it isn't possible to simply uninflect each constituent before
		# searching; rather, a list of variant compounds containing all possible
		# inflected/uninflected constituents would probably be needed (compounds
		# rarely exceed length four so the quadratic search space wouldn't be
		# too scary).

		new_sentence = []
		compound = sentence.pop(0)

		# Pop (word token, PoS tag) tuples from the sentence until all words
		# have been consumed. Glue the word tokens together while they form
		# a substring of a valid compound. When adding a new token makes the
		# compound invalid, append the current compound onto the new sentence
		# queue and assign the new (token, tag) tuple as the current compound
		# base. 

		while len(sentence) > 0:

			(token, tag) = sentence.pop(0)
			compound_token = compound[0] + ' ' + token

			# Perform a binary search through the list of all compounds. The
			# search necessarily accepts partial matches. The search returns
			# the compound type ('nc' for noun compound or 'vbc' for verb
			# compound) of the matched compound, or False if no match was
			# found. Recording the compound type is necessary so that the
			# correct frequency distribution can be updated later.

			compound_tag = substr_binary_search(compound_token, compounds)

			if compound_tag:
				compound = (compound_token, compound_tag)

			# If appending the new token to the current compound results in
			# an invalid compound, append the current compound to the new
			# sentence queue and reset it, placing the new token as the
			# beginning of a (possible) new compound.

			else:
				new_sentence.append(compound)
				compound = (token, tag)

		# The final (possibly compound) token in each sentence needs to be
		# manually appended onto the new sentence list.

		new_sentence.append(compound)

		for (token, tag) in new_sentence:

			# Give the user some feedback to let him or her know the
			# distributions are still being built.

			count += 1

			if count % increment == 0:
				sys.stdout.write('.')

			# Basic splitting based on the word token's POS. Later this could
			# be further developed using the additional (now commented out)
			# tag types and adding conditional checks to turn e.g. "you'll"
			# into "you" + "will". This would increase the accuracy of the
			# distribution, as currently all such contractions are discarded
			# (because they won't match any entries in the dictionary).

			if tag in noun_tags:
				pos = "noun"
				dictionary = N
				freq_dist = noun_freq_dist

			elif tag in verb_tags:
				pos = "verb"
				dictionary = V
				freq_dist = verb_freq_dist

			else: token = None

			# If the word form is inflected e.g. plural, retrieve its base
			# or uninflected form.

			if token is not None:

				if dictionary.has_key(token): uninflected_token = token
				else: uninflected_token = morphy(token, pos)

			else: uninflected_token = None

			# Increment the count for each sense of the word token, there
			# being no practical way to distinguish between word senses in the
			# Brown corpus (SemCor would be another story).

			if uninflected_token is not None:
				senses = dictionary[uninflected_token].getSenses()

				for sense in senses:
					synset = sense.synset
					freq_dist.inc(synset)

	# Propogate the frequency counts up the taxonomy structure. Thus the
	# root node (or nodes) will have a frequency equal to the sum of all
	# of their descendent node frequencies (plus a bit extra, if the root
	# node appeared in the source text). The ditribution will then adhere
	# to the IR principle that nodes (synsets) that appear less frequently
	# have a higher information content.

	sys.stdout.write(' done.\n')
	sys.stdout.write('Finding taxonomy roots...')

	noun_roots = get_roots(N)
	verb_roots = get_roots(V)

	sys.stdout.write(' done.\n')
	sys.stdout.write('Propogating frequencies up the taxonomy trees...')

	for root in noun_roots:
		propogate_frequencies(noun_freq_dist, root)

	for root in verb_roots:
		propogate_frequencies(verb_freq_dist, root)

	sys.stdout.write(' done.\n')

	# Output the frequency distributions to a file in some manner.

	outfile.close()

	return (noun_freq_dist, verb_freq_dist)
