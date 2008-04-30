# Natural Language Toolkit: Interface to the Prover9 Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#              Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
import tempfile
import subprocess
from string import join
from nltk.sem.logic import *
from api import ProverI
from nltk.internals import deprecated, Deprecated, find_binary

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
        url='http://www.cs.unm.edu/~mccune/prover9/')

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
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
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
    
class Prover9Parent:
    """
    A common base class used by both L{Prover9} and L{Mace
    <mace.Mace>}, which is responsible for maintaining a goal and a
    set of assumptions, and generating prover9-style input files from
    them.
    """
    def __init__(self, goal=None, assumptions=[], timeout=60):
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
        self._goal = goal
        """The logic expression to prove.
           L{logic.Expression}"""
        
        self._assumptions = list(assumptions)
        """The set of expressions to use as assumptions in the proof.
           C{list} of L{logic.Expression}"""
        
        self._p9_assumptions = []
        """The set of assumption expressions listed in L{self._assumptions},
           transformed into a list of string expressions using
           L{convert_to_prover9()}."""
        
        self._p9_goal = None
        """The logic ecpression to prove (L{self._goal}), transformed
           into a string expression using L{convert_to_prover9()}."""
        
        if goal:
            self._p9_goal = convert_to_prover9(self._goal)
            
        if self._assumptions:
            self._p9_assumptions = convert_to_prover9(self._assumptions)
            
        self._timeout = timeout
        """The timeout value for prover9.  If a proof can not be found
           in this amount of time, then prover9 will return false.
           (Use 0 for no timeout.)"""
        
    def prover9_input(self):
        """
        @return: The input string that should be provided to the
        prover9 binary.  This string is formed based on the goal,
        assumptions, and timeout value of this object.
        """
        s = ''
        if self._timeout > 0:
            s += 'assign(max_seconds, %d).\n' % self._timeout
            
        if self._p9_assumptions:
            s += 'formulas(assumptions).\n'
            for p9_assumption in self._p9_assumptions:
                s += '    %s.\n' % p9_assumption
            s += 'end_of_list.\n\n'
    
        s += 'formulas(goals).\n'
        if self._p9_goal:
            s += '    %s.\n' % self._p9_goal
        s += 'end_of_list.\n\n'

        return s
    
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
        self._p9_assumptions += convert_to_prover9(new_assumptions)
        return None
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on 
        assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        retracted = set(retracted)
        result = [a for a in self._assumptions if a not in retracted]
        if debug and result == self._assumptions:
            print Warning("Assumptions list has not been changed:")
            self.assumptions()
            
        self._assumptions = result
        self._p9_assumptions = convert_to_prover9(self._assumptions)
        return None
    
    def assumptions(self, output_format='nltk'):
        """
        List the current assumptions.       
        """
        if output_format.lower() == 'nltk':
            for a in self._assumptions:
                print a.infixify()
        elif output_format.lower() == 'prover9':
            for a in self._p9_assumptions:
                print a
        else:
            raise NameError("Unrecognized value for 'output_format': %s" %
                            output_format)
        
#{ Deprecated     
    @deprecated("Use nltk.data.load(<file.fol>) instead.")    
    def load(self, filename):
        """
        Load and parse a file of logical statements.
        These must be parsable by LogicParser.
        """
        statements = open(filename).readlines()
        lp = LogicParser()
        result = []
        for s in statements:
            result.append(lp.parse(s))
        return result                 
#}       

######################################################################
#{ Prover9 <-> logic.Expression conversion
######################################################################

def convert_to_prover9(input):
    """
    Convert C{logic.Expression}s to Prover9 format.
    """
    if isinstance(input, list):
        result = []
        for s in input:
            try:
                result.append(toProver9String(s.simplify().infixify()))
            except AssertionError:
                print 'input %s cannot be converted to Prover9 input syntax' % input
        return result    
    else:
        try:
            return toProver9String(input.simplify().infixify())
        except AssertionError:
            print 'input %s cannot be converted to Prover9 input syntax' % input
    
def toProver9String(current):
    toProver9String_method = None
    if isinstance(current, SomeExpression):
        toProver9String_method = _toProver9String_SomeExpression
    elif isinstance(current, VariableBinderExpression):
        toProver9String_method = _toProver9String_VariableBinderExpression
    elif isinstance(current, ApplicationExpression):
        toProver9String_method = _toProver9String_ApplicationExpression
    elif isinstance(current, Operator):
        toProver9String_method = _toProver9String_Operator
    elif isinstance(current, Expression):
        toProver9String_method = _toProver9String_Expression
    elif isinstance(current, Variable):
        toProver9String_method = _toProver9String_Variable
    elif isinstance(current, Constant):
        toProver9String_method = _toProver9String_Constant
    else:
        raise AssertionError, 'Not a valid expression'

    return toProver9String_method(current)

def _toProver9String_SomeExpression(current):
    return '%s %s %s' % ('exists', toProver9String(current.variable), toProver9String(current.term))
    
def _toProver9String_VariableBinderExpression(current):
    prefix = current.__class__.PREFIX
    variable = toProver9String(current.variable)
    term = toProver9String(current.term)
    return '%s%s %s' % (prefix, variable, term)

def _toProver9String_ApplicationExpression(current):
    # Print '((M op) N)' as '(M op N)'.
    # Print '(M N)' as 'M(N)'.
    if isinstance(current.first, ApplicationExpression) \
        and isinstance(current.first.second, Operator):
            firstStr = toProver9String(current.first.first)
            opStr = toProver9String(current.first.second)
            secondStr = toProver9String(current.second)
            return '(%s %s %s)' % (firstStr, opStr, secondStr)
    else:
        accum = '%s(' % toProver9String(current.fun)
        for arg in current.args:
            accum += '%s, ' % toProver9String(arg)
        return '%s)' % accum[0:-2]
    
def _toProver9String_Operator(current):
    if(current.operator == 'and'):
        return '&';
    if(current.operator == 'or'):
        return '|';
    if(current.operator == 'not'):
        return '-';
    if(current.operator == 'implies'):
        return '->';
    if(current.operator == 'iff'):
        return '<->';
    else:
        return current.operator

def _toProver9String_Expression(current):
    return current.__str__()

def _toProver9String_Variable(current):
    return current.name

def _toProver9String_Constant(current):
    return current.name


######################################################################
#{ Prover9
######################################################################

class Prover9(Prover9Parent, ProverI):
    _proof = None  #: text output from running prover9
    _result = None #: bool indicating if proof succeeded
    
    def get_executable(self):
        return 'prover9'

    def prove(self, debug=False):
        """
        Use Prover9 to prove a theorem.
        @return: C{True} if the proof was successful 
        (i.e. returns value of 0), else C{False}        
        """
        stdout, returncode = call_prover9(self.prover9_input())
        self._result = (returncode == 0)
        self._proof = stdout
        return self._result
    
    def proof_successful(self):
        return self._result
    
    def show_proof(self, simplify=True):
        """
        Print out a Prover9 proof.    
        
        @parameter simplify: if C{True}, simplify the output file 
        using Prover9's C{prooftrans}.
        @type simplify: C{bool}
        """
        if not self._proof:
            raise LookupError("You have to call prove() first to get a proof!")
            
        if simplify:
            #print 'calling with\n', self._proof
            print call_prooftrans(self._proof, ['striplabels'])[0].rstrip()
        else:
            print self._proof.rstrip()


######################################################################
#{ Tests & Demos
######################################################################

def test_config():
    
    a = LogicParser().parse('((walk j) and (sing j))')
    g = LogicParser().parse('(walk j)')
    p = Prover9(g, assumptions=[a])
    p._executable_path = None
    p.prover9_search=[]
    p.prove()
    #config_prover9('/usr/local/bin')
    print p.prove()
    p.show_proof()
    
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
        p = Prover9(g, assumptions=alist).prove()
        for a in alist:
            print '   %s' % a.infixify()
        print '|- %s: %s\n' % (g.infixify(), p)
    
arguments = [
    ('((man x) iff (not (not (man x))))', []),
    ('(not ((man x) and (not (man x))))', []),
    ('((man x) or (not (man x)))', []),
    ('((man x) and (not (man x)))', []),
    ('((man x) implies (man x))', []),
    ('(not ((man x) and (not (man x))))', []),
    ('((man x) or (not (man x)))', []),
    ('((man x) implies (man x))', []),
    ('((man x) iff (man x))', []),
    ('(not ((man x) iff (not (man x))))', []),
    ('(mortal Socrates)', ['all x.((man x) implies (mortal x))', '(man Socrates)']),
    ('((all x.((man x) implies (walks x)) and (man Socrates)) implies some y.(walks y))', []),
    ('(all x.(man x) implies all x.(man x))', []),
    ('some x.all y.(sees x y)', []),
    ('some e3.((walk e3) and (subj e3 mary))', 
        ['some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))']),
    ('some x e1.((see e1) and (subj e1 x) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))', 
       ['some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))'])
]

expressions = [r'some x y.(sees x y)',
               r'some x.((man x) and (walks x))',
               r'\x.((man x) and (walks x))',
               r'\x y.(sees x y)',
               r'(walks john)',
               r'\x.(big x \y.(mouse y))',
               r'((walks x) and ((runs x) and ((threes x) and (fours x))))',
               r'((walks x) implies (runs x))',
               r'some x.((PRO x) and (sees John x))',
               r'some x.((man x) and (not (walks x)))',
               r'all x.((man x) implies (walks x))']

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
