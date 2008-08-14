# Natural Language Toolkit (NLTK) Coreference Chunkers
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

from nltk.utilities import LazyMap, LazyConcatenation, LazyZip
from nltk.evaluate import precision, recall, accuracy, f_measure

from nltk.chunk.util import conllstr2tree

from nltk.tag.hmm import HiddenMarkovModelTagger, \
     HiddenMarkovModelTaggerTransform

from nltk_contrib.coref import *
from nltk_contrib.coref.features import *

class HiddenMarkovModelChunkTaggerTransform(HiddenMarkovModelChunkTaggerTransformI):
    """
    An abstract subclass of C{HiddenMarkovModelChunkTaggerTransformI}.
    """
    def __init__(self):
        if self.__class__ == HiddenMarkovModelTaggerTransform:
            raise AssertionError, "Abstract classes can't be instantiated"
                    
    def __getstate__(self):
        state = self.__dict__
        state['_lambda_functions'] = {}
        state['_instance_methods'] = {}
        for name, attr in state.items():
            if isinstance(attr, LambdaType) and attr.__name__ == '<lambda>':
                state['_lambda_functions'][name] = dumps(attr.func_code)
                del state[name]
            elif isinstance(attr, MethodType):
                state['_instance_methods'][name] = \
                    (attr.im_self, attr.im_func.func_name)
                del state[name]
        return state
    
    def __setstate__(self, state):
        for name, mcode in state.get('_lambda_functions', {}).items():
            state[name] = function(loads(mcode), {})
        if '_lambda_functions' in state:
            del state['_lambda_functions']
        for name, (im_self, im_func_name) \
        in state.get('_instance_methods', {}).items():
            state[name] = getattr(im_self, im_func_name)
        if '_instance_methods' in state:
            del state['_instance_methods']
        self.__dict__ = state 
        

class ClosedCategoryChunkTransform(HiddenMarkovModelChunkTaggerTransformI):
    """
    Returns a list of symbols transformed for Treebank chunk parsing.
    Closed category tokens (CC, DT, MD, POS, PP$, RP, TO, WDT, WP$, EX, 
    IN, PDT, PRP, WP, WRB) are mapped to the tuple consisting of the word
    and POS tag.  Their respective BIO tags are mapped to the tuple 
    consisting of the word, POS tag, and BIO tag. Open category tokens are
    mapped to the POS tag.  Their respective BIO tags are mapped to the
    tuple consisting of the POS tag and BIO tag.  For example, in a case with
    Treebank tags,

        (in, IN, O)  --> ((in, IN), (in, IN, O))

        (car, NN, B) --> (NN, (NN, B))

    @return: a list of symbols transformed for chunk parsing, the list
        corresponds to a list of tuples representation of a sentence
    @rtype: list
    @param symbols: a list of POS tagged POS and BIO tagged symbols
        correpsonding to a list of tuples representation of a sentence
    @type symbols: list
    @kwparam closed_cats: lists of closed categories
    @type closed_cats: C{set}
    """    
    def __init__(self, closed_cats=None):
        self._closed_cats = closed_cats
        if not self._closed_cats:
            self._closed_cats = set()
    
    def is_closed_cat(self, symbol):
        (word, tag) = symbol[:2]
        return tag in self._closed_cats

    def path2tags(self, path):
        return [tag[-1] for tag in path]
                            
    def transform(self, labeled_symbols):       
        result = []
        for symbol in labeled_symbols:
            symbol_len = len(symbol or [])
            if symbol_len == 3:
                word, tag, iob_tag = symbol
                if self.is_closed_cat(symbol):
                    transformed_symbol = ((word, tag), symbol)
                else:
                    transformed_symbol = (tag, (tag, iob_tag))
            elif symbol_len == 2:
                word, tag = symbol
                if self.is_closed_cat(symbol):
                    transformed_symbol = (word, tag)
                else:
                    transformed_symbol = tag
            else:
                raise
            result.append(transformed_symbol)
        return result


class NamedEntityChunkTransform(ClosedCategoryChunkTransform):
    """
    """
    def is_closed_cat(self, symbol):
        word = symbol[0]
        return ClosedCategoryChunkTransform.is_closed_cat(self, symbol) or \
               self.word_type(word)
                
    def transform(self, labeled_symbols):
        typed_symbols = []
        for symbol in labeled_symbols:
            symbol_len = len(symbol or []) 
            if symbol_len == 3:
                word, tag, iob_tag = symbol
                typed_symbol = (self.word_type(word) or word, tag, iob_tag)
            elif symbol_len == 2:
                word, tag = symbol
                typed_symbol = (self.word_type(word) or word, tag)
            else:
                raise
            typed_symbols.append(typed_symbol)
        return ClosedCategoryChunkTransform.transform(self, typed_symbols)

    def word_type(self, word):        
        if contains_person_prefix(word) or contains_person_suffix(word):
            return 'PERSON'
        if contains_org_suffix(word):
            return 'ORG'
        if is_name(word):
            return 'NAME'
        if is_nationality(word):
            return 'NATIONALITY'
        if is_city(word) or is_country(word):
            return 'LOCATION'
        if is_roman_numeral(word):
            return 'ROMAN_NUMERAL'
        if is_tla(word):
            return 'TLA'
        if is_initial(word):
            return 'INITIAL'
        if contains_currency(word):
            return 'CURRENCY'
        if contains_percent(word):
            return 'PERCENT'
        if contains_numeric(word) or contains_number(word) or \
           contains_ordinal(word) or is_digit(word):
            return 'NUMBER'
        if contains_day(word) or contains_month(word) or \
           contains_date(word):
            return 'DATE'
        if is_suffix(word):
            return 'SUFFIX'
        if is_prefix(word):
            return 'PREFIX'
        if is_title_case(word):
            return 'TITLE_CASE'
        if is_punct(word):
            return 'PUNCT'
        return
                

class HiddenMarkovModelChunkTagger(HiddenMarkovModelTagger, TrainableI):
    """
    """
    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'
    
    def __init__(self, symbols, states, transitions, outputs, priors, **kwargs):
        transform = kwargs.get('transform')
        if not transform \
        or not isinstance(transform, HiddenMarkovModelChunkTaggerTransformI):
            raise AssertionError, 'Transform must be instance of ', \
                'HiddenMarkovModelChunkTaggerTransformI'
        HiddenMarkovModelTagger.__init__(self, symbols, states, transitions, 
                                               outputs, priors, **kwargs)
    
    @classmethod
    def train(cls, labeled_sequence, test_sequence=None,
    		       unlabeled_sequence=None, **kwargs):
        transform = kwargs.get('transform')
        if not transform \
        or not isinstance(transform, HiddenMarkovModelChunkTaggerTransformI):
            raise AssertionError, 'Transform must be instance of ', \
                'HiddenMarkovModelChunkTaggerTransformI'
        return cls._train(labeled_sequence, test_sequence,
    		              unlabeled_sequence, **kwargs)     
    		        
    def chunk(self, sent):
        chunks = []
        for node in self.parse(sent):
            if not isinstance(node, tuple):
                chunks.append(node.leaves())
            else:
                chunks.append(node)
        return chunks

    def parse(self, sent):
        conllstr = '\n'.join('%s %s %s' % (word, tag, iob_tag)
                             for ((word, tag), iob_tag) in self.tag(sent))
        return conllstr2tree(conllstr)
    
    def tag(self, unlabeled_sequence):
        tagged_sequence = self._tag(self._transform.transform(unlabeled_sequence))
        path = [tag for (word, tag) in tagged_sequence]
        tags = self._transform.path2tags(path)
        return zip(unlabeled_sequence, tags)
                
    def test(self, test_sequence, **kwargs):        
        # This is used more than once and tagging is likely to happen lazily
        # so it's really time-inefficient to determine the values lazily.
        test_sequence = list(test_sequence)
                        
        HiddenMarkovModelTagger.test(self, test_sequence, **kwargs)
        
        def words(sent):
            return [word for (word, tag) in sent]
        
        def tags(sent):
            return self._transform.path2tags([tag for (word, tag) in sent])
            
        def tag_set(tags):
            return set([(index, tag) for (index, tag) in enumerate(tags)
                        if tag != self.OUT])
        
        # Same goes here w.r.t. non-lazy map.        
        test_sequence = map(self._transform.transform, test_sequence)
        predicted_sequence = map(self._tag, LazyMap(words, test_sequence))
                  
        test_tags = LazyConcatenation(LazyMap(tags, test_sequence))
        predicted_tags = LazyConcatenation(LazyMap(tags, predicted_sequence))
        
        test_tag_set = tag_set(test_tags)
        predicted_tag_set = tag_set(predicted_tags)
        
        pre = precision(test_tag_set, predicted_tag_set)
        rec = recall(test_tag_set, predicted_tag_set)   
        f1 = f_measure(test_tag_set, predicted_tag_set)
        
        count = sum([len(sent) for sent in test_sequence])        
        
        print 'precision over %d tokens: %.2f' % (count, pre * 100)    
        print 'recall over %d tokens: %.2f' % (count, rec * 100)                    
        print 'F1 over %d tokens: %.2f' % (count, f1 * 100)


def demo():
    from nltk_contrib.coref.util import treebank_chunk_tagger_demo
    treebank_chunk_tagger_demo()
    
if __name__ == '__main__':
    demo()
