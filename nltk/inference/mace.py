# Natural Language Toolkit: Interface to the Mace4 Model Builder 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
import tempfile

from nltk.sem.logic import *
from nltk.sem import Valuation
from api import ModelBuilder, BaseModelBuilderCommand
from prover9 import *

"""
A model builder that makes use of the external 'Mace4' package.
"""

class MaceCommand(Prover9CommandParent, BaseModelBuilderCommand):
    """
    A L{MaceCommand} specific to the L{Mace} model builder.  It contains
    a print_assumptions() method that is used to print the list
    of assumptions in multiple formats.
    """
    _interpformat_bin = None
    
    def __init__(self, goal=None, assumptions=None, max_models=500, model_builder=None):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in
            the proof.
        @type assumptions: C{list} of L{logic.Expression}
        @param max_models: The maximum number of models that Mace will try before
            simply returning false. (Use 0 for no maximum.)
        @type max_models: C{int}
        """
        if model_builder is not None:
            assert isinstance(model_builder, Mace)
        else:
            model_builder = Mace(max_models)
        
        BaseModelBuilderCommand.__init__(self, model_builder, goal, assumptions)
        
    valuation = property(lambda mbc: mbc.model('valuation'))
        
    def _convert2val(self, valuation_str):
        """
        Transform the output file into an NLTK-style Valuation. 
        
        @return: A model if one is generated; None otherwise.
        @rtype: L{nltk.sem.Valuation} 
        """
        valuation_standard_format = self._transform_output(valuation_str, 'standard')
        
        val = []
        for line in valuation_standard_format.splitlines(False):
            l = line.strip()
            
            if l.startswith('interpretation'):
                # find the number of entities in the model
                num_entities = int(l[l.index('(')+1:l.index(',')].strip())
            
            elif l.startswith('function') and l.find('_') == -1:
                # replace the integer identifier with a corresponding alphabetic character
                name = l[l.index('(')+1:l.index(',')].strip()
                if is_indvar(name):
                    name = name.upper()
                value = int(l[l.index('[')+1:l.index(']')].strip())
                val.append((name, MaceCommand._make_model_var(value)))
            
            elif l.startswith('relation'):
                l = l[l.index('(')+1:]
                if '(' in l:
                    #relation is not nullary
                    name = l[:l.index('(')].strip()
                    values = [int(v.strip()) for v in l[l.index('[')+1:l.index(']')].split(',')]
                    val.append((name, MaceCommand._make_relation_set(num_entities, values)))
                else:
                    #relation is nullary
                    name = l[:l.index(',')].strip()
                    value = int(l[l.index('[')+1:l.index(']')].strip())
                    val.append((name, value == 1))

        return Valuation(val)
        
    @staticmethod
    def _make_relation_set(num_entities, values):
        """
        Convert a Mace4-style relation table into a dictionary.
        
        @parameter num_entities: the number of entities in the model; determines the row length in the table.
        @type num_entities: C{int}
        @parameter values: a list of 1's and 0's that represent whether a relation holds in a Mace4 model.
        @type values: C{list} of C{int}
        """
        r = set()
        for position in [pos for (pos,v) in enumerate(values) if v == 1]:
            r.add(tuple(MaceCommand._make_relation_tuple(position, values, num_entities)))
        return r
                
    @staticmethod
    def _make_relation_tuple(position, values, num_entities):
        if len(values) == 1:
            return []
        else: 
            sublist_size = len(values) / num_entities
            sublist_start = position / sublist_size
            sublist_position = position % sublist_size
            
            sublist = values[sublist_start*sublist_size:(sublist_start+1)*sublist_size]
            return [MaceCommand._make_model_var(sublist_start)] + \
                   MaceCommand._make_relation_tuple(sublist_position, 
                                                    sublist, 
                                                    num_entities)
                
    @staticmethod
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
                
    def _decorate_model(self, valuation_str, format):
        """
        Print out a Mace4 model using any Mace4 C{interpformat} format. 
        See U{http://www.cs.unm.edu/~mccune/mace4/manual/} for details.
        
        @param valuation_str: C{str} with the model builder's output 
        @param format: C{str} indicating the format for displaying
        models. Defaults to 'standard' format.
        @return: C{str}
        """
        if not format:
            return valuation_str
        elif format == 'valuation':
            return self._convert2val(valuation_str)
        else:
            return self._transform_output(valuation_str, format)

    def _transform_output(self, valuation_str, format):
        """
        Transform the output file into any Mace4 C{interpformat} format. 
        
        @parameter format: Output format for displaying models. 
        @type format: C{str}
        """
        if format in ['standard', 'standard2', 'portable', 'tabular', 
                      'raw', 'cooked', 'xml', 'tex']:
            return self._call_interpformat(valuation_str, [format])[0]
        else:
            raise LookupError("The specified format does not exist")

    def _call_interpformat(self, input_str, args=[], verbose=False):
        """
        Call the C{interpformat} binary with the given input.
    
        @param input_str: A string whose contents are used as stdin.
        @param args: A list of command-line arguments.
        @return: A tuple (stdout, returncode)
        @see: L{config_prover9}
        """
        if self._interpformat_bin is None:
            self._interpformat_bin = self._modelbuilder._find_binary(
                                                'interpformat', verbose)

        return self._modelbuilder._call(input_str, self._interpformat_bin, 
                                        args, verbose)


class Mace(Prover9Parent, ModelBuilder):
    _mace4_bin = None
    
    def __init__(self, end_size=500):
        self._end_size = end_size
        """The maximum model size that Mace will try before 
           simply returning false. (Use -1 for no maximum.)"""

    def _build_model(self, goal=None, assumptions=None, verbose=False):
        """
        Use Mace4 to build a first order model.
        
        @return: C{True} if a model was found (i.e. Mace returns value of 0),
        else C{False}        
        """
        if not assumptions:
            assumptions = []
            
        stdout, returncode = self._call_mace4(self.prover9_input(goal, assumptions),
                                              verbose=verbose)
        return (returncode == 0, stdout)

    def _call_mace4(self, input_str, args=[], verbose=False):
        """
        Call the C{mace4} binary with the given input.
    
        @param input_str: A string whose contents are used as stdin.
        @param args: A list of command-line arguments.
        @return: A tuple (stdout, returncode)
        @see: L{config_prover9}
        """
        if self._mace4_bin is None:
            self._mace4_bin = self._find_binary('mace4', verbose)

        updated_input_str = ''
        if self._end_size > 0:
            updated_input_str += 'assign(end_size, %d).\n\n' % self._end_size
        updated_input_str += input_str

        return self._call(updated_input_str, self._mace4_bin, args, verbose)
    

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
    lp = LogicParser()
    for (goal, assumptions) in arguments:
        g = lp.parse(goal)
        alist = [lp.parse(a) for a in assumptions]
        m = MaceCommand(g, assumptions=alist, end_size=50)
        found = m.build_model()
        for a in alist:
            print '   %s' % a
        print '|- %s: %s\n' % (g, decode_result(found))
        
        
def test_build_model(arguments):
    """
    Try to build a L{nltk.sem.Valuation}.
    """
    lp = LogicParser()
    g = lp.parse('all x.man(x)')
    alist = [lp.parse(a) for a in ['man(John)', 
                                   'man(Socrates)', 
                                   'man(Bill)', 
                                   'some x.(-(x = John) & man(x) & sees(John,x))',
                                   'some x.(-(x = Bill) & man(x))',
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
    print m.valuation, '\n'

def test_transform_output(argument_pair):
    """
    Transform the model into various Mace4 C{interpformat} formats.
    """
    lp = LogicParser()
    g = lp.parse(argument_pair[0])
    alist = [lp.parse(a) for a in argument_pair[1]]
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
        
def test_make_relation_set():
    print MaceCommand._make_relation_set(num_entities=3, values=[1,0,1]) == set([('c',), ('a',)])
    print MaceCommand._make_relation_set(num_entities=3, values=[0,0,0,0,0,0,1,0,0]) == set([('c', 'a')])
    print MaceCommand._make_relation_set(num_entities=2, values=[0,0,1,0,0,0,1,0]) == set([('a', 'b', 'a'), ('b', 'b', 'a')])
    
arguments = [
    ('mortal(Socrates)', ['all x.(man(x) -> mortal(x))', 'man(Socrates)']),
    ('(not mortal(Socrates))', ['all x.(man(x) -> mortal(x))', 'man(Socrates)'])
]

def demo():
    test_model_found(arguments)
    test_build_model(arguments)
    test_transform_output(arguments[1])

if __name__ == '__main__':
    demo()
