import sys
import nltk
import nltk.corpus
import marshal

def score(l1, l2):
    correct = 0
    total = 0
    for i in range(len(l1)):
        if l1[i] == l2[i]:
            correct += 1
        total += 1
    print "total", total
    print "correct", correct
    print correct * 100.0 / total


class MyBrown:
    def __init__(self):
        self.brown = nltk.corpus.brown

    def items(self, grp=None):
        if grp:
            return self.brown.items(grp)
        else:
            return self.brown.items()

    def tokenize(self, item):
        token = self.brown.tokenize(item)
        for t in token['SUBTOKENS']:
            t['TEXT'] = t['TEXT'].lower()
        return token


class MyNthOrderTagger(nltk.tagger.NthOrderTagger):
    def __init__(self, n):
        nltk.tagger.NthOrderTagger.__init__(self, n)

    def train(self, trainer):
        if isinstance(trainer, nltk.token.Token):
            tagged_token = trainer
            SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
            TEXT = self._property_names.get('TEXT', 'TEXT')
            TAG = self._property_names.get('TAG', 'TAG')
            left, right = self._left, self._right

            # Extract the list of subtokens & list of tags.
            subtokens = tagged_token[SUBTOKENS]
            tags = tuple([t[TEXT] for t in subtokens])

            for i, subtok in enumerate(subtokens):
                if i+left<0: continue
                # Construct the context from the current subtoken's text
                # and the adjacent tokens' tags.
                context = (tags[i+left:i+right], subtok[TEXT])

                # Record the current token in the frequency distribution.
                tag = subtok[TAG]
                self._freqdist[context].inc(tag)
        elif isinstance(trainer, nltk.tagger.TaggerI):
            tagger = trainer
            if self == tagger or self._n != tagger._n:
                return
            print "training"
            for c, fd in tagger._freqdist._fdists.items():
                for k, v in fd._count.items():
                    self._freqdist[c].inc(k,v)

    def tag_subtoken(self, subtokens, i):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        TAG = self._property_names.get('TAG', 'TAG')
        left, right = self._left, self._right
        if i+left<0: return None

        # Construct the cotext from the current subtoken's text and
        # the adjacent tokens' tags.
        context_tags = [tok[TEXT] for tok in subtokens[i+left:i+right]]

        context = (tuple(context_tags), subtokens[i][TEXT])

        # Find the most likely tag for this subtoken, given the context.
        tag = self._freqdist[context].max()

        # If we're sufficiently confident in this tag, then return it.
        # Otherwise, return None.
        if self._freqdist[context].count(tag) >= self._cutoff:
            return tag
        else:
            return None


class MyTagger(nltk.tagger.BackoffTagger):
    def __init__(self, *orders):
        self._taggers = []
        self._taggerByOrder = {}
        h = {}
        for n in orders:
            if self._taggerByOrder.has_key(n):
                continue
            if n == -1:
                tagger = nltk.tagger.DefaultTagger('nn')
            else:
                tagger = MyNthOrderTagger(n)
            self._taggers.append(tagger)
            self._taggerByOrder[n] = tagger
            
        nltk.tagger.BackoffTagger.__init__(self, self._taggers)
        
    def train(self, trainer):
        if isinstance(trainer, nltk.token.Token):
            print "training with token"
            for n,tagger in self._taggerByOrder.items():
                if n == -1: continue
                tagger.train(trainer)
        elif isinstance(trainer, nltk.tagger.TaggerI):
            print "training with tagger"
            try:
                self._taggerByOrder[trainer._n].train(trainer)
            except KeyError:
                return
        elif type(trainer) == list or type(trainer) == tuple:
            print "training with list of trainer"
            for t in trainer:
                self.train(t)
        elif isinstance(trainer, MyTagger):
            print "training with MyTagger"
            for t in trainer.taggers():
                self.train(t)
                
    def taggers(self):
        return self._taggers

def test():

    tagger = MyTagger(2,1,0,-1)

    brown = MyBrown()

    tagger.train([brown.tokenize(item) for item in brown.items()[1:3]])

    test_result = brown.tokenize(brown.items()[0])
    
    test_token = test_result.freeze()
    
    tagger.tag(test_result)
    
    score(test_token['SUBTOKENS'], test_result['SUBTOKENS'])

    #f = open("tagger.sav", "wb")
    #marshal.dump(tagger, f)
    #f.close()
    

def test2():

    tagger = MyTagger(2,1,0,-1)
    f = open("tagger.sav","rb")
    trainer = marshal.load(f)
    f.close()
    tagger.trainer(trainer)

    brown = MyBrown()
    test_result = brown.tokenize(brown.items()[0])
    
    test_token = test_result.freeze()
    
    tagger.tag(test_result)
    
    score(test_token['SUBTOKENS'], test_result['SUBTOKENS'])
  
test()
#test2()
