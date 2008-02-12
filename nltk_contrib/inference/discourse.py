# Natural Language Toolkit: Discourse Processing
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.sem import root_semrep
from nltk import parse
from nltk_contrib.inference import Mace, spacer, get_prover
from nltk.data import show_cfg
import os

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
            
    def expand_threads(self, tid, threads=None):
        """
        Given a thread ID, find the list of L{logic.Expression}s corresponding to the reading IDs in that thread.
        
        @parameter tid: Thread ID
        @type tid: C{str}
        """
        if threads is None:
            threads = self._threads
        return [(rid, self._readings[sid][rid]) for rid in threads[tid] for sid in rid.split('-')[:1]]

            
    def add_sentence(self, sentence, informchk=False, consistchk=False,):
        """
        Add a sentence to the discourse.
        
        @parameter sentence: An input sentence
        @type sentence: C{str}
        @parameter informchk: if C{True}, check that the result of adding the sentence is thread-informative
        @parameter consistchk: if C{True}, check that the result of adding the sentence is thread-consistent
        """
                
        if informchk:
            self.readings(quiet=True)
            for tid in sorted(self._threads.keys()):
                assumptions = [reading for (rid, reading) in self.expand_threads(tid)]
                for sent_reading in self._get_readings(sentence):
                    tp = get_prover(goal=sent_reading, assumptions=assumptions)
                    if tp.prove():
                        print "Sentence '%s' under reading '%s' is not informative relative to thread '%s'" % (sentence, str(sent_reading.infixify()), tid)
           
        self._input.append(sentence)
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        if consistchk:
            self.readings(quiet=True)
            self.models(show=False)
       
            
    def grammar(self):
        show_cfg(self._gramfile)
    
    def models(self, thread_id=None, show=True):
        if thread_id is None:
            threads = self._threads
        else:
            threads = {thread_id: self._threads[thread_id]}
        
        for tid in sorted(threads.keys()):
            assumptions = [reading for (rid, reading) in self.expand_threads(tid, threads=threads)]
            mb = Mace('', assumptions, timeout=2)
            idlist = [rid for rid in threads[tid]]
            if not mb.model_found():
                print "Inconsistent discourse: %s" % idlist
                for  rid, reading in [(rid, str(reading.infixify()))  for (rid, reading) in self.expand_threads(tid)]:
                    print "    %s: %s" % (rid, reading)
            elif show:
                m = mb.build_model()
                spacer(80)
                print "Discourse Thread %s" % tid
                spacer(80)
                for a in assumptions:
                    print a.infixify()
                spacer(80)
                mb.show_output(format='cooked')
            else:
                print "Consistent discourse: %s" % idlist
        

    def _get_readings(self, sentence):
        tokens = sentence.split()
        trees = self._parser.nbest_parse(tokens)
        return [root_semrep(tree) for tree in trees]


    
    def readings(self, sentence=None, threaded=False,quiet=False):
        
        if sentence is not None:
            print "The sentence '%s' has these readings:" % sentence
            for r in [str(reading.infixify()) for reading in (self._get_readings(sentence))]:
                print "    %s" % r
                return None
        else:
            for sid in self._sentences:
                readings = self._get_readings(self._sentences[sid])
                self._readings[sid] = dict([("%s-r%s" % (sid, rid), reading)
                                                            for rid, reading in enumerate(readings)])
  
        discourse = [[]]
        for sid in sorted(self._readings.keys()):
            discourse = self.multiply(discourse, sorted(self._readings[sid].keys()))
            if not threaded and not quiet:
                print
                print '%s readings:' % sid
                print '-' * 30
                for rid in self._readings[sid]:
                    lf = str(self._readings[sid][rid].infixify())
                    print "%s: %s" % (rid, lf)
        self._threads = dict([("d%s" % tid, thread) for tid, thread in enumerate(discourse)])
        if threaded and not quiet:
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
 
def demo():   
    dt = DiscourseTester(['a boxer walks', 'every boxer chases a girl'])
    print
    #dt.grammar()
    print 
    dt.sentences()
    print 
    dt.readings()
    print
    dt.readings(threaded=True)
    print
    dt.models('d1')
    dt.add_sentence('John is a boxer')
    print 
    dt.sentences()
    print
    dt.readings(threaded=True)
    dt = DiscourseTester(['A student dances', 'Every student is a person'])
    
    print
    dt.readings()
    print 
    dt.models()
    print
    dt.readings('A person dances')
    print
    dt.add_sentence('A person dances', consistchk=True, informchk=True)
    

if __name__ == '__main__':
    demo()
