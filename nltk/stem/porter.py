# Copyright (c) 2002 Vivake Gupta (vivakeATomniscia.org).  All rights reserved.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# This software is maintained by Vivake (vivakeATomniscia.org) and is available at:
#     http://www.omniscia.org/~vivake/python/PorterStemmer.py
#
# Additional modifications were made to incorporate this module into
# NLTK.  All such modifications are marked with "--NLTK--".  The NLTK
# version of this module is maintained by NLTK developers,
# and is available via http://www.nltk.org/
#
# GNU Linking Exception:
# Using this module statically or dynamically with other modules is
# making a combined work based on this module. Thus, the terms and
# conditions of the GNU General Public License cover the whole combination.
# As a special exception, the copyright holders of this module give
# you permission to combine this module with independent modules to
# produce an executable program, regardless of the license terms of these
# independent modules, and to copy and distribute the resulting
# program under terms of your choice, provided that you also meet,
# for each linked independent module, the terms and conditions of
# the license of that module. An independent module is a module which
# is not derived from or based on this module. If you modify this module,
# you may extend this exception to your version of the module, but you
# are not obliged to do so. If you do not wish to do so, delete this
# exception statement from your version.

"""
Porter Stemmer

This is the Porter stemming algorithm, ported to Python from the
version coded up in ANSI C by the author. It follows the algorithm
presented in

Porter, M. "An algorithm for suffix stripping." Program 14.3 (1980): 130-137.

only differing from it at the points maked --DEPARTURE-- and --NEW--
below.

For a more faithful version of the Porter algorithm, see

    http://www.tartarus.org/~martin/PorterStemmer/

Later additions:

   June 2000

   The 'l' of the 'logi' -> 'log' rule is put with the stem, so that
   short stems like 'geo' 'theo' etc work like 'archaeo' 'philo' etc.

   This follows a suggestion of Barry Wilkins, reasearch student at
   Birmingham.


   February 2000

   the cvc test for not dropping final -e now looks after vc at the
   beginning of a word, so are, eve, ice, ore, use keep final -e. In this
   test c is any consonant, including w, x and y. This extension was
   suggested by Chris Emerson.

   -fully    -> -ful   treated like  -fulness -> -ful, and
   -tionally -> -tion  treated like  -tional  -> -tion

   both in Step 2. These were suggested by Hiranmay Ghosh, of New Delhi.

   Invariants proceed, succeed, exceed. Also suggested by Hiranmay Ghosh.

Additional modifications were made to incorperate this module into
nltk.  All such modifications are marked with \"--NLTK--\".  The nltk
version of this module is maintained by the NLTK developers, and is
available from <http://nltk.sourceforge.net>
"""

## --NLTK--
## Declare this module's documentation format.
__docformat__ = 'plaintext'

import sys
import re

## --NLTK--
## Import the nltk.stemmer module, which defines the stemmer interface
from api import StemmerI

class PorterStemmer(StemmerI):

    ## --NLTK--
    ## Add a module docstring
    """
    A word stemmer based on the Porter stemming algorithm.

        Porter, M. \"An algorithm for suffix stripping.\"
        Program 14.3 (1980): 130-137.

    A few minor modifications have been made to Porter's basic
    algorithm.  See the source code of this module for more
    information.

    The Porter Stemmer requires that all tokens have string types.
    """

    # The main part of the stemming algorithm starts here.
    # b is a buffer holding a word to be stemmed. The letters are in b[k0],
    # b[k0+1] ... ending at b[k]. In fact k0 = 0 in this demo program. k is
    # readjusted downwards as the stemming progresses. Zero termination is
    # not in fact used in the algorithm.
    # Note that only lower case sequences are stemmed. Forcing to lower case
    # should be done before stem(...) is called.

    def __init__(self):

        self.b = ""  # buffer for word to be stemmed
        self.k = 0
        self.k0 = 0
        self.j = 0   # j is a general offset into the string

        ## --NEW--
        ## This is a table of irregular forms. It is quite short, but still
        ## reflects the errors actually drawn to Martin Porter's attention over
        ## a 20 year period!
        ##
        ## Extend it as necessary.
        ##
        ## The form of the table is:
        ##  {
        ##  "p1" : ["s11","s12","s13", ... ],
        ##  "p2" : ["s21","s22","s23", ... ],
        ##  ...
        ##  "pn" : ["sn1","sn2","sn3", ... ]
        ##  }
        ##
        ## String sij is mapped to paradigm form pi, and the main stemming
        ## process is then bypassed.

        irregular_forms = {
            "sky" :     ["sky", "skies"],
            "die" :     ["dying"],
            "lie" :     ["lying"],
            "tie" :     ["tying"],
            "news" :    ["news"],
            "inning" :  ["innings", "inning"],
            "outing" :  ["outings", "outing"],
            "canning" : ["cannings", "canning"],
            "howe" :    ["howe"],

            # --NEW--
            "proceed" : ["proceed"],
            "exceed"  : ["exceed"],
            "succeed" : ["succeed"], # Hiranmay Ghosh
            }

        self.pool = {}
        for key in irregular_forms:
            for val in irregular_forms[key]:
                self.pool[val] = key

    def cons(self, i):
        """cons(i) is TRUE <=> b[i] is a consonant."""
        if self.b[i] == 'a' or self.b[i] == 'e' or self.b[i] == 'i' or self.b[i] == 'o' or self.b[i] == 'u':
            return 0
        if self.b[i] == 'y':
            if i == self.k0:
                return 1
            else:
                return (not self.cons(i - 1))
        return 1

    def m(self):
        """m() measures the number of consonant sequences between k0 and j.
        if c is a consonant sequence and v a vowel sequence, and <..>
        indicates arbitrary presence,

           <c><v>       gives 0
           <c>vc<v>     gives 1
           <c>vcvc<v>   gives 2
           <c>vcvcvc<v> gives 3
           ....
        """
        n = 0
        i = self.k0
        while 1:
            if i > self.j:
                return n
            if not self.cons(i):
                break
            i = i + 1
        i = i + 1
        while 1:
            while 1:
                if i > self.j:
                    return n
                if self.cons(i):
                    break
                i = i + 1
            i = i + 1
            n = n + 1
            while 1:
                if i > self.j:
                    return n
                if not self.cons(i):
                    break
                i = i + 1
            i = i + 1

    def vowelinstem(self):
        """vowelinstem() is TRUE <=> k0,...j contains a vowel"""
        for i in range(self.k0, self.j + 1):
            if not self.cons(i):
                return 1
        return 0

    def doublec(self, j):
        """doublec(j) is TRUE <=> j,(j-1) contain a double consonant."""
        if j < (self.k0 + 1):
            return 0
        if (self.b[j] != self.b[j-1]):
            return 0
        return self.cons(j)

    def cvc(self, i):
        """cvc(i) is TRUE <=>

        a) ( --NEW--) i == 1, and p[0] p[1] is vowel consonant, or

        b) p[i - 2], p[i - 1], p[i] has the form consonant -
           vowel - consonant and also if the second c is not w, x or y. this
           is used when trying to restore an e at the end of a short word.
           e.g.

               cav(e), lov(e), hop(e), crim(e), but
               snow, box, tray.
        """
        if i == 0: return 0  # i == 0 never happens perhaps
        if i == 1: return (not self.cons(0) and self.cons(1))
        if not self.cons(i) or self.cons(i-1) or not self.cons(i-2): return 0

        ch = self.b[i]
        if ch == 'w' or ch == 'x' or ch == 'y':
            return 0

        return 1

    def ends(self, s):
        """ends(s) is TRUE <=> k0,...k ends with the string s."""
        length = len(s)
        if s[length - 1] != self.b[self.k]: # tiny speed-up
            return 0
        if length > (self.k - self.k0 + 1):
            return 0
        if self.b[self.k-length+1:self.k+1] != s:
            return 0
        self.j = self.k - length
        return 1

    def setto(self, s):
        """setto(s) sets (j+1),...k to the characters in the string s, readjusting k."""
        length = len(s)
        self.b = self.b[:self.j+1] + s + self.b[self.j+length+1:]
        self.k = self.j + length

    def r(self, s):
        """r(s) is used further down."""
        if self.m() > 0:
            self.setto(s)

    def step1ab(self):
        """step1ab() gets rid of plurals and -ed or -ing. e.g.

           caresses  ->  caress
           ponies    ->  poni
           sties     ->  sti
           tie       ->  tie        (--NEW--: see below)
           caress    ->  caress
           cats      ->  cat

           feed      ->  feed
           agreed    ->  agree
           disabled  ->  disable

           matting   ->  mat
           mating    ->  mate
           meeting   ->  meet
           milling   ->  mill
           messing   ->  mess

           meetings  ->  meet
        """
        if self.b[self.k] == 's':
            if self.ends("sses"):
                self.k = self.k - 2
            elif self.ends("ies"):
                if self.j == 0:
                    self.k = self.k - 1
                # this line extends the original algorithm, so that
                # 'flies'->'fli' but 'dies'->'die' etc
                else:
                    self.k = self.k - 2
            elif self.b[self.k - 1] != 's':
                self.k = self.k - 1

        if self.ends("ied"):
            if self.j == 0:
                self.k = self.k - 1
            else:
                self.k = self.k - 2
        # this line extends the original algorithm, so that
        # 'spied'->'spi' but 'died'->'die' etc

        elif self.ends("eed"):
            if self.m() > 0:
                self.k = self.k - 1
        elif (self.ends("ed") or self.ends("ing")) and self.vowelinstem():
            self.k = self.j
            if self.ends("at"):   self.setto("ate")
            elif self.ends("bl"): self.setto("ble")
            elif self.ends("iz"): self.setto("ize")
            elif self.doublec(self.k):
                self.k = self.k - 1
                ch = self.b[self.k]
                if ch == 'l' or ch == 's' or ch == 'z':
                    self.k = self.k + 1
            elif (self.m() == 1 and self.cvc(self.k)):
                self.setto("e")

    def step1c(self):
        """step1c() turns terminal y to i when there is another vowel in the stem.
        --NEW--: This has been modified from the original Porter algorithm so that y->i
        is only done when y is preceded by a consonant, but not if the stem
        is only a single consonant, i.e.

           (*c and not c) Y -> I

        So 'happy' -> 'happi', but
          'enjoy' -> 'enjoy'  etc

        This is a much better rule. Formerly 'enjoy'->'enjoi' and 'enjoyment'->
        'enjoy'. Step 1c is perhaps done too soon; but with this modification that
        no longer really matters.

        Also, the removal of the vowelinstem(z) condition means that 'spy', 'fly',
        'try' ... stem to 'spi', 'fli', 'tri' and conflate with 'spied', 'tried',
        'flies' ...
        """
        if self.ends("y") and self.j > 0 and self.cons(self.k - 1):
            self.b = self.b[:self.k] + 'i' + self.b[self.k+1:]

    def step2(self):
        """step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give m() > 0.
        """
        if self.b[self.k - 1] == 'a':
            if self.ends("ational"):   self.r("ate")
            elif self.ends("tional"):  self.r("tion")
        elif self.b[self.k - 1] == 'c':
            if self.ends("enci"):      self.r("ence")
            elif self.ends("anci"):    self.r("ance")
        elif self.b[self.k - 1] == 'e':
            if self.ends("izer"):      self.r("ize")
        elif self.b[self.k - 1] == 'l':
            if self.ends("bli"):       self.r("ble") # --DEPARTURE--
            # To match the published algorithm, replace this phrase with
            #   if self.ends("abli"):      self.r("able")
            elif self.ends("alli"):
                if self.m() > 0:                     # --NEW--
                    self.setto("al")
                    self.step2()
            elif self.ends("fulli"):   self.r("ful") # --NEW--
            elif self.ends("entli"):   self.r("ent")
            elif self.ends("eli"):     self.r("e")
            elif self.ends("ousli"):   self.r("ous")
        elif self.b[self.k - 1] == 'o':
            if self.ends("ization"):   self.r("ize")
            elif self.ends("ation"):   self.r("ate")
            elif self.ends("ator"):    self.r("ate")
        elif self.b[self.k - 1] == 's':
            if self.ends("alism"):     self.r("al")
            elif self.ends("iveness"): self.r("ive")
            elif self.ends("fulness"): self.r("ful")
            elif self.ends("ousness"): self.r("ous")
        elif self.b[self.k - 1] == 't':
            if self.ends("aliti"):     self.r("al")
            elif self.ends("iviti"):   self.r("ive")
            elif self.ends("biliti"):  self.r("ble")
        elif self.b[self.k - 1] == 'g': # --DEPARTURE--
            if self.ends("logi"):
                self.j = self.j + 1     # --NEW-- (Barry Wilkins)
                self.r("og")
        # To match the published algorithm, delete this phrase

    def step3(self):
        """step3() dels with -ic-, -full, -ness etc. similar strategy to step2."""
        if self.b[self.k] == 'e':
            if self.ends("icate"):     self.r("ic")
            elif self.ends("ative"):   self.r("")
            elif self.ends("alize"):   self.r("al")
        elif self.b[self.k] == 'i':
            if self.ends("iciti"):     self.r("ic")
        elif self.b[self.k] == 'l':
            if self.ends("ical"):      self.r("ic")
            elif self.ends("ful"):     self.r("")
        elif self.b[self.k] == 's':
            if self.ends("ness"):      self.r("")

    def step4(self):
        """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""
        if self.b[self.k - 1] == 'a':
            if self.ends("al"): pass
            else: return
        elif self.b[self.k - 1] == 'c':
            if self.ends("ance"): pass
            elif self.ends("ence"): pass
            else: return
        elif self.b[self.k - 1] == 'e':
            if self.ends("er"): pass
            else: return
        elif self.b[self.k - 1] == 'i':
            if self.ends("ic"): pass
            else: return
        elif self.b[self.k - 1] == 'l':
            if self.ends("able"): pass
            elif self.ends("ible"): pass
            else: return
        elif self.b[self.k - 1] == 'n':
            if self.ends("ant"): pass
            elif self.ends("ement"): pass
            elif self.ends("ment"): pass
            elif self.ends("ent"): pass
            else: return
        elif self.b[self.k - 1] == 'o':
            if self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't'): pass
            elif self.ends("ou"): pass
            # takes care of -ous
            else: return
        elif self.b[self.k - 1] == 's':
            if self.ends("ism"): pass
            else: return
        elif self.b[self.k - 1] == 't':
            if self.ends("ate"): pass
            elif self.ends("iti"): pass
            else: return
        elif self.b[self.k - 1] == 'u':
            if self.ends("ous"): pass
            else: return
        elif self.b[self.k - 1] == 'v':
            if self.ends("ive"): pass
            else: return
        elif self.b[self.k - 1] == 'z':
            if self.ends("ize"): pass
            else: return
        else:
            return
        if self.m() > 1:
            self.k = self.j

    def step5(self):
        """step5() removes a final -e if m() > 1, and changes -ll to -l if
        m() > 1.
        """
        self.j = self.k
        if self.b[self.k] == 'e':
            a = self.m()
            if a > 1 or (a == 1 and not self.cvc(self.k-1)):
                self.k = self.k - 1
        if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
            self.k = self.k -1

    def stem_word(self, p, i=0, j=None):
        """In stem(p,i,j), p is a char pointer, and the string to be stemmed
        is from p[i] to p[j] inclusive. Typically i is zero and j is the
        offset to the last character of a string, (p[j+1] == '\0'). The
        stemmer adjusts the characters p[i] ... p[j] and returns the new
        end-point of the string, k. Stemming never increases word length, so
        i <= k <= j. To turn the stemmer into a module, declare 'stem' as
        extern, and delete the remainder of this file.
        """
        ## --NLTK--
        ## Don't print results as we go (commented out the next line)
        #print p[i:j+1]
        if j is None:
            j = len(p) - 1

        # copy the parameters into statics
        self.b = p
        self.k = j
        self.k0 = i

        if self.b[self.k0:self.k+1] in self.pool:
            return self.pool[self.b[self.k0:self.k+1]]

        if self.k <= self.k0 + 1:
            return self.b # --DEPARTURE--

        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.

        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()
        return self.b[self.k0:self.k+1]

    def adjust_case(self, word, stem):
        lower = word.lower()

        ret = ""
        for x in xrange(len(stem)):
            if lower[x] == stem[x]:
                ret += word[x]
            else:
                ret += stem[x]

        return ret

    ## --NLTK--
    ## Don't use this procedure; we want to work with individual
    ## tokens, instead.  (commented out the following procedure)
    #def stem(self, text):
    #    parts = re.split("(\W+)", text)
    #    numWords = (len(parts) + 1)/2
    #
    #    ret = ""
    #    for i in xrange(numWords):
    #        word = parts[2 * i]
    #        separator = ""
    #        if ((2 * i) + 1) < len(parts):
    #            separator = parts[(2 * i) + 1]
    #
    #        stem = self.stem_word(string.lower(word), 0, len(word) - 1)
    #        ret = ret + self.adjust_case(word, stem)
    #        ret = ret + separator
    #    return ret

    ## --NLTK--
    ## Define a stem() method that implements the StemmerI interface.
    def stem(self, word):
        stem = self.stem_word(word.lower(), 0, len(word) - 1)
        return self.adjust_case(word, stem)

    ## --NLTK--
    ## Add a string representation function
    def __repr__(self):
        return '<PorterStemmer>'

## --NLTK--
## This test procedure isn't applicable.
#if __name__ == '__main__':
#    p = PorterStemmer()
#    if len(sys.argv) > 1:
#        for f in sys.argv[1:]:
#            infile = open(f, 'r')
#            while 1:
#                w = infile.readline()
#                if w == '':
#                    break
#                w = w[:-1]
#                print p.stem(w)

##--NLTK--
## Added a demo() function

def demo():
    """
    A demonstration of the porter stemmer on a sample from
    the Penn Treebank corpus.
    """

    from nltk.corpus import treebank
    from nltk import stem

    stemmer = stem.PorterStemmer()

    orig = []
    stemmed = []
    for item in treebank.files()[:3]:
        for (word, tag) in treebank.tagged_words(item):
            orig.append(word)
            stemmed.append(stemmer.stem(word))

    # Convert the results to a string, and word-wrap them.
    results = ' '.join(stemmed)
    results = re.sub(r"(.{,70})\s", r'\1\n', results+' ').rstrip()

    # Convert the original to a string, and word wrap it.
    original = ' '.join(orig)
    original = re.sub(r"(.{,70})\s", r'\1\n', original+' ').rstrip()

    # Print the results.
    print '-Original-'.center(70).replace(' ', '*').replace('-', ' ')
    print original
    print '-Results-'.center(70).replace(' ', '*').replace('-', ' ')
    print results
    print '*'*70

##--NLTK--


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

