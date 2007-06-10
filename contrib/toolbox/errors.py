# Natural Language Toolkit: Shoebox Errors
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Stuart Robinson <Stuart.Robinson@mpi.nl>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module provides Shoebox exceptions.
"""

# ---------------------------------------------------------------------
# CLASS:  ShoeboxError
# DESC:   ???
# ---------------------------------------------------------------------

class ShoeboxError(Exception):
    """
    This is the base class for all Shoebox errors.
    """
    def __init__(self):
        self._msg = ""

    
# ---------------------------------------------
# CLASS:  ValidationError
# DESC:   ???
# ---------------------------------------------

class NonUniqueEntryError(ShoeboxError):
    """
    ???
    """
    def __init__(self) :
        pass

class ValidationError(ShoeboxError):    

    def __init__(self):
        pass

    def setField(self, field):
       self._field = field
    
    def getField(self):
       return self._field


# ---------------------------------------------
# CLASS:  NoMetadataFound
# DESC:   ???
# ---------------------------------------------

class NoMetadataFound(ValidationError):

  def __init__(self, field):
    self._field = field


class FieldError(ShoeboxError):

    def __init__(self):
        pass

    def __str__(self) :
        return self.get_message()

  
class NonUniqueFieldError(FieldError):
  """
  Error raised when an attempt is made to retrieve a unique field which has more than one value
  """
  def __init__(self, entry):
    self._entry = entry

  def setEntry(self, entry):
    self._entry = entry
    
  def getEntry(self):
    return self._entry


# ---------------------------------------------
# CLASS:  BadFieldValue
# DESC:   ???
# ---------------------------------------------

class BadFieldValueError(ValidationError, FieldError):
  
  FIELD_VALUE_ERROR_RANGE_SET    = '1'
  FIELD_VALUE_ERROR_NO_WORD_WRAP = '2'
  FIELD_VALUE_ERROR_EMPTY_VALUE  = '3'
  FIELD_VALUE_ERROR_SINGLE_WORD  = '4'
  
  errorTypes = {
    '1': "Range Set",
    '2': "No Word Wrap",
    '3': "Empty Value",
    '4': "Single Word"
    }

  def __init__(self, errorType, entry, field, fmMetadata):
    self._entry       = entry
    self._errorType   = errorType
    self._field       = field
    self._fmMetadata  = fmMetadata

  def __str__(self):
    e   = self.getEntry()
    f   = self.getField()
    typ = self.getErrorDescription()
    s = "'%s' error in '\\%s' field of record %i!\nRecord:\n%s" % (typ, f.getMarker(), e.getNumber(), e.getRawText())
    return s

  def getFieldMarkerMetadata(self):
    return self._fmMetadata

  def setFieldMarkerMetadata(self, fmMetadata):
    self._fmMetadata = fmMetadata

  def getErrorDescription(self):
    try:
      return self.errorTypes[self.getErrorType()]
    except:
      return None
    
  def getErrorType(self):
    return self._errorType

  def setErrorType(self, errorType):
    self._errorType = errorType
    
  def getEntry(self):
    return self._entry

  def setEntry(self, entry):
    self._entry = entry
