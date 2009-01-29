# Natural Language Toolkit (NLTK) Coreference Named Entity Components
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.data import load
from nltk.util import LazyMap, LazyZip, LazyConcatenation, LazyEnumerate

from nltk.tag import TaggerI, ClassifierBasedTagger
from nltk.classify import MaxentClassifier, ClassifierI

from nltk_contrib.coref import *
from nltk_contrib.coref.features import *
from nltk_contrib.coref.chunk import ClosedCategoryChunkTransform

class Person(NamedEntityI):
    pass
    
    
class Organization(NamedEntityI):
    pass
    
    
class Location(NamedEntityI):
    pass
    
    
class Money(NamedEntityI):
    pass
    
    
class Percent(NamedEntityI):
    pass
    

class Out(NamedEntityI):
    def __init__(self, s):
        NamedEntityI.__init__(self, s, iob_tag=NamedEntityI.OUT)


class BaselineNamedEntityChunkTagger(ChunkTaggerI):
    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'
    
    def chunk(self, sent):
        chunked_sent = []
        chunk = []
        for (index, word) in LazyEnumerate(sent):
            if isinstance(word, tuple):
                word = word[0]
            elif not isinstance(word, str):
                raise
            word_type_ = word_type(word)
            if word_type_ and word_type_[0] != 'PUNCT' and \
            not (index == 0 and word_type_[0] == 'TITLE_CASE'):
                if not chunk:
                    chunk = []
                chunk.append(word)
            else:
                if chunk:
                    chunked_sent.append(chunk)
                    chunk = []
                chunked_sent.append(word)
        if chunk:
            chunked_sent.append(chunk)
        return chunked_sent

    def tag(self, sent):
        iob_sent = []        
        chunked_sent = self.chunk(sent)
        for elt in chunked_sent:
            if isinstance(elt, str) or isinstance(elt, tuple):
                iob_sent.append((elt, self.OUT))
            elif isinstance(elt, list):
                for (index, word) in LazyEnumerate(elt):
                    if index == 0:
                        iob_sent.append((word, self.BEGINS))
                    else:
                        iob_sent.append((word, self.IN))
        return iob_sent


class NamedEntityChunkTransform(ClosedCategoryChunkTransform):
    """
    """
    def is_closed_cat(self, symbol):
        word = symbol[0]
        if isinstance(word, tuple):
            return True
        elif isinstance(word, str):
            return word_type(word) or \
                   ClosedCategoryChunkTransform.is_closed_cat(self, symbol)
        else:
            raise
                
    def transform(self, labeled_symbols):
        typed_symbols = []
        for symbol in labeled_symbols:
            symbol_len = len(symbol or []) 
            if symbol_len == 3:
                word, tag, iob_tag = symbol
                typed_symbol = (word_type(word)[:2] or word, tag, iob_tag)
            elif symbol_len == 2:
                word, tag = symbol
                typed_symbol = (word_type(word)[:2] or word, tag)
            else:
                raise
            typed_symbols.append(typed_symbol)
        return ClosedCategoryChunkTransform.transform(self, typed_symbols)


class NamedEntityFeatureDetector(dict):
    def __init__(self, tokens, index=0, history=None):
        dict.__init__(self)
        
        chunk = tokens[index]
        
        self['word_type'] = word_type(chunk)[:2]

        features = ['contains_person_prefix', 'contains_person_suffix', 
            'contains_org_suffix', 'contains_period', 'contains_punct', 
            'contains_hyphen', 'contains_numeric', 'contains_currency', 
            'contains_number', 'contains_percent', 'contains_city', 
            'part_of_city', 'contains_country', 'contains_nationality',
            'contains_state', 'is_upper_case', 'is_lower_case', 
            'is_title_case', 'is_mixed_case', 'is_alpha_numeric', 
            'contains_month', 'contains_roman_numeral', 'contains_initial',
            'contains_tla', 'contains_day', 'contains_month', 'contains_date', 
            'contains_ordinal', 'len', 'log_length', 'contains_name',
            'startswith_person_prefix', 'endswith_person_suffix',
            'endswith_org_suffix', 'is_city', 'is_country', 'is_state',
            'contains_of_location', 'is_location', 'contains_location',
            'contains_name_sequence', 'contains_title_case_sequence',
            'is_year', 'contains_year', 'is_time', 'contains_time']

        for fname in features:
            self[fname] = eval(fname)(chunk)
        
        W = 1
        for i in range(index - W, index + W + 1):
            if i != index and i >= 0 and i < len(history or []):
                featureset, tag = history[i]
                if tag and i < 0:
                    self[('tag', i)] = tag
                for key, val in featureset.items():
                    if not isinstance(key, tuple):
                        self[(key, i - index)] = val


class NamedEntityFeatureDetector2(dict):
    def __init__(self, tokens, index=0, history=None):
        dict.__init__(self)
        
        word = tokens[index]
        
        self['word'] = word
        self['word_type'] = word_type(word)[:1]
        self['start_of_sent'] = index == 0
        self['end_of_sent'] = index == len(tokens) - 1
        self['is_bridge_word'] = word.lower() in ['of', 'and', '&']
        
        for i in range(2, 4):
            self['prefix_%d' % i] = word[:i]
            self['suffix_%d' % i] = word[-i:]

        features = ['is_person_prefix', 'is_person_suffix', 
            'is_org_suffix', 'contains_period', 'contains_punct', 
            'contains_hyphen', 'is_numeric', 'is_currency', 
            'is_number', 'is_percent', 'is_city', 
            'part_of_city', 'is_country', 'is_nationality',
            'is_state', 'is_upper_case', 'is_lower_case', 
            'is_title_case', 'is_mixed_case', 'is_alpha_numeric', 
            'is_month', 'is_roman_numeral', 'is_initial',
            'is_tla', 'is_day', 'is_month', 'is_date', 
            'is_ordinal', 'len', 'log_length', 'is_name',
            'startswith_person_prefix', 'endswith_person_suffix',
            'endswith_org_suffix', 'is_location', 'is_year', 'is_time']

        for fname in features:
            self[fname] = eval(fname)(word)
        
        W = 1
        for i in range(index - W, index + W + 1):
            if i != index and i >= 0 and i < len(history or []):
                featureset, tag = history[i]
                if tag and i < index:
                    self[('tag', i - index)] = tag
                for key, val in featureset.items():
                    if not isinstance(key, tuple):
                        self[(key, i - index)] = val

        prev_word = self.get(('word', -1), '')
        next_word = self.get(('word', 1), '')
        word_sequence = '%s %s %s' % (prev_word, word, next_word)
        self['in_name_sequence'] = contains_name_sequence(word_sequence)
        self['in_title_case_sequence'] = \
            contains_title_case_sequence(word_sequence)
        self['in_country_sequence'] = contains_country(word_sequence)
        self['in_of_location'] = contains_of_location(word_sequence)
        self['in_bridge_sequence'] = \
            self.get(('is_title_case', -1)) and \
            self.get('is_bridge_word') and \
            self.get(('is_title_case', 1))
        #self['prev_word_in_chunk'] = self.get(('tag', -1)) != 'O'
        

class NamedEntityClassifier(ClassifierBasedTagger, 
                            ClassifierI, TrainableI):    
    def __getattr__(self, name):
        if name != '_classifier':
            return getattr(self._classifier, name)
    
    def labels(self):
        return self._classifier.labels()
    
    def batch_classify(self, featuresets):
        return self._classifier.batch_classify(featuresets)
    
    def batch_prob_classify(self, featuresets):
        return self._classifier.batch_prob_classify(featuresets)
    
    @classmethod
    def train(cls, labeled_sequence, test_sequence=None,
                   unlabeled_sequence=None, **kwargs):
        algorithm = kwargs.get('algorithm', 'tadm')
        encoding = kwargs.get('encoding', None)
        gaussian_prior_sigma = kwargs.get('gaussian_prior_sigma', 1000)
        count_cutoff = kwargs.get('count_cutoff', 5)
        min_lldelta = kwargs.get('min_lldelta', 1e-5)
        feature_detector = kwargs.get('feature_detector')        
        out_tag = kwargs.get('out_tag')
        
        def maxent_classifier_builder(labeled_featuresets):
            return MaxentClassifier.train(
                labeled_featuresets,
                algorithm=algorithm,
                encoding=encoding,
                gaussian_prior_sigma=gaussian_prior_sigma,
                count_cutoff=count_cutoff,
                min_lldelta=min_lldelta)

        classifier_builder = \
            kwargs.get('classifier_builder', maxent_classifier_builder)
            
        classifier = \
            cls(feature_detector, labeled_sequence, classifier_builder)
        
        if test_sequence:
            classifier.test(test_sequence, out_tag=out_tag)
        
        return classifier
    
    
class NamedEntityRecognizer(TaggerI):
    def __init__(self, tagger, chunker, classifier):
        self._tagger = tagger
        self._chunker = chunker
        self._classifier = classifier
    
    def tag(self, tokens):
        tagged_tokens = self._tagger.tag(tokens)
        chunked_tokens = self._chunker.chunk(tagged_tokens)


def demo():
    from nltk_contrib.coref.util import baseline_chunk_tagger_demo
    baseline_chunk_tagger_demo()
    
if __name__ == '__main__':
    try:
        import psyco
        psyco.full(memory=100)
    except:
        pass
    demo()
