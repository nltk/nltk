# Natural Language Toolkit: Brown Corpus Information Content Module
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Oliver Steele <steele@osteele.com>
#         David Ormiston Smith <daosmith@csse.unimelb.edu.au>>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import pickle
import sys

from itertools import islice

from nltk.corpus import brown
from nltk.probability import FreqDist
from util import *
from dictionary import N, V

def substr_binary_search(item, list):

    if not list:
        return None

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

def read_word_list(filename):

    word_list = []
    infile = open(filename, 'r')

    for line in infile:
        line = line.rstrip()
        word_list.append(line)

    word_list.sort()

    return word_list

def get_roots(dictionary):
    roots = []
    for word in dictionary:
        for synset in dictionary[word].synsets():
            hypernyms = set(synset[HYPERNYM]) | set(synset[INSTANCE_HYPERNYM])
            if len(hypernyms) == 0: roots.append(synset)
    return roots

def propogate_frequencies(freq_dist, synset):
    hyponyms = set(synset[HYPONYM]) | set(synset[INSTANCE_HYPONYM])
    for hyponym in hyponyms:
        freq_dist.inc(hyponym, propogate_frequencies(freq_dist, hyponym))
    return freq_dist[synset]

def brown_information_content(output_filename, compounds_filename, \
        stopwords_filename=None, smoothing=True):

    # A list of all the noun and verb parts of speech as recorded in the
    # Brown corpus. Currently many are ignored because the Wordnet morphy()
    # method, which derives the base form of inflected words, can't handle
    # contractions, genetive forms etc.

    noun_tags = [ 
        'nn',        # N. sing. common (burden)
#        'nn$',        # N. sing. common, genetive (company's)
#        'nn+bez',    # N. sing. common + 'to be' pres. 3rd pers sing. (wife's)
#        'nn+hvd',    # N. sing. common + 'to have' past (James'd)
#        'nn+hvz',    # N. sing. common + 'to have' pres. 3rd pers sing. (guy's)    
#        'nn+in',    # N. sing. common + prep. (buncha)
#        'nn+md',    # N. sing. common + modal aux. (sun'll)
#        'nn+nn',    # N. sing. common, hyphenated pair (stomach-belly)
        'nns',        # N. plu. common (burdens)
#        'nns$',        # N. plu. common genetive (companies')
#        'nns+md',    # N. plu. common + modal aux. (cowboys'll)
        'np',        # N. sing. proper (September)
#        'np$',        # N. sing. proper genetive (William's)
#        'np+bez',    # N. sing. proper + 'to be' pres. 3rd pers sing. (Rob's)
#        'np+hvd',    # N. sing. proper + 'to have' past (James'd)
#        'np+hvz',    # N. sing. proper + 'to have' pres. 3rd pers sing. (Bill's)    
#        'np+md',    # N. sing. proper + modal aux. (John'll)
        'nps',        # N. plu. proper (Catholics)
#        'nps$',        # N. plu. proper, genetive (Republicans')
        'nr',        # N. sing. adverbial (today, Saturday, East)
#        'nr$',        # N. sing. adverbial, genetive (Saturday's)
#        'nr+md'        # N. sing. adverbial + modal aux. (today'll)
        'nrs',        # N. plu. adverbial (Sundays)
        'nc',        # N. compound (jigsaw puzzle, egg cup)
    ]

    verb_tags = [
        'vb',        # V. base: pres. imp. or inf. (find, act)
#        'vb+at',    # V. base: pres. or inf. + article (wanna)
#        'vb+in',    # V. base: pres. imp. or inf. + prep. (lookit)
#        'vb+jj',    # V. base: pres. imp. or inf. + adj. (die-dead)
#        'vb+ppo',    # V. pres. + pronoun, personal, acc. (let's)
#        'vb+rp',    # V. imperative + adverbial particle (g'ahn, c'mon)
#        'vb+vb',    # V. base: pres. imp. or inf. hyphenated pair (say-speak)
        'vbd',        # V. past (said, produced)
        'vbg',        # V. pres. part./gerund (keeping, attending)
#        'vbg+to',    # V. pres part. + infinitival to (gonna)
        'vbn',        # V. past part. (conducted, adopted)
#        'vbn+to',    # V. past part. + infinitival to (gotta)
        'vbz',        # V. pres. 3rd pers. sing. (deserves, seeks)
        'vbc'        # V. compound (band together, run over)
    ]

    outfile = open(output_filename, "wb")

    if compounds_filename:
        compounds = read_word_list(compounds_filename)
    else:
        compounds = []

    if stopwords_filename:
        stopwords = read_word_list(stopword_filename)
    else:
        stopwords = []

    noun_fd = FreqDist()
    verb_fd = FreqDist()

    count = 0
    increment = 10000

    sys.stdout.write("Building initial frequency distributions")

    for file in brown.files():
        for sentence in brown.tagged_sents(file):

            if len(sentence) == 0:
                continue

            # Greedily search for compound nouns/verbs. The search is naive and
            # doesn't account for inflected words within the compound (so
            # variant forms of the compound will not be identified e.g. the
            # compound 'abdominal cavities' will not be recognised as the plural of
            # 'abdominal cavity'); this is in keeping with the original Perl
            # implementation. Rectifying this is mildy tricky in that some compound
            # constituents are expected to be inflected e.g. 'abandoned ship' so
            # it isn't possible to simply uninflect each constituent before
            # searching; rather, a list of variant compounds containing all possible
            # inflected/uninflected constituents would be needed (compounds rarely
            # exceed length four so the quadratic search space wouldn't be too scary).

            new_sentence = []
            compound = sentence.pop(0)

            # Pop (word token, PoS tag) tuples from the sentence until all words
            # have been consumed. Glue the word tokens together while they form
            # a substring of a valid compound. When adding a new token makes the
            # compound invalid, append the current compound onto the new sentence
            # queue and assign the new (token, tag) tuple as the current compound base. 

            while len(sentence) > 0:
                (token, tag) = sentence.pop(0)
                token = token.lower()

                # Add this token to the current compound string, creating a
                # candidate compound token that may or may not exist in Wordnet.
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
                # distributions are still being built. The initial stage can take
                # quite some time (half an hour or more).

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
                    freq_dist = noun_fd

                elif tag in verb_tags:
                    pos = "verb"
                    dictionary = V
                    freq_dist = verb_fd

                else:
                    token = None

                # If the word form is inflected e.g. plural, retrieve its base
                # or uninflected form.

                if token is not None:

                    if dictionary.has_key(token):
                        uninflected_token = token
                    else:
                        uninflected_token = morphy(token, pos)

                else: uninflected_token = None

                # Increment the count for each sense of the word token, there
                # being no practical way to distinguish between word senses in the
                # Brown corpus (SemCor would be another story).

                if uninflected_token:
                    for synset in dictionary[uninflected_token]:
                        freq_dist.inc(synset)

    # If smoothing is True perform Laplacian smoothing i.e. add 1 to each
    # synset's frequency count.

    if smoothing:
        for sample in noun_fd:
            noun_fd.inc(sample)
        for sample in verb_fd:
            verb_fd.inc(sample)

    # Propogate the frequency counts up the taxonomy structure. Thus the
    # root node (or nodes) will have a frequency equal to the sum of all
    # of their descendent node frequencies (plus a bit extra, if the root
    # node appeared in the source text). The distribution will then adhere
    # to the IR principle that nodes (synsets) that appear less frequently
    # have a higher information content.

    sys.stdout.write(" done.\n")
    sys.stdout.write("Finding taxonomy roots...")

    noun_roots = get_roots(N)
    verb_roots = get_roots(V)

    sys.stdout.write(" done.\n")
    sys.stdout.write("Propogating frequencies up the taxonomy trees...")

    for root in noun_roots:
        propogate_frequencies(noun_fd, root)

    for root in verb_roots:
        propogate_frequencies(verb_fd, root)

    sys.stdout.write(" done.\n")

    # Output the frequency distributions to a file. Rather than pickle the
    # frequency distributions, and the synsets contained therein, output
    # a dict of synset identifiers and probabilities. This results in a file
    # which is a great deal smaller than the pickled FreqDist object file.

    sys.stdout.write("Converting to synset/sample count dictionaries...")

    noun_dict = {}
    verb_dict = {}

    # The probabilities are not calculated as is normal for a frequency
    # distribution (i.e. sample count / sum of all sample counts). Instead
    # they are (sample count / sample count of root node), because of the
    # propagation step that was performed earlier; this has the desirable
    # consequence that root nodes have a probability of 1 and an
    # Information Content (IC) score of 0.

    root = N['entity'][0].synset

    for sample in noun_fd:
        noun_dict[sample.offset] = (noun_fd[sample], noun_fd[root])

    for sample in verb_fd:
        root = sample.hypernym_paths()[0][0]
        verb_dict[sample.offset] = (verb_fd[sample], verb_fd[root])

    sys.stdout.write(" done.\n")
    sys.stdout.write("Writing probability hashes to file %s..." % (output_filename))

    pickle.dump(noun_dict, outfile)
    pickle.dump(verb_dict, outfile)

    sys.stdout.write(" done.\n")

    outfile.close()
    
if __name__ == '__main__':
    brown_information_content('brown_ic.dat', None)
