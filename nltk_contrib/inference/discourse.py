# Natural Language Toolkit: Discourse Processing
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
"""
Module for incrementally developing simple discourses, and checking for semantic ambiguity, 
consistency and informativeness.

Many of the ideas are based on the CURT family of programs of Blackburn and Bos 
(see U{http://homepages.inf.ed.ac.uk/jbos/comsem/book1.html}).

Consistency checking is carried out with the use of Mace4 from L{mace}. 
Informativeness checking is carried out with a call to C{get_prover()} from
the L{inference}  module.

C{DiscourseTester} is a constructor for discourses. 
The basic data structure is a list of sentences, stored as C{self._sentences}. Each sentence in the list
is assigned a I{sentence ID} (C{sid}) of the form C{s}I{i}.

Each sentence can be ambiguous between a number of readings, each of which receives a 
I{reading ID} (C{rid}) of the form C{s}I{i} -C{r}I{j}. A I{thread} is a list of readings, represented
as a list of C{rid}s. Each thread receives a I{thread ID} (C{tid}) of the form C{d}I{i}. The set of
all threads for a discourse is the Cartesian product of all the readings of the sequences of sentences.
(This is not intended to scale beyond very short discourses!)
"""

from nltk.sem import root_semrep, Expression
from nltk import parse
from nltk_contrib.inference import Mace, spacer, get_prover
from nltk.data import show_cfg
import os

class DiscourseTester(object):
    """
    Check properties of an ongoing discourse.
    """
    def __init__(self, input, gramfile=None, background=None):       
        """
        Initialize a C{DiscourseTester}.
        
        @parameter input: the discourse sentences
        @type input: C{list} of C{str}
        @parameter gramfile: name of file where grammar can be loaded
        @type gramfile: C{str}
        @parameter background: Formulas which express background assumptions
        @type background: C{list} of L{logic.Expression}.
        """
        self._input = input
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(input)])
        self._models = None
        self._readings = {}
        if gramfile is None:
            self._gramfile = 'grammars/sem4.fcfg'
        else:
            self._gramfile = gramfile
        self._threads = {} 
        self._parser = parse.load_earley(self._gramfile) 
        if background is not None:
            for e in background:
                assert isinstance(e, Expression)
            self._background = background
        else:
            self._background = []
              
    def sentences(self):
        for id in sorted(self._sentences.keys()):
            print "%s: %s" % (id, self._sentences[id])            
            
    def expand_threads(self, thread_id, threads=None):
        """
        Given a thread ID, find the list of L{logic.Expression}s corresponding to the reading IDs in that thread.
        
        @parameter thread_id: thread ID
        @type thread_id: C{str}
        @parameter threads: a mapping from thread IDs to lists of reading IDs
        @type threads: C{dict}
        @return: A list of pairs (C{rid}, I{reading}) where I{reading} is the L{logic.Expression} associated with a reading ID 
        @rtype: C{list} of C{tuple}
        """
        if threads is None:
            threads = self._threads
        return [(rid, self._readings[sid][rid]) for rid in threads[thread_id] for sid in rid.split('-')[:1]]

            
    def add_sentence(self, sentence, informchk=False, consistchk=False,):
        """
        Add a sentence to the discourse.
        
        Updates C{self._input} and C{self._sentences}.
        @parameter sentence: An input sentence
        @type sentence: C{str}
        @parameter informchk: if C{True}, check that the result of adding the sentence is thread-informative. Updates C{self._readings}.
        @parameter consistchk: if C{True}, check that the result of adding the sentence is thread-consistent. Updates C{self._readings}.
        
        """
        # check whether the new sentence is informative (i.e. not entailed by the previous discourse)       
        if informchk:
            self.readings(quiet=True)
            for tid in sorted(self._threads.keys()):
                assumptions = [reading for (rid, reading) in self.expand_threads(tid)]
                assumptions += self._background
                for sent_reading in self._get_readings(sentence):
                    tp = get_prover(goal=sent_reading, assumptions=assumptions)
                    if tp.prove():
                        print "Sentence '%s' under reading '%s' is not informative relative to thread '%s'" % (sentence, str(sent_reading.infixify()), tid)
           
        self._input.append(sentence)
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        # check whether adding the new sentence to the discourse preserves consistency (i.e. a model can be found for the combined set of
        # of assumptions
        if consistchk:
            self.readings(quiet=True)
            self.models(show=False)
            
    def retract_sentence(self, sentence, quiet=False):
        """
        Remove a sentence from the input.
        
        Updates C{self._input}, C{self._sentences} and C{self._readings}.
        @parameter sentence: An input sentence
        @type sentence: C{str}
        @parameter quiet: If C{False},  report on the updated list of sentences.
        """
        self._input.remove(sentence)
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        self.readings(quiet=True)
        if not quiet:
            print "Current sentences are "
            for sent in self._sentences:
                print sent
                  
    def grammar(self):
        """
        Print out the grammar currently in use for parsing.
        """
        show_cfg(self._gramfile)
    
    def models(self, thread_id=None, show=True):
        """
        Call Mace4 to build a model for each current discourse thread.
        
        @parameter thread_id: thread ID
        @type thread_id: C{str}
        @parameter show: If C{True}, display the model that has been found.
        """
        if thread_id is None:
            threads = self._threads
        else:
            threads = {thread_id: self._threads[thread_id]}
        
        for tid in sorted(threads.keys()):
            assumptions = [reading for (rid, reading) in self.expand_threads(tid, threads=threads)]
            assumptions += self._background
            mb = Mace('', assumptions, timeout=2)
            idlist = [rid for rid in threads[tid]]
            if not mb.build_model():
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
                mb.show_model(format='cooked')
            else:
                print "Consistent discourse: %s" % idlist
        

    def _get_readings(self, sentence):
        """
        @rtype: C{list} of  L{logic.Expression}.
        """
        tokens = sentence.split()
        trees = self._parser.nbest_parse(tokens)
        return [root_semrep(tree) for tree in trees]

    def add_background(self, background):
        """
        Update C{self._background}
        
        @parameter background: Formulas which contain background information
        @type background: C{list} of L{logic.Expression}.
        """
        for e in background:
            assert isinstance(e, Expression)
        self._background += background
        
    
    def readings(self, sentence=None, threaded=False,quiet=False):
        """
        Update and show the readings of the discourse (or of a single sentence).
        
        @parameter sentence: test just this sentence
        @type sentence: C{str}
        @parameter threaded: if C{True}, print out each thread ID and the corresponding thread.
        """
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
    def multiply(discourse, readings):
        """
        Multiply every thread in C{discourse} by every reading in C{readings}.
        
        Given discourse = [['A'], ['B']], readings = ['a', 'b', 'c'] , returns        
        [['A', 'a'], ['A', 'b'], ['A', 'c'], ['B', 'a'], ['B', 'b'], ['B', 'c']]
        
        @parameter discourse: the current list of readings
        @type discourse: C{list} of C{list}s
        @parameter readings: an additional list of readings
        @type readings: C{list} of C{logic.Expression}s
        @rtype: A C{list} of C{list}s
        """
        result = []
        for sublist in discourse:
            for r in readings:
                new = []
                new += sublist
                new.append(r)
                result.append(new)
        return result

#multiply = DiscourseTester.multiply
#L1 = [['A'], ['B']]
#L2 = ['a', 'b', 'c'] 
#print multiply(L1,L2)

def discourse_demo():  
    """
    Illustrate the various methods of C{DiscourseTester}
    """
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
    print
    dt = DiscourseTester(['A student dances', 'Every student is a person'])
    print 
    dt.add_sentence('No person dances', consistchk=True)
    print
    dt.readings()
    print
    dt.retract_sentence('No person dances', quiet=False)
    print 
    dt.models()
    print
    dt.readings('A person dances')
    print
    dt.add_sentence('A person dances', informchk=True)
    

if __name__ == '__main__':
    discourse_demo()
