#!/usr/bin/python
# -*- coding: utf-8 -*- 
# Sets the encoding to utf-8 to avoid problems with æøå
import string
import re
import os

syllable_path = "files", "specialSyllables_no"

syllablesInFile = {}

#The last 7, starting at "ai", are the Norwegian diphthongs.
subSyllableIf = ["ai","au","oy","oi","ui","øy"]
for item in subSyllableIf:
    item = item.decode("utf-8")
#Tok bort "en$" og "et$"; må forskes mer på.


#Syllables who are not counted as one, but should be.
#Between two vowels that do not form a diphthong.
addSyllableIf = ["oa", "io", "eo", "ia", "ee", "ie"]
for item in addSyllableIf:
    item = item.decode("utf-8")

# Compile the regular expressions in aubSyllableIf
for i in range(len(subSyllableIf)):
    subSyllableIf[i] = re.compile(subSyllableIf[i])
for i in range(len(addSyllableIf)):
    addSyllableIf[i] = re.compile(addSyllableIf[i])

def _stripWord(word):
    return word.strip().lower()

# Read our syllable override file and add to the syllablesInFile list
in_syll = open(syllable_path)
for line in in_syll.xreadlines():
    line = line.strip()
    if line:
        toks = line.split()
        assert len(toks) == 2
        syllablesInFile[_stripWord(unicode(toks[0],"latin-1").encode("utf-8"))] = int(toks[1])
in_syll.close()

def count(word):

    word = unicode(word,"utf-8").encode("utf-8")
    word = _stripWord(word)

    if not word:
        return 0

    # Check for a cached syllable count
    count = syllablesInFile.get(word, -1)
    
    if count > 0:
        return count

    # Count vowel groups
    count = 0
    prev_was_vowel = 0
    vowels = [u"a", u"e", u"i", u"o", u"u", u"y", u"æ", u"ø", u"å"]
    #for vow in vowels:
        #vow = vow.decode("utf-8")
    for c in word.decode("utf-8"):
        is_vowel = c in vowels
        if is_vowel and not prev_was_vowel:
            count += 1
        prev_was_vowel = is_vowel

    # Add & subtract syllables
    for r in addSyllableIf:
        if r.search(word):
            count += 1
    for r in subSyllableIf:
        if r.search(word):
            count -= 1

    # Cache the syllable count
    syllablesInFile[word] = count
    
#    Add syllable to file
#    if count > 0:
#        file = open(syllable_path, "a")
#        file.write( unicode(word,"utf-8").encode("latin-1") + " " + str(count) + "\n")
#        file.close()

    return count
