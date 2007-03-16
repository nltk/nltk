from featurechart import *
import time

sent = 'Poirot sent the solutions to the police'
print "Sentence:\n", sent
t = time.time()
cp = load_earley('speer.cfg')
trees = cp.parse(sent)
print "Time: %s" % (time.time() - t)
for tree in trees: print tree

