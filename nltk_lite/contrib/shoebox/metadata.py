# Natural Language Toolkit: Shoebox Dictionary
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module provides functionality for handling the metadata associated
with Shoebox lexicons and texts.
"""

import re

# ---------------------------------------------------------------------
# CLASS:  ShoeboxError
# DESC:   ???
# ---------------------------------------------------------------------

class ShoeboxError(Exception):
  """
  This is the base class for all Shoebox errors.
  """
  def __init__(self):
    pass  


# ---------------------------------------------
# CLASS:  ValidationError
# DESC:   ???
# ---------------------------------------------

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



# --------------------------------------------------------
# CLASS:  TextMetadataParser
# DESC:   Class for parsing text type definition file
#           into a DictionaryMetadata object
# --------------------------------------------------------

class TextMetadataParser:

  def __init__(self, filePath):
    self._filePath        = filePath
    
  def setFilePath(self, filePath):
    self._filePath = filePath

  def getFilePath(self):
    return self._filePath

  def parse(self):
    md = DictionaryMetadata()

    # Get lines from file
    fo = open(self.getFilePath(), 'rU')
    lines = fo.readlines()
    fo.close()

    # Raw text for parsing
    rawMarkerSet    = ''
#     rawFileSet      = ''
#     rawJumpSet      = ''
#     rawExportSet    = ''
#     rawExportRTFSet = ''    
#     rawTemplate     = ''

    # Flags for parsing
    flagMarkerSet    = False
#     flagJumpSet      = False
#     flagFileSet      = False
#     flagExportSet    = False
#     flagTemplate     = False
#     flagExportRTFSet = False
    
    for l in lines:
      # Market Set
      if l.startswith("\\+" + DictionaryMetadata.MARKER_SET):
        flagMarkerSet = True
      elif l.startswith("\\-" + DictionaryMetadata.MARKER_SET):
        flagMarkerSet = False
#       # Jump Set
#       elif l.startswith("\\+" + DictionaryMetadata.JUMP_SET):
#         flagJumpSet = True
#       elif l.startswith("\\-" + DictionaryMetadata.JUMP_SET):
#         flagJumpSet = False
#       # File Set
#       elif l.startswith("\\+" + DictionaryMetadata.FILE_SET):
#         flagFileSet = True
#       elif l.startswith("\\-" + DictionaryMetadata.FILE_SET):
#         flagFileSet = False
#       # Export Set
#       elif l.startswith("\\+" + DictionaryMetadata.EXPORT_SET):
#         flagExportSet = True
#       elif l.startswith("\\-" + DictionaryMetadata.EXPORT_SET):
#         flagExportSet = False
#       # RTF Export Set
#       elif l.startswith("\\+" + DictionaryMetadata.EXPORT_RTF_SET):
#         flagExportRTFSet = True
#       elif l.startswith("\\-" + DictionaryMetadata.EXPORT_RTF_SET):
#         flagExportRTFSet = False
#       # Template
#       elif l.startswith("\\+" + DictionaryMetadata.TEMPLATE):
#         flagTemplate = True
#       elif l.startswith("\\-" + DictionaryMetadata.TEMPLATE):
#         flagTemplate = False
      elif l.startswith("\\"):
        mo1 = re.match(r"\\(.*?) (.*)", l)
        mo2 = re.match(r"\\([A-Za-z][A-Za-z0-9_-]*)", l)
        if mo1:
          fm = mo1.group(1)
          fv = mo1.group(2)
          md.addField(fm, fv)
        elif mo2:
          fm = mo2.group(1)
          md.addField(fm, True)
        else:
          pass

      if flagMarkerSet == True:
        rawMarkerSet = rawMarkerSet + l
#       elif flagExportSet == True:
#         rawExportSet = rawExportSet + l
#       elif flagFileSet == True:
#         rawFileSet = rawFileSet + l
#       elif flagJumpSet == True:
#         rawJumpSet = rawJumpSet + l

#     # TODO
#     # Deal with template
#     # Deal with jump set
#     # Deal with file set
    
    # Deal with raw marker metadata
    regex = r"\\\+mkr +([a-zA-Z][a-zA-Z0-9_-]*)\n(.*?)\\\-mkr"
    reo = re.compile(regex, re.DOTALL)
    for mo in reo.findall(rawMarkerSet):
      fieldMarker = mo[0]
      rawText = mo[1]
      #print "[%s]" % fieldMarker
      #print "[%s]" % rawText
      mmp = FieldMarkerMetadataParser(rawText)
      mmd = mmp.parse()
      mmd.setFieldMarker(fieldMarker)
      md.addMarkerMetadata(fieldMarker, mmd)

    return md



# ---------------------------------------------
# CLASS:  TextMetadata
# DESC:   Class for storing and manipulating
#           the information contained within a
#           Shoebox text type definition
# ---------------------------------------------

class TextMetadata:

  def __init__(self):
    self._markerSet = {}
    self._fields    = {}

  def getFields(self):
    return self._fields
  
  def addField(self, fieldMarker, fieldValue):
    self._fields[fieldMarker] = fieldValue

  def getFieldMarkerMetadataByFieldMarker(self, fieldMarker):
    try:
      return self._fields[fieldMarker]
    except:
      return None
    
  def setFileContent(self, fileContent):
    self._fileContent = fileContent

  def getFileContent(self):
    return self._fileContent

  def getMarkerSet(self):
    return self._markerSet

  def setMarkerSet(self, markerSet):
    self._markerSet = markerSet

  def getMarkerMetadata(self, fieldMarker):
    try:
      return self._markerSet[fieldMarker]
    except:
      return None

  def addMarkerMetadata(self, fieldMarker, markerMetadata):
    self._markerSet[fieldMarker] = markerMetadata

  def setHeadFieldMarker(self, headFieldMarker):
    self.addField(Metadata.HEAD_FIELD, headFieldMarker)

  def getHeadFieldMarker(self):
    return self.getFieldMarkerMetadataByFieldMarker(DictionaryMetadata.HEAD_FIELD)

  def setDefaultLanguage(self, headFieldMarker):
    self.addField(DictionaryMetadata.DEFAULT_LANGUAGE, headFieldMarker)
    
  def getDefaultLanguage(self):
    return self.getFieldData(DictionaryMetadata.DEFAULT_LANGUAGE)

  def getVersion(self):
    return self.getFieldData(DictionaryMetadata.VERSION)





class ProjectParser:
  """
  Class for parsing a project file into a Project object.
  """
  SECTION_CORPUS_SET      = "CorpusSet"
  SECTION_FONT_MARKERS    = "fntMarkers"
  SECTION_RUN_DOS_MARKERS = "rundosMarkers"
  SECTION_DATABASE_LIST   = "dblst"
  SECTION_FIND            = "Find"
        
  def __init__(self, filePath):
    self._filePath = filePath
    
  def getFilePath(self):
    return self._filePath

  def setFilePath(self, filePath):
    self._filePath = filePath
    
  def parse(self):
    if not self.getFilePath():
      raise Exception("No .prj file specified!")
    elif not self.getFilePath().endswith(".prj"):
      raise Exception("Wrong project file suffix!")

    # Extract file contents
    fo = open(self.getFilePath(), 'rU')
    lines = fo.readlines()
    fo.close()

    p = Project()

    # Flags for parsing
    flagCorpusSet     = False
    flagFontMarkers   = False
    flagRunDOSMarkers = False
    flagDatabaseList  = False
    flagFind          = False

    # Temporary strings for storing raw sections
    rawCorpusSet     = ""
    rawFontMarkers   = ""
    rawRunDOSMarkers = ""
    rawDatabaseList  = ""
    rawFind          = ""
    
    # Go through file content line by line and
    # populate various subsections of project file
    for l in lines:
      if l.startswith(r"\ProjectPath"):
        p.setProjectPath(utilities.parseFieldForValue(l))
      elif l.startswith(r"\ver"):
        p.setVersion(utilities.parseFieldForValue(l))
      elif l.startswith(r"\automatickeyboardswitching"):
        p.setKeyboardSwitching("automatic")
      elif l.startswith("\\+" + ProjectParser.SECTION_CORPUS_SET):
        flagCorpusSet = True
      elif l.startswith("\\-" + ProjectParser.SECTION_CORPUS_SET):
        flagCorpusSet = False
      elif l.startswith("\\+" + ProjectParser.SECTION_FONT_MARKERS):
        flagFontMarkers = True
      elif l.startswith("\\-" + ProjectParser.SECTION_FONT_MARKERS):
        flagFontMarkers = False
      elif l.startswith("\\+" + ProjectParser.SECTION_RUN_DOS_MARKERS):
        flagDatabaseList = True
      elif l.startswith("\\-" + ProjectParser.SECTION_RUN_DOS_MARKERS):
        flagDatabaseList = False
      elif l.startswith("\\+" + ProjectParser.SECTION_DATABASE_LIST):
        flagDatabaseList = True
      elif l.startswith("\\-" + ProjectParser.SECTION_DATABASE_LIST):
        flagDatabaseList = False
      elif l.startswith("\\+" + ProjectParser.SECTION_FIND):
        flagFind = True
      elif l.startswith("\\-" + ProjectParser.SECTION_FIND):
        flagFind = False
      elif flagCorpusSet == True:
        rawCorpusSet = rawCorpusSet + l
      elif flagFontMarkers == True:
        rawFontMarkers = rawFontMarkers + l
      elif flagRunDOSMarkers == True:
        rawRunDOSMarkers = rawRunDOSMarkers + l
      elif flagDatabaseList == True:
        rawDatabaseList = rawDatabaseList + l
      elif flagFind == True:
        rawFind = rawFind + l

    p.setRawCorpusSet(rawCorpusSet.strip())
    p.setRawFontMarkers(rawFontMarkers.strip())
    p.setRawRunDOSMarkers(rawRunDOSMarkers.strip())
    p.setRawDatabaseList(rawDatabaseList.strip())
    p.setRawFind(rawFind.strip())
      
    return p
    

class Project:
  """
  Class for representing the data in a Shoebox project file.
  """
  def __init__(self):
    self._version           = None
    self._projectPath       = None
    self._keyboardSwitching = None
    self._rawCorpusSet      = None
    self._rawFontMarkers    = None
    self._rawRunDOSMarkers  = None
    self._rawDatabaseList   = None
    self._rawFind           = None

  def getRawCorpusSet(self):
    return self._rawCorpusSet
  
  def getRawFontMarkers(self):
    return self._rawFontMarkers

  def getRawRunDOSMarkers(self):
    return self._rawRunDOSMarkers

  def getRawDatabaseList(self):
    return self._rawDatabaseList

  def getRawFind(self):
    return self._rawFind
  
  def setRawCorpusSet(self, rawCorpusSet):
    self._rawCorpusSet = rawCorpusSet

  def setRawFontMarkers(self, rawFontMarkers):
    self._rawFontMarkers = rawFontMarkers

  def setRawRunDOSMarkers(self, rawRunDOSMarkers):
    self._rawRunDOSMarkers = rawRunDOSMarkers

  def setRawDatabaseList(self, rawDatabaseList):
    self._rawDatabaseList = rawDatabaseList

  def setRawFind(self, rawFind):
    self._rawFind = rawFind
    
  def getVersion(self):
    return self._version

  def setVersion(self, version):
    self._version = version

  def getProjectPath(self):
    return self._projectPath

  def setProjectPath(self, projectPath):
    self._projectPath = projectPath

  def getKeyboardSwitching(self):
    return self._keyboardSwitching

  def setKeyboardSwitching(self, keyboardSwitching):
    self._keyboardSwitching = keyboardSwitching

    

# ---------------------------------------------
# CLASS:  DictionaryMetadataParser
# DESC:   Class for parsing dictionary type
#           definition file into a
#           DictionaryMetadata object
# ---------------------------------------------

class DictionaryMetadataParser:

  def __init__(self, filePath):
    self._filePath        = filePath
    self._entries         = []
    self._headFieldMarker = None
    self._defaultLanguage = None
    
  def setFilePath(self, filePath):
    self._filePath = filePath

  def getFilePath(self):
    return self._filePath

  def parse(self):
    md = DictionaryMetadata()

    # Get lines from file
    fo = open(self.getFilePath(), 'rU')
    lines = fo.readlines()
    fo.close()

    # Raw text for parsing
    rawMarkerSet    = ''
    rawFileSet      = ''
    rawJumpSet      = ''
    rawExportSet    = ''
    rawExportRTFSet = ''    
    rawTemplate     = ''

    # Flags for parsing
    flagMarkerSet    = False
    flagJumpSet      = False
    flagFileSet      = False
    flagExportSet    = False
    flagTemplate     = False
    flagExportRTFSet = False
    
    for l in lines:
      # Market Set
      if l.startswith("\\+" + DictionaryMetadata.MARKER_SET):
        flagMarkerSet = True
      elif l.startswith("\\-" + DictionaryMetadata.MARKER_SET):
        flagMarkerSet = False
      # Jump Set
      elif l.startswith("\\+" + DictionaryMetadata.JUMP_SET):
        flagJumpSet = True
      elif l.startswith("\\-" + DictionaryMetadata.JUMP_SET):
        flagJumpSet = False
      # File Set
      elif l.startswith("\\+" + DictionaryMetadata.FILE_SET):
        flagFileSet = True
      elif l.startswith("\\-" + DictionaryMetadata.FILE_SET):
        flagFileSet = False
      # Export Set
      elif l.startswith("\\+" + DictionaryMetadata.EXPORT_SET):
        flagExportSet = True
      elif l.startswith("\\-" + DictionaryMetadata.EXPORT_SET):
        flagExportSet = False
      # RTF Export Set
      elif l.startswith("\\+" + DictionaryMetadata.EXPORT_RTF_SET):
        flagExportRTFSet = True
      elif l.startswith("\\-" + DictionaryMetadata.EXPORT_RTF_SET):
        flagExportRTFSet = False
      # Template
      elif l.startswith("\\+" + DictionaryMetadata.TEMPLATE):
        flagTemplate = True
      elif l.startswith("\\-" + DictionaryMetadata.TEMPLATE):
        flagTemplate = False
      elif l.startswith("\\"):
        mo1 = re.match(r"\\(.*?) (.*)", l)
        mo2 = re.match(r"\\([A-Za-z][A-Za-z0-9_-]*)", l)
        if mo1:
          fm = mo1.group(1)
          fv = mo1.group(2)
          md.addField(fm, fv)
        elif mo2:
          fm = mo2.group(1)
          md.addField(fm, True)
      else:
        pass

      if flagExportSet == True:
        rawExportSet = rawExportSet + l
      elif flagMarkerSet == True:
        rawMarkerSet = rawMarkerSet + l
      elif flagFileSet == True:
        rawFileSet = rawFileSet + l
      elif flagJumpSet == True:
        rawJumpSet = rawJumpSet + l

    # TODO
    # Deal with template
    # Deal with jump set
    # Deal with file set
    
    # Deal with raw marker metadata
    regex = r"\\\+mkr +([a-zA-Z][a-zA-Z0-9_-]*)\n(.*?)\\\-mkr"
    reo = re.compile(regex, re.DOTALL)
    for mo in reo.findall(rawMarkerSet):
      fieldMarker = mo[0]
      rawText = mo[1]
      mmp = FieldMarkerMetadataParser(rawText)
      mmd = mmp.parse()
      mmd.setFieldMarker(fieldMarker)
      md.addMarkerMetadata(fieldMarker, mmd)

    return md



# ---------------------------------------------
# CLASS:  DictionaryMetadata
# DESC:   Class for storing and manipulating
#           the information contained within a
#           Shoebox dictionary type definition
#           (dictionary metadata)
# ---------------------------------------------

class DictionaryMetadata:

  DEFAULT_LANGUAGE = 'lngDefault'
  VERSION          = 'ver'
  HEAD_FIELD       = 'mkrRecord'
  TEMPLATE         = 'template'
  MARKER_SET       = 'mkrset'
  JUMP_SET         = 'jmpset'
  FILE_SET         = 'filset'
  EXPORT_SET       = 'expset'
  EXPORT_RTF_SET   = 'expRTF'  
  
  def __init__(self):
    self._markerSet = {}
    self._fields    = {}

  def getFields(self):
    return self._fields
  
  def addField(self, fieldMarker, fieldValue):
    self._fields[fieldMarker] = fieldValue

  def getFieldMarkerMetadataByFieldMarker(self, fieldMarker):
    try:
      return self._fields[fieldMarker]
    except:
      return None
    
  def setFileContent(self, fileContent):
    self._fileContent = fileContent

  def getFileContent(self):
    return self._fileContent

  def getMarkerSet(self):
    return self._markerSet

  def setMarkerSet(self, markerSet):
    self._markerSet = markerSet

  def getMarkerMetadata(self, fieldMarker):
    try:
      return self._markerSet[fieldMarker]
    except:
      return None

  def addMarkerMetadata(self, fieldMarker, markerMetadata):
    self._markerSet[fieldMarker] = markerMetadata

  def setHeadFieldMarker(self, headFieldMarker):
    self.addField(Metadata.HEAD_FIELD, headFieldMarker)

  def getHeadFieldMarker(self):
    return self.getFieldMarkerMetadataByFieldMarker(DictionaryMetadata.HEAD_FIELD)

  def setDefaultLanguage(self, headFieldMarker):
    self.addField(DictionaryMetadata.DEFAULT_LANGUAGE, headFieldMarker)
    
  def getDefaultLanguage(self):
    return self.getFieldData(DictionaryMetadata.DEFAULT_LANGUAGE)

  def getVersion(self):
    return self.getFieldData(DictionaryMetadata.VERSION)



# ---------------------------------------------
# CLASS:  FieldMarkerMetadataParser
# DESC:   Class for parsing a chunk of raw text
#           describing a field marker in a
#           Shoebox type definition file into a
#           MarkerMetadata object.
# ---------------------------------------------

class FieldMarkerMetadataParser:

  FM_RANGE_SET      = 'rngset'

  def __init__(self, rawText):
    self._rawText = rawText
    
  def getRawText(self):
    return self._rawText

  def parse(self):
    mmd = FieldMarkerMetadata()

    rawText = self.getRawText()

    # TODO: Deal with Font Information
    reo = re.compile(r"\\\+fnt.*\\\-fnt", re.DOTALL)
    content = reo.sub("", rawText)

    # Deal with other parameters
    for l in content.split("\n"):
      mo1 = re.match(r"\\(.*?) (.*)", l)
      mo2 = re.match(r"\\([A-Za-z][A-Za-z0-9_-]*)", l)
      if mo1:
        fm = mo1.group(1)
        fv = mo1.group(2).strip()
        if fm == FieldMarkerMetadataParser.FM_RANGE_SET:
          mmd.setRangeSet(fv.split(" "))
        mmd.addField(fm, fv)
      elif mo2:
        fm = mo2.group(1)
        mmd.addField(fm, True)
    return mmd



# ---------------------------------------------
# CLASS:  FieldMarkerMetadata
# DESC:   Class for storing and manipulating
#           information about field markers
#           in a dictioary type definition
#           (dictionary metadata)
# ---------------------------------------------

class FieldMarkerMetadata:

  FM_METADATA_NO_WORD_WRAP   = 'NoWordWrap'
  FM_METADATA_SINGLE_WORD    = 'SingleWord'
  FM_METADATA_MUST_HAVE_DATA = 'MustHaveData'
  FM_METADATA_PARENT_FM      = 'mkrOverThis'
  FM_METADATA_NEXT_FM        = 'mkrFollowingThis'
  FM_METADATA_NAME           = 'nam'
  FM_METADATA_LANGUAGE       = 'lng'
  FM_METADATA_DESCRIPTION    = 'desc'

  def __init__(self):
    self._metadata = {}
    self._fieldMarker = None
    self._rangeSet = None
    
  def __str__(self):
    pass
      
  def getFieldMarker(self):
    return self._fieldMarker

  def setFieldMarker(self, fieldMarker):
    self._fieldMarker = fieldMarker

  def getFields(self):
    keys = self._metadata.keys()
    keys.sort()
    return keys
  
  def addField(self, fieldMarker, fieldData):
    self._metadata[fieldMarker] = fieldData
    
  def getFieldData(self, fieldMarker):
    try:
      return self._metadata[fieldMarker]
    except:
      return None

  def getMustHaveData(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_MUST_HAVE_DATA)
  
  def getIsNoWordWrap(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_NO_WORD_WRAP)
    
  def getIsSingleWord(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_SINGLE_WORD)

  def getLanguage(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_LANGUAGE)

  def getName(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_NAME)

  def getParentFieldMarker(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_PARENT_FM)

  def getDescription(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_DESCRIPTION)

  def getRangeSet(self):
    return self._rangeSet

  def setRangeSet(self, rangeSet):
    self._rangeSet = rangeSet
    
  def getNextFieldMarker(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_NEXT_FM)

  def getMustHaveData(self):
    return self.getFieldData(MarkerMetadata.FM_METADATA_MUST_HAVE_DATA)



# ---------------------------------------------
# CLASS:  ShoeboxValidator
# DESC:   Class for validating Shoebox entry
#         using metadata
# ---------------------------------------------

class ShoeboxValidator:

  def __init__(self):
    self._metadata = None
    self._shoebox  = None
        
  def getMetadata(self):
    return self._metadata

  def setMetadata(self, metadata):
    self._metadata = metadata

  def getShoebox(self):
    return self._shoebox

  def setShoebox(self, shoebox):
    self._shoebox = shoebox

  def validate(self):
    for e in self.getShoebox().getEntries():
      for fm in e.getFields():
        fvs = e.getFieldValuesByFieldMarker(fm)
        for fv in fvs:
          fmm = self.getMetadata().getMarkerMetadata(fm)
          f = Field(fm, fv)
          if not fmm:
            raise NoMetadataFound(f)
          if fmm.getMustHaveData() and not fv:
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_MUST_HAVE_DATA, e, f, fmm)
          if fmm.getIsSingleWord() and " " in fv: 
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_SINGLE_WORD, e, f, fmm)
          if fmm.getRangeSet() and not fv in fmm.getRangeSet():
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_RANGE_SET, e, f, fmm)
          if fmm.getIsNoWordWrap() and "\n" in fv:
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_NO_WORD_WRAP, e, f, fmm)

  # TODO: Modify to take into account changes to Field object
  def validateRangeSets(self):
    for e in self.getShoebox().getEntries():
      for fm in e.getFieldMarkers():
        for fv in e.getFieldValuesByFieldMarker(fm):
          fmm = self.getMetadata().getMarkerMetadata(fm)
          if not fmm:
            raise NoMetadataFound(fm)
          if fmm.getRangeSet() and not fv in fmm.getRangeSet():
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_RANGE_SET, e, fv, fmm)
