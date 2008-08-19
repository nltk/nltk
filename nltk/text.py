# Natural Language Toolkit: Texts
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk import FreqDist, defaultdict

class Text(list):
    """A text object, which can be loaded with a sequence of words,
    and which supports counting, concordancing, collocation discovery, etc.
    This class is intended to support initial exploration of texts.
    It is initialized with a list of words, e.g.:
    
    >>> moby = Text(nltk.corpus.gutenberg.words('melville-moby_dick.txt')) 
    
    Many of the methods simply print their results, and are intended
    for use via the interactive console.
    """
    
    def __init__(self, text):
        """
        Create a Text object.
        
        @param words: The source text.
        @type words: C{sequence} of C{str}
        """
        list.__init__(self, text)
        self.vocab = FreqDist(self)
        self.offsets = defaultdict(list)
        for i in range(len(self)):
            word = self[i].lower()
            self.offsets[word].append(i)
    
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
        word = word.lower()
        half_width = (width - len(word)) / 2
        context = width/4 # approx number of words of context
        if word in self.offsets:
            print "Found %s matches; displaying first %s:" %\
                    (len(self.offsets[word]), lines)
            for i in self.offsets[word]:
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
            from operator import itemgetter
            text = filter(lambda w: len(w) > 2, self)
            fd = FreqDist(tuple(text[i:i+2])
                          for i in range(len(text)-1))
            scored = [((w1,w2), fd[(w1,w2)] ** 3 / float(self.vocab[w1] * self.vocab[w2])) 
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
            from nltk.probability import LidstoneProbDist
            from nltk.model import NgramModel
            estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
            self._model = NgramModel(3, self, estimator)
        text = self._model.generate(length)
        import textwrap
        print '\n'.join(textwrap.wrap(' '.join(text)))
    
    def dispersion_plot(self, words):
        from nltk.draw import dispersion_plot
        dispersion_plot(self, words)

    def __str__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        return '<Text with %d words>' % len(self)
        
    def __repr__(self):
        """
        @return: A string representation of this C{FreqDist}.
        @rtype: string
        """
        return '<Text with %d words>' % len(self)
        
def demo():
    from nltk.corpus import brown
    text = Text(brown.words(categories='a'))
    print text
    print
    print "Concordance:"
    text.concordance('news')
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
    text.vocab.zipf_plot()
    print
    print "Indexing:"
    print "text[3]:", text[3]
    print "text[3:5]:", text[3:5]
    print "text.vocab['news']:", text.vocab['news']
                         
if __name__ == '__main__':
    demo()

__all__ = ['Text']
