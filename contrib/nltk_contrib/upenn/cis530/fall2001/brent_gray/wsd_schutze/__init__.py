##  CIS 530
##  Brent Gray
##  Automatic Word Sense Discrimination
##  based on Schutze, 1998
##

"""
An implementation of the automatic word sense discrimination algorithm
described in Schutze, 1998.
"""

import string, os, sys, time, ioutils, cluster

## class TargetAppearance
## stores the fileName, position with the file
## k-word window of context, and context vector
## for each instance of a found target word

class TargetAppearance:
    def __init__(self, file, position, windowSize):
        self._document = file.name
        self._position = position
        self.setWindow(file, self._position, windowSize)
        self._contextVector = []
        self._contextVectorDictionary = {}
        
    def getContextVector(self):
        return self._contextVector

    def getContextVectorDictionary(self):
        return self._contextVectorDictionary
    
    def setContextVector(self, wordVectorList):
        lcase = string.lower
        tempVector = {}
        win = self.getWindow()
        for key,val in wordVectorList.items():
            if key in win:
                tempVector = sumVectors(tempVector, wordVectorList[key])
            else:
                tempVector[key] = 0
        
        ## now generate a consistent vector representation,
        ## by alpha ordering on the keys
        keys = tempVector.keys()
        keys.sort()
        for k in keys:
            self._contextVector.append(tempVector[k])

        self._contextVectorDictionary = tempVector

    def getWindow(self):
        return self._window

    def setWindow(self, _f, position, size):
        lcase = string.lower
        pre_window = []
        post_window = []
        _f.seek(position, 0)

        for i in range(size / 2):
            pre_window.insert(0, lcase(ioutils.wordRead(_f, -1)))

        _f.seek(position, 0)  ## return to the original position
        temp = ioutils.wordRead(_f, 1)  ## skip the target word

        for i in range(size / 2):
            post_window.append(lcase(ioutils.wordRead(_f, 1)))

        self._window = pre_window + post_window


def sumVectors(tDict, wDict):
    for key,val in wDict.items():
        if tDict.has_key(key):
            tDict[key] += val
        else:
            tDict[key] = val
    return tDict

##
##  function:  findAppearances
##  parameters:
##      _f:  a file object
##      word:  the target word
##      windowSize:  the size of the context window
##      localAppearances:  a list of TargetAppearance objects
##  returns:
##      a list of TargetAppearance objects
##

def findAppearances(_f, word, windowSize, localAppearances):
    positions = []
    lcase = string.lower
    _f.seek(0)
    tempWord = ioutils.wordRead(_f, 1)
    while tempWord != 'unk':
        if lcase(tempWord) == word:
            numBytes = len(tempWord) + 1
            positions.append(_f.tell() - numBytes)
        tempWord = ioutils.wordRead(_f, 1)
    if positions:
        for position in positions:
            localAppearances.append(TargetAppearance(_f, position, windowSize))
    return localAppearances

def count(wordList, currFreqCount):
    lower = string.lower
    for word in wordList:
        if not currFreqCount.has_key(word):
            currFreqCount[lower(word)] = 1
        else:
            currFreqCount[lower(word)] += 1
    return currFreqCount

def analyzeLocalDistribution(_f, word, windowSize, localApps):
    localContextFrequencyCount = {}
    if isinstance(localApps[0], TargetAppearance):
        for app in localApps:
            localContextFrequencyCount = count(app.getWindow(),
                                               localContextFrequencyCount)
    elif isinstance(localApps[0], types.StringType):
        localContextFrequencyCount = count(localApps,
                                           localContextFrequencyCount)
    ## return a dictionary of {word: count}
    return localContextFrequencyCount

def reverseDictionary(localD):
    bucket = {}
    for key,val in localD.items():
        if not bucket.has_key(val):
            bucket[val] = []
        bucket[val].append(key)
    return bucket

def freqBasedLocalSelection(currFreqCount, maxDimensions):
    stopWordList = ['a', 'was', 'm', 'an', 'and', 'by',
                    'for', 'of', 'the', 'to', 'with', 'unk']
    returnList = []
    ##  create a bucket dictionary of {frequency:[wordList]}
    ##  then pick out of it the words in decreasing order
    ##  of frequency
    bucket = reverseDictionary(currFreqCount)
    freqs = bucket.keys()
    freqs.sort()
    freqs.reverse()
    for freq in freqs:
        words = bucket[freq]
        for word in words:
            if (word not in stopWordList) and (len(returnList) < maxDimensions):
                returnList.append(word)
    return returnList

def createWordVector2(_f, _windowSize, _featureList):
    ##  findAppearances2 now will take a list of words to find.
    ##  it will return a dictionary of word: [list of featureAppearances]
    wordVectorDictionary = {}
    wordVectorDictionary = findAppearances2(_f, _featureList, _windowSize,
                                            wordVectorDictionary)

##  returns a wordVectorDictionary for a single document

def createWordVector(_f, _windowSize, _featureList):
    wordVectorDictionary = {}
    for feature in _featureList:
        tempFreqCount = {}
        tempReturn = {}
        featureAppearances = []
        featureAppearances = findAppearances(_f, feature, windowSize,
                                             featureAppearances)
        if featureAppearances:
            tempFreqCount = analyzeLocalDistribution(_f, feature, _windowSize,
                                                     featureAppearances)
        if tempFreqCount:
            for key,val in tempFreqCount.items():
                if key in _featureList:
                    tempReturn[key] = val
        wordVectorDictionary[feature] = tempReturn
    return wordVectorDictionary

##main starts here

def main(fileNames, target='bank'):
    maxFeatures = 10
    windowSize = 20

    freqCount = {}
    targetAppearances = []
    wordVectors = {}
    
    ##
    ##  Choose featureset by analyzing data.
    ##  First go through dataset and create a list of
    ##  TargetAppearance objects
    ##
    
    #filePathPrefix = basedir #'.'
    #try:
    #    os.chdir(filePathPrefix)
    #except OSError, e:
    #    print e
    #    
    #fileNames = os.listdir(os.curdir)
    
    ##
    ##  perform the analysis for each datafile in the directory
    ##  during this step we also collect all the TargetAppearance
    ##  objects and contextWindows
    ##
    startTime = time.time()
    for file in fileNames:
        if not file.endswith('.txt'): continue
        print 'opening file:  ', file
        f = open(file, 'r')
        targetAppearances = findAppearances(f, target, windowSize,
                                            targetAppearances)
        f.close()      ##  play nice with others...
    
    stopTime = time.time()
    print ('**Training Phase --> datafile analysis time:  %.3f seconds.' %
           (stopTime - startTime))
    print ('**Training Phase --> found ', len(targetAppearances),
           ' instances of target word:  ', target)
    ##  once we have analyzed all the data files, we analyze to choose
    ##  the features (# of dimensions) of the word vector space

    freqCount = analyzeLocalDistribution(f, target, windowSize,
                                         targetAppearances)

    ##  freqList is a purely frequency driven selection
    if freqCount:
        featureList = freqBasedLocalSelection(freqCount, maxFeatures)
    else:
        print 'No occcurrences of target word:  ', target, '.'

    ##
    ##  word vector creation
    ##

    startTime = time.time()
    for file in fileNames:
        if not file.endswith('.txt'): continue
        tempWordVectors = {}
        f = open(file, 'r')
        print 'wordVector:  opening ', file
        ##  derive the word vectors for that file
        tempWordVectors = createWordVector(f, windowSize, featureList)
        f.close()
        ##  add the resulting vectors to our total
        if tempWordVectors:
            if wordVectors:
                for key,val in tempWordVectors.items():
                    sumVectors(wordVectors[str(key)],
                               tempWordVectors[str(key)])
            else:
                wordVectors = tempWordVectors
  
    stopTime = time.time()
    print ('**Training Phase --> word vector creation time:  %.3f seconds.' %
           (stopTime - startTime))

    ##
    ##  context vector creation
    ##

    for tA in targetAppearances:
        tA.setContextVector(wordVectors)

    ##
    ##  sense cluster creation
    ##
    print '**Training Phase --> sense clustering'
    senses = []
    senses = cluster.cluster(targetAppearances)

    ###################################
    ##
    ##  testing phase
    ##
    ###################################

    tempWordVectors = {}
    testWordVectors = {}
    testAppearances = []
    startTime = time.time()
    for file in fileNames:
        if not file.endswith('.tst'): continue
        print 'opening file:  ', file
        f = open(file, 'r')
        ##  first find the appearances of the target word in the text
        testAppearances = findAppearances(f, target, windowSize,
                                          testAppearances)
        tempWordVectors = createWordVector(f, windowSize, featureList)
        f.close()      ##  play nice with others...
        if tempWordVectors:
            if wordVectors:
                for key,val in tempWordVectors.items():
                    testWordVectors = sumVectors(testWordVectors[str(key)],
                                                 tempWordVectors[str(key)])
    stopTime = time.time()

    print ('**Testing Phase --> file analysis time:  %.3f seconds.' %
           (stopTime - startTime))

    ##
    ##  context vector creation
    ##

    for tA in testAppearances:
        tA.setContextVector(wordVectors)

if __name__ == '__main__':
    import nltk.corpus
    file = os.path.join(nltk.corpus.get_basedir(), 'gutenberg',
                        'milton-paradise.txt')
    main([file])
