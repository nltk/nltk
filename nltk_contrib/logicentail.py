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
        for word_text in textbow|hypbow:
            pos = None
            if word_text in wordnet.N:
                pos = wordnet.N
            elif word_text in wordnet.V:
                pos = wordnet.V
            elif word_text in wordnet.ADJ:
                pos = wordnet.ADJ
            elif word_text in wordnet.ADV:
                pos = wordnet.ADV
                
            synonyms = set([])
            hypernyms = set([])
                
            if pos:
                for synset in pos[word_text]:
                    for synonym_text in synset:
                        if synonym_text != word_text:
                            synonyms.add(synonym_text)
                    for hypernymset in synset[wordnet.HYPERNYM]:
                        for hypernym_text in hypernymset:
                            hypernyms.add(hypernym_text)
                            
                ######################################
                # synonym: all x.((word1 x) iff (word2 x))
                # hypernym: all x.((word1 x) implies (word2 x))
                # synset-sister: all x.((word1 x) and (not (word2 x)))
                ######################################            
                
                for synonym_text in synonyms:
                    bk.append(self._create_axiom(word_text, synset, synonym_text, pos, 'iff'))
        
                for hypernym_text in hypernyms - synonyms:
                    bk.append(self._create_axiom(word_text, synset, hypernym_text, pos, 'implies'))
        
        if verbose:
            for bk_pair in bk:
                print (str(bk_pair[0].infixify()), bk_pair[1])
            
        return bk
    
    def _create_axiom(self, word_text, word_synset, nym_text, pos, operator):
        nym_word = pos[nym_text]
        dist = min([word_synset.shortest_path_distance(nym_synset) for nym_synset in nym_word])

        word_text = word_text.replace('.', '')
        nym_text = nym_text.replace('.', '')
        
        exp_text = 'all x.((%s x) %s (%s x))' % (word_text, operator, nym_text)
        return (logic.LogicParser().parse(exp_text), dist)
    
    
def demo(verbose=False):
    from nltk_contrib.gluesemantics import drt_glue
    
    tagger = RTEInferenceTagger()
    
    text = 'John own a car'
    print 'Text: ', text
    hyp = 'John have an auto'
    print 'Hyp:  ', hyp

#    text_ex = logic.LogicParser().parse('some e.some x.some y.((david x) and ((own e) and ((subj e x) and ((obj e y) and (car y)))))))')
#    hyp_ex = logic.LogicParser().parse('some e.some x.some y.((david x) and ((have e) and ((subj e x) and ((obj e y) and (auto y)))))))')

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

    result = prover.prove(hyp_ex, [text_ex])
    print 'T -> H: %s' % result

    if not result:
        bk = tagger._generate_BK(text, hyp, verbose)
        bk_exs = [bk_pair[0] for bk_pair in bk]
        
        result = prover.prove(hyp_ex, [text_ex]+bk_exs)
        print '(T & BK) -> H: %s' % result

        # Check if the background knowledge axioms are inconsistant
#        if not result:
#            result = prover.prove([text_ex]+bk_exs)
#            print '~(BK & T): %s' % result
#    
#        if not result:
#            result = prover.prove(hyp_ex, [text_ex])
#            print '~(BK & T & H): %s' % result
    

if __name__ == '__main__':
    demo(False)
