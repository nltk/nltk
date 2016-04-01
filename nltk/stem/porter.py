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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301
# USA
#
# This software is maintained by Vivake (vivakeATomniscia.org) and is available at:
#     http://www.omniscia.org/~vivake/python/PorterStemmer.py
#
# Additional modifications were made to incorporate this module into
# NLTK.  All such modifications are marked with "--NLTK--".  The NLTK
# version of this module is maintained by NLTK developers,
# and is available via http://nltk.org/
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

only differing from it at the points marked --DEPARTURE-- and --NEW--
below.

For a more faithful version of the Porter algorithm, see

    http://www.tartarus.org/~martin/PorterStemmer/

Later additions:

   June 2000

   The 'l' of the 'logi' -> 'log' rule is put with the stem, so that
   short stems like 'geo' 'theo' etc work like 'archaeo' 'philo' etc.

   This follows a suggestion of Barry Wilkins, research student at
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
nltk.  All such modifications are marked with \"--NLTK--\".
"""

from __future__ import print_function, unicode_literals

## --NLTK--
## Declare this module's documentation format.
__docformat__ = 'plaintext'

import re

from nltk.stem.api import StemmerI
from nltk.compat import python_2_unicode_compatible

@python_2_unicode_compatible
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
    # Note that only lower case sequences are stemmed. Forcing to lower case
    # should be done before stem(...) is called.

    def __init__(self):

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

        self.vowels = frozenset(['a', 'e', 'i', 'o', 'u'])

    def _cons(self, word, i):
        """cons(i) is TRUE <=> b[i] is a consonant."""
        if word[i] in self.vowels:
            return False
        if word[i] == 'y':
            if i == 0:
                return True
            else:
                return (not self._cons(word, i - 1))
        return True

    def _m(self, word, j):
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
        i = 0
        while True:
            if i > j:
                return n
            if not self._cons(word, i):
                break
            i = i + 1
        i = i + 1

        while True:
            while True:
                if i > j:
                    return n
                if self._cons(word, i):
                    break
                i = i + 1
            i = i + 1
            n = n + 1

            while True:
                if i > j:
                    return n
                if not self._cons(word, i):
                    break
                i = i + 1
            i = i + 1

    def _vowelinstem(self, stem):
        """vowelinstem(stem) is TRUE <=> stem contains a vowel"""
        for i in range(len(stem)):
            if not self._cons(stem, i):
                return True
        return False

    def _doublec(self, word):
        """doublec(word) is TRUE <=> word ends with a double consonant"""
        if len(word) < 2:
            return False
        if (word[-1] != word[-2]):
            return False
        return self._cons(word, len(word)-1)

    def _cvc(self, word, i):
        """cvc(i) is TRUE <=>

        a) ( --NEW--) i == 1, and word[0] word[1] is vowel consonant, or

        b) word[i - 2], word[i - 1], word[i] has the form consonant -
           vowel - consonant and also if the second c is not w, x or y. this
           is used when trying to restore an e at the end of a short word.
           e.g.

               cav(e), lov(e), hop(e), crim(e), but
               snow, box, tray.
        """
        if i == 0: return False  # i == 0 never happens perhaps
        if i == 1: return (not self._cons(word, 0) and self._cons(word, 1))
        if not self._cons(word, i) or self._cons(word, i-1) or not self._cons(word, i-2): return False

        ch = word[i]
        if ch == 'w' or ch == 'x' or ch == 'y':
            return False

        return True

    def _step1ab(self, word):
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
        if word[-1] == 's':
            if word.endswith("sses"):
                word = word[:-2]
            elif word.endswith("ies"):
                if len(word) == 4:
                    word = word[:-1]
                # this line extends the original algorithm, so that
                # 'flies'->'fli' but 'dies'->'die' etc
                else:
                    word = word[:-2]
            elif word[-2] != 's':
                word = word[:-1]

        ed_or_ing_trimmed = False
        if word.endswith("ied"):
            if len(word) == 4:
                word = word[:-1]
            else:
                word = word[:-2]
        # this line extends the original algorithm, so that
        # 'spied'->'spi' but 'died'->'die' etc

        elif word.endswith("eed"):
            if self._m(word, len(word)-4) > 0:
                word = word[:-1]


        elif word.endswith("ed") and self._vowelinstem(word[:-2]):
            word = word[:-2]
            ed_or_ing_trimmed = True
        elif word.endswith("ing") and self._vowelinstem(word[:-3]):
            word = word[:-3]
            ed_or_ing_trimmed = True

        if ed_or_ing_trimmed:
            if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
                word += 'e'
            elif self._doublec(word):
                if word[-1] not in ['l', 's', 'z']:
                    word = word[:-1]
            elif (self._m(word, len(word)-1) == 1 and self._cvc(word, len(word)-1)):
                word += 'e'

        return word

    def _step1c(self, word):
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
        if word[-1] == 'y' and len(word) > 2 and self._cons(word, len(word) - 2):
            return word[:-1] + 'i'
        else:
            return word

    def _step2(self, word):
        """step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give m() > 0.
        """
        if len(word) <= 1: # Only possible at this stage given unusual inputs to stem_word like 'oed'
            return word

        ch = word[-2]

        if ch == 'a':
            if word.endswith("ational"):
                return word[:-7] + "ate" if self._m(word, len(word)-8) > 0 else word
            elif word.endswith("tional"):
                return word[:-2] if self._m(word, len(word)-7) > 0 else word
            else:
                return word
        elif ch == 'c':
            if word.endswith("enci"):
                return word[:-4] + "ence" if self._m(word, len(word)-5) > 0 else word
            elif word.endswith("anci"):
                return word[:-4] + "ance" if self._m(word, len(word)-5) > 0 else word
            else:
                return word
        elif ch == 'e':
            if word.endswith("izer"):
                return word[:-1] if self._m(word, len(word)-5) > 0 else word
            else:
                return word
        elif ch == 'l':
            if word.endswith("bli"):
                return word[:-3] + "ble" if self._m(word, len(word)-4) > 0 else word # --DEPARTURE--
            # To match the published algorithm, replace "bli" with "abli" and "ble" with "able"
            elif word.endswith("alli"):
                # --NEW--
                if self._m(word, len(word)-5) > 0:
                    word = word[:-2]
                    return self._step2(word)
                else:
                    return word
            elif word.endswith("fulli"):
                return word[:-2] if self._m(word, len(word)-6) else word # --NEW--
            elif word.endswith("entli"):
                return word[:-2] if self._m(word, len(word)-6) else word
            elif word.endswith("eli"):
                return word[:-2] if self._m(word, len(word)-4) else word
            elif word.endswith("ousli"):
                return word[:-2] if self._m(word, len(word)-6) else word
            else:
                return word
        elif ch == 'o':
            if word.endswith("ization"):
                return word[:-7] + "ize" if self._m(word, len(word)-8) else word
            elif word.endswith("ation"):
                return word[:-5] + "ate" if self._m(word, len(word)-6) else word
            elif word.endswith("ator"):
                return word[:-4] + "ate" if self._m(word, len(word)-5) else word
            else:
                return word
        elif ch == 's':
            if word.endswith("alism"):
                return word[:-3] if self._m(word, len(word)-6) else word
            elif word.endswith("ness"):
                if word.endswith("iveness"):
                    return word[:-4] if self._m(word, len(word)-8) else word
                elif word.endswith("fulness"):
                    return word[:-4] if self._m(word, len(word)-8) else word
                elif word.endswith("ousness"):
                    return word[:-4] if self._m(word, len(word)-8) else word
                else:
                    return word
            else:
                return word
        elif ch == 't':
            if word.endswith("aliti"):
                return word[:-3] if self._m(word, len(word)-6) else word
            elif word.endswith("iviti"):
                return word[:-5] + "ive" if self._m(word, len(word)-6) else word
            elif word.endswith("biliti"):
                return word[:-6] + "ble" if self._m(word, len(word)-7) else word
            else:
                return word
        elif ch == 'g': # --DEPARTURE--
            if word.endswith("logi"):
                return word[:-1] if self._m(word, len(word) - 4) else word # --NEW-- (Barry Wilkins)
            # To match the published algorithm, pass len(word)-5 to _m instead of len(word)-4
            else:
                return word

        else:
            return word

    def _step3(self, word):
        """step3() deals with -ic-, -full, -ness etc. similar strategy to step2."""

        ch = word[-1]

        if ch == 'e':
            if word.endswith("icate"):
                return word[:-3] if self._m(word, len(word)-6) else word
            elif word.endswith("ative"):
                return word[:-5] if self._m(word, len(word)-6) else word
            elif word.endswith("alize"):
                return word[:-3] if self._m(word, len(word)-6) else word
            else:
                return word
        elif ch == 'i':
            if word.endswith("iciti"):
                return word[:-3] if self._m(word, len(word)-6) else word
            else:
                return word
        elif ch == 'l':
            if word.endswith("ical"):
                return word[:-2] if self._m(word, len(word)-5) else word
            elif word.endswith("ful"):
                return word[:-3] if self._m(word, len(word)-4) else word
            else:
                return word
        elif ch == 's':
            if word.endswith("ness"):
                return word[:-4] if self._m(word, len(word)-5) else word
            else:
                return word

        else:
            return word

    def _step4(self, word):
        """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""

        if len(word) <= 1: # Only possible at this stage given unusual inputs to stem_word like 'oed'
            return word

        ch = word[-2]

        if ch == 'a':
            if word.endswith("al"):
                return word[:-2] if self._m(word, len(word)-3) > 1 else word
            else:
                return word
        elif ch == 'c':
            if word.endswith("ance"):
                return word[:-4] if self._m(word, len(word)-5) > 1 else word
            elif word.endswith("ence"):
                return word[:-4] if self._m(word, len(word)-5) > 1 else word
            else:
                return word
        elif ch == 'e':
            if word.endswith("er"):
                return word[:-2] if self._m(word, len(word)-3) > 1 else word
            else:
                return word
        elif ch == 'i':
            if word.endswith("ic"):
                return word[:-2] if self._m(word, len(word)-3) > 1 else word
            else:
                return word
        elif ch == 'l':
            if word.endswith("able"):
                return word[:-4] if self._m(word, len(word)-5) > 1 else word
            elif word.endswith("ible"):
                return word[:-4] if self._m(word, len(word)-5) > 1 else word
            else:
                return word
        elif ch == 'n':
            if word.endswith("ant"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            elif word.endswith("ement"):
                return word[:-5] if self._m(word, len(word)-6) > 1 else word
            elif word.endswith("ment"):
                return word[:-4] if self._m(word, len(word)-5) > 1 else word
            elif word.endswith("ent"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        elif ch == 'o':
            if word.endswith("sion") or word.endswith("tion"): # slightly different logic to all the other cases
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            elif word.endswith("ou"):
                return word[:-2] if self._m(word, len(word)-3) > 1 else word
            else:
                return word
        elif ch == 's':
            if word.endswith("ism"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        elif ch == 't':
            if word.endswith("ate"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            elif word.endswith("iti"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        elif ch == 'u':
            if word.endswith("ous"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        elif ch == 'v':
            if word.endswith("ive"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        elif ch == 'z':
            if word.endswith("ize"):
                return word[:-3] if self._m(word, len(word)-4) > 1 else word
            else:
                return word
        else:
            return word

    def _step5(self, word):
        """step5() removes a final -e if m() > 1, and changes -ll to -l if
        m() > 1.
        """
        if word[-1] == 'e':
            a = self._m(word, len(word)-1)
            if a > 1 or (a == 1 and not self._cvc(word, len(word)-2)):
                word = word[:-1]
        if word.endswith('ll') and self._m(word, len(word)-1) > 1:
            word = word[:-1]

        return word

    def stem_word(self, p, i=0, j=None):
        """
        Returns the stem of p, or, if i and j are given, the stem of p[i:j+1].
        """
        ## --NLTK--
        if j is None and i == 0:
            word = p
        else:
            if j is None:
                j = len(p) - 1
            word = p[i:j+1]

        if word in self.pool:
            return self.pool[word]

        if len(word) <= 2:
            return word # --DEPARTURE--
        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.

        word = self._step1ab(word)
        word = self._step1c(word)
        word = self._step2(word)
        word = self._step3(word)
        word = self._step4(word)
        word = self._step5(word)
        return word

    def _adjust_case(self, word, stem):
        lower = word.lower()

        ret = ""
        for x in range(len(stem)):
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
        return self._adjust_case(word, stem)

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
#            with open(f, 'r') as infile:
#                while 1:
#                    w = infile.readline()
#                    if w == '':
#                        break
#                    w = w[:-1]
#                    print(p.stem(w))

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
    print('-Original-'.center(70).replace(' ', '*').replace('-', ' '))
    print(original)
    print('-Results-'.center(70).replace(' ', '*').replace('-', ' '))
    print(results)
    print('*'*70)

##--NLTK--


