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
import prover9
from prover9 import Prover9Parent

"""
A model builder that makes use of the external 'Mace4' package.
"""

class Mace(Prover9Parent, ModelBuilderI):
    def get_executable(self):
        return 'mace4'

    def build_model(self):
        """
        Use Mace4 to build a first order model.
        
        @return: C{True} if a model was found (i.e. Mace returns value of 0), else C{False}        
        """
        self.prover9_files('mace')
        exe = os.path.join(self._executable_path, self.get_executable())
        execute_string = '%s -c -f %s > %s 2>> %s' % \
            (exe, self._infile, self._outfile, self._outfile)
                
        valuation = None
                
        self._result = (os.system(execute_string) == 0)
        return self._result

    def convert2val(self):
        """
        Transform the output file into an NLTK-style Valuation. 
        
        @return: A model if one is generated; None otherwise.
        @rtype: L{nltk.sem.Valuation} 
        """
        from nltk.sem import Valuation
        valuation = None
        if self.model_found():
            self._transform_output('standard')
            
            d = {}
            for line in open(os.path.join(self._p9_dir, 'mace.standard.out')):
                l = line.strip()
                # find the number of entities in the model
                if l.startswith('interpretation'):
                    num_entities = int(l[l.index('(')+1:l.index(',')].strip())
                # replace the integer identifier with a corresponding alphabetic character
                elif l.startswith('function') and l.find('_') == -1:
                    name = l[l.index('(')+1:l.index(',')].strip()
                    d[name] = Mace._make_model_var(int(l[l.index('[')+1:l.index(']')].strip()))
                
                elif l.startswith('relation'):
                    name = l[l.index('(')+1:l.index('(', l.index('(')+1)].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    d[name] = Mace._make_model_dict(num_entities, values)
                    
            valuation = Valuation(d)
        return valuation
        
    def _make_model_dict(num_entities, values):
        """
        Convert a Mace4-style relation table into a dictionary similar to L{nltk.sem.CharFun}.
        
        @parameter num_entities: the number of entities in the model; determines the row length in the table.
        @type num_entities: C{int}
        @parameter values: integers that represent semantic values in a Mace4 model.
        @type values: C{list} of C{int}
        """
        if len(values) == 1:
            return (values[0] == 1)
        else:
            d = {}
            for i in range(num_entities):
                size = len(values) / num_entities
                d[Mace._make_model_var(i)] = \
                    Mace._make_model_dict(num_entities, values[i*size:(i+1)*size])
            return d
        
    _make_model_dict = staticmethod(_make_model_dict)
                
    def _make_model_var(value):
        """
        Pick an alphabetic character as identifier for an entity in the model.
        
        @parameter value: where to index into the list of characters
        @type value: C{int}
        """
        letter = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n',
                  'o','p','q','r','s','t','u','v','w','x','y','z'][value]
        num = int(value) / 26
        if num > 0:
            return letter + str(num)
        else:
            return letter
        
    _make_model_var = staticmethod(_make_model_var)
                
    def model_found(self):
        """
        Test whether Mace4 can build a model.
        
        @return: C{True} if a model was found (i.e. Mace returns value of 0), else C{False}        
        """
        if not self._outfile:
            print "You have to call build_model() first to get a model!"
        return self._result
    
    def show_model(self, format=None):
        """
        Print out a Mace4 model using any Mace4 C{interpformat} format. 
        See U{http://www.cs.unm.edu/~mccune/mace4/manual/} for details.
        
        @parameter format: Output format for displaying models. Defaults to 'standard' format.
        @type format: C{str}
        """
        if self._outfile:
            if not format:
                for l in open(self._outfile):
                    print l,
            else:
                for l in open(self._transform_output(format)):
                    print l,
            print
        else:
            print "You have to call build_model() first to get a model!"
        return None
    
    def _transform_output(self, format):
        """
        Transform the output file into any Mace4 C{interpformat} format. 
        
        @parameter format: Output format for displaying models. 
        @type format: C{str}
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
        

def spacer(num=30):
    print '-' * num
    
def decode_result(found):
    """
    Decode the result of model_found() 
    
    @parameter found: The output of model_found() 
    @type found: C{boolean}
    """
    return {True: 'Countermodel found', False: 'No countermodel found', None: 'None'}[found]

def test_model_found(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        m = Mace(g, assumptions=alist, timeout=5)
        m.build_model()
        found = m.model_found()
        for a in alist:
            print '   %s' % a.infixify()
        print '|- %s: %s\n' % (g.infixify(), decode_result(found))
        
        
def test_build_model(arguments):
    """
    Try to build a L{nltk.sem.Valuation}.
    """
    g = LogicParser().parse('all x.(man x)')
    alist = [LogicParser().parse(a) for a in ['(man John)', 
                                              '(man Socrates)', 
                                              '(man Bill)', 
                                              'some x.((not (x = John)) and ((man x) and (sees John x)))',
                                              'some x.((not (x = Bill)) and (man x))',
                                              'all x.some y.((man x) implies (gives Socrates x y))']]
    
    m = Mace(g, assumptions=alist)
    m.build_model()
    spacer()
    print "Assumptions and Goal"
    spacer()
    for a in alist:
        print '   %s' % a.infixify()
    print '|- %s: %s\n' % (g.infixify(), decode_result(m.model_found()))
    spacer()
    #m.show_model('standard')
    #m.show_model('cooked')
    print "Valuation"
    spacer()
    print m.convert2val(), '\n'

def test_transform_output(argument_pair):
    """
    Transform the model into various Mace4 C{interpformat} formats.
    """
    g = LogicParser().parse(argument_pair[0])
    alist = [LogicParser().parse(a) for a in argument_pair[1]]
    m = Mace(g, assumptions=alist)
    m.build_model()
    for a in alist:
        print '   %s' % a.infixify()
    print '|- %s: %s\n' % (g.infixify(), m.model_found())
    for format in ['standard', 'portable', 'xml', 'cooked']:
        spacer()
        print "Using '%s' format" % format 
        spacer()
        m.show_model(format=format)
        
def test_make_model_dict():
    print Mace._make_model_dict(num_entities=3, values=[1,0,1])
    print Mace._make_model_dict(num_entities=3, values=[0,0,0,0,0,0,1,0,0])
    
arguments = [
    ('(mortal Socrates)', ['all x.((man x) implies (mortal x))', '(man Socrates)']),
    ('(not (mortal Socrates))', ['all x.((man x) implies (mortal x))', '(man Socrates)'])
]

if __name__ == '__main__':
    test_model_found(arguments)
    test_build_model(arguments)
    test_transform_output(arguments[1])
