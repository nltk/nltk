##  cluster.py
##  clustering utilities for word sense discrimination
##  Brent Gray -- CIS 530

from math import sqrt

def calcCentroid(tAList):
    result = []
    for t1 in tAList:
        temp1 = t1.getContextVector()
        if not result:
            result = temp1
        else:
            for i in range(len(result)):
                result[i] += temp1[i]
    return result
        
def euclidDistance(tA1, tA2):
    distance = 0
    if len(tA1) > 1:
        a = calcCentroid(tA1)
##        print 'calcCentroid on ', tA1
    else:
        a = tA1[0].getContextVector()
        
    if len(tA2) > 1:
##        print 'calcCentroid on ', tA2
        b = calcCentroid(tA2)
    else:
        b = tA2[0].getContextVector()

    if len(a) != len(b):
        return 0
    else:
        for i in range(len(a)):
            distance += (a[i] - b[i])**2
        return sqrt(distance)

def getClosest(_C):
    distances = {}
    returnVal = []
    distance = 0
    for i in range(len(_C)):
        elt1 = _C[i]
        for j in range(0, i):
            elt2 = _C[j]
            distance = euclidDistance(elt1, elt2)
            distances[distance] = [i, j]
    ks = distances.keys()
    ks.sort()
    returnVal = distances[ks[0]]
    return returnVal

def cluster(targetAppearances):
    clusterings = []
    # Put each TargetAppearance into a separate cluster, to start.
    C = []
    top = []
    for i in range(len(targetAppearances)):
        C.append([targetAppearances[i]])
        top.append([targetAppearances[i]])
    clusterings.append(top)
        
    # Join clusters until there's only one top-level cluster left
    while len(C) != 1:
            
        # Get the indices of the closest two clusters
        returnList = getClosest(C)
        i = returnList[0]
        j = returnList[1]
        
        # Join them
        a = C[i]
        b = C[j]
        n = C[i] + C[j]
        C.append(n)
        C.remove(a)
        C.remove(b)
            
        # Add to the list of clusterings
        new = []
        for k in range(len(C)):
            new.append(C[k])
        clusterings.append(new)
                
    return clusterings
