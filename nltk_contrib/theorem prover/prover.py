from nltk_contrib.drt import DRT

def attempt_proof(expression, prover_name='Prover9'):
    assert isinstance(expression, DRT.Expression)
    
    if prover_name == 'tableau':
        return expression.tableau()
    elif prover_name == 'Prover9':
        return attempt_proof_prover9(expression)
    
def attempt_proof_prover9(expression):
    import os
    
    FILENAME = 'prove'
    PROVER_PATH = '/usr/share/nltk/tools/prover'
    
    f = None
    try:
        f = open('%s/%s.in' % (PROVER_PATH, FILENAME), 'w')
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
      from nltk_contrib.drt import DRT
      
      DRT.testTp_equals()
      print '\n\n'
      demo_drt_glue_remove_duplicates()

if __name__ == '__main__': demo()