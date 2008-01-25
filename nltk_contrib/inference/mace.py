# Natural Language Toolkit: Interface to the Mace4 Model Builder 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
import tempfile
from string import join
from nltk.sem.logic import *
from api import ModelBuilderI
from nltk_contrib.inference import prover9
from nltk_contrib.inference.prover9 import Prover9Parent

class Mace(ModelBuilderI, Prover9Parent):
    def __init__(self, goal, assumptions=[], timeout=60):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in the proof
        @type assumptions: L{list} of logic.Expression objects
        @param timeout: number of seconds before timeout; set to 0 for no timeout.
        @type timeout: C{int}
        """
        self.config_prover9()
        self._goal = goal
        self._assumptions = assumptions
        self._p9_dir = ''
        self._infile = ''
        self._outfile = '' 
        self._p9_assumptions = []
        self._p9_goal = prover9.convert_to_prover9(self._goal)
        if self._assumptions:
            self._p9_assumptions = prover9.convert_to_prover9(self._assumptions)
        self._timeout = timeout
    
    def get_executable(self):
        return 'mace4'

    def build_model(self):
        """
        Use Mace4 to build a model
        @return: A model if one is generated; None otherwise.
        @rtype: C{nltk.sem.evaluate.Valuation} 
        """
        from nltk.sem import Valuation
        
        self.prover9_files('mace')
        exe = os.path.join(self._executable_path, self.get_executable())
        execute_string = '%s -c -f %s > %s 2>> %s' % \
            (exe, self._infile, self._outfile, self._outfile)
                
        valuation = None
                
        result = os.system(execute_string)
        if result == 0:
            self.transform_output('standard')
            
            d = {}
            for line in open(os.path.join(self._p9_dir, 'mace.standard.out')):
                l = line.strip()
                if l.startswith('interpretation'):
                    num_entities = int(l[l.index('(')+1:l.index(',')].strip())
                elif l.startswith('function') and l.find('_') == -1:
                    name = l[l.index('(')+1:l.index(',')].strip()
                    d[name] = Mace.make_model_var(int(l[l.index('[')+1:l.index(']')].strip()))
                elif l.startswith('relation'):
                    name = l[l.index('(')+1:l.index('(', l.index('(')+1)].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    d[name] = Mace.make_model_dict(num_entities, values)
                    
            valuation = Valuation(d)
                    
        return valuation
        
    def make_model_dict(num_entities, values):
        if len(values) == 1:
            return values[0] == 1
        else:
            d = {}
            for i in range(num_entities):
                size = len(values) / num_entities
                d[Mace.make_model_var(i)] = \
                    Mace.make_model_dict(num_entities, values[i*size:(i+1)*size])
            return d
        
    make_model_dict = staticmethod(make_model_dict)
                
    def make_model_var(value):
        return ['a','b','c','d','e','f','g','h','i','j','k','l','m','n',
                'o','p','q','r','s','t','u','v','w','x','y','z'][value]
        
    make_model_var = staticmethod(make_model_var)
                
    def model_found(self):
        """
        Use Mace4 to build a model
        @return: C{True} if the proof was successful 
        (i.e. returns value of 0), else C{False}        
        """
        self.prover9_files('mace')
        exe = os.path.join(self._executable_path, self.get_executable())
        execute_string = '%s -c -f %s > %s 2>> %s' % \
            (exe, self._infile, self._outfile, self._outfile)
        result = os.system(execute_string)
        return result == 0
    
    def show_output(self, format=None):
        """
        Print out a Prover9 proof.
        """
        if self._outfile:
            if not format:
                for l in open(self._outfile):
                    print l,
            else:
                for l in open(self.transform_output(format)):
                    print l,
            print ''
        else:
            print "You have to call build_model() first to get a model!"
        return None
    
    def transform_output(self, format):
        """
        Transform the output file into any interpformat format
        """
        output_file = None
        
        if self._outfile:
            if format in ['standard', 'standard2', 'portable', 'tabular', 
                          'raw', 'cooked', 'xml', 'tex']:
                output_file = os.path.join(self._p9_dir, 'mace.' + format + '.out')
                
                exe = os.path.join(self._executable_path, 'interpformat')
                execute_string = '%s %s -f %s > %s 2>> %s' % \
                    (exe, format, self._outfile, output_file, output_file)
                os.system(execute_string)
            else:
                print "The specified format does not exist"
        else:
            print "You have to call build_model() first to get a model!"
            
        return output_file
        

def test_build_model(arguments):
    g = LogicParser().parse('all x.(man x)')
    alist = [LogicParser().parse(a) for a in ['(man John)', 
                                              '(man Socrates)', 
                                              '(man Bill)', 
                                              'some x.((not (x = John)) and ((man x) and (sees John x)))',
                                              'some x.((not (x = Bill)) and (man x))',
                                              'all x.some y.((man x) implies (gives Socrates x y))']]
    
    m = Mace(g, assumptions=alist)
    for a in alist:
        print '   %s' % a.infixify()
    print '|- %s: %s\n' % (g.infixify(), m.model_found())
    #m.show_output('standard')
    #m.show_output('cooked')
    print m.build_model(), '\n'

def test_model_found(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        found = Mace(g, assumptions=alist).model_found()
        for a in alist:
            print '   %s' % a.infixify()
        print '|- %s: %s\n' % (g.infixify(), found)

def test_transform_output(argument_pair):
    g = LogicParser().parse(argument_pair[0])
    alist = [LogicParser().parse(a) for a in argument_pair[1]]
    m = Mace(g, assumptions=alist)
    found = m.model_found()
    for a in alist:
        print '   %s' % a.infixify()
    print '|- %s: %s\n' % (g.infixify(), found)
    for format in ['standard', 'portable', 'xml', 'cooked']:
        m.transform_output(format)
        
def test_make_model_dict():
    print Mace.make_model_dict(num_entities=3, values=[1,0,1])
    print Mace.make_model_dict(num_entities=3, values=[0,0,0,0,0,0,1,0,0])
    
arguments = [
    ('(mortal Socrates)', ['all x.((man x) implies (mortal x))', '(man Socrates)']),
    ('(not (mortal Socrates))', ['all x.((man x) implies (mortal x))', '(man Socrates)'])
]

if __name__ == '__main__':
    test_model_found(arguments)
    test_build_model(arguments)
    test_transform_output(arguments[1])
