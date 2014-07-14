from __future__ import print_function

from words import *
from nltk.wordnet import *
from operator import itemgetter
import nltk
import re
from string import join

def build_word_associations():
    cfd = nltk.ConditionalFreqDist()

    # get a list of all English stop words
    stopwords_list = nltk.corpus.stopwords.words('english')

    # count words that occur within a window of size 5 ahead of other words
    for sentence in nltk.corpus.brown.tagged_sents():
        sentence = [(token.lower(), tag) for (token, tag) in sentence if token.lower() not in stopwords_list]
        for (index, (token, tag)) in enumerate(sentence):
            if token not in stopwords_list:
                window = sentence[index+1:index+5]
                for (window_token, window_tag) in window:
                    if window_token not in stopwords_list and window_tag[0] is tag[0]:
                        cfd[token].inc(window_token)
    return cfd

def associate():
    while True:
        word = raw_input("Enter a word: ")
        for i in range(100):
            next = cfd[word].max()
            if next:
                print("->", next,)
                word = next
            else:
                break
        print()

def build_word_contexts(words):
    contexts_to_words = {}
    words = [w.lower() for w in words]
    for i in range(1,len(words)-1):
        context = words[i-1]+"_"+words[i+1]
        if context not in contexts_to_words:
            contexts_to_words[context] = []
        contexts_to_words[context].append(words[i])
    # inverted structure, tracking frequency
    words_to_contexts = {}
    for context in contexts_to_words:
        for word in contexts_to_words[context]:
            if word not in words_to_contexts:
                words_to_contexts[word] = []
            words_to_contexts[word].append(context)
    return words_to_contexts, contexts_to_words

def search_contexts(words):
    words_to_contexts, contexts_to_words = build_word_contexts(words)
    while True:
        hits = []
        word = raw_input("word> ")
        if word not in words_to_contexts:
            print("Word not found")
            continue
        contexts = words_to_contexts[word]
        for w in words_to_contexts:  # all words
            for context in words_to_contexts[w]:
                if context in contexts:
                    hits.append(w)
        hit_freqs = count_words(hits).items()
        sorted_hits = sorted(hit_freqs, key=itemgetter(1), reverse=True)
        words = [word for (word, count) in sorted_hits[1:] if count > 1]
        print(join(words))

def lookup(word):
    for category in [N, V, ADJ, ADV]:
        if word in category:
            for synset in category[word]:
                print(category[word], ":", synset.gloss)

############################################
# Simple Tagger
############################################

# map brown pos tags
# http://khnt.hit.uib.no/icame/manuals/brown/INDEX.HTM

def map1(tag):
    tag = re.sub(r'fw-', '', tag)     # foreign words
    tag = re.sub(r'-[th]l', '', tag)  # headlines, titles
    tag = re.sub(r'-nc', '', tag)     # cited
    tag = re.sub(r'ber?', 'vb', tag)  # verb "to be"
    tag = re.sub(r'hv', 'vb', tag)    # verb "to have"
    tag = re.sub(r'do', 'vb', tag)    # verb "to do"
    tag = re.sub(r'nc', 'nn', tag)    # cited word
    tag = re.sub(r'z', '', tag)       # third-person singular
    return tag

def map2(tag):
    tag = re.sub(r'\bj[^-+]*', 'J', tag)  # adjectives
    tag = re.sub(r'\bp[^-+]*', 'P', tag)  # pronouns
    tag = re.sub(r'\bm[^-+]*', 'M', tag)  # modals
    tag = re.sub(r'\bq[^-+]*', 'Q', tag)  # qualifiers
    tag = re.sub(r'\babl',     'Q', tag)  # qualifiers
    tag = re.sub(r'\bab[nx]',  'D', tag)  # determiners
    tag = re.sub(r'\bap',      'D', tag)  # determiners
    tag = re.sub(r'\bd[^-+]*', 'D', tag)  # determiners
    tag = re.sub(r'\bat',      'D', tag)  # determiners
    tag = re.sub(r'\bw[^-+]*', 'W', tag)  # wh words
    tag = re.sub(r'\br[^-+]*', 'R', tag)  # adverbs
    tag = re.sub(r'\bto',      'T', tag)  # "to"
    tag = re.sub(r'\bc[cs]',   'C', tag)  # conjunctions
    tag = re.sub(r's',         '',  tag)  # plurals
    tag = re.sub(r'\bin',      'I', tag)  # prepositions
    tag = re.sub(r'\buh',      'U', tag)  # interjections (uh)
    tag = re.sub(r'\bex',      'E', tag)  # existential "there"
    tag = re.sub(r'\bvbn',     'VN', tag) # past participle
    tag = re.sub(r'\bvbd',     'VD', tag) # past tense
    tag = re.sub(r'\bvbg',     'VG', tag) # gerund
    tag = re.sub(r'\bvb',      'V', tag)  # verb
    tag = re.sub(r'\bnn',      'N', tag)  # noun
    tag = re.sub(r'\bnp',      'NP', tag) # proper noun
    tag = re.sub(r'\bnr',      'NR', tag) # adverbial noun
    tag = re.sub(r'\bex',      'E', tag)  # existential "there"
    tag = re.sub(r'\bod',      'OD', tag) # ordinal
    tag = re.sub(r'\bcd',      'CD', tag) # cardinal
    tag = re.sub(r'-t',        '', tag)   # misc
    tag = re.sub(r'[a-z\*]',   '', tag)   # misc
    return tag

def map(tag):
    return map2(map1(tag.lower()))

# print(sorted(set(map2(map1(tag)) for s in brown.tagged() for w,tag in s)))

def load_brown_corpus(sections):
    global map
    corpus = nltk.corpus.brown.tagged_sents(tuple(sections))
    return [[(w.lower(), map(t)) for w, t in sent] for sent in corpus]

def train_tagger(corpus):
    t0 = nltk.tag.Default('N')
    t1 = nltk.tag.Unigram(cutoff=0, backoff=t0)
    t2 = nltk.tag.Bigram(cutoff=0, backoff=t1)
    t3 = nltk.tag.Trigram(cutoff=1, backoff=t2)

    t1.train(corpus, verbose=True)
    t2.train(corpus, verbose=True)
    t3.train(corpus, verbose=True)
    return t3

def tag(corpus):
    print("Training tagger...")
    tagger = train_tagger(corpus)
    while True:
        text = raw_input("sentence> ")
        words = text.split()
        print(join(word+"/"+tag for word, tag in tagger.tag(words)))

WORD_OR_TAG = '[^/ ]+'
BOUNDARY = r'\b'

def process(pattern):
    new = []
    for term in pattern.split():
        if re.match('[A-Z]+$', term):
            new.append(BOUNDARY + WORD_OR_TAG + '/' + term + BOUNDARY)
        elif '/' in term:
            new.append(BOUNDARY + term + BOUNDARY)
        else:
            new.append(BOUNDARY + term + '/' + WORD_OR_TAG + BOUNDARY)
    return join(new)

def search(corpus, num=25):
    print("Loading corpus...")
    strings = [join(w+'/'+t for (w,t) in sent) for sent in corpus]
    while True:
        pattern = ""
        while not pattern:
            pattern = raw_input("search> ")
        pattern = process(pattern)
        i = 0
        for sent in strings:
            m = re.search(pattern, sent)
            if m:
                sent = ' '*35 + sent + ' '*45
                print(sent[m.start():m.start()+80])
                i += 1
                if i > num:
                    break

############################################
# Wordnet Browser
# now incorporated into NLTK as wordnet.browse
############################################

############################################
# Mad Libs
############################################

madlib = """Britney Spears will meet up with her %(NP)s label for
crisis talks about the future of her %(N)s this week reports Digital Spy.
%(NP)s Records plan to tell Spears to stop %(VG)s and take more
care of her %(J)s image if she wants to avoid being %(VD)s by the noun.
The news %(V)s shortly after Britney posted a message on her
website promising a new album and tour.  The last couple of years
have been quite a ride for me, the media has criticized %(P)s every
noun %(C)s printed a skewed perception of who I really am as a human
being, she wrote in a letter posted %(NR)s."""

# mapping = {}
# mapping['NP'] =
# mapping['N'] =
# mapping['VG'] =
# mapping['J'] =
# mapping['VD'] =
# mapping['V'] =
# mapping['P'] =
# mapping['C'] =
# mapping['NR'] =

# print(madlib % mapping)

