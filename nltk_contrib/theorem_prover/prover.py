# Natural Language Toolkit: Interface to Theorem Provers 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#              Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_contrib.drt import ApplicationExpression, FolOperator, Parser

import os
from string import join

def attempt_proof(expression, prover_name='Prover9'):
    """
    Try to prove an expression of First Order Logic. 
    
    @param expression: Input expression, which should support the ``toProver9String()``
    method
    @type expression: L{DRT.Expression}
    @type prover_name: C{str}
    @param prover_name: Name of the prover to use.
    
    """
    #assert isinstance(expression, DRT.Expression)

    if prover_name == 'tableau':
        return expression.tableau()
    
    elif prover_name == 'Prover9':
        config_prover9(verbose=False)
        try:
            p9_expression = expression.toProver9String()
        except:
            raise AttributeError("%s cannot be converted to Prover9 input syntax" % expression)
        
        return attempt_proof_prover9(p9_expression)

_prover9_path = None
_prover9_executable = None

_prover9_search = ['.',
                   '/usr/local/bin',
                   '/usr/local/prover9',
                   '/usr/local/share/prover9']

def config_prover9(path=None, verbose=True):
    """
    Configure the location of Prover9 Executable
    
    @param path: Path to the Prover9 executable
    @type path: C{str}
    """
    
    global _prover9_path, _prover9_executable
    _prover_path = None

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = _prover9_search
        if 'PROVER9HOME' in os.environ:
            searchpath.insert(0, os.environ['PROVER9HOME'])

    for path in searchpath:
        exe = os.path.join(path, 'prover9')
        if os.path.exists(exe):
            _prover9_path = path
            _prover9_executable = exe
            if verbose:
                print '[Found Prover9: %s]' % _prover9_executable
            break
  
    if _prover9_path is None:
        raise LookupError("Unable to find Prover9 executable in '%s'\n" 
            "Use 'config_prover9(path=<path>) '," 
            " or set the PROVER9HOME environment variable to a valid path." % join(searchpath)) 
        
def attempt_proof_prover9(expression):
    """
    Use Prover9 to prove an expression.
    
    @param expression: logic expression to be proved
    @rtype: C{str}
    @return: C{True} if the proof was successful (i.e. returns value of 0),
    else C{False}
    
    """
    if _prover9_executable is None:
        config_prover9(verbose=False)
        
    FILENAME = 'prove'
    f = None
    
    try:
        FILEPATH = os.path.join('/tmp', FILENAME)
        
        f = open('%s.in' % FILEPATH, 'w')
        f.write('formulas(goals).\n')
        #s = expression.infixify().toProver9String()
        f.write('    %s.\n' % expression)
        f.write('end_of_list.\n')
        f.close()
        
        execute_string = \
                       '%s -f %s.in > %s.out 2>> %s.out' % \
                       (_prover9_executable, FILEPATH, FILEPATH, FILEPATH)
        
    finally:
        if f: f.close()

    tp_result = os.system(execute_string)
    return tp_result == 0

def demo_drt_glue_remove_duplicates():
    from nltk_contrib.gluesemantics import drt_glue
    drt_glue.demo(remove_duplicates=True)

def demo():
    from nltk_contrib.drt import DRT

    DRT.testTp_equals()
    #print '\n\n'
    #demo_drt_glue_remove_duplicates()
    #lp = Parser()
    #a = lp.parse(r'drs([x],[(man x), (walks x)])').simplify().toFol()
    #b = lp.parse(r'drs([x],[(walks x), (man x)])').simplify().toFol()
    #bicond = ApplicationExpression(ApplicationExpression(FolOperator('iff'), a), b)
    
    #print "Trying to prove:\n '%s <-> %s'" % (a, b)
    #print attempt_proof(bicond)
    

if __name__ == '__main__': 
    demo()
