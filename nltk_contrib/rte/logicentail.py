# Natural Language Toolkit: Recognizing Textual Entailment (RTE)
#                           using deep semantic entailment 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.corpus import rte
from nltk import evaluate
from nltk import wordnet
from nltk.sem import logic
from nltk_contrib.gluesemantics import drt_glue
from nltk_contrib.inference import inference
import ctypes
import threading
import bow

class RTEInferenceTagger(object):
    """
    Predict whether a hypothesis can be inferred from a text, 
    based on the degree of word overlap.
    """
    def __init__(self, threshold=33, stop=True, stemming=False):
        self.threshold = threshold
        self.stemming = stemming
        self.stop = stop
        self.stopwords = set(['a', 'the', 'it', 'they', 'of', 'in', 'is', 'are', 'were', 'and'])
    
    def tag(self, rtepair, verbose=False):
        """
        Tag a RTEPair as to whether the hypothesis can be inferred from the text.
        """
        return self.tag_sentences(rtepair.text, rtepair.hyp )

    def tag_sentences(self, text, hyp, verbose=False):
        """
        Tag a RTEPair as to whether the hypothesis can be inferred from the text.
        """
        
        text_drs_list = drt_glue.parse_to_meaning(text, dependency=True)
        if text_drs_list:
            text_ex = text_drs_list[0].simplify().toFol()
        else:
            if verbose: print 'ERROR: No readings were be generated for the Text'
        
        hyp_drs_list  = drt_glue.parse_to_meaning(hyp, dependency=True)
        if hyp_drs_list:
            hyp_ex = hyp_drs_list[0].simplify().toFol()
        else:
            if verbose: print 'ERROR: No readings were be generated for the Hypothesis'

        #1. proof T -> H
        #2. proof (BK & T) -> H
        #3. proof :(BK & T)
        #4. proof :(BK & T & H)
        #5. satisfy BK & T
        #6. satisfy BK & T & H
            
        result = inference.get_prover(hyp_ex, [text_ex]).prove()
        if verbose: print 'prove: T -> H: %s' % result
        
        if not result:
            bk = tagger._generate_BK(text, hyp, verbose)
            bk_exs = [bk_pair[0] for bk_pair in bk]
            
            if verbose: 
                print 'Generated Background Knowledge:'
                for bk_ex in bk_exs:
                    print bk_ex.infixify()
                
            result = inference.get_prover(hyp_ex, [text_ex]+bk_exs).prove()
            if verbose: print 'prove: (T & BK) -> H: %s' % result
            
            if not result:
                consistent = self.check_consistency(bk_exs+[text_ex])                
                if verbose: print 'consistency check: (BK & T): %s' % consistent

                if consistent:
                    consistent = self.check_consistency(bk_exs+[text_ex, hyp_ex])                
                    if verbose: print 'consistency check: (BK & T & H): %s' % consistent
                    
        return result
    
    def check_consistency(self, assumptions, verbose=False):
        # Set up two thread, Prover and ModelBuilder to run in parallel
        prover = inference.get_prover(assumptions=assumptions)
        model_builder = inference.get_model_builder(assumptions=assumptions)
        
        prover_result = [None]
        prover_thread = ProverThread(prover, prover_result, verbose)
        model_builder_result = [None]
        model_builder_thread = ModelBuilderThread(model_builder, model_builder_result, verbose)
        
        prover_thread.start()
        model_builder_thread.start()
        
        while not prover_result[0] and not model_builder_result[0]:
            # wait until either the prover or the model builder is done
            pass
    
        if prover_result[0]:
            consistency = prover_result[0]
        else:
            consistency = model_builder_result[0]

        return (consistency == 'consistent')
        
    def _tag(self, text, hyp, verbose=False):
        self._generate_BK(text, hyp, verbose)
    
    def _generate_BK(self, text, hyp, verbose=False):
        from nltk.tokenize import WordTokenizer
        from nltk.stem.porter import PorterStemmer
        tokenizer = WordTokenizer()
        stemmer = PorterStemmer()
        
        text = tokenizer.tokenize(text)
        hyp = tokenizer.tokenize(hyp)
        
        if self.stemming:
            textbow = set(stemmer.stem(word) for word in text)
            hypbow = set(stemmer.stem(word) for word in hyp)
        else:
            textbow = set(word.lower() for word in text)
            hypbow = set(word.lower() for word in hyp)
        
        if verbose:
            print 'textbow: %s' % textbow
            print 'hypbow: %s' % hypbow
        
        if self.stop:
            textbow = textbow - self.stopwords
            hypbow = hypbow - self.stopwords

        bk = []
        fullbow = textbow|hypbow
        for word_text in fullbow:
            pos = None
            if word_text in wordnet.N:
                bk.extend(self._generate_BK_word(word_text, wordnet.N, fullbow))
            if word_text in wordnet.V:
                bk.extend(self._generate_BK_word(word_text, wordnet.V, fullbow))
            if word_text in wordnet.ADJ:
                bk.extend(self._generate_BK_word(word_text, wordnet.ADJ, fullbow))
            if word_text in wordnet.ADV:
                bk.extend(self._generate_BK_word(word_text, wordnet.ADV, fullbow))
                
        return bk
        
    def _generate_BK_word(self, word_text, pos, fullbow):
        bk = []
        synonyms = set([])
        hypernyms = set([])
                
        for synset in pos[word_text]:
            for synonym_text in synset:
                if synonym_text != word_text and synonym_text.lower() in fullbow \
                                             and word_text.lower() in fullbow:
                    synonyms.add(synonym_text)
            for hypernymset in synset[wordnet.HYPERNYM]:
                for hypernym_text in hypernymset:
                    if hypernym_text != word_text and hypernym_text.lower() in fullbow \
                                                  and word_text.lower() in fullbow:
                        hypernyms.add(hypernym_text)
                    
        ######################################
        # synonym: all x.((synonym x) implies (word x))
        # hypernym: all x.((word x) implies (hypernym x))
        # synset-sister: all x.((word x) implies (not (sister x)))
        ######################################            
        
        for synonym_text in synonyms:
            bk.append(self._create_axiom_reverse(word_text, synset, synonym_text, pos, 'implies'))

        for hypernym_text in hypernyms - synonyms:
            bk.append(self._create_axiom(word_text, synset, hypernym_text, pos, 'implies'))

        # Create synset-sisters
        for i in range(len(pos[word_text])):
            synset1 = pos[word_text][i]
            j = i+1
            while j < len(pos[word_text]):
                synset2 = pos[word_text][j]
                for word1 in synset1:
                    if word1 != word_text and word1.lower() in fullbow:
                        for word2 in synset2:
                            if word2 != word_text and word2 != word1 and word2.lower() in fullbow:
                                bk.append(self._create_axiom_synset_sisters(word1, synset1, word2, synset2, pos))
                j = j+1
        
        return bk
        
    def _common_BK():
        # From Recognising Textual Entailment by Bos&Markert
        return [LogicParser().parse('all x y z.(((in x y) and (in y z)) implies (in x z))'),
                LogicParser().parse('all e x y.(((event e) and (subj e x) and (in e y)) implies (in x y))'),
                LogicParser().parse('all e x y.(((event e) and (obj e x) and (in e y)) implies (in x y))'),
                LogicParser().parse('all e x y.(((event e) and (theme e x) and (in e y)) implies (in x y))'),
                LogicParser().parse('all x y.((in x y) implies some e.((locate e) and (obj e x) and (in e y)))'),
                LogicParser().parse('all x y.((of x y) implies some e.((have e) and (subj e y) and (obj e x)))'),
                LogicParser().parse('all e y.(((event e) and (subj e x)) implies (by e x))')]
    
    def _create_axiom(self, word_text, word_synset, nym_text, pos, operator):
        nym_text = nym_text.split('(')[0];
        
        nym_word = pos[nym_text]
        dist = 1#min([word_synset.shortest_path_distance(nym_synset) for nym_synset in nym_word])

        word_text = word_text.replace('.', '')
        nym_text = nym_text.replace('.', '')

        exp_text = 'all x.((%s x) %s (%s x))' % (word_text, operator, nym_text)
        return (logic.LogicParser().parse(exp_text), dist)

    def _create_axiom_reverse(self, word_text, word_synset, nym_text, pos, operator):
        nym_text = nym_text.split('(')[0];

        nym_word = pos[nym_text]
        dist = 1#min([word_synset.shortest_path_distance(nym_synset) for nym_synset in nym_word])

        word_text = word_text.replace('.', '')
        nym_text = nym_text.replace('.', '')

        exp_text = 'all x.((%s x) %s (%s x))' % (nym_text, operator, word_text)
        return (logic.LogicParser().parse(exp_text), dist)

    def _create_axiom_synset_sisters(self, text1, word1_synset, text2, word2_synset, pos):
        """
        Return an expression of the form 'all x.((word x) implies (not (sister x)))'.
        The reverse is not needed because it is equal to 'all x.((not (word x)) or (not (sister x)))'
        """
        
        text2 = text2.split('(')[0];

        dist = 1#word1_synset.shortest_path_distance(word2_synset)

        text1 = text1.replace('.', '')
        text2 = text2.replace('.', '')

        exp_text = 'all x.((%s x) implies (not (%s x)))' % (text1, text2)
        return (logic.LogicParser().parse(exp_text), dist)
    
    def _parallel_prove_satisfy(self, goal=None, assumptions=[]):
        prover = inference.get_prover(assumptions=bk_exs+[text_ex])
        model_builder = inference.get_model_builder(assumptions=bk_exs+[text_ex])
        
        inconsistent = ProverThread(prover).start()
        consistent = ModelBuilderThread(model_builder).start()
    
class ProverThread( threading.Thread ):
    def __init__(self, prover, result, verbose=False):
        self.prover = prover
        self.result = result
        self.verbose = verbose
        threading.Thread.__init__(self)
        
    def run( self ):
        tp_result = self.prover.prove()
        if tp_result:
            self.result[0] = 'inconsistent'
        else:
            self.result[0] = 'consistent'
        if self.verbose: print 'Prover finished with \'%s\'' % self.result[0]

class ModelBuilderThread( threading.Thread ):
    def __init__(self, model_builder, result, verbose=False):
        self.model_builder = model_builder
        self.result = result
        self.verbose = verbose
        threading.Thread.__init__(self)
        
    def run( self ):
        mb_result = self.model_builder.build_model()
        if mb_result:
            self.result[0] = 'consistent'
        else:
            self.result[0] = 'inconsistent'
        if self.verbose: print 'Model Builder finished with \'%s\'' % self.result[0]

def demo_inference_tagger(verbose=False):
    tagger = RTEInferenceTagger()
    
    text = 'John see a car'
    print 'Text: ', text
    hyp = 'John watch an auto'
    print 'Hyp:  ', hyp

#    text_ex = logic.LogicParser().parse('some e x y.((david x) and ((own e) and ((subj e x) and ((obj e y) and (car y)))))))')
#    hyp_ex = logic.LogicParser().parse('some e x y.((david x) and ((have e) and ((subj e x) and ((obj e y) and (auto y)))))))')

    text_drs_list = drt_glue.parse_to_meaning(text, dependency=True, verbose=verbose)
    if text_drs_list:
        text_ex = text_drs_list[0].simplify().toFol()
    else:
        print 'ERROR: No readings were be generated for the Text'
    
    hyp_drs_list  = drt_glue.parse_to_meaning(hyp, dependency=True, verbose=verbose)
    if hyp_drs_list:
        hyp_ex = hyp_drs_list[0].simplify().toFol()
    else:
        print 'ERROR: No readings were be generated for the Hypothesis'

    print 'Text: ', text_ex
    print 'Hyp:  ', hyp_ex
    print ''

    #1. proof T -> H
    #2. proof (BK & T) -> H
    #3. proof :(BK & T)
    #4. proof :(BK & T & H)
    #5. satisfy BK & T
    #6. satisfy BK & T & H
        
    result = inference.get_prover(hyp_ex, [text_ex]).prove()
    print 'prove: T -> H: %s' % result
    if result:
        print 'Logical entailment\n'
    else:
        print 'No logical entailment\n'

    bk = tagger._generate_BK(text, hyp, verbose)
    bk_exs = [bk_pair[0] for bk_pair in bk]
    
    print 'Generated Background Knowledge:'
    for bk_ex in bk_exs:
        print bk_ex.infixify()
    print ''
        
    result = inference.get_prover(hyp_ex, [text_ex]+bk_exs).prove()
    print 'prove: (T & BK) -> H: %s' % result
    if result:
        print 'Logical entailment\n'
    else:
        print 'No logical entailment\n'

    # Check if the background knowledge axioms are inconsistant
    result = inference.get_prover(assumptions=bk_exs+[text_ex]).prove()
    print 'prove: (BK & T): %s' % result
    if result:
        print 'Inconsistency -> Entailment unknown\n'
    else:
        print 'No inconsistency\n'

    result = inference.get_prover(assumptions=bk_exs+[text_ex, hyp_ex]).prove()
    print 'prove: (BK & T & H): %s' % result
    if result:
        print 'Inconsistency -> Entailment unknown\n'
    else:
        print 'No inconsistency\n'

    result = inference.get_model_builder(assumptions=bk_exs+[text_ex]).build_model()
    print 'satisfy: (BK & T): %s' % result
    if result:
        print 'No inconsistency\n'
    else:
        print 'Inconsistency -> Entailment unknown\n'

    result = inference.get_model_builder(assumptions=bk_exs+[text_ex, hyp_ex]).build_model()
    print 'satisfy: (BK & T & H): %s' % result
    if result:
        print 'No inconsistency\n'
    else:
        print 'Inconsistency -> Entailment unknown\n'
    
def test_check_consistency():
    a = logic.LogicParser().parse('(man j)')
    b = logic.LogicParser().parse('(not (man j))')
    print '%s, %s: %s' % (a.infixify(), b.infixify(), 
                          RTEInferenceTagger().check_consistency([a,b], True))
    print '%s, %s: %s' % (a.infixify(), a.infixify(), 
                          RTEInferenceTagger().check_consistency([a,a], True))

if __name__ == '__main__':
    demo_inference_tagger(False)
    
    text = 'John see a car'
    print 'Text: ', text
    hyp = 'John watch an auto'
    print 'Hyp:  ', hyp
    tagger = RTEInferenceTagger()
    print 'Entailment =', tagger.tag_sentences(text, hyp, True)
    print ''
    
    test_check_consistency()