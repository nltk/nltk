# Natural Language Toolkit: Texts
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import textwrap

from probability import FreqDist, LidstoneProbDist
from compat import defaultdict
from util import ngram
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
            self.name = " ".join(self[1:end])
        else:
            self.name = " ".join(self[:8]) + "..."
    
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
        print '; '.join([w1+' '+w2 for w1, w2 in self._collocations[:num]])

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
        print '\n'.join(textwrap.wrap(' '.join(text)))
    
    def similar(self, word, num=20):
        """
        Distributional similarity: find other words which appear in the
        same contexts as the specified word.
        
        @param word: The word used to seed the similarity search
        @type word: C{str} 
        @param num: The number of words to generate (default=20)
        @type num: C{int} 
        """
        
        if '_word_context_map' not in self.__dict__:
            print "Building word-context index..."
            self._word_context_map = defaultdict(list)
            for w1, w2, w3 in ngram([w.lower() for w in self], 3): 
                self._word_context_map[w2].append( (w1, w3) )            

        word = word.lower()
        if word in self._word_context_map:
            contexts = set(self._word_context_map[word])
            fd = FreqDist(w for w in self._word_context_map
                          for c in self._word_context_map[w]
                          if c in contexts and not w == word)
            words = fd.sorted()[:num]
            print '\n'.join(textwrap.wrap(' '.join(words)))
        else:
            return "No matches"
    
    def dispersion_plot(self, words):
        from nltk.draw import dispersion_plot
        dispersion_plot(self, words)

    def zipf_plot(self, *args):
        self.vocab().zipf_plot(*args)
    
    def vocab(self):
        if "_vocab" not in self.__dict__:
            print "Building vocabulary index..."
            self._vocab = FreqDist(self)
        return self._vocab

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
        
def demo():
    from nltk.corpus import brown
    text = Text(brown.words(categories='a'))
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
    text.zipf_plot()
    print
    print "Indexing:"
    print "text[3]:", text[3]
    print "text[3:5]:", text[3:5]
    print "text.vocab['news']:", text.vocab['news']
                         
if __name__ == '__main__':
    demo()


