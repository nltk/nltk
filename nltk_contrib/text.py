# Prototype Text class

from nltk import FreqDist, defaultdict

class Text(FreqDist):
    
    def __init__(self, words):
        self._text = list(words)
        FreqDist.__init__(self, self._text)
        self._index = defaultdict(set)
        for i in range(len(self._text)):
            word = self._text[i].lower()
            self._index[word].add(i)
    
    def __getitem__(self, index):
        if isinstance(index, (int, slice)):
            return self._texts[index]
        else:
            return FreqDist.__getitem__(self, index)

    def concordance(self, word, width=80, lines=20):
        "Generate a concordance for the word with the specified context window"
        word = word.lower()
        offset = (width - len(word)) / 2
        context = width/4 # approx number of words of context
        if word in self._index:
            print "Found %s matches; displaying first %s:" %\
                    (len(self._index[word]), lines)
            for i in self._index[word]:
                left = ' ' * offset + ' '.join(self._text[i-context:i])
                right = ' '.join(self._text[i+1:i+context])
                left = left[-offset:]
                right = right[:offset]
                print left, word, right
                lines -= 1
                if lines < 0:
                    break
        else:
            print "No matches"
    
    def collocations(self, num=20):
        if '_collocations' not in self.__dict__:
            from operator import itemgetter
            text = filter(lambda w: len(w) > 2, self._text)
            fd = FreqDist(tuple(text[i:i+2])
                          for i in range(len(text)-1))
            scored = [((w1,w2), fd[(w1,w2)] ** 3 / float(self[w1] * self[w2])) 
                      for w1, w2 in fd]
            scored.sort(key=itemgetter(1), reverse=True)
            self._collocations = map(itemgetter(0), scored)
        print '; '.join([w1+' '+w2 for w1, w2 in self._collocations[:num]])

    def readability(self, method):
        # code from nltk_contrib.readability
        raise NotImplementedError
    
    def generate(self, length=100):
        if '_model' not in self.__dict__:
            from nltk.probability import LidstoneProbDist
            from nltk.model import NgramModel
            estimator = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
            self._model = NgramModel(3, self._text, estimator)
        text = self._model.generate(length)
        import textwrap
        print '\n'.join(textwrap.wrap(' '.join(text)))
    
    def dispersion_plot(self, words):
        from nltk.draw import dispersion_plot
        dispersion_plot(self._text, words)

def demo():
    from nltk.corpus import brown
    text = Text(brown.words(categories='a'))
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
                         
if __name__ == '__main__':
    demo()
