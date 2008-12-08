# Natural Language Toolkit: RTE Classifier
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Simple classifier for RTE corpus.

It calculates the overlap in words and named entities between text and
hypothesis, and also whether there are words / named entities in the
hypothesis which fail to occur in the text, since this is an indicator that
the hypothesis is more informative than (i.e not entailed by) the text.

TO DO: better Named Entity classification
TO DO: add lemmatization
"""

from nltk.corpus import rte
from util import accuracy

def ne(token):
    """
    This just assumes that words in all caps or titles are 
    named entities.
    
    @param
    """
    if token.istitle() or \
       token.isupper():
        return True
    return False

class RTEFeatureExtractor(object):
    """
    This builds a bag of words for both the text and the hypothesis after
    throwing away some stopwords, then calculates overlap and difference.
    """
    def __init__(self, rtepair, stop=True):
        """
        @param rtepair: a L{RTEPair} from which features should be extracted
        @param stop: if C{True}, stopwords are thrown away.
        @type stop: C{bool}
        """
        self.stop = stop
        self.stopwords = set(['a', 'the', 'it', 'they', 'of', 'in', 'to',
                              'have', 'is', 'are', 'were', 'and', 'very', '.',','])
        
        # Try to tokenize so that abbreviations like U.S.and monetary amounts
        # like "$23.00" are kept as tokens.
        from nltk.tokenize import RegexpTokenizer
        tokenizer = RegexpTokenizer('([A-Z]\.)+|\w+|\$[\d\.]+|\S+')
        
        self.textbow = set(tokenizer.tokenize(rtepair.text))
        self.hypbow = set(tokenizer.tokenize(rtepair.hyp))
        
        if self.stop:
            self.textbow = self.textbow - self.stopwords
            self.hypbow = self.hypbow - self.stopwords
            
        self._overlap = self.hypbow & self.textbow
        self._extra = self.hypbow - self.textbow
            
    
    def overlap(self, toktype, debug=False):
        """
        Compute the overlap between text and hypothesis.
        
        @param toktype: distinguish Named Entities from ordinary words
        @type toktype: 'ne' or 'word'
        """
        ne_overlap = set([token for token in self._overlap if ne(token)])
        if toktype == 'ne':
            if debug: print "ne overlap", ne_overlap
            return ne_overlap
        elif toktype == 'word':
            if debug: print "word overlap", self._overlap - ne_overlap
            return self._overlap - ne_overlap
        else:
            raise ValueError("Type not recognized:'%s'" % toktype)
    
    def extra(self, toktype, debug=True):
        """
        Compute the extraneous material in the hypothesis.
        
        @param toktype: distinguish Named Entities from ordinary words
        @type toktype: 'ne' or 'word'
        """
        ne_extra = set([token for token in self._extra if ne(token)])
        if toktype == 'ne':
            return ne_extra
        elif toktype == 'word':
            return self._extra - ne_extra
        else:
            raise ValueError("Type not recognized: '%s'" % toktype)
           
def rte_features(rtepair):
    extractor = RTEFeatureExtractor(rtepair)
    features = {}
    features['alwayson'] = True
    features['word_overlap'] = len(extractor.overlap('word'))
    features['word_extra'] = len(extractor.extra('word'))
    features['ne_overlap'] = len(extractor.overlap('ne'))
    features['ne_extra'] = len(extractor.extra('ne'))
    return features            
           
    
def rte_classifier(trainer, features=rte_features):
    """
    Classify RTEPairs
    """
    train = [(pair, pair.value) for pair in rte.pairs(['rte1_dev.xml', 'rte2_dev.xml', 'rte3_dev.xml'])]
    test = [(pair, pair.value) for pair in rte.pairs(['rte1_test.xml', 'rte2_test.xml', 'rte3_test.xml'])]

    # Train up a classifier.
    print 'Training classifier...'
    classifier = trainer( [(features(pair), label) for (pair,label) in train] )

    # Run the classifier on the test data.
    print 'Testing classifier...'
    acc = accuracy(classifier, [(features(pair), label) for (pair,label) in test])
    print 'Accuracy: %6.4f' % acc

    # Return the classifier
    return classifier


#def view():
    #pairs = rte.pairs(['rte1_dev.xml'])[:6]
    #for pair in pairs:
        #print rte_features(pair)
        
if __name__ == '__main__':
    import nltk
    try:
        nltk.config_megam('/usr/local/bin/megam')
        trainer = lambda x: nltk.MaxentClassifier.train(x, 'megam')
    except ValueError:
        try:
            trainer = lambda x: nltk.MaxentClassifier.train(x, 'BFGS')
        except ValueError:
            trainer = nltk.MaxentClassifier.train
    rte_classifier(trainer)
