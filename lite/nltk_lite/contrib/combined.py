import math
import os

# tagger importing
from nltk_lite import tag
from nltk_lite.tag import SequentialBackoff
# work-around while marshal is not moved into standard tree
from nltk_lite.contrib.marshal import MarshalDefault ; Default = MarshalDefault
from nltk_lite.contrib.marshal import MarshalUnigram ; Unigram = MarshalUnigram
from nltk_lite.contrib.marshal import MarshalAffix   ; Affix   = MarshalAffix
from nltk_lite.contrib.marshal import MarshalNgram   ; Ngram   = MarshalNgram
from nltk_lite.contrib.marshalbrill import *

class CombinedTagger (SequentialBackoff):
    def __init__ (self):
        self._tagger = []
        self._brill = None

    def _append_default (self, default_tag, verbose=False):
        self._tagger.append( Default(default_tag) )

    def _append_affix (self, a_len, w_len, train_sents, verbose=False):
        self._tagger.append( Affix(a_len, w_len, backoff=self._tagger[-1]) )
        self._tagger[-1].train([train_sents], verbose)

    def _append_unigram (self, train_sents, verbose=False):
        self._tagger.append( Unigram(backoff=self._tagger[-1]) )
        self._tagger[-1].train(train_sents, verbose)

    def _append_ngram (self, size, train_sents, verbose=False, cutoff_value=0.001):
        cutoff = math.floor(len(train_sents)*cutoff_value)
        self._tagger.append( Ngram(size, cutoff=cutoff, backoff=self._tagger[-1]) )
        self._tagger[-1].train([train_sents], verbose)
        
    def _append_brill (self, train_sents, max_rules, min_score=2, trace=0):
        templates = [
            SymmetricProximateTokensTemplate(ProximateTagsRule,  ( 1,  1)        ),
            SymmetricProximateTokensTemplate(ProximateTagsRule,  ( 2,  2)        ),
            SymmetricProximateTokensTemplate(ProximateTagsRule,  ( 1,  2)        ),
            SymmetricProximateTokensTemplate(ProximateTagsRule,  ( 1,  3)        ),
            SymmetricProximateTokensTemplate(ProximateWordsRule, ( 1,  1)        ),
            SymmetricProximateTokensTemplate(ProximateWordsRule, ( 2,  2)        ),
            SymmetricProximateTokensTemplate(ProximateWordsRule, ( 1,  2)        ),
            SymmetricProximateTokensTemplate(ProximateWordsRule, ( 1,  3)        ),
            ProximateTokensTemplate         (ProximateTagsRule,  (-1, -1), (1,1) ),
            ProximateTokensTemplate         (ProximateWordsRule, (-1, -1), (1,1) ),
            ]

        trainer = BrillTrainer(self._tagger[-1], templates, trace)
        self._brill = trainer.train(train_sents, max_rules, min_score)
        
    def marshal (self, basepath):
        # create the model files, one for each tagger (*.mod) plus a general one
        handler = file(os.path.join(basepath, "model.mrs"), "w")

        for index in range(len(self._tagger)):
            filename = os.path.join(basepath, "tagger%02d.mod" % index)
            handler.write("%s %s\n" % (self._tagger[index]._classname, filename) )
            self._tagger[index].marshal(filename)

        filename = os.path.join(basepath, "tagger%02d.mod" % (index+1))
        handler.write("%s %s\n" % (self._brill._classname, filename) )
        self._brill.marshal(filename)

        handler.close()

    def unmarshal (self, basepath):
        # clear taggers
        self._tagger = []
        self._brill = None

        # read model's configuration
        filename = os.path.join(basepath, "model.mrs")
        handler = file(filename, "r")
        model = handler.readlines()
        handler.close()
        model = [line[:-1] for line in model] # remove "\n"s
        model = [line for line in model if len(line) > 0] # remove empty lines

        # tagger by tagger
        for tagger in model:
            tagger_type, tagger_file = tagger.split(" ")
            if   tagger_type == "DefaultTagger":
                self._tagger.append( Default("") )
                self._tagger[-1].unmarshal(tagger_file)
            elif tagger_type == "AffixTagger":
                self._tagger.append( Affix(1, 2, backoff=self._tagger[-1]) )
                self._tagger[-1].unmarshal(tagger_file)
            elif tagger_type == "UnigramTagger":
                self._tagger.append( Unigram(backoff=self._tagger[-1]) )
                self._tagger[-1].unmarshal(tagger_file)
            elif tagger_type == "NgramTagger":
                self._tagger.append( Ngram(2, backoff=self._tagger[-1]) )
                self._tagger[-1].unmarshal(tagger_file)
            elif tagger_type == "BrillTagger":
                self._brill = Brill(self._tagger[-1], [])
                self._brill.unmarshal(tagger_file)
            else:
                 print "error, tagger type not recognized."

    def exemple_train (self, train_sents, verbose=False):
        self._append_default("N")

        self._append_affix(-2, 6, train_sents, verbose)
        self._append_affix(-3, 7, train_sents, verbose)
        self._append_affix(-4, 8, train_sents, verbose)
        self._append_affix(-5, 9, train_sents, verbose)

        self._append_unigram(train_sents, verbose)
        
        self._append_ngram(2, train_sents, verbose)
        
        self._append_brill(train_sents, 1, 2, trace=3)

    def tag_one (self, token):
        return self._tagger[-1].tag_one(token)

    def tag (self, tokens, verbose=False):
        return self._tagger[-1].tag(tokens, verbose)

def create_tagger (train_sents):
    ct = CombinedTagger()
#    ct.example_train(train_sents, True)
    ct.unmarshal("tresoldi")
    
    tokens = "Mauro viu o livro sobre a mesa".split()
    print list(ct.tag(tokens))

    # tests
    acc = tag.accuracy(ct, [train_sents])
    print 'Accuracy = %4.2f%%' % (100 * acc)
