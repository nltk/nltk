# Natural Language Toolkit: Interface to the Mace4 Model Builder 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import os
import tempfile
from string import join
from nltk.sem.logic import *
from nltk.sem import Valuation
from api import ModelBuilder, BaseModelBuilderCommand
import prover9
from prover9 import Prover9Parent, Prover9CommandParent, \
                    call_mace4, call_interpformat

"""
A model builder that makes use of the external 'Mace4' package.
"""

class MaceCommand(Prover9CommandParent, BaseModelBuilderCommand):
    """
    A L{MaceCommand} specific to the L{Mace} model builder.  It contains
    the a print_assumptions() method that is used to print the list
    of assumptions in multiple formats.
    """
    def __init__(self, goal=None, assumptions=None, timeout=60):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in
            the proof.
        @type assumptions: C{list} of L{logic.Expression}
        @param timeout: number of seconds before timeout; set to 0 for
            no timeout.
        @type timeout: C{int}
        """
        BaseModelBuilderCommand.__init__(self, Mace(timeout), goal, assumptions)
        
    def convert2val(self):
        """
        Transform the output file into an NLTK-style Valuation. 
        
        @return: A model if one is generated; None otherwise.
        @rtype: L{nltk.sem.Valuation} 
        """
        valuation = None
        if self.build_model():
            valuation_standard_format = self._transform_output('standard')
            
            d = {}
            for line in valuation_standard_format.splitlines(False):
                l = line.strip()
                # find the number of entities in the model
                if l.startswith('interpretation'):
                    num_entities = int(l[l.index('(')+1:l.index(',')].strip())
                # replace the integer identifier with a corresponding alphabetic character
                elif l.startswith('function') and l.find('_') == -1:
                    name = l[l.index('(')+1:l.index(',')].strip()
                    if is_indvar(name):
                        name = name.upper()
                    d[name] = MaceCommand._make_model_var(int(l[l.index('[')+1:l.index(']')].strip()))
                
                elif l.startswith('relation'):
                    name = l[l.index('(')+1:l.index('(', l.index('(')+1)].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    d[name] = MaceCommand._make_model_dict(num_entities, values)
                    
            valuation = Valuation(d.items())
        return valuation
        
    def _make_model_dict(num_entities, values):
        """
        Convert a Mace4-style relation table into a dictionary.
        
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
                d[MaceCommand._make_model_var(i)] = \
                    MaceCommand._make_model_dict(num_entities, values[i*size:(i+1)*size])
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
                
    def decorate_model(self, valuation_str, format):
        """
        Print out a Mace4 model using any Mace4 C{interpformat} format. 
        See U{http://www.cs.unm.edu/~mccune/mace4/manual/} for details.
        
        @param valuation_str: C{str} with the model builder's output 
        @param format: C{str} indicating the format for displaying
        models. Defaults to 'standard' format.
        @return: C{str}
        """
        if not format:
            return self._valuation
        else:
            return self._transform_output(format)

    def _transform_output(self, format):
        """
        Transform the output file into any Mace4 C{interpformat} format. 
        
        @parameter format: Output format for displaying models. 
        @type format: C{str}
        """
        if format in ['standard', 'standard2', 'portable', 'tabular', 
                      'raw', 'cooked', 'xml', 'tex']:
            return call_interpformat(self._valuation, [format])[0]
        else:
            raise LookupError("The specified format does not exist")

class Mace(Prover9Parent, ModelBuilder):
    def build_model(self, goal=None, assumptions=None, verbose=False):
        """
        Use Mace4 to build a first order model.
        
        @return: C{True} if a model was found (i.e. Mace returns value of 0),
        else C{False}        
        """
        if not assumptions:
            assumptions = []
            
        stdout, returncode = call_mace4(self.prover9_input(goal, assumptions))
        return (returncode == 0, stdout)

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
        m = MaceCommand(g, assumptions=alist, timeout=5)
        found = m.build_model()
        for a in alist:
            print '   %s' % a
        print '|- %s: %s\n' % (g, decode_result(found))
        
        
def test_build_model(arguments):
    """
    Try to build a L{nltk.sem.Valuation}.
    """
    g = LogicParser().parse('all x.man(x)')
    alist = [LogicParser().parse(a) for a in ['man(John)', 
                                              'man(Socrates)', 
                                              'man(Bill)', 
                                              'some x.((not (x = John)) and (man(x) and sees(John,x)))',
                                              'some x.((not (x = Bill)) and man(x))',
                                              'all x.some y.(man(x) -> gives(Socrates,x,y))']]
    
    m = MaceCommand(g, assumptions=alist)
    m.build_model()
    spacer()
    print "Assumptions and Goal"
    spacer()
    for a in alist:
        print '   %s' % a
    print '|- %s: %s\n' % (g, decode_result(m.build_model()))
    spacer()
    #print m.model('standard')
    #print m.model('cooked')
    print "Valuation"
    spacer()
    print m.convert2val(), '\n'

def test_transform_output(argument_pair):
    """
    Transform the model into various Mace4 C{interpformat} formats.
    """
    g = LogicParser().parse(argument_pair[0])
    alist = [LogicParser().parse(a) for a in argument_pair[1]]
    m = MaceCommand(g, assumptions=alist)
    m.build_model()
    for a in alist:
        print '   %s' % a
    print '|- %s: %s\n' % (g, m.build_model())
    for format in ['standard', 'portable', 'xml', 'cooked']:
        spacer()
        print "Using '%s' format" % format 
        spacer()
        print m.model(format=format)
        
def test_make_model_dict():
    print MaceCommand._make_model_dict(num_entities=3, values=[1,0,1])
    print MaceCommand._make_model_dict(num_entities=3, values=[0,0,0,0,0,0,1,0,0])
    
arguments = [
    ('mortal(Socrates)', ['all x.(man(x) -> mortal(x))', 'man(Socrates)']),
    ('(not mortal(Socrates))', ['all x.(man(x) -> mortal(x))', 'man(Socrates)'])
]

if __name__ == '__main__':
    test_model_found(arguments)
    test_build_model(arguments)
    test_transform_output(arguments[1])
    
    a = LogicParser().parse('(see(mary,john) & -(mary = john))')
    mb = MaceCommand(assumptions=[a])
    mb.build_model()
    print mb.convert2val()
