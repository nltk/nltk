from mit.six863.parse.featurechart import *
import time

t = time.time()
cp = load_earley('speer.cfg')
trees = cp.parse('the fly spied the tie')

print "Time: %s" % (time.time() - t)
for tree in trees: print tree

