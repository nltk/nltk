# Natural Language Toolkit: Shoebox Utilities
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module provides basic functionality for handling shoebox format files.
These feed into the more sophisticated Shoebox tools available in the
modules I{lexicon}, I{text}, and I{metadata}.
"""

import re
from UserDict import UserDict


def parse_field(line):
  """
  This function returns the field marker and field value of a Shoebox field.

  @return: parses field as string and returns tuple with field marker and field value
  @rtype: tuple
  """
  mo = re.match(r"\\(.*?) (.*)", line)
  if mo:
    fm = mo.group(1)
    fv = mo.group(2)
    return (fm, fv)
  else:
    return None


class Field:
  """
  Class used to represent a standard fromat field. A field
  consists of a field marker and its value, stored as a tuple.
  """

  def __init__(self, fieldMarker, fieldValue):
    """
    This method constructs a Field object as a tuple of a field
    marker and a field value.
    @param fieldMarker: a field's marker
    @type  fieldMarker: string
    @param fieldValue : a field's value (the actual data)
    @type  fieldValue : string
    """
    self._field = (fieldMarker, fieldValue)

  def __str__(self):
    """
    This method returns the string representation of a Field object.
    
    @return: a Field object formatted as a string
    @rtype: string
    """
    return "\\%s %s" % (self.getMarker(), self.getValue())
  
  def get_marker(self):
    """
    This method returns the marker for a field.
    
    @return: a field's marker
    @rtype: string
    """
    return self._field[0]

  def has_unique_value(self):
    """
    This method checks whether a field has a single value, in
    which case it returns true, or multiple values, in which
    case it returns false.
    
    @return: whether the value for a given field is unique
    @rtype: boolean
    """
    if not self.get_values() or len(self.get_values()) > 1:
      return True
    else:
      return False
    
  def has_value(self):
    """
    This method checks whether a field has a value or not.

    @return: whether a given field has a value
    @rtype: boolean
    """
    if self.get_values():
      return True
    else:
      return False
    
  def get_values(self, sep=None):
    """
    This method returns the values for a field, either as a raw list of
    values or, if a separator string is provided, as a formatted string.
    
    @return: the values for a field; if sep provided, formatted as string
    @rtype: a list of values or a string of these values joined by I{sep}
    """    
    values = self._field[1]
    if sep == None:
      return values 
    else:
      return sep.join(values)


# class FieldParser:
#   """
#   Parses raw Shoebox field into a field object.
#   """
#   def __init__(self, rawText):
#     self._rawText = rawText

#   def getRawText(self):
#     """
#     This method returns the raw text to be parsed as a field by the parser.
    
#     @return: string
#     @rtype: a string with a standard format field as raw text
#     """    
#     return self._rawText

#   def setRawText(self, rawtext):
#     """
#     This method constructs a Field object as a tuple of a field
#     marker and a field value.
#     @param rawtext: the raw text to be parsed into a field object
#     @type  rawtext: string
#     """
#     self._rawtext = rawtext
#     return self._rawtext

#   def parse(self):
#     regex = r"\\([A-Za-z][A-Za-z0-9\_\-]*) (.*)"
#     mo = re.search(regex,
#                    self.getRawText())
#     fm = mo.group(1)
#     fv = mo.group(2)
#     return Field(fm, fv)


class SequentialDictionary(UserDict):
  """
  Dictionary that retains the order in which keys were added to it.
  """
  def __init__(self, dict=None):
    self._keys = []
    UserDict.__init__(self, dict)

  def __delitem__(self, key):
    UserDict.__delitem__(self, key)
    self._keys.remove(key)

  def __setitem__(self, key, item):
    UserDict.__setitem__(self, key, item)
    if key not in self._keys:
      self._keys.append(key)

  def clear(self):
    UserDict.clear(self)
    self._keys = []

  def copy(self):
    dict = UserDict.copy(self)
    dict._keys = self.keys[:]
    return dict

  def items(self):
    return zip(self._keys, self.values())

  def keys(self):
    return self._keys

  def popitem(self):
    try:
      key = self._keys[-1]
    except IndexError:
      raise KeyError('dictionary is empty')
    val = self[key]
    del self[key]

    return (key, val)

  def setdefault(self, key, failobj=None):
    if key not in self._keys:
      self._keys.append(key)
    return UserDict.setdefault(self, key, failobj)
  
  def update(self, dict):
    UserDict.update(self, dict)
    for key in dict.keys():
      if key not in self._keys:
        self._keys.append(key)

  def values(self):
    return map(self.get, self._keys)
