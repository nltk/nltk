# Natural Language Toolkit: Discourse Processing
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
# $Id$

import os

from nltk.sem import root_semrep, Expression
from nltk import parse
from nltk.data import show_cfg

from nltk.inference import MaceCommand, spacer, get_prover

"""
Module for incrementally developing simple discourses, and checking for semantic ambiguity, 
consistency and informativeness.

Many of the ideas are based on the CURT family of programs of Blackburn and Bos 
(see U{http://homepages.inf.ed.ac.uk/jbos/comsem/book1.html}).

Consistency checking is carried out  by using the L{mace} module to call the Mace4 model builder.
Informativeness checking is carried out with a call to C{get_prover()} from
the L{inference}  module.

C{DiscourseTester} is a constructor for discourses. 
The basic data structure is a list of sentences, stored as C{self._sentences}. Each sentence in the list
is assigned a I{sentence ID} (C{sid}) of the form C{s}I{i}. For example::

    s0: A boxer walks
    s1: Every boxer chases a girl

Each sentence can be ambiguous between a number of readings, each of which receives a 
I{reading ID} (C{rid}) of the form C{s}I{i} -C{r}I{j}. For example::

    s0 readings:
    ------------------------------
    s0-r1: some x.((boxer x) and (walk x))
    s0-r0: some x.((boxerdog x) and (walk x))

A I{thread} is a list of readings, represented
as a list of C{rid}s. Each thread receives a I{thread ID} (C{tid}) of the form C{d}I{i}. 
For example::

    d0: ['s0-r0', 's1-r0']

The set of all threads for a discourse is the Cartesian product of all the readings of the sequences of sentences.
(This is not intended to scale beyond very short discourses!) The method L{readings(filter=True)} will only show
those threads which are consistent (taking into account any background assumptions).
"""



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
        self._filtered_threads = {}
        self._parser = parse.load_earley(self._gramfile) 
        if background is not None:
            for e in background:
                assert isinstance(e, Expression)
            self._background = background
        else:
            self._background = []

    ###############################
    # Sentences
    ###############################
    
    def sentences(self):
        """
        Display the list of sentences in the current discourse.
        """
        for id in sorted(self._sentences.keys()):
            print "%s: %s" % (id, self._sentences[id]) 
              
    def add_sentence(self, sentence, informchk=False, consistchk=False,):
        """
        Add a sentence to the current discourse.
        
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
                    tp = get_prover(goal=sent_reading, assumptions=assumptions, prover_name='Prover9')
                    if tp.prove():
                        print "Sentence '%s' under reading '%s':" % (sentence, str(sent_reading))
                        print "Not informative relative to thread '%s'" % tid
           
        self._input.append(sentence)
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        # check whether adding the new sentence to the discourse preserves consistency (i.e. a model can be found for the combined set of
        # of assumptions
        if consistchk:
            self.readings(quiet=True)
            self.models(show=False) 
                       
    def retract_sentence(self, sentence, quiet=False):
        """
        Remove a sentence from the current discourse.
        
        Updates C{self._input}, C{self._sentences} and C{self._readings}.
        @parameter sentence: An input sentence
        @type sentence: C{str}
        @parameter quiet: If C{False},  report on the updated list of sentences.
        """
        try:
            self._input.remove(sentence)
        except ValueError:
            print "Retraction failed. The sentence '%s' is not part of the current discourse:" % sentence
            self.sentences()
            return None
        self._sentences = dict([('s%s' % i, sent) for i, sent in enumerate(self._input)])
        self.readings(quiet=True)
        if not quiet:
            print "Current sentences are "
            self.sentences()
            
    def grammar(self):
        """
        Print out the grammar in use for parsing input sentences
        """
        show_cfg(self._gramfile)
        
    ###############################
    # Readings and Threads
    ###############################        

    def _get_readings(self, sentence):
        """
        Build a list of semantic readings for a sentence.
        
        @rtype: C{list} of  L{logic.Expression}.
        """
        tokens = sentence.split()
        trees = self._parser.nbest_parse(tokens)
        return [root_semrep(tree) for tree in trees]    
                         
    def _construct_readings(self):
        """
        Use C{self._sentences} to construct a value for C{self._readings}.
        """
        # re-initialize self._readings in case we have retracted a sentence
        self._readings = {}
        for sid in self._sentences:
            readings = self._get_readings(self._sentences[sid])
            self._readings[sid] = dict([("%s-r%s" % (sid, rid), reading)
                                                        for rid, reading in enumerate(readings)])
                
    def _construct_threads(self):
        """
        Use C{self._readings} to construct a value for C{self._threads}
        and use the model builder to construct a value for C{self._filtered_threads}
        """
        thread_list = [[]]
        for sid in sorted(self._readings.keys()):
            thread_list = self.multiply(thread_list, sorted(self._readings[sid].keys()))      
        self._threads = dict([("d%s" % tid, thread) for tid, thread in enumerate(thread_list)])
        # re-initialize the filtered threads
        self._filtered_threads = {}
        # keep the same ids, but only include threads which get models
        for (tid, thread) in self._threads.items():
            if (tid, True) in self._check_consistency(self._threads):
                self._filtered_threads[tid] = thread
   
 
    def _show_readings(self, sentence=None):
        """
        Print out the readings for  the discourse (or a single sentence).
        """
        if sentence is not None:
            print "The sentence '%s' has these readings:" % sentence
            for r in [str(reading) for reading in (self._get_readings(sentence))]:
                print "    %s" % r
        else:
            for sid in sorted(self._readings.keys()):
                print
                print '%s readings:' % sid
                print '-' * 30
                for rid in sorted(self._readings[sid]):
                    lf = self._readings[sid][rid]
                    #TODO lf = lf.normalize('[xyz]\d*', 'z%d')
                    print "%s: %s" % (rid, lf)
    
    def _show_threads(self, filter=False):
        """
        Print out the value of C{self._threads} or C{self._filtered_hreads} 
        """
        if filter:
            threads = self._filtered_threads
        else:
            threads = self._threads
        for tid in sorted(threads.keys()):
            print "%s:" % tid, self._threads[tid] 
        
        
    def readings(self, sentence=None, threaded=False, quiet=False, filter=False):
        """
        Construct and show the readings of the discourse (or of a single sentence).
        
        @parameter sentence: test just this sentence
        @type sentence: C{str}
        @parameter threaded: if C{True}, print out each thread ID and the corresponding thread.
        @parameter filter: if C{True}, only print out consistent thread IDs and threads.
        """
        self._construct_readings()
        self._construct_threads()
        
        # if we are filtering, just show threads
        if filter: threaded=True
        if not quiet:
            if not threaded:
                self._show_readings(sentence=sentence)
            else:
                self._show_threads(filter=filter)                            
    
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
    
           
    ###############################
    # Models and Background
    ###############################       
     
    def _check_consistency(self, threads, show=False, quiet=True):
        results = []
        for tid in sorted(threads.keys()):
            assumptions = [reading for (rid, reading) in self.expand_threads(tid, threads=threads)]
            assumptions += self._background
            # if Mace4 finds a model, it always seems to find it quickly
            mb = MaceCommand(None, assumptions, timeout=2)
            modelfound = mb.build_model()
            results.append((tid, modelfound))
            if show:
                spacer(80)
                print "Model for Discourse Thread %s" % tid
                spacer(80)
                if not quiet:
                    for a in assumptions:
                        print a
                    spacer(80)
                if modelfound:
                    print mb.model(format='cooked')
                else:
                    print "No model found!\n"
        return results
    
    def models(self, thread_id=None, show=True, quiet=True):
        """
        Call Mace4 to build a model for each current discourse thread.
        
        @parameter thread_id: thread ID
        @type thread_id: C{str}
        @parameter show: If C{True}, display the model that has been found.
        """
        self._construct_readings()
        self._construct_threads()
        if thread_id is None:
            threads = self._threads
        else:
            threads = {thread_id: self._threads[thread_id]}
        
        for (tid, modelfound) in self._check_consistency(threads, show=show, quiet=quiet):            
            idlist = [rid for rid in threads[tid]]
            
            if not modelfound:
                print "Inconsistent discourse %s %s:" % (tid, idlist)
                for  rid, reading in [(rid, str(reading))  for (rid, reading) in self.expand_threads(tid)]:
                    print "    %s: %s" % (rid, reading)
                print 
            else:
                print "Consistent discourse: %s %s:" % (tid, idlist)
                for  rid, reading in [(rid, str(reading))  for (rid, reading) in self.expand_threads(tid)]:
                    print "    %s: %s" % (rid, reading)
                print 
        
    def add_background(self, background, quiet=True):
        """
        Add a list of background assumptions for reasoning about the discourse.
        
        When called,  this method also updates the discourse model's set of readings and threads.
        @parameter background: Formulas which contain background information
        @type background: C{list} of L{logic.Expression}.
        """
        for (count, e) in enumerate(background):
            assert isinstance(e, Expression)
            if not quiet:
                print "Adding assumption %s to background" % count
            self._background.append(e) 
            
        #update the state
        self._construct_readings()
        self._construct_threads()
        
    def background(self):
        """
        Show the current background assumptions.
        """
        for e in self._background:
            print str(e)
    
   ###############################
    # Misc
    ###############################                              
                
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

def parse_fol(s):
    """
    Temporarily duplicated from L{nltk.sem.util}.
    Convert a  file of First Order Formulas into a list of C{Expression}s.
    
    @parameter s: the contents of the file
    @type s: C{str}
    @return: a list of parsed formulas.
    @rtype: C{list} of L{Expression}
    """
    from nltk.sem import LogicParser
    statements = []
    lp = LogicParser()
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try:
            statements.append(lp.parse(line))
        except Error:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    return statements
            
###############################
# Demo
###############################    

def discourse_demo():  
    """
    Illustrate the various methods of C{DiscourseTester}
    """
    dt = DiscourseTester(['A boxer walks', 'Every boxer chases a girl'])
    dt.models()
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
    dt = DiscourseTester(['Vincent is a boxer', 'Fido is a boxer', 'Vincent is married', 'Fido barks'])
    dt.readings(filter=True)
    import nltk.data
    world = nltk.data.load('/grammars/world.fol')
    print
    dt.add_background(world, quiet=True)
    dt.background()
    print
    dt.readings(filter=True)
    print
    dt.models()
    
    

if __name__ == '__main__':
    discourse_demo()
