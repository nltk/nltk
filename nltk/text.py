# Natural Language Toolkit: Texts
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from math import log
import re

from probability import FreqDist, LidstoneProbDist
from compat import defaultdict
from util import ngrams, tokenwrap
from model import NgramModel

class Text(list):
    """A text object, which can be loaded with a sequence of words,
    and which supports counting, concordancing, collocation discovery, etc.
    This class is intended to support initial exploration of texts.
    It is initialized with a list of words, e.g.:
    
    >>> moby = Text(nltk.corpus.gutenberg.words('melville-moby_dick.txt')) 
    
    Many of the methods simply print their results, and are intended
    for use via the interactive console.
    """
    
    def __init__(self, text, name=None):
        """
        Create a Text object.
        
        @param words: The source text.
        @type words: C{sequence} of C{str}
        """
        list.__init__(self, text)
        
        if name:
            self.name = name
        elif ']' in self[:20]:
            end = self[:20].index(']')
            self.name = " ".join(map(str, self[1:end]))
        else:
            self.name = " ".join(map(str, self[:8])) + "..."
    
    def concordance(self, word, width=80, lines=25):
        """
        Print a concordance for the word with the specified context window.
        
        @param word: The target word
        @type word: C{str}
        @param width: The width of each line, in characters (default=80)
        @type width: C{int}
        @param lines: The number of lines to display (default=25)
        @type lines: C{int}
        """
        if '_offsets' not in self.__dict__:
            print "Building index..."
            self._offsets = defaultdict(list)
            for i in range(len(self)):
                w = self[i].lower()
                self._offsets[w].append(i)

        word = word.lower()
        half_width = (width - len(word)) / 2
        context = width/4 # approx number of words of context
        if word in self._offsets:
            lines = min(lines, self._offsets[word])
            print "Displaying %s of %s matches:" %\
                    (lines, len(self._offsets[word]))
            for i in self._offsets[word]:
                left = ' ' * half_width + ' '.join(self[i-context:i])
                right = ' '.join(self[i+1:i+context])
                left = left[-half_width:]
                right = right[:half_width]
                print left, word, right
                lines -= 1
                if lines < 0:
                    break
        else:
            print "No matches"
    
    def collocations(self, num=20):
        """
        Print collocations derived from the text.
        
        @param num: The number of collocations to produce.
        @type num: C{int}
        """
        if '_collocations' not in self.__dict__:
            print "Building word index..."
            from operator import itemgetter
            text = filter(lambda w: len(w) > 2, self)
            fd = FreqDist(tuple(text[i:i+2])
                          for i in range(len(text)-1))
            scored = [((w1,w2), fd[(w1,w2)] ** 3 / float(self.vocab()[w1] * self.vocab()[w2])) 
                      for w1, w2 in fd]
            scored.sort(key=itemgetter(1), reverse=True)
            self._collocations = map(itemgetter(0), scored)

        colloc_strings = [w1+' '+w2 for w1, w2 in self._collocations[:num]]
        print tokenwrap(colloc_strings, separator="; ")

    def readability(self, method):
        # code from nltk_contrib.readability
        raise NotImplementedError
    
    def generate(self, length=100):
        """
        Print random text, generated using a trigram language model.
        
        @param length: The length of text to generate (default=100)
        @type length: C{int} 
        """
        if '_model' not in self.__dict__:
            print "Building ngram index..."
            estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
            self._model = NgramModel(3, self, estimator)
        text = self._model.generate(length)
        print tokenwrap(text)

    def _build_word_context_map(self):    
        if '_word_context_map' not in self.__dict__:
            print "Building word-context index..."
            self._word_context_map = defaultdict(list)
            for w1, w2, w3 in ngrams([w.lower() for w in self if w.isalpha()], 3): 
                self._word_context_map[w2].append( (w1, w3) )            

    def similar(self, word, num=20):
        """
        Distributional similarity: find other words which appear in the
        same contexts as the specified word; list most similar words first.
        
        @param word: The word used to seed the similarity search
        @type word: C{str} 
        @param num: The number of words to generate (default=20)
        @type num: C{int} 
        """
        
        self._build_word_context_map()
        word = word.lower()
        if word in self._word_context_map:
            contexts = set(self._word_context_map[word])
            fd = FreqDist(w for w in self._word_context_map
                          for c in self._word_context_map[w]
                          if c in contexts and not w == word)
            words = fd.keys()[:num]
            print tokenwrap(words)
        else:
            print "No matches"
    
    def common_contexts(self, words, num=20):
        """
        Find contexts where the specified words appear; list
        most frequent common contexts first.
        
        @param word: The word used to seed the similarity search
        @type word: C{str} 
        @param num: The number of words to generate (default=20)
        @type num: C{int} 
        """
        
        self._build_word_context_map()
        contexts = [set(self._word_context_map[w.lower()]) for w in words]
        empty = [words[i] for i in range(len(words)) if not contexts[i]]
        common = reduce(set.intersection, contexts)
        if empty:
            print "The following word(s) were not found:", " ".join(words)
        elif not common:
            print "No common contexts were found"
        else:
            fd = FreqDist(c for w in words
                          for c in self._word_context_map[w]
                          if c in common)
            ranked_contexts = fd.keys()[:num]
            print tokenwrap(w1+"_"+w2 for w1,w2 in ranked_contexts)

    def dispersion_plot(self, words):
        """
        Produce a plot showing the distribution of the words through the text.
        Requires pylab to be installed.
        
        @param words: The words to be plotted
        @type word: C{str}
        """
        from nltk.draw import dispersion_plot
        dispersion_plot(self, words)

    def plot(self, *args):
        """
        See documentation for FreqDist.plot()
        """
        self.vocab().plot(*args)
    
    def vocab(self):
        if "_vocab" not in self.__dict__:
            print "Building vocabulary index..."
            self._vocab = FreqDist(self)
        return self._vocab

    def findall(self, regexp):
        """
        Find instances of the regular expression in the text.
        The text is a list of tokens, and a regexp pattern to match
        a single token must be surrounded by angle brackets.  E.g.
        
        >>> text5.findall("<.*><.*><bro>")
        you rule bro; telling you bro; u twizted bro
        >>> text1.findall("<a>(<.*>)<man>")
        monied; nervous; dangerous; white; white; white; pious; queer; good;
        mature; white; Cape; great; wise; wise; butterless; white; fiendish;
        pale; furious; better; certain; complete; dismasted; younger; brave;
        brave; brave; brave
        >>> text9.findall("<th.*>{3,}")
        thread through those; the thought that; that the thing; the thing
        that; that that thing; through these than through; them that the;
        through the thick; them that they; thought that the
        
        @param regexp: A regular expression
        @type regexp: C{str}
        """
        
        if "_raw" not in self.__dict__:
            self._raw = ''.join('<'+w+'>' for w in self) 

        # preprocess the regular expression
        regexp = re.sub(r'\s', '', regexp)
        regexp = re.sub(r'<', '(?:<(?:', regexp)
        regexp = re.sub(r'>', ')>)', regexp)
        regexp = re.sub(r'(?<!\\)\.', '[^>]', regexp)

        # perform the search
        hits = re.findall(regexp, self._raw)

        # postprocess the output
        hits = [re.sub(r'><', ' ', h) for h in hits]
        hits = [re.sub(r'^<|>$', '', h) for h in hits]
        print tokenwrap(hits, "; ") 

    def __str__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        return '<Text: %s>' % self.name
        
    def __repr__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        return self.__str__()


# Prototype only; this approach will be slow to load
class TextCollection(Text):
    """A collection of texts, which can be loaded with list of texts, or
    with a corpus consisting of one or more texts, and which supports
    counting, concordancing, collocation discovery, etc.  Initialize a
    TextCollection as follows:
    
    >>> gutenberg = TextCollection(nltk.corpus.gutenberg)
    >>> mytexts = TextCollection([text1, text2, text3])
    
    Iterating over a TextCollection produces all the tokens of all the
    texts in order.
    """
    
    def __init__(self, source):
        if hasattr(source, 'words'): # bridge to the text corpus reader
            self._texts = source.files()
            list.__init__(self, source.words())
        else: # source is a list of texts 
            self._texts = source
            list.__init__(self, [word for text in source for word in text])
    
    def tf(self, term, text, method=None):
        return float(text.count(term)) / len(text)

    def df(self, term, method=None):
        return float(len(True for text in self._texts if term in text)) / len(self._texts)

    def tf_idf(self, term, text):
        return self.tf(term, text) / log(self.df(term))
    
def demo():
    from nltk.corpus import brown
    text = Text(brown.words(categories='news'))
    print text
    print
    print "Concordance:"
    text.concordance('news')
    print
    print "Distributionally similar words:"
    text.similar('news')
    print
    print "Collocations:"
    text.collocations()
    print
    print "Automatically generated text:"
    text.generate()
    print
    print "Dispersion plot:"
    text.dispersion_plot(['news', 'report', 'said', 'announced'])
    print
    print "Vocabulary plot:"
    text.plot(50)
    print
    print "Indexing:"
    print "text[3]:", text[3]
    print "text[3:5]:", text[3:5]
    print "text.vocab()['news']:", text.vocab()['news']
                         
if __name__ == '__main__':
    demo()


