#! /usr/bin/env python

import sys
import nltk
import nltk.corpus
import marshal
import gzip
import os.path

def score(l1, l2):
    correct = 0
    total = 0
    for i in range(len(l1)):
        if l1[i] == l2[i]:
            correct += 1
        total += 1
    #print total, correct, correct * 100.0 / total
    sys.stderr.write(correct * 100.0 / total)


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
        self._symfreq = nltk.probability.ConditionalFreqDist()

    def train(self, trainer):
        if isinstance(trainer, nltk.token.Token):
            tagged_token = trainer
            SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
            TEXT = self._property_names.get('TEXT', 'TEXT')
            TAG = self._property_names.get('TAG', 'TAG')
            left, right = self._left, self._right

            # Extract the list of subtokens & list of tags.
            subtokens = tagged_token[SUBTOKENS]
            #tags = tuple([t[TAG] for t in subtokens])
            texts = tuple([t[TEXT] for t in subtokens])

            for i, subtok in enumerate(subtokens):
                if i+left<0: continue
                # Construct the context from the current subtoken's text
                # and the adjacent tokens' tags.
                #context = (tags[i+left:i+right], subtok[TEXT])
                context = (texts[i+left:i+right], subtok[TEXT])

                # Record the current token in the frequency distribution.
                tag = subtok[TAG]
                word = subtok[TEXT]
                self._freqdist[context].inc(tag)
                self._symfreq[tag].inc(word)

        elif isinstance(trainer, nltk.tagger.TaggerI):
            tagger = trainer
            if self == tagger or self._n != tagger._n:
                return
            sys.stderr.write("training")
            for c, fd in tagger._freqdist._fdists.items():
                for k, v in fd._count.items():
                    self._freqdist[c].inc(k,v)

        elif isinstance(trainer, TaggerGut):
            if self._n != trainer.order():
                return
            for c, fd in trainer.items():
                for k, v in fd.items():
                    self._freqdist[c].inc(k,v)

                    
    def tag_subtoken(self, subtokens, i):
        TEXT = self._property_names.get('TEXT', 'TEXT')
        TAG = self._property_names.get('TAG', 'TAG')
        left, right = self._left, self._right
        if i+left<0: return None

        # Construct the cotext from the current subtoken's text and
        # the adjacent tokens' tags.
        #context_tags = [tok[TAG] for tok in subtokens[i+left:i+right]]
        context_texts = [tok[TEXT] for tok in subtokens[i+left:i+right]]

        #context = (tuple(context_tags), subtokens[i][TEXT])
        context = (tuple(context_texts), subtokens[i][TEXT])

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
        nltk.tagger.BackoffTagger.__init__(self, [])
        self._taggerByOrder = {}
        self._build(orders)


    def _build(self, orders):
        h = {}
        self._subtaggers = []
        for n in orders:
            if self._taggerByOrder.has_key(n):
                continue
            if n == -1:
                tagger = nltk.tagger.DefaultTagger('nn')
                tagger._n = -1
            else:
                tagger = MyNthOrderTagger(n)
            self._subtaggers.append(tagger)
            self._taggerByOrder[n] = tagger
        nltk.tagger.BackoffTagger.__init__(self, self._subtaggers)


    def taggers(self):
        return self._subtaggers

    
    def train(self, trainer):
        if isinstance(trainer, nltk.token.Token):
            sys.stderr.write("training with token")
            for n,tagger in self._taggerByOrder.items():
                if n == -1: continue
                tagger.train(trainer)
        elif isinstance(trainer, nltk.tagger.TaggerI):
            sys.stderr.write("training with tagger")
            try:
                self._taggerByOrder[trainer._n].train(trainer)
            except KeyError:
                return
        elif type(trainer) == list or type(trainer) == tuple:
            sys.stderr.write("training with list of trainer")
            for t in trainer:
                self.train(t)
        elif isinstance(trainer, MyTagger):
            sys.stderr.write("training with MyTagger")
            for t in trainer.taggers():
                self.train(t)
        elif isinstance(trainer, TaggerGut):
            sys.stderr.write("training with TaggerGut")
            n = trainer.order()
            if n == -1: return
            try:
                self._taggerByOrder[n].train(trainer)
            except KeyError:
                sys.stderr.write("WARNING: i don't have %d-th order tagger")
                sys.stderr.write("WARNING:   skipping training")
                return
        elif isinstance(trainer, ComplexTaggerGut):
            sys.stderr.write("training with ComplexTaggerGut")
            for t in trainer:
                self.train(t)
        else:
            sys.stderr.write("WARINIG: unsupported trainer type %s" % str(type(trainer)))
            sys.stderr.write("WARINIG:     training aborted")


    def loadGut(self, gut):
        sys.stderr.write("building tagger from ComplexTaggerGut")
        self._build([t.order() for t in gut])
        for t in gut:
            self.train(t)


    def test(self, items):
        correct = 0
        total = 0
        for item in items:
            test_result = nltk.corpus.brown.tokenize(item)
            test_token = test_result.freeze()
            tagger.tag(test_result)
            test_toks = test_result['SUBTOKENS']
            for i,tok in enumerate(test_token['SUBTOKENS']):
                if tok == test_toks[i]:
                    correct += 1
                total += 1
        print correct * 100.0 / total
                               

class TaggerGut(dict):
    
    def __init__(self, trainer):
        dict.__init__(self)
        self["__order__n__"] = {-999:0}

        if isinstance(trainer, nltk.tagger.TaggerI):
            if isinstance(trainer, nltk.tagger.BackoffTagger):
                raise ValueError("BackoffTagger is not supported")
            self._trainFromTagger(trainer)
        elif isinstance(trainer, TaggerGut):
            self._trainFromTrainer(trainer)
        elif isinstance(trainer, dict):
            self._trainFromDict(trainer)
        else:
            raise ValueError("unsupported trainer type %s" % str(type(trainer)))

    def setOrder(self, n):
        self["__order__n__"] = {n:0}

        
    def order(self):
        return self["__order__n__"].keys()[0]


    def _trainFromTagger(self, tagger):
        if tagger._n >= 0:
            for c, fd in tagger._freqdist._fdists.items():
                for k, v in fd._count.items():
                    try:
                        self[c][k] += v
                    except KeyError:
                        try:
                            self[c][k] = v
                        except KeyError:
                            self[c] = {k:v}
        self.setOrder(tagger._n)


    def _trainFromTrainer(self, trainer):
        for c, fd in trainer.items():
            for k, v in fd.items():
                try:
                    self[c][k] += v
                except KeyError:
                    try:
                        self[c][k] = v
                    except KeyError:
                        self[c] = {k:v}
        self.setOrder(trainer.order())

    def _trainFromDict(self, trainer):
        for c, fd in trainer.items():
            for k, v in fd.items():
                try:
                    self[c][k] += v
                except KeyError:
                    try:
                        self[c][k] = v
                    except KeyError:
                        self[c] = {k:v}
        self.setOrder(trainer["__order__n__"].keys()[0])



class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

        
class ComplexTaggerGut(list):
    
    def __init__(self, tagger):
        list.__init__(self)
        if isinstance(tagger, MyTagger): 
            for t in tagger.taggers():
                self.append(TaggerGut(t))
        elif isinstance(tagger, list):
            for t in tagger:
                self.append(TaggerGut(t))
        else:
            raise ValueError("1st arg of ComplesTaggerGut.__init__: "
                             "unsupported data type %s" % \
                             str(type(tagger)))


    def save(filename, tagger):
        f = gzip.open(filename, "wb")
        f.write(marshal.dumps(ComplexTaggerGut(tagger)))
        f.close()

    def load(filename):
        f = gzip.open(filename,"rb")
        gut = ComplexTaggerGut(marshal.loads(f.read(f)))
        f.close()
        return gut

    save = Callable(save)
    load = Callable(load)


    
def test():

    tagger = MyTagger(2, 1, 0,-1)

    brown = MyBrown()

    for item in brown.items()[1:50]:
        tagger.train(brown.tokenize(item))

    test_result = brown.tokenize(brown.items()[0])
    
    test_token = test_result.freeze()
    
    tagger.tag(test_result)
    
    score(test_token['SUBTOKENS'], test_result['SUBTOKENS'])

    ComplexTaggerGut.save("tagger.sav", tagger)

    

def test2():

    tagger = MyTagger()
    gut = ComplexTaggerGut.load("tagger.sav")
    tagger.loadGut(gut)

    brown = MyBrown()
    test_result = brown.tokenize(brown.items()[0])
    
    test_token = test_result.freeze()
    
    tagger.tag(test_result)
    
    score(test_token['SUBTOKENS'], test_result['SUBTOKENS'])


def test3():
    gut = ComplexTaggerGut.load("tagger.sav")
    print gut


if __name__ == "__main__":
    
    def usage():
        print "usage: %s <n,> [-res <f>] [-items <i,>] [-gut <g,>] [-test <i,>]" % os.path.basename(sys.argv[0])
        print
        print "  -res    save trained tagger core result as a file"
        print "  -items  specifies training items (nltk brown corpus items)"
        print "  -gut    specifies saved  'gut', core of a trained tagger"
        print "  -test   specifies test items"
        print
        print "       n  n-gram size (>= -1). if (-1)-th order tagger assigns"
        print "          'nn' to every word"
        print
        print "       i  an item in the nltk.corpus.brown"
        print
        print "       g  the core of a trained tagger"
        print
        print "    ex) %s 2 1 0 -res new.gut -items ca01 ca02 -guts ./t1.gut ./t2.gut \\\n" \
              "                                                 -test ca03" % \
              os.path.basename(sys.argv[0])
        print
        print "        This trains a tagger with items 'ca02' and 'ca03', and saved \n" \
              "        tagger core './t1.gut' and './t2.gut', then test the tagger \n" \
              "        with item 'ca03'.  The test result is printed out on STDOUT.\n" \
              "        Finally, it saves the trained tagger core as a file new.gut."
        print
        sys.exit(1)

    if len(sys.argv) < 4:
        usage()

    try:
        r = sys.argv.index('-res')
    except ValueError:
        r = None
    try:
        i = sys.argv.index('-items')
    except ValueError:
        i = None
    try:
        j = sys.argv.index('-gut')
    except ValueError:
        j = None
    try:
        k = sys.argv.index('-test')
    except ValueError:
        k = None

    if i == 1 or j == 1 or (i is None and j is None):
        usage()

    try:
        minVal = min(filter(lambda x:x is not None, (r,i,j,k)))
        orders = [int(n) for n in sys.argv[1:minVal]]
    except ValueError:
        usage()

    if r:
        try:
            resfile = sys.argv[r+1]
        except IndexError:
            resfile = None
    else:
        resfile = None
            
    items = []
    if i is not None:
        if j is not None:
            can = sys.argv[i+1:j]
        elif k is not None:
            can = sys.argv[i+1:k]
        else:
            can = sys.argv[i+1:]
        bitems = nltk.corpus.brown.items()
        for item in can:
            try:
                bitems.index(item)
            except ValueError:
                sys.stderr.write("WARNING: training item %s doesn't exist. skipping" % item)
            items.append(item)

    guts = []
    if j is not None:
        if k is not None:
            can = sys.argv[j+1:k]
        else:
            can = sys.argv[j+1:]
        for item in can:
            if os.path.exists(item):
                guts.append(item)
            else:
                sys.stderr.write("WARNING: saved training file %s doesn't exist. skipping" % item)


    tests = []
    if k is not None:
        can = sys.argv[k+1:]
        bitems = nltk.corpus.brown.items()
        for item in can:
            try:
                bitems.index(item)
            except IndexError:
                sys.stderr.write("WARNING: test item %s doesn't exist. skipping" % item)
            tests.append(item)

    tagger = apply(MyTagger, orders)

    for item in items:
        tagger.train(nltk.corpus.brown.tokenize(item))

    for gut in guts:
        tagger.train(ComplexTaggerGut.load(gut))

    if tests:
        tagger.test(tests)

    if resfile:
        ComplexTaggerGut.save(resfile, tagger)
