from featurechart import *
from treeview import *

def demo():
    cp = load_earley('gazdar6.cfg', trace=2)
    cp.batch_test('all-gazdar-sentences.txt')

#run_profile()
if __name__ == '__main__': demo()
