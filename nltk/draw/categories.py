from words import *
from nltk.wordnet import *
from operator import itemgetter
from nltk.corpus import brown, stopwords
from nltk.probability import ConditionalFreqDist
import re
from string import join
from Tkinter import *
from nltk.draw import *


def build_word_associations():
    cfd = ConditionalFreqDist()

    # get a list of all English stop words
    stopwords_list = list(stopwords.raw('english'))

    # count words that occur within a window of size 5 ahead of other words
    for sentence in brown.tagged():
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
                print "->", next,
                word = next
            else:
                break
        print

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
            print "Word not found"
            continue
        contexts = words_to_contexts[word]
        for w in words_to_contexts:  # all words
            for context in words_to_contexts[w]:
                if context in contexts:
                    hits.append(w)
        hit_freqs = count_words(hits).items()
        sorted_hits = sorted(hit_freqs, key=itemgetter(1), reverse=True)
        words = [word for (word, count) in sorted_hits[1:] if count > 1]
        print join(words)
        
def lookup(word):
    for category in [N, V, ADJ, ADV]:
        if word in category:
            for synset in category[word]:
                print category[word], ":", synset.gloss

#def common_hypernyms(s1, s2):
#    h1 = s1.hypernym_paths()
#    h2 = s2.hypernym_paths()
#    for path1 in h1:
#        for path2 in h2:
#


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
    return map2(map1(tag))

# print sorted(set(map2(map1(tag)) for s in brown.tagged() for w,tag in s))

def load_brown_corpus(sections):
    global map
    corpus = brown.tagged(tuple(sections))
    return [[(w.lower(), map(t)) for w, t in sent] for sent in corpus]

def train_tagger(corpus):
    from nltk import tag
    t0 = tag.Default('N')
    t1 = tag.Unigram(cutoff=0, backoff=t0)
    t2 = tag.Bigram(cutoff=0, backoff=t1)
    t3 = tag.Trigram(cutoff=1, backoff=t2)
    
    t1.train(corpus, verbose=True)
    t2.train(corpus, verbose=True)
    t3.train(corpus, verbose=True)
    return t3

def tag(corpus):
    print "Training tagger..."
    tagger = train_tagger(corpus)
    while True:
        text = raw_input("sentence> ")
        words = text.split()
        print join(word+"/"+tag for word, tag in tagger.tag(words))

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

def search(corpus, num=50):
    print "Loading corpus..."
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
                print sent[m.start()-35:m.start()+45]
                i += 1
                if i > num:
                    break

############################################
# Wordnet Browser
############################################

from nltk.wordnet import *
from textwrap import TextWrapper
from string import join
from random import randint

# this code is proof of concept only, and needs a lot of tidying up

tw = TextWrapper(subsequent_indent="    ")

def show(synsets, index):
    return "%d %s;" % (index, synsets[index][0])

def print_gloss(synsets, index):
    print index, join(tw.wrap(synsets[index].gloss), "\n")

def print_all_glosses(synsets):
    for index in range(len(synsets)):
        print_gloss(synsets, index)

def print_all(synsets):
    for index in range(len(synsets)):
        print show(synsets, index),
    print

def help():
    print 'Lookup a word by giving the word in double quotes, e.g. "dog".'
    print 'Each word has one or more senses, pick a sense by typing a number.'
    print 'd=down, u=up, g=gloss, s=synonyms, a=all-senses, v=verbose, r=random.'
    print 'N=nouns, V=verbs, J=adjectives, R=adverbs.'

def _print_lookup(D, section, word):
    try:
        synsets = D[word]
        print section,
        print_all(synsets)
    except KeyError:
        pass

def _new_word(word):
    _print_lookup(N, "N", word)
    _print_lookup(V, "V", word)
    _print_lookup(ADJ, "J", word)
    _print_lookup(ADV, "R", word)
    if word in N: D = N
    elif word in V: D = V
    elif word in ADJ: D = ADJ
    elif word in ADV: D = ADV
    if word:
        synsets = D[word]
    else:
        synsets = _random_synset(D)
    return D, synsets

def _random_synset(D):
    return D[randint(0,len(D)-1)]

def browse(word="", index=0):
    print "Wordnet browser (type 'h' for help)"
    if word:
        D, synsets = _new_word(word)
        print show(synsets, index)
    else:
        D = N
        synsets = _random_synset(D)

    while True:
        if index >= len(synsets):
            index = 0
        if synsets:
            input = raw_input(synsets[index][0] + "_" + `index` + "/" + `len(synsets)` + "> ")
        else:
            input = raw_input("> ")  # safety net
        if input[0] == '"' and input[-1] == '"':
            D, synsets = _new_word(input[1:-1])
            index = 0
        elif input[0] in "0123456789":
            if int(input) < len(synsets):
                index = int(input)
                print_gloss(synsets, index)
            else:
                print "There are %d synsets" % len(synsets)
        elif input[0] is "a":
            print_all(synsets)
        elif input[0] is "g":
            print_gloss(synsets, index)
        elif input[0] is "v":
            print_all_glosses(synsets)
        elif input[0] is "h":
            help()
        elif input[0] is "r":
            synsets = _random_synset(D)
        elif input[0] is "u":
            try:
                hypernyms = synsets[index][HYPERNYM]
                hypernyms[0]
                synsets = hypernyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go up"
        elif input[0] is "d":
            try:
                hyponyms = synsets[index][HYPONYM]
                hyponyms[0]
                synsets = hyponyms
                print_all(synsets)
                index = 0
            except IndexError:
                print "Cannot go down"
        elif input[0] is "s":
            print "Synonyms:", join(word for word in synsets[index])
        elif input[0] in "N": # nouns
            if word in N:
                D = N
                synsets = D[word]
        elif input[0] is "V": # verbs
            if word in V:
                D = V
                synsets = D[word]
        elif input[0] is "J": # adjectives
            if word in ADJ:
                D = ADJ
                synsets = D[word]
        elif input[0] is "R": # adverbs
            if word in ADV:
                D = ADV
                synsets = D[word]
        elif input[0] is "q":
            print "Goodbye"
            break
        else:
            print "Unrecognised command, type 'h' for help"

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

# print madlib % mapping

############################################
# Category Search Demo
############################################

class CategorySearchView:
    def __init__(self):
        self.model = CategorySearchModel()
        self.top = Tk()
        self._init_top(self.top)
        self._init_widgets(self.top)
        
    def _init_top(self, top):
        top.geometry('+50+50')
        top.title('Category Search Demo')
        top.bind('<Control-q>', self.destroy)
        
    def _init_widgets(self, parent):
        self.main_frame = Frame(parent, dict(background='#777', padx=1, pady=1, border=1, width=80))        
        self._init_corpus_select(self.main_frame)
        self._init_query_box(self.main_frame)
        self._init_results_box(self.main_frame)
        self._init_status(self.main_frame)
        self.main_frame.pack(fill='both', expand=False)
                
    def _init_corpus_select(self, parent):
        self.var = StringVar(parent)
        self.var.set(self.model.DEFAULT_CORPUS)
        Label(parent, justify=LEFT, text=' Corpus: ', background='#777', padx = 2, pady = 1, border = 0).grid(row=0, column = 0, sticky = W)
        other_corpora = self.model.CORPORA.keys().remove(self.model.DEFAULT_CORPUS)
        OptionMenu(parent, self.var, self.model.DEFAULT_CORPUS, command=self.corpus_selected, *self.model.non_default_corpora()).grid(row=0, column=0)
        
    def corpus_selected(self, *args):
        self.status['text'] = self.var.get() + ' corpus selected'
        self.load_corpus(self.var.get())
        
    def load_corpus(self, name):
        self.status['text'] = 'Loading ' + self.var.get() + ' corpus'

    def _init_status(self, parent):
        self.status = Label(parent, justify=LEFT, relief=SUNKEN, background='#777', border=0, padx = 1, pady = 0)
        self.status.grid(row = 9, column= 0, columnspan=4, sticky=W)
    
    def _init_query_box(self, parent):
        scrollbar = Scrollbar(parent)
        scrollbar.grid(sticky=E, row=1,column=3,rowspan=3)
        self.query = Text(parent, name= "query", height = 10, yscrollcommand=scrollbar.set)
        self.query.grid(row=1,column=0,rowspan=3,columnspan=3)
        self.query.insert('1.0', 'Enter query here')
        scrollbar.config(command=self.query.yview)
    
    def _init_results_box(self, parent):
        scrollbar = Scrollbar(parent)
        scrollbar.grid(sticky=E, row=4, column =3, rowspan=5)
        self.results = Text(parent, name = "results", height = 30, state="disabled", yscrollcommand=scrollbar.set)
        self.results.grid(row=4, column =0, rowspan=5, columnspan =3)
        scrollbar.config(command=self.results.yview)
        
    def _scrollbar(self, parent, position):
        scrollbar = Scrollbar(parent)
        scrollbar.grid(sticky=E, **position)
        return scrollbar        
        
    def destroy(self, *e):
        if self.top is None: return
        self.top.destroy()
        self.top = None
        
    def mainloop(self, *args, **kwargs):
        if in_idle(): return
        self.top.mainloop(*args, **kwargs)
        
class CategorySearchModel:
    def __init__(self):
        self._BROWN_CORPUS = "brown"
        self.CORPORA = {self._BROWN_CORPUS:nltk.corpus.brown , "indian":nltk.corpus.indian}
        self.DEFAULT_CORPUS = self._BROWN_CORPUS
        
    def non_default_corpora(self):
        copy = []
        copy.extend(self.CORPORA.keys())
        copy.remove(self.DEFAULT_CORPUS)
        return copy

def demo():
    d = CategorySearchView()
    d.mainloop()
        