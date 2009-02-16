# Natural Language Toolkit: Recognizing Textual Entailment (RTE)
#                           using deep semantic entailment 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus import rte
from nltk import wordnet
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from nltk.sem.logic import LogicParser 
from nltk.sem.glue import DrtGlue
from nltk import inference

class RTEInferenceTagger(object):
    """
    Predict whether a hypothesis can be inferred from a text, 
    based on the degree of word overlap.
    """
    def __init__(self, threshold=33, stop=True):
        self.threshold = threshold
        self.stop = stop
        self.stopwords = set(['a', 'the', 'it', 'they', 'of', 'in', 'is', 'are', 'were', 'and'])
        self.stemmer = WordNetLemmatizer()
    
    def tag(self, rtepair, verbose=False):
        """
        Tag a RTEPair as to whether the hypothesis can be inferred from the text.
        """
        return self.tag_sentences(rtepair.text, rtepair.hyp )

    def tag_sentences(self, text, hyp, verbose=False):
        """
        Tag a RTEPair as to whether the hypothesis can be inferred from the text.
        """
        glueclass = DrtGlue()
        text_drs_list = glueclass.parse_to_meaning(text)
        if text_drs_list:
            text_ex = text_drs_list[0].simplify().toFol()
        else:
            if verbose: print 'ERROR: No readings were generated for the Text'
        
        hyp_drs_list = glueclass.parse_to_meaning(hyp)
        if hyp_drs_list:
            hyp_ex = hyp_drs_list[0].simplify().toFol()
        else:
            if verbose: print 'ERROR: No readings were generated for the Hypothesis'

        #1. proof T -> H
        #2. proof (BK & T) -> H
        #3. proof :(BK & T)
        #4. proof :(BK & T & H)
        #5. satisfy BK & T
        #6. satisfy BK & T & H
            
        result = inference.Prover9().prove(hyp_ex, [text_ex])
        if verbose: print 'prove: T -> H: %s' % result
        
        if not result:
            bk = self._generate_BK(text, hyp, verbose)
            bk_exs = [bk_pair[0] for bk_pair in bk]
            
            if verbose: 
                print 'Generated Background Knowledge:'
                for bk_ex in bk_exs:
                    print bk_ex
                
            result = inference.Prover9().prove(hyp_ex, [text_ex]+bk_exs)
            if verbose: print 'prove: (T & BK) -> H: %s' % result
            
            if not result:
                consistent = self.check_consistency(bk_exs+[text_ex])                
                if verbose: print 'consistency check: (BK & T): %s' % consistent

                if consistent:
                    consistent = self.check_consistency(bk_exs+[text_ex, hyp_ex])                
                    if verbose: print 'consistency check: (BK & T & H): %s' % consistent
                    
        return result
    
    def check_consistency(self, assumptions, verbose=False):
        return inference.ParallelProverBuilderCommand(assumptions=assumptions).build_model()
        
    def _tag(self, text, hyp, verbose=False):
        self._generate_BK(text, hyp, verbose)
    
    def _generate_BK(self, text, hyp, verbose=False):
        text = word_tokenize(text)
        hyp = word_tokenize(hyp)
        
        if self.stemmer:
            textbow = set(self._stem(word) for word in text)
            hypbow = set(self._stem(word) for word in hyp)
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
        synonyms = set()
        hypernyms = set()
                
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
        # synonym: all x.((synonym x) -> (word x))
        # hypernym: all x.((word x) -> (hypernym x))
        # synset-sister: all x.((word x) -> (not (sister x)))
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
        return [LogicParser().parse('all x y z.((in(x,y) & in(y,z)) -> in(x,z))'),
                LogicParser().parse('all e x y.((event(e) & subj(e,x) & in(e,y)) -> in(x,y))'),
                LogicParser().parse('all e x y.((event(e) & obj(e,x) & in(e,y)) -> in(x,y))'),
                LogicParser().parse('all e x y.((event(e) & theme(e,x) & in(e,y)) -> in(x,y))'),
                LogicParser().parse('all x y.(in(x,y) -> some e.(locate(e) & obj(e,x) & in(e,y)))'),
                LogicParser().parse('all x y.(of(x,y) -> some e.(have(e) & subj(e,y) & obj(e,x)))'),
                LogicParser().parse('all e y.((event(e) & subj(e,x)) -> by(e,x))')]
    
    def _create_axiom(self, word_text, word_synset, nym_text, pos, operator):
        nym_text = nym_text.split('(')[0];
        
        nym_word = pos[nym_text]
        dist = 1#min([word_synset.shortest_path_distance(nym_synset) for nym_synset in nym_word])

        word_text = word_text.replace('.', '')
        nym_text = nym_text.replace('.', '')

        exp_text = 'all x.(%s(x) %s %s(x))' % (word_text, operator, nym_text)
        return (LogicParser().parse(exp_text), dist)

    def _create_axiom_reverse(self, word_text, word_synset, nym_text, pos, operator):
        nym_text = nym_text.split('(')[0];

        nym_word = pos[nym_text]
        dist = 1#min([word_synset.shortest_path_distance(nym_synset) for nym_synset in nym_word])

        word_text = word_text.replace('.', '')
        nym_text = nym_text.replace('.', '')

        exp_text = 'all x.(%s(x) %s %s(x))' % (nym_text, operator, word_text)
        return (LogicParser().parse(exp_text), dist)

    def _create_axiom_synset_sisters(self, text1, word1_synset, text2, word2_synset, pos):
        """
        Return an expression of the form 'all x.(word(x) -> (not sister(x)))'.
        The reverse is not needed because it is equal to 'all x.((not word(x)) or (not sister(x)))'
        """
        
        text2 = text2.split('(')[0];

        dist = 1#word1_synset.shortest_path_distance(word2_synset)

        text1 = text1.replace('.', '')
        text2 = text2.replace('.', '')

        exp_text = 'all x.(%s(x) -> (not %s(x)))' % (text1, text2)
        return (LogicParser().parse(exp_text), dist)
    
    def _stem(self, word):
        stem = self.stemmer.stem(word)
        if stem:
            return stem
        else:
            return word
    

def demo_inference_tagger(verbose=False):
    tagger = RTEInferenceTagger()
    
    text = 'John see a car'
    print 'Text: ', text
    hyp = 'John watch an auto'
    print 'Hyp:  ', hyp

#    text_ex = LogicParser().parse('exists e x y.(david(x) & own(e)  & subj(e,x) & obj(e,y) & car(y))')
#    hyp_ex  = LogicParser().parse('exists e x y.(david(x) & have(e) & subj(e,x) & obj(e,y) & auto(y))')

    glueclass = DrtGlue(verbose=verbose)
    text_drs_list = glueclass.parse_to_meaning(text)
    if text_drs_list:
        text_ex = text_drs_list[0].simplify().toFol()
    else:
        print 'ERROR: No readings were be generated for the Text'
    
    hyp_drs_list = glueclass.parse_to_meaning(hyp)
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
        
    result = inference.Prover9().prove(hyp_ex, [text_ex])
    print 'prove: T -> H: %s' % result
    if result:
        print 'Logical entailment\n'
    else:
        print 'No logical entailment\n'

    bk = tagger._generate_BK(text, hyp, verbose)
    bk_exs = [bk_pair[0] for bk_pair in bk]
    
    print 'Generated Background Knowledge:'
    for bk_ex in bk_exs:
        print bk_ex
    print ''
        
    result = inference.Prover9().prove(hyp_ex, [text_ex]+bk_exs)
    print 'prove: (T & BK) -> H: %s' % result
    if result:
        print 'Logical entailment\n'
    else:
        print 'No logical entailment\n'

    # Check if the background knowledge axioms are inconsistent
    result = inference.Prover9().prove(assumptions=bk_exs+[text_ex]).prove()
    print 'prove: (BK & T): %s' % result
    if result:
        print 'Inconsistency -> Entailment unknown\n'
    else:
        print 'No inconsistency\n'

    result = inference.Prover9().prove(assumptions=bk_exs+[text_ex, hyp_ex])
    print 'prove: (BK & T & H): %s' % result
    if result:
        print 'Inconsistency -> Entailment unknown\n'
    else:
        print 'No inconsistency\n'

    result = inference.Mace().build_model(assumptions=bk_exs+[text_ex])
    print 'satisfy: (BK & T): %s' % result
    if result:
        print 'No inconsistency\n'
    else:
        print 'Inconsistency -> Entailment unknown\n'

    result = inference.Mace().build_model(assumptions=bk_exs+[text_ex, hyp_ex]).build_model()
    print 'satisfy: (BK & T & H): %s' % result
    if result:
        print 'No inconsistency\n'
    else:
        print 'Inconsistency -> Entailment unknown\n'
    
def test_check_consistency():
    a = LogicParser().parse('man(j)')
    b = LogicParser().parse('-man(j)')
    print '%s, %s: %s' % (a, b, RTEInferenceTagger().check_consistency([a,b], True))
    print '%s, %s: %s' % (a, a, RTEInferenceTagger().check_consistency([a,a], True))

def tag(text, hyp):
    print 'Text: ', text
    print 'Hyp:  ', hyp
    print 'Entailment =', RTEInferenceTagger().tag_sentences(text, hyp, True)
    print ''

if __name__ == '__main__':
#    test_check_consistency()
#    print '\n'
    
    demo_inference_tagger(False)
    
    tag('John sees a car', 'John watches an auto')
    tag('John sees a car', 'John watches an airplane')
