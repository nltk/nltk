# Prototype Text class

from nltk import FreqDist
from nltk.corpus import PlaintextCorpusReader

class Text(PlaintextCorpusReader, FreqDist):
    
    def __init__(self, *args, **kwargs):
        # (a) should use higher-level corpus reader if given corpus
        #     has more annotations, e.g. parsed_sents()
        # (b) support initialization from words, sents, strings
        PlaintextCorpusReader.__init__(self, *args, **kwargs)
        FreqDist.__init__(self, self.words())
    
    def __getitem__(self, index):
        if isinstance(index, (int, slice)):
            return FreqDist.__getitem__(self, index)
        else:
            return PlaintextCorpusReader.__getitem__(self, index)

    def concordance(self, pattern):
        # code from nltk.draw.concordance
        raise NotImplementedError
    
    def readability(self, method):
        # code from nltk_contrib.readability
        raise NotImplementedError
    
    def generate(self, length):
        # build and cache a language model using nltk.model
        # generate random text of specified length
        raise NotImplementedError
    
    def dispersion_plot(self, words):
        # produce a dispersion plot using nltk.draw.dispersion
        raise NotImplementedError
    
    def sents(self):
        # use CorpusReader.sents() if it exists
        # else invoke a sentence segmenter (on the *list* of words?)
        raise NotImplementedError

    def tagged_words(self):
        # use CorpusReader.tagged_sents() if it exists
        # else invoke a tagger
        raise NotImplementedError

    def tagged_sents(self):
        # use CorpusReader.tagged_sents() if it exists
        # else invoke a tagger
        raise NotImplementedError

    def parsed_sents(self):
        # use CorpusReader.parsed_sents() if it exists
        # else invoke a parser
        raise NotImplementedError
    
    