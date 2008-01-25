from nltk.corpus import rte
from nltk import evaluate
from nltk import wordnet
from nltk.sem import logic
from nltk_contrib.theorem_prover import prover


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
        return _tag(rtepair.text, rtepair.hyp, verbose)
        
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
                
        if verbose:
            for bk_pair in bk:
                print (str(bk_pair[0].infixify()), bk_pair[1])
            
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
    
    
def demo(verbose=False):
    from nltk_contrib.gluesemantics import drt_glue
    
    tagger = RTEInferenceTagger()
    
    text = 'John own a car'
    print 'Text: ', text
    hyp = 'John have an auto'
    print 'Hyp:  ', hyp

#    text_ex = logic.LogicParser().parse('some e x y.((david x) and ((own e) and ((subj e x) and ((obj e y) and (car y)))))))')
#    hyp_ex = logic.LogicParser().parse('some e x y.((david x) and ((have e) and ((subj e x) and ((obj e y) and (auto y)))))))')

    text_drs_list = drt_glue.parse_to_meaning(text, dependency=True, verbose=verbose)
    if(text_drs_list):
        text_ex = text_drs_list[0].simplify().toFol()
    else:
        print 'ERROR: No readings were be generated for the Text'
    
    hyp_drs_list  = drt_glue.parse_to_meaning(hyp, dependency=True, verbose=verbose)
    if(hyp_drs_list):
        hyp_ex = hyp_drs_list[0].simplify().toFol()
    else:
        print 'ERROR: No readings were be generated for the Hypothesis'

    if verbose:
        print 'Text: ', text_ex
        print 'Hyp:  ', hyp_ex

    result = prover.get_prover(hyp_ex, [text_ex]).prove()
    print 'T -> H: %s\n' % result

    if not result:
        bk = tagger._generate_BK(text, hyp, verbose)
        bk_exs = [bk_pair[0] for bk_pair in bk]
        
        print 'Generated Background Knowledge:'
        for bk_ex in bk_exs:
            print bk_ex.infixify()
            
        result = prover.get_prover(hyp_ex, [text_ex]+bk_exs).prove()
        print '(T & BK) -> H: %s' % result

        # Check if the background knowledge axioms are inconsistant
        if not result:
            result = prover.prove([text_ex]+bk_exs)
            print '~(BK & T): %s' % result
    
        if not result:
            result = prover.prove(hyp_ex, [text_ex])
            print '~(BK & T & H): %s' % result
    
    
if __name__ == '__main__':
    demo(False)
