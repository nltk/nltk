# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem import root_semrep
from nltk import parse
from nltk_contrib.inference import Mace, spacer
from nltk.data import show_cfg


class DiscourseTester(object):
    """
    Check the consistency of an ongoing discourse.
    """
    def __init__(self, input, gramfile=None):
        self._input = input
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(input)])
        self._models = None
        self._readings = {}
        if gramfile is None:
            self._gramfile = 'file:sem4.fcfg'
        else:
            self._gramfile = gramfile
        self._threads = {} 
        self._parser = parse.load_earley(self._gramfile)
    
    def sentences(self):
        for id in sorted(self._sentences.keys()):
            print "%s: %s" % (id, self._sentences[id])            
            
    def add_sentence(self, sentence):
        self._input.append(sentence)
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        
    def grammar(self):
        show_cfg(self._gramfile)
    
    def models(self, thread_id=None):
        if thread_id is None:
            threads = self._threads
        else:
            threads = {thread_id: self._threads[thread_id]}
        
        for tid in sorted(threads.keys()):
            assumptions = [self._readings[sid][rid] for rid in threads[tid] for sid in rid.split('-')[:1]]
            mb = Mace('', assumptions, timeout=2)
            m = mb.build_model()
            spacer(80)
            print "Discourse Thread %s" % tid
            spacer(80)
            for a in assumptions:
                print a.infixify()
            spacer(80)
            mb.show_output(format='cooked')
        
    
    def readings(self, sentence=None, summarize=False):
        #if sentence is None:
        for sid in self._sentences:
            tokens = self._sentences[sid].split()
            trees = self._parser.nbest_parse(tokens)
            readings = [root_semrep(tree) for tree in trees]
            self._readings[sid] = \
                dict([("%s-r%s" % (sid, rid), reading)
                      for rid, reading in enumerate(readings)])
                
 
        discourse = [[]]
        for sid in sorted(self._readings.keys()):
            discourse = self.multiply(discourse, sorted(self._readings[sid].keys()))
            if not summarize:
                print
                print '%s readings:' % sid
                print '-' * 30
                for rid in self._readings[sid]:
                    lf = str(self._readings[sid][rid].infixify())
                    print "%s: %s" % (rid, lf)
        self._threads = dict([("d%s" % tid, thread) for tid, thread in enumerate(discourse)])
        if summarize:
            for tid in sorted(self._threads.keys()):
                print "%s:" % tid, self._threads[tid]
       
    @staticmethod
    def multiply(list1, list2):
        result = []
        for sublist in list1:
            for item in list2:
                new = []
                new += sublist
                new.append(item)
                result.append(new)
        return result
 
    
dt = DiscourseTester(['a boxer walks', 'every boxer chases a girl'])
print
dt.grammar()
print 
dt.sentences()
print 
dt.readings()
print
dt.readings(summarize=True)
print
dt.models('d1')
dt.add_sentence('John is a boxer')
print 
dt.sentences()
print
dt.readings(summarize=True)
dt = DiscourseTester(['John is in the garden'])
print
dt.readings()

