# Natural Language Toolkit: Interface to the Prover9 Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import os
import tempfile
import subprocess
from string import join

from nltk.sem import logic 
from nltk.sem.logic import LogicParser

from nltk.internals import deprecated, Deprecated, find_binary

from api import BaseProverCommand, Prover

"""
A theorem prover that makes use of the external 'Prover9' package.
"""
#
# Following is not yet used. Return code for 2 actually realized as 512. 
#
p9_return_codes = {
    0: True,
    1:  "(FATAL)",      #A fatal error occurred (user's syntax error).
    2: False,           # (SOS_EMPTY) Prover9 ran out of things to do
                        #   (sos list exhausted).
    3: "(MAX_MEGS)",    # The max_megs (memory limit) parameter was exceeded.
    4: "(MAX_SECONDS)", # The max_seconds parameter was exceeded.
    5: "(MAX_GIVEN)",   # The max_given parameter was exceeded.
    6: "(MAX_KEPT)",    # The max_kept parameter was exceeded.
    7: "(ACTION)",      # A Prover9 action terminated the search.
    101: "(SIGSEGV)",   # Prover9 crashed, most probably due to a bug.   
 }
 
######################################################################
#{ Configuration
######################################################################

_prover9_bin = None
_prooftrans_bin = None
_mace4_bin = None
_interpformat_bin = None
def config_prover9(bin=None):
    """
    Configure NLTK's interface to the C{prover9} package.  This
    searches for a directory containing the executables for
    C{prover9}, C{mace4}, C{prooftrans}, and C{interpformat}.
    
    @param bin: The full path to the C{prover9} binary.  If not
        specified, then nltk will search the system for a C{prover9}
        binary; and if one is not found, it will raise a
        C{LookupError} exception.
    @type bin: C{string}
    """
    # Find the prover9 binary.
    prover9_bin = find_binary('prover9', bin,
        searchpath=prover9_path, env_vars=['PROVER9HOME'],
        url='http://www.cs.unm.edu/~mccune/prover9/',
        verbose=False)

    # Make sure that mace4 and prooftrans are available, too.
    basedir = os.path.split(prover9_bin)[0]
    mace4_bin = os.path.join(basedir, 'mace4')
    prooftrans_bin = os.path.join(basedir, 'prooftrans')
    interpformat_bin = os.path.join(basedir, 'interpformat')
    if not os.path.isfile(mace4_bin):
        raise ValueError('prover9 was found, but mace4 was not -- '
                         'incomplete prover9 installation?')
    if not os.path.isfile(prooftrans_bin):
        raise ValueError('prover9 was found, but prooftrans was not -- '
                         'incomplete prover9 installation?')
    if not os.path.isfile(interpformat_bin):
        raise ValueError('prover9 was found, but interpformat was not -- '
                         'incomplete prover9 installation?')

    # Save the locations of all three binaries.
    global _prover9_bin, _prooftrans_bin, _mace4_bin, _interpformat_bin
    _prover9_bin = prover9_bin
    _mace4_bin = mace4_bin
    _prooftrans_bin = prooftrans_bin
    _interpformat_bin = interpformat_bin

#: A list of directories that should be searched for the prover9
#: executables.  This list is used by L{config_prover9} when searching
#: for the prover9 executables.
prover9_path = ['/usr/local/bin/prover9',
                '/usr/local/bin/prover9/bin',
                '/usr/local/bin',
                '/usr/bin',
                '/usr/local/prover9',
                '/usr/local/share/prover9']

######################################################################
#{ Interface to Binaries
######################################################################

def call_prover9(input_str, args=[]):
    """
    Call the C{prover9} binary with the given input.

    @param input_str: A string whose contents are used as stdin.
    @param args: A list of command-line arguments.
    @return: A tuple (stdout, returncode)
    @see: L{config_prover9}
    """
    if _prover9_bin is None:
        config_prover9()
        
    # Call prover9 via a subprocess
    cmd = [_prover9_bin] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input_str)
    return (stdout, p.returncode)

def call_prooftrans(input_str, args=[]):
    """
    Call the C{prooftrans} binary with the given input.

    @param input_str: A string whose contents are used as stdin.
    @param args: A list of command-line arguments.
    @return: A tuple (stdout, returncode)
    @see: L{config_prover9}
    """
    if _prooftrans_bin is None:
        config_prover9()
        
    # Call prooftrans via a subprocess
    cmd = [_prooftrans_bin] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input_str)
    return (stdout, p.returncode)

def call_mace4(input_str, args=[]):
    """
    Call the C{mace4} binary with the given input.

    @param input_str: A string whose contents are used as stdin.
    @param args: A list of command-line arguments.
    @return: A tuple (stdout, returncode)
    @see: L{config_prover9}
    """
    if _mace4_bin is None:
        config_prover9()
        
    # Call mace4 via a subprocess
    cmd = [_mace4_bin] + args
    p = subprocess.Popen(cmd, 
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input_str)
    return (stdout, p.returncode)

def call_interpformat(input_str, args=[]):
    """
    Call the C{interpformat} binary with the given input.

    @param input_str: A string whose contents are used as stdin.
    @param args: A list of command-line arguments.
    @return: A tuple (stdout, returncode)
    @see: L{config_prover9}
    """
    if _interpformat_bin is None:
        config_prover9()
        
    # Call interpformat via a subprocess
    cmd = [_interpformat_bin] + args
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input_str)
    return (stdout, p.returncode)

######################################################################
#{ Base Class
######################################################################
    
class Prover9CommandParent(object):
    """
    A common base class used by both L{Prover9Command} and L{MaceCommand
    <mace.MaceCommand>}, which is responsible for maintaining a goal and a
    set of assumptions, and generating prover9-style input files from
    them.
    """
    def print_assumptions(self, output_format='nltk'):
        """
        Print the list of the current assumptions.       
        """
        if output_format.lower() == 'nltk':
            for a in self.assumptions():
                print a
        elif output_format.lower() == 'prover9':
            for a in convert_to_prover9(self.assumptions()):
                print a
        else:
            raise NameError("Unrecognized value for 'output_format': %s" %
                            output_format)

class Prover9Command(Prover9CommandParent, BaseProverCommand):
    """
    A L{ProverCommand} specific to the L{Prover9} prover.  It contains
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
        if not assumptions:
            assumptions = []
            
        BaseProverCommand.__init__(self, Prover9(timeout), goal, assumptions)
        
    def decorate_proof(self, proof_string, simplify=True):
        """
        @see BaseProverCommand.decorate_proof()
        """
        if simplify:
            return call_prooftrans(proof_string, ['striplabels'])[0].rstrip()
        else:
            return proof_string.rstrip()


class Prover9Parent(object):
    """
    A common class extended by both L{Prover9} and L{Mace <mace.Mace>}.  
    It contains the functionality required to convert NLTK-style 
    expressions into Prover9-style expressions.
    """
    def __init__(self, timeout=60):
        self._timeout = timeout
        """The timeout value for prover9.  If a proof can not be found
           in this amount of time, then prover9 will return false.
           (Use 0 for no timeout.)"""
    
    def prover9_input(self, goal, assumptions):
        """
        @return: The input string that should be provided to the
        prover9 binary.  This string is formed based on the goal,
        assumptions, and timeout value of this object.
        """
        s = ''
        if self._timeout > 0:
            s += 'assign(max_seconds, %d).\n\n' % self._timeout
        
        if assumptions:
            s += 'formulas(assumptions).\n'
            for p9_assumption in convert_to_prover9(assumptions):
                s += '    %s.\n' % p9_assumption
            s += 'end_of_list.\n\n'
    
        if goal:
            s += 'formulas(goals).\n'
            s += '    %s.\n' % convert_to_prover9(goal)
            s += 'end_of_list.\n\n'

        return s
    
def convert_to_prover9(input):
    """
    Convert C{logic.Expression}s to Prover9 format.
    """
    if isinstance(input, list):
        result = []
        for s in input:
            try:
                result.append(s.simplify().str(logic.Tokens.PROVER9))
            except AssertionError:
                print 'input %s cannot be converted to Prover9 input syntax' % input
        return result    
    else:
        try:
            return input.simplify().str(logic.Tokens.PROVER9)
        except AssertionError:
            print 'input %s cannot be converted to Prover9 input syntax' % input


######################################################################
#{ Prover9
######################################################################

class Prover9(Prover9Parent, Prover):
    def prove(self, goal=None, assumptions=None, debug=False):
        """
        Use Prover9 to prove a theorem.
        @return: A pair whose first element is a boolean indicating if the 
        proof was successful (i.e. returns value of 0) and whose second element
        is the output of the prover.        
        """
        if not assumptions:
            assumptions = []
            
        stdout, returncode = call_prover9(self.prover9_input(goal, 
                                                             assumptions))
        return (returncode == 0, stdout)
    
    def prover9_input(self, goal, assumptions):
        """
        @see: Prover9Parent.prover9_input
        """
        s = 'clear(auto_denials).\n' #only one proof required
        return s + Prover9Parent.prover9_input(self, goal, assumptions)
        

    
######################################################################
#{ Tests and Demos
######################################################################

def test_config():
    
    a = LogicParser().parse('(walk(j) & sing(j))')
    g = LogicParser().parse('walk(j)')
    p = Prover9Command(g, assumptions=[a])
    p._executable_path = None
    p.prover9_search=[]
    p.prove()
    #config_prover9('/usr/local/bin')
    print p.prove()
    print p.proof()
    
def test_convert_to_prover9(expr):
    """
    Test that parsing works OK.
    """
    for t in expr:
        e = LogicParser().parse(t)
        print convert_to_prover9(e)
        
def test_prove(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        p = Prover9Command(g, assumptions=alist).prove()
        for a in alist:
            print '   %s' % a
        print '|- %s: %s\n' % (g, p)
    
arguments = [
    ('(man(x) <-> (not (not man(x))))', []),
    ('(not (man(x) & (not man(x))))', []),
    ('(man(x) | (not man(x)))', []),
    ('(man(x) & (not man(x)))', []),
    ('(man(x) -> man(x))', []),
    ('(not (man(x) & (not man(x))))', []),
    ('(man(x) | (not man(x)))', []),
    ('(man(x) -> man(x))', []),
    ('(man(x) <-> man(x))', []),
    ('(not (man(x) <-> (not man(x))))', []),
    ('mortal(Socrates)', ['all x.(man(x) -> mortal(x))', 'man(Socrates)']),
    ('((all x.(man(x) -> walks(x)) & man(Socrates)) -> some y.walks(y))', []),
    ('(all x.man(x) -> all x.man(x))', []),
    ('some x.all y.sees(x,y)', []),
    ('some e3.(walk(e3) & subj(e3, mary))', 
        ['some e1.(see(e1) & subj(e1, john) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))']),
    ('some x e1.(see(e1) & subj(e1, x) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))', 
       ['some e1.(see(e1) & subj(e1, john) & some e2.(pred(e1, e2) & walk(e2) & subj(e2, mary)))'])
]

expressions = [r'some x y.sees(x,y)',
               r'some x.(man(x) & walks(x))',
               r'\x.(man(x) & walks(x))',
               r'\x y.sees(x,y)',
               r'walks(john)',
               r'\x.big(x, \y.mouse(y))',
               r'(walks(x) & (runs(x) & (threes(x) & fours(x))))',
               r'(walks(x) -> runs(x))',
               r'some x.(PRO(x) & sees(John, x))',
               r'some x.(man(x) & (not walks(x)))',
               r'all x.(man(x) -> walks(x))']

def spacer(num=45):
    print '-' * num

if __name__ == '__main__':
    print "Testing configuration"
    spacer()
    test_config()
    print
    print "Testing conversion to Prover9 format"
    spacer()
    test_convert_to_prover9(expressions)
    print
    print "Testing proofs"
    spacer()
    test_prove(arguments)
