from nltk_contrib.drt import DRT
import os
from string import join

def attempt_proof(expression, prover_name='Prover9'):
    assert isinstance(expression, DRT.Expression)

    if prover_name == 'tableau':
        return expression.tableau()
    elif prover_name == 'Prover9':
        return attempt_proof_prover9(expression)

_prover9_path = None
_prover9_search = ['.',
                   '/usr/local/bin',
                   '/usr/share/prover9',
                   '/usr/local/share/prover9',
                   '/usr/share/nltk/tools/prover',]

def config_prover9(path=None):
    global _prover9_path
    global _prover9_executable
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
            print '[Found Prover9: %s]' % _prover9_executable
            break
  
    if _prover9_path is None:
        raise LookupError("Unable to find Prover9 executable in '%s'\n" 
            "Use 'config_prover9(path=<path>) ',where '<path>' is valid path to the Prover9  directory,"
            " or set the PROVER9HOME environment variable to a valid path." % join(searchpath)) 
        
def attempt_proof_prover9(expression):
    import os

    FILENAME = 'prove'

    f = None
    try:
        f = open('%s/%s.in' % (_prover9_path, FILENAME), 'w')
        f.write('formulas(goals).\n')

        s = expression.infixify().toProver9String()

        execute_string = \
                       '%s/prover9/provers.src/prover9 -f %s/%s.in > %s/%s.out 2>> %s/%s.out' % \
                       (PROVER_PATH, PROVER_PATH, FILENAME, \
                        PROVER_PATH, FILENAME, \
                        PROVER_PATH, FILENAME)

        f.write('    %s.\n' % s)
        f.write('end_of_list.\n')
    finally:
        if f: f.close()

    tp_result = os.system(execute_string)
    return tp_result == 0

def demo_drt_glue_remove_duplicates():
    from nltk_contrib.gluesemantics import drt_glue
    drt_glue.demo(remove_duplicates=True)

def demo():
    #from nltk_contrib.drt import DRT

    #DRT.testTp_equals()
    #print '\n\n'
    #demo_drt_glue_remove_duplicates()
    config_prover9('foo')

if __name__ == '__main__': demo()