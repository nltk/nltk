from nltk.probability import *
from nltk.tokenizer import *
from string import lower

#An abstract class representing a feature
#Contains public methods for evaluating a summary and a document; these use the private
#methods for evaluating a paragraph and a sentence.
class FeatureI:
    def __init__(self, features=[]):
        self.feature_list = [None] + features

    #evaluate a sentence (return an element of self.feature_list)
    def _evaluate_sentence(self, document, paragraph, s):
        raise AssertionError, 'FeatureI is an abstract interface'
    
    #evaluate a paragraph (return a FreqDist over self.feature_list)
    def _evaluate_paragraph(self, document, paragraph):
        counts = FreqDist()
        #evaluate each sentence in the paragraph
        for s in range(0, len(paragraph.type())):
            counts.inc(self._evaluate_sentence(document, paragraph, s))
        return counts

    #evaluate a document (return a FreqDist)
    def evaluate_document(self, document):
        counts = FreqDist()
        #evaluate each paragraph in the document
        for paragraph in document:
            paragraph_counts = self._evaluate_paragraph(document, paragraph)
            #and add the counts to the total
            for feature in paragraph_counts.samples():
                counts.inc(feature, paragraph_counts.count(feature))
        return counts

    #evaluate a summary (a list of sentences, with indices to the corresponding sentences in the document)
    def evaluate_summary(self, summary, document):
        counts = FreqDist()
        for summary_sentence in summary:
            #find out where this sentence came from in the document
            p = summary_sentence.loc().source().start()
            s = summary_sentence.loc().start()
            #and evaluate that sentence
            counts.inc(self._evaluate_sentence(document, document[p], s))
        return counts

#A class representing the sentence length feature
class SentenceLength(FeatureI):
    def __init__(self):
	FeatureI.__init__(self, ['long', 'short'])
        
    def _evaluate_sentence(self, document, paragraph, s):
        sentence = paragraph.type()[s]
        #if our sentence is longer than 5 words, it is considered to be long
        if sentence.type().count(' ')+1 > 5:
            return 'long'
        #otherwise it is short
        else:
            return 'short'

#A class representing the fixed-phrase feature. Note that we have only defined 3 phrases.
#However, it is trivially extensible.
class FixedPhrase(FeatureI):
    def __init__(self):
        self._key_phrases = ["this paper describes", "we present", "the performance of"]
        FeatureI.__init__(self, self._key_phrases)
        
    def _evaluate_sentence(self, document, paragraph, s):
        sentence = paragraph.type()[s]

        #if our sentence contains any of the phrases (ignoring case), return that one
        for phrase in self._key_phrases:
            if phrase in lower(sentence.type()):
                return phrase

        #if we haven't found anything, return None
        return None

#We only record paragraph data for the first 10 and last 5 paragraphs
MAX_STARTING_PARAGRAPHS = 10
MAX_ENDING_PARAGRAPHS = 5

#A class representing the sentence's position within its paragraph
class Paragraph(FeatureI):
    def __init__(self):
        FeatureI.__init__(self, ['initial', 'medial', 'final'])
        
    def _evaluate_sentence(self, document, paragraph, s):
        #if this paragraph is near the start or end of the document
        if paragraph.loc() < Location(MAX_STARTING_PARAGRAPHS) or paragraph.loc() >= Location(len(document) - MAX_ENDING_PARAGRAPHS):
            #decide if we are the first, last or middle sentence in the paragraph
            if s == 0:
                return 'initial'
            elif s == len(paragraph.type()):
                return 'final'
            else:
                return 'medial'
        #otherwise don't bother
        else:
            return None

#A class for the uppercase feature
class Uppercase(FeatureI):
    def __init__(self):
	FeatureI.__init__(self, ['yes', 'no'])
        
    def _evaluate_sentence(self, document, paragraph, s):
        sentence = paragraph.type()[s]

        #if our word is two or more uppercase letters, and nothing else, then we call it uppercase
        for word in WSTokenizer().tokenize(sentence.type()):
            if re.match(r'[A-Z][A-Z]+$', word.type()):
                return 'yes'        
        return 'no'
