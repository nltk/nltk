from featurechart import *
from treeview import *

def demo():
    cp = load_earley('lab3-slash.cfg', trace=1)
    trees = cp.parse('Mary walks')
    for tree in trees:
        print tree
        sem = tree[0].node['sem']
        print sem
        print sem.skolemise().clauses()
        return sem.skolemise().clauses()

#run_profile()
if __name__ == '__main__': demo()
