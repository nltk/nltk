qualifier = 'http://nltk.svn.sourceforge.net/viewvc/*checkout*/nltk/trunk/nltk/'
local = 'examples/parse/feat0.cfg'

from featurechart import *

file1 = 'gazdar6.cfg'

def demo():
    cp = load_earley(file1, trace=2)
    trees = cp.parse('the man who chased Fido returned')
    if trees:
        for tree in trees: print tree

#run_profile()
if __name__ == '__main__': demo()
