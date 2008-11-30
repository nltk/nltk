# Natural Language Toolkit: Toolbox Lexicon
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This modules provides functionality for parsing and manipulating the
contents of a Toolbox lexicon without reference to its metadata.
"""

import os, re, sys
import nltk.data
from nltk.corpus.reader.toolbox import StandardFormat
from utilities import Field, SequentialDictionary


class Lexicon(StandardFormat):

  """
  This class represents a Toolbox lexicon, which consists of an
  optional header and one or more Entry objects, saved in a dictionary
  whose keys are passed as a parameter to the parse() method.
  """

  def __init__(self, file):
    """
    This method construct a Lexicon object with a header and a dictionary of
    entries.
    """
    self._key_fields = ['lx']
    self._header  = ''
    self._entries = {}
    self._file = file
    
  def __str__(self):
    """
    This method defines the string representation of a Lexicon object
    """
    s = "%s\n" % self.get_header()
    for e in self.get_entries():
      s = "%s%s\n" % (s, e)
    return s
    
  def set_header(self, header):
    """
    This method sets the raw text of the header.
    @param header: header (as raw text)
    @type  header: string
    """
    self._header = header

  def get_header(self):
    """
    This method obtains the raw text of the header.
    @return: raw header
    @rtype: string
    """
    return self._header

  def get_entries(self):
    """
    This method obtains all of the entries found in a
    parsed Toolbox lexicon.
    
    @return: all of the entries in the Lexicon
    @rtype: list of Entry objects
    """
    keys = self._entries.keys()
    keys.sort()
    for k in keys :
      v = self._entries[k]
      for e in v :
        yield e

  def add_entry(self, entry, unique=False):
      """
      This method adds an Entry object to a Lexicon object. It adds the
      entry to the Lexicon keyed by the values of the fields specified
      by the I{key_fields} argument.

      @param entry: a parsed entry from a Toolbox lexicon
      @type entry: Entry object
      @param unique: raise exception if entry key already exists
      @type unique: boolean
      """
      key = ""
      for field_marker in self._key_fields:
          f = entry.get_field(field_marker)
          if f:
              values = f.get_values("/")
              key = key + "-" + values
          else:
              # Should this throw an error if a field with no values
              # is used in the list of key fields?
              pass
      if self._entries.has_key(key) :
          if unique :
              msg = "Non-unique entry! \nEntry: \n%s\nKey Fields: %s\nKey: '%s'\n" % (entry, self._key_fields, key)    
              raise ValueError, msg
      else :
          self._entries[key] = []
      # Now append entry to list of entries for key
      self._entries[key].append(entry)


  def parse(self,
            head_field_marker     = 'lx',
            subentry_field_marker = None,
            key_fields            = None,
            unique_entry          = True,
            unique_subentry       = False):
      """
      This method parses a Toolbox file in a Lexicon object. It will also parse
      subentries provided that the field marker identifying subentries is passed to it.
    
      @param head_field_marker:     field marker that identifies the start of an entry
      @type  head_field_marker:     string
      @param key_fields:            the field(s) to which entries are keyed
      @type  key_fields:            list of strings
      @param subentry_field_marker: field marker that identifies subentries
      @type  subentry_field_marker: string
      @param unique_entry:          raise warning if entries are non-unique according
                                      to I{key_fields} parameter
      @type  unique_entry:          boolean
      @param unique_subentry:       raise warning if entries are non-unique according to
                                      I{key_fields} parameter
      @type  unique_subentry:       boolean    
      @return:                      a parsed Lexicon object
      @rtype:                       dictionary object
      """

      if key_fields :
        self._key_fields = key_fields
        
      # Set up variables
      inside_entry = False
      inside_subentry = False
      e = None
      se = None
      # Use low-level functionality to get raw fields and walk through them
      self.open(self._file)
      for f in self.raw_fields() :
          fmarker, fvalue = f
          # What kind of field marker is it?
          if fmarker.startswith("_") :
              # TODO: Add field to header
              pass
          elif fmarker == head_field_marker :
              inside_entry = True
              inside_subentry = False
              if e :
                  self.add_entry(e, unique_entry)
              e = Entry()
          elif subentry_field_marker and fmarker == subentry_field_marker :
              inside_subentry = True
              if se :
                  e.add_subentry(se)
              se = Entry()               
          # Add field to entry or subentry
          if inside_subentry :
              se.add_field(fmarker, fvalue)
          elif inside_entry :
              e.add_field(fmarker, fvalue)
          else :
              pass
      # Deal with last entry
      if e :
          self.add_entry(e, unique_entry)
      self.close()

class Entry:
  """
  This class represents an entry (record) from a Toolbox lexicon. Each entry
  consists of a collection of fields, stored as a special type of dictionary
  which keeps track of the sequence in which its keys were entered.
  """

  def __init__(self):
    """
    This method constructs a new Entry object.
    """
    self._fields     = SequentialDictionary()
    self._rawText    = ""
    self._number     = None
    self._subentries = None

  def __str__(self):
    """
    This method defines the string representation of an entry.

    @rtype:  string
    @return: an entry as a string in Standard Format
    """
    s = ""
    fields = self.get_fields()
    for fm, fvs in self._fields.items():
      for fv in fvs:
        s = s + "\n\\%s %s" % (fm, fv)          
    return s
    
  def set_raw_text(self, rawText):
    """
    This method provides access to the raw text from which the
    Entry object was parsed.
    
    @param rawText: raw Toolbox text from which entry was parsed
    @type  rawText: string
    """
    self._rawText = rawText

  def get_raw_text(self):
    """
    This method sets the raw text from which the Entry object was parsed.

    @rtype: string
    """
    return self._rawText
  
  def get_subentries(self):
    """
    This method obtains all of the subentries for an entry.

    @rtype: list of Entry objects
    @returns: all of the subentries of an entry
    """
    return self._subentries

  def add_subentry(self, subentry):
    """
    This method adds to an entry a subentry, which is simply another
    Entry object.

    @param subentry: subentry
    @type  subentry: Entry object    : 
    """
    if not self._subentries:
      self._subentries = []
    self._subentries.append(subentry)

  def set_number(self, number):
    """
    This method sets the position of the entry in
    the dictionary as a cardinal number.
    
    @param number: number of entry
    @type  number: integer
    """
    self._number = number

  def get_number(self):
    """
    This method obtains the position of the entry in the dictionary
    as a cardinal number.
    
    @rtype: integer
    """
    return self._number
  
  def get_fields(self):
    """
    This method obtains all of the fields found in the Entry object.
    
    @rtype: list of Field objects
    """
    return self._fields.values()

  def get_field_markers(self):
    """
    This method obtains of the field markers found in the Entry object.

    @return: the field markers of an entry
    @rtype: list
    """
    return self._fields.keys()

  def get_values_by_marker(self, field_marker, sep=None) :
    return self.get_field_values_by_field_marker(field_marker, sep)

  def get_field_values_by_field_marker(self, field_marker, sep=None):
    """
    This method returns all of the field values for a given field marker.
    If the L(sep) is set, it will return a string; otherwise, it will
    return a list of Field objects.
    
    @param field_marker: marker of desired field
    @type  field_marker: string
    @param sep: separator for field values
    @type  sep: string    
    @rtype: string (if sep); otherwise, list of Field objects
    """
    try:
      values = self._fields[field_marker]
      if sep == None:
        return values
      else:
        return sep.join(values)
    except KeyError:
      return None

  def get_field_as_string(self,
                          field_marker,
                          join_string=""):
    """
    This method returns a particular field given a field marker.
    Returns a blank string if field is not found.
    
    @param field_marker: marker of desired field
    @type  field_marker: string
    @param join_string: string used to join field values (default to blank string)
    @type  join_string: string
    @rtype: string
    """
    try:
      return join_string.join(self._fields[field_marker])
    except KeyError:
      return ""

  def get_field(self, fieldMarker):
    """
    This method returns a particular field given a field marker.
    
    @param fieldMarker: marker of desired field
    @type  fieldMarker: string
    @rtype: Field object
    """
    try:
      return Field(fieldMarker, self._fields[fieldMarker])
    except KeyError:
      return None

  def set_field(self, fieldMarker, field):
    """
    This method sets a field, given a marker and its associated data.
    
    @param fieldMarker: field marker to set
    @type  fieldMarker: string
    @param field      : field object associated with field marker
    @type  field      : Field
    """
    fvs = []
    fvs.append(fieldData)
    self._fields[fieldMarker] = fvs

  def set_field_values(self, fieldMarker, fieldValues):
    """
    This method sets all of the values associated with a field.
    
    @param fieldMarker: field marker to set
    @type  fieldMarker: string
    @param fieldValues: list of field values
    @type  fieldValues: list
    """
    self._fields[fieldMarker] = fieldValues
  
  def add_field(self, marker, value):
    """
    This method adds a field to an entry if it does not already exist
    and adds a new value to the field of an entry if it does.
    
    @param marker: field marker
    @type  marker: string
    @param value : field value
    @type  value : string    
    """
    if self._fields.has_key(marker):
      fvs = self._fields[marker]
      fvs.append(value)
    else:
      fvs = []
      fvs.append(value)
    self._fields[marker] = fvs

  def remove_field(self, fieldMarker):
    """
    This method removes from an entry every field for a given
    field marker. It will not raise an error if the specified field
    does not exist.
    
    @param fieldMarker: field marker to be deleted
    @type  fieldMarker: string
    """
    if self._fields.has_key(fieldMarker):
      del self._fields[fieldMarker]

def demo() :
    path = nltk.data.find("corpora/toolbox/rotokas.dic")
    l = Lexicon(path)
    l.parse(key_fields=['lx','ps','sn'], unique_entry=False)
    h = l.get_header()
    for e in l.get_entries() :
        print "<%s><%s><%s>" % (e.get_field_as_string("lx", ""),
                                e.get_field_as_string("ps", ""),
                                e.get_field_as_string("sn", ""))
  
if __name__ == '__main__':
    demo()
