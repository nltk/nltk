# requires kimmo 

from featurechart import *

def demo():
    cp = load_earley('gazdar6.cfg', trace=2)
    trees = cp.parse('the man returned')
    if trees:
        for tree in trees: print tree

#run_profile()
if __name__ == '__main__': demo()
