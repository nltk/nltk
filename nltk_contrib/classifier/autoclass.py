# Natural Language Toolkit - AutoClass
#  automatic class value generator
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

class AutoClass:
    def __init__(self, name):
        self.name = name
        
    def next(self):
        base26 = self.base26()
        base26 += 1
        return AutoClass(string(base26))

    def base26(self):
        base26 = 0
        length = len(self.name)
        for index in range(length):
            numeric = ord(self.name[index]) - 97
            if (index == length - 1): base26 += numeric
            else: base26 += numeric * 26 * (length - index - 1)
        return base26
    
    def __eq__(self, other):
        if other is None: return False
        if self.__class__ != other.__class__: return False
        if self.name == other.name: return True
        return False
    
    def __hash__(self):
        if self.name == None: return id(self)
        return 3 * self.name + 7 
    
    def __str__(self):
        return self.name

FIRST = AutoClass('a')

def string(base26):
    strn = ''
    while (base26 /26 > 0):
        strn = chr((base26 % 26) + 97) + strn
        base26 = base26 / 26
    strn = chr((base26 % 26) + 97) + strn
    return strn
