# --------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   2 May 2005
# DESC:   ???
# --------------------------------------------------------

import sys, re
from shoebox.standardformat import StandardFormatFileParser

def extractWords(f) :
    words = []
    fp = StandardFormatFileParser(f)
    sf = fp.parse()
    for e in sf.getEntries() :
        fri = e.getFieldValuesByFieldMarkerAsString("fri")
        words.append(fri)
    return words

def sortWordsByLength(words) :
    wordLengths = {}
    for w in words :
        wl = len(w)
        if not wordLengths.has_key(wl) :
            wordLengths[wl] = []
        wordLengths[wl].append(w)
    return wordLengths

def findMinPairs(words) :
    wordsByLength = sortWordsByLength(words)
    for l in wordsByLength.keys() :
        words = wordsByLength[l]
        for w1 in words :
            for w2 in words :
                i = 0
                diffCount = 0
                diffChar1 = ''
                diffChar2 = ''
                while i < l :
                    if not w1[i] == w2[i] :
                        diffCount = diffCount + 1
                        diffChar1 = w1[i]
                        diffChar2 = w2[i]
                    i = i + 1
                if diffCount == 1 :
                    print "%s/%s:%s/%s" % (diffChar1, diffChar2, w1, w2)

def main() :
    filepath = sys.argv[1]
    words = extractWords(filepath)
    minPairs = findMinPairs(words)

main()
