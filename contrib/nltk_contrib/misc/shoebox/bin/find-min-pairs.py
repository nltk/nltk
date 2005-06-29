# --------------------------------------------------------
# AUTHOR: Stuart Robinson
# DATE:   2 May 2005
# DESC:   This script finds all latent minimal pairs in a
#         Shoebox dictionary file.
# --------------------------------------------------------

import sys, re
from shoebox.standardformat import StandardFormatFileParser

def handle_options() :
    try :
        return sys.argv[1]
    except :
        print "Usage: %s <FILEPATH>" % sys.argv[0]
        sys.exit(0)

def extract_words(filepath) :
    words = []
    sffp = StandardFormatFileParser(filepath)
    sff = sffp.parse()
    for e in sff.getEntries() :
        hf = e.getHeadField()
        words.append(hf[1])
    return words

def sortWordsByLength(words) :
    wordLengths = {}
    for w in words :
        wl = len(w)
        if not wordLengths.has_key(wl) :
            wordLengths[wl] = []
        wordLengths[wl].append(w)
    return wordLengths

def findMinPairs(wordsByLength) :
    for l in wordsByLength.keys() :
        words1 = wordsByLength[l]
        words2 = wordsByLength[l]
        for w1 in words1 :
            for w2 in words2 :
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
                    if diffCount > 1 :
                        continue
                if diffCount == 1 :
                    print "%s/%s:%s/%s" % (diffChar1, diffChar2, w1, w2)
            words1.remove(w1)

def main() :
    filepath = handle_options()
    words = extract_words(filepath)
    wordsByLength = sortWordsByLength(words)
    minPairs = findMinPairs(wordsByLength)

main()
