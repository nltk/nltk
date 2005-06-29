# --------------------------------------------------------
# AUTHOR: Stuart P. Robinson
# DATE:   22 June 2005
# DESC:   This module provides a number of utility classes
#         used by the standardformat and shoebox modules.
# --------------------------------------------------------

from UserDict import UserDict


# --------------------------------------------------------
# CLASS:  SequentialDictionary
# DESC:   Dictionary that retains the order in which keys
#         were added to it.
# --------------------------------------------------------
class SequentialDictionary(UserDict) :

  def __init__(self, dict=None) :
    self._keys = []
    UserDict.__init__(self, dict)

  def __delitem__(self, key) :
    UserDict.__delitem__(self, key)
    self.keys.remove(key)

  def __setitem__(self, key, item) :
    UserDict.__setitem__(self, key, item)
    if key not in self._keys :
      self._keys.append(key)

  def clear(self) :
    UserDict.clear(self)
    self._keys = []

  def copy(self) :
    dict = UserDict.copy(self)
    dict._keys = self.keys[:]
    return dict

  def items(self) :
    return zip(self._keys, self.values())

  def keys(self) :
    return self._keys

  def popitem(self) :
    try :
      key = self._keys[-1]
    except IndexError :
      raise KeyError('dictionary is empty')

    val = self[key]
    del self[key]

    return (key, val)

  def setdefault(self, key, failobj=None) :
    if key not in self._keys :
      self._keys.append(key)
    return UserDict.setdefault(self, key, failobj)
  
  def update(self, dict) :
    UserDict.update(self, dict)
    for key in dict.keys() :
      if key not in self._keys :
        self._keys.append(key)

  def values(self) :
    return map(self.get, self._keys)
  

# -------------------------------------------------------------
# Given a line of text that is morpheme aligned, the indices
# for each left word boundary is returned.
#
#     0    5  8   12              28          <- indices
#     |    |  |   |               |
#     |||||||||||||||||||||||||||||||||||||||
# \sf dit  is een goede           explicatie  <- surface form
# \um dit  is een goed      -e    explicatie  <- underlying morphemes
# \mg this is a   good      -ADJ  explanation <- morpheme gloss
# \gc DEM  V  ART ADJECTIVE -SUFF N           <- grammatical categories
# \ft This is a good explanation.             <- free translation
# 
# c  flag.before  flag.after  index?
# -- -----------  ----------  ------
# 0  1       	  0           yes
# 1  0       	  1           no
# 2  1       	  0           no
# 3  0       	  1           no
# 4  1       	  0           no   
# 5  1            0           yes
# ...
# ------------------------------------------------------------
def getIndices(str) :
  indices = []
  flag = 1
  for i in range(0, len(str)) :
    c = str[i]
    if flag and c != ' ' :
      indices.append(i)
      flag = 0
    elif not flag and c == ' ' :
      flag = 1
  return indices


# --------------------------------------------------------
# Given a string a list of indices, this function returns
# a list the substrings defined by those indices.
# For example, given the arguments 
#   'antidisestablishmentarianism',
#   [4, 7, 16, 20, 25]
# this function returns
#   ['anti', 'dis', 'establish', 'ment', arian', 'ism']
# --------------------------------------------------------
def sliceByIndices(str, indices) :
  slices = []
  for i in range(0, len(indices)) :
    slice = None
    start = indices[i]
    if i == len(indices)-1 :
      slice = str[start : ]
    else :
      finish = indices[i+1]
      slice = str[start : finish]
    slices.append(slice)
  return slices
