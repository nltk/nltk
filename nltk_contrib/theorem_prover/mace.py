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
from nltk_contrib.theorem_prover import prover9

_prover9_path = None
_mace_executable = None

prover9_search = ['.',
                   '/usr/local/bin/prover9',
                   '/usr/local/bin/prover9/bin',
                   '/usr/local/bin',
                   '/usr/bin',
                   '/usr/local/prover9',
                   '/usr/local/share/prover9']

def config_mace(path=None, verbose=True):
    """
    Configure the location of Mace Executable
    
    @param path: Path to the Mace executable
    @type path: C{str}
    """
    
    global _prover9_path, _mace_executable
    _prover9_path = None

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = prover9_search
        if 'PROVER9HOME' in os.environ:
            searchpath.insert(0, os.environ['PROVER9HOME'])

    for path in searchpath:
        exe = os.path.join(path, 'mace4')
        if os.path.exists(exe):
            _prover9_path = path
            _mace_executable = exe
            if verbose:
                print '[Found Mace4: %s]' % _mace_executable
            break
  
    if _prover9_path is None:
        raise LookupError("Unable to find Mace4 executable in '%s'\n" 
            "Use 'config_mace(path=<path>) '," 
            " or set the PROVER9HOME environment variable to a valid path." % join(searchpath))


class Mace(ModelBuilderI):
    def __init__(self, goal, assumptions=[], timeout=60):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in the proof
        @type assumptions: L{list} of logic.Expression objects
        @param timeout: number of seconds before timeout; set to 0 for no timeout.
        @type timeout: C{int}
        """
        config_mace()
        self._goal = goal        
        self._assumptions = assumptions
        self._infile = ''
        self._outfile = '' 
        self._p9_assumptions = []
        self._p9_goal = prover9.convert_to_prover9(self._goal)
        if self._assumptions:
            self._p9_assumptions = prover9.convert_to_prover9(self._assumptions)
        self._timeout = timeout
        
        
    def prover9_files(self, filename='prover9', p9_dir=None):
        """
        Generate names for the input and output files and write to the input file.
        """     
        # If no directory specified, use system temp directory
        if p9_dir is None:
            p9_dir = tempfile.gettempdir()
        self._infile = os.path.join(p9_dir, filename + '.in')
        self._outfile = os.path.join(p9_dir, filename + '.out')
        f = open(self._infile, 'w')
        
        if self._timeout > 0:
            f.write('assign(max_seconds, %d).\n' % self._timeout)
            
        if self._p9_assumptions:
            f.write('formulas(assumptions).\n')
            for p9_assumption in self._p9_assumptions:
                f.write('    %s.\n' % p9_assumption)
            f.write('end_of_list.\n\n')
    
        f.write('formulas(goals).\n')
        f.write('    %s.\n' % self._p9_goal)
        f.write('end_of_list.\n')
        f.close()
            
        return None
    
    def build_model(self):
        """
        Use Prover9 to prove a theorem.
        @return: C{True} if the proof was successful 
        (i.e. returns value of 0), else C{False}
        """
        self.prover9_files()
        
        execute_string = '%s -f %s > %s 2>> %s' % \
            (_mace_executable, self._infile, self._outfile, self._outfile)
                
        result = os.system(execute_string)
        return result == 0
    
    def show_proof(self):
        """
        Print out a Prover9 proof.
        """
        if self._outfile:
            for l in open(self._outfile):
                print l,
        else:
            print "You have to call prove() first to get a proof!"
        return None
    
            
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
        
        @param debug: If True, give warning when C{retracted} is not present on assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        
        result = set(self._assumptions) - set(retracted)
        if debug and result == set(self._assumptions):
            print Warning("Assumptions list has not been changed:")
            self.assumptions()
            
        self._assumptions = list(result)
        self._p9_assumptions = convert_to_prover9(self._assumptions)
        return None
    
    def assumptions(self, output_format='nltk'):
        """
        List the current assumptions.       
        """
        if output_format.lower() == 'nltk':
            print [str(a.infixify()) for a in self._assumptions]
 
        elif output_format.lower() == 'prover9':
            print self._p9_assumptions
        else:
            raise NameError("Unrecognized value for 'output_format': %s" % output_format)
        
        
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
       

def testBuild_model(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        p = Mace(g, assumptions=alist).build_model()
        for a in alist:
            print '   %s' % a.infixify()
        print '|- %s: %s\n' % (g.infixify(), p)

        
    
arguments = [
    ('(mortal Socrates)', ['all x.((man x) implies (mortal x))', '(man Socrates)']) ,
    ('(not (mortal Socrates))', ['all x.((man x) implies (mortal x))', '(man Socrates)'])
]

if __name__ == '__main__':
    testBuild_model(arguments)
