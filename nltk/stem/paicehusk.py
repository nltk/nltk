# Whoosh: Paice-Husk Stemmeing Algorithm
# URL: https://bitbucket.org/mchaput/whoosh/src
#
# Copyright 2011 Matt Chaput. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY MATT CHAPUT ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL MATT CHAPUT OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of Matt Chaput.

"""
Paice-Husk Stemmer

If you just want to use the standard Paice-Husk stemming rules, use the
module's stem()` function::

    paicehusk = PaiceHuskStemmer()
    stemmed_word = paicehusk.stem(word)

If you want to use a custom rule set, read the rules into a string where the
rules are separated by newlines, and instantiate the object with the string,
then use the object's stem method to stem words::

    paicehusk = PaiceHuskStemmer(custom_rule)
    stemmed_word = paicehusk.stem(word)

Guide for custom rules:
    Ending  Intact+  Number (Append|Cont)

    Ending is consist of alphabet (Specifically ending of a word). (a-z)
        - -ment -> tnem
    Intact is denoted by asterisk (*)
    Number is denoted by integer (1 ~ n)
    Append is denoted by plus sign (+)
    Cont is denoted by greater than sign (>)


"""

import re
from collections import defaultdict


class PaiceHuskStemmer(object):
    """
    PaiceHuskStemmer

        >>> from nltk.stem.paicehusk import PaiceHuskStemmer
        >>> st = PaiceHuskStemmer()
        >>> st.stem('maximum')     # Remove "-um" when word is intact
        'maxim'
        >>> st.stem('presumably')  # Don't remove "-um" when word is not intact
        'presum'
        >>> st.stem('multiply')    # No action taken if word ends with "-ply"
        'multiply'
        >>> st.stem('provision')   # Replace "-sion" with "-j" to trigger "j" set of rules
        'provid'
        >>> st.stem('owed')        # Word starting with vowel must contain at least 2 letters
        'ow'
        >>> st.stem('ear')         # ditto
        'ear'
        >>> st.stem('saying')      # Words starting with consonant must contain at least 3
        'say'
        >>> st.stem('crying')      #     letters and one of those letters must be a vowel
        'cry'
        >>> st.stem('string')      # ditto
        'string'
        >>> st.stem('meant')       # ditto
        'meant'
        >>> st.stem('cement')      # ditto
        'cem'
        >>> st.stem('kilometer')      # ditto
        'met'
    """

    rule_expr = re.compile(r"""
    ^(?P<ending>\w+)
    (?P<intact>[*]?)
    (?P<num>\d+)
    (?P<append>\w*)
    (?P<cont>[.>])
    """, re.UNICODE | re.VERBOSE)

    stem_expr = re.compile("^\w+", re.UNICODE)

    defaultrules = """
    ai*2.     { -ia > -   if intact }
    a*1.      { -a > -    if intact }
    bb1.      { -bb > -b   }
    city3s.   { -ytic > -ys }
    ci2>      { -ic > -    }
    cn1t>     { -nc > -nt  }
    dd1.      { -dd > -d   }
    dei3y>    { -ied > -y  }
    deec2ss.  { -ceed > -cess }
    dee1.     { -eed > -ee }
    de2>      { -ed > -    }
    dooh4>    { -hood > -  }
    e1>       { -e > -     }
    feil1v.   { -lief > -liev }
    fi2>      { -if > -    }
    gni3>     { -ing > -   }
    gai3y.    { -iag > -y  }
    ga2>      { -ag > -    }
    gg1.      { -gg > -g   }
    ht*2.     { -th > -   if intact }
    hsiug5ct. { -guish > -ct }
    hsi3>     { -ish > -   }
    i*1.      { -i > -    if intact }
    i1y>      { -i > -y    }
    ji1d.     { -ij > -id   --  see nois4j> & vis3j> }
    juf1s.    { -fuj > -fus }
    ju1d.     { -uj > -ud  }
    jo1d.     { -oj > -od  }
    jeh1r.    { -hej > -her }
    jrev1t.   { -verj > -vert }
    jsim2t.   { -misj > -mit }
    jn1d.     { -nj > -nd  }
    j1s.      { -j > -s    }
    lbaifi6.  { -ifiabl > - }
    lbai4y.   { -iabl > -y }
    lba3>     { -abl > -   }
    lbi3.     { -ibl > -   }
    lib2l>    { -bil > -bl }
    lc1.      { -cl > c    }
    lufi4y.   { -iful > -y }
    luf3>     { -ful > -   }
    lu2.      { -ul > -    }
    lai3>     { -ial > -   }
    lau3>     { -ual > -   }
    la2>      { -al > -    }
    ll1.      { -ll > -l   }
    mui3.     { -ium > -   }
    mu*2.     { -um > -   if intact }
    msi3>     { -ism > -   }
    mm1.      { -mm > -m   }
    nois4j>   { -sion > -j }
    noix4ct.  { -xion > -ct }
    noi3>     { -ion > -   }
    nai3>     { -ian > -   }
    na2>      { -an > -    }
    nee0.     { protect  -een }
    ne2>      { -en > -    }
    nn1.      { -nn > -n   }
    pihs4>    { -ship > -  }
    pp1.      { -pp > -p   }
    re2>      { -er > -    }
    rae0.     { protect  -ear }
    ra2.      { -ar > -    }
    ro2>      { -or > -    }
    ru2>      { -ur > -    }
    rr1.      { -rr > -r   }
    rt1>      { -tr > -t   }
    rei3y>    { -ier > -y  }
    sei3y>    { -ies > -y  }
    sis2.     { -sis > -s  }
    si2>      { -is > -    }
    ssen4>    { -ness > -  }
    ss0.      { protect  -ss }
    suo3>     { -ous > -   }
    su*2.     { -us > -   if intact }
    s*1>      { -s > -    if intact }
    s0.       { -s > -s    }
    tacilp4y. { -plicat > -ply }
    ta2>      { -at > -    }
    tnem4>    { -ment > -  }
    tne3>     { -ent > -   }
    tna3>     { -ant > -   }
    tpir2b.   { -ript > -rib }
    tpro2b.   { -orpt > -orb }
    tcud1.    { -duct > -duc }
    tpmus2.   { -sumpt > -sum }
    tpec2iv.  { -cept > -ceiv }
    tulo2v.   { -olut > -olv }
    tsis0.    { protect  -sist }
    tsi3>     { -ist > -   }
    tt1.      { -tt > -t   }
    uqi3.     { -iqu > -   }
    ugo1.     { -ogu > -og }
    vis3j>    { -siv > -j  }
    vie0.     { protect  -eiv }
    vi2>      { -iv > -    }
    ylb1>     { -bly > -bl }
    yli3y>    { -ily > -y  }
    ylp0.     { protect  -ply }
    yl2>      { -ly > -    }
    ygo1.     { -ogy > -og }
    yhp1.     { -phy > -ph }
    ymo1.     { -omy > -om }
    ypo1.     { -opy > -op }
    yti3>     { -ity > -   }
    yte3>     { -ety > -   }
    ytl2.     { -lty > -l  }
    yrtsi5.   { -istry > - }
    yra3>     { -ary > -   }
    yro3>     { -ory > -   }
    yfi3.     { -ify > -   }
    ycn2t>    { -ncy > -nt }
    yca3>     { -acy > -   }
    zi2>      { -iz > -    }
    zy1s.     { -yz > -ys  }
    """

    def __init__(self, ruletable=None):
        """
        :param ruletable: a string containing the rule data, separated
            by newlines.
        """
        self.rules = defaultdict(list)
        self._ruletable = ruletable if ruletable else self.defaultrules
        self.read_rules(self._ruletable)

    def read_rules(self, ruletable):
        """Verify integrity of ruletable.
        """
        for line in ruletable.split("\n"):
            line = line.strip()
            if not line:
                continue

            match = self.rule_expr.match(line)
            if match:
                ending = match.group("ending")[::-1]
                intact = match.group("intact") == "*"
                num = int(match.group("num"))
                append = match.group("append")
                cont = match.group("cont") == ">"

                lastchar = ending[-1]
                self.rules[lastchar].append((ending, intact, num,
                                             append, cont))
            else:
                raise Exception("Bad rule: %r" % line)

    def first_vowel(self, word):
        """Returns index of vowel or y.
        """
        find_vowel = [p for p in [word.find(v) for v in "aeiou"] if p > -1]
        yp = word.find("y")
        # If find_vowel is empty, vowel pos always be greater than y pos
        vp = min(find_vowel) if find_vowel else yp + 1

        # If a word doesn't contain vowel and doesn't contain vowel return -1
        if yp < 0 and not find_vowel:
            return -1
        # If y was found and comes before any vowels return y position
        if yp > 0 and yp < vp:
            return yp
        return vp

    def strip_prefix(self, word):
        """Remove prefix from a word.
        """
        for prefix in ("kilo", "micro", "milli", "intra", "ultra", "mega",
                       "nano", "pico", "pseudo"):
            if word.startswith(prefix):
                return word[len(prefix):]
        return word

    def stem(self, word):
        """Returns a stemmed version of the argument string.
        """

        rules = self.rules
        match = self.stem_expr.match(word)
        if not match:
            return word
        stem = self.strip_prefix(match.group(0))

        # Check if word starts with vowel or constant with specified length of
        # 2 and 3 respectively. If not break out of for loop.
        # After this is_intact becomes true, while loop will end in the next
        # cycle.
        is_intact = True
        # While loop breaking condition
        continuing = True
        while continuing:
            pfv = self.first_vowel(stem)
            # pfv returns -1 when there is no y or vowels inside of a word
            if pfv is -1:
                return word
            rulelist = rules.get(stem[-1])
            if not rulelist:
                break

            continuing = False
            for ending, intact, num, append, cont in rulelist:
                if stem.endswith(ending):
                    if intact and not is_intact:
                        continue
                    newlen = len(stem) - num + len(append)

                    if ((pfv == 0 and newlen < 2)
                            or (pfv > 0 and newlen < 3)):
                        # If word starts with vowel, minimum stem length is 2.
                        # If word starts with consonant, minimum stem length is
                        # 3.
                        continue

                    is_intact = False
                    stem = stem[:0 - num] + append

                    continuing = cont
                    break

        if len(stem) > 0:
            return stem
        else:
            return word
