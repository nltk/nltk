from featurechart import *
from treeview import *

def demo():
    cp = load_earley('sem2.cfg', trace=2)
    trees = cp.parse('a dog chases a girl')
    for tree in trees: print tree

#run_profile()
if __name__ == '__main__': demo()
