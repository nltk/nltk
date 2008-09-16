#!/usr/bin/env python

"""
this script shows how to iteratively run the MapReduce task
"""

from subprocess import Popen
import sys

# convergence threshold
diff = 0.0001
oldlog = 0
newlog = 1
iter = 100
i = 0

# while not converged or not reach maximum iteration number
while (abs(newlog - oldlog) > diff and i <= iter):
    print "oldlog", oldlog
    print "newlog", newlog

    i += 1
    oldlog = newlog


    # iteratively execute the MapReduce task
    userdir = '/home/mxf/nltknew/nltk_contrib/hadoop/EM/'
    p = Popen([userdir + 'runStreaming.sh' ], shell=True, stdout=sys.stdout)
    p.wait()
    print "returncode", p.returncode

    # open the parameter output from finished iteration
    # and get the new loglikelihood
    f = open("hmm_parameter", 'r')
    for line in f:
        li = line.strip().split()
        if li[0] == "loglikelihood":
            newlog = float(li[1])
    f.close()

print "oldlog", oldlog
print "newlog", newlog
