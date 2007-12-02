def attempt_proof(formula, prover_name='Prover9'):
    assert isinstance(formula, str)
    
    import os
    
    FILENAME = 'prove'
    PROVER_PATH = '/usr/share/nltk/tools/prover'
    
    try:
        f = open('%s/%s.in' % (PROVER_PATH, FILENAME), 'w')
        f.write('formulas(goals).\n')
        f.write('    %s.\n' % formula)
        f.write('end_of_list.\n')
    finally:
        f.close()
    
    if prover_name == 'Prover9':
        execute_string = \
            '%s/prover9/provers.src/prover9 -f %s/%s.in > %s/%s.out 2>> %s/%s.out' % \
                                          (PROVER_PATH, PROVER_PATH, FILENAME, \
                                                        PROVER_PATH, FILENAME, \
                                                        PROVER_PATH, FILENAME)
    
    os.system(execute_string)
    
def demo_drt_glue_remove_duplicates():
    from nltk_contrib.gluesemantics import drt_glue
    drt_glue.demo(remove_duplicates=True)
    
if __name__ == '__main__':
      from nltk_contrib.drt import DRT
      
      DRT.testEquals()
      print '\n\n'
      demo_drt_glue_remove_duplicates()
