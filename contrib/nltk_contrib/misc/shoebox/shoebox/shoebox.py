# --------------------------------------------------------
# AUTHOR: Stuart P. Robinson
# DATE:   22 June 2005
# DESC:   This module provide various classes for the
#         manipulation of the hidden metadata files used
#         by Shoebox/Toolbox.
# --------------------------------------------------------

import re

# ---------------------------------------------
# CLASS:  MetadataParser
# DESC:   Class for parsing a file in Standard
#         Format (SF) into a manipulable data
#         structure.
# ---------------------------------------------
class MetadataParser :

  def __init__(self, fileContent) :
    self._entries         = []
    self._headFieldMarker = None
    self._fileContent     = fileContent
    self._defaultLanguage = None
    
  def setFileContent(self, fileContent) :
    self._fileContent = fileContent

  def getFileContent(self) :
    return self._fileContent

  def parse(self) :
    fc = self.getFileContent()
    md = Metadata()

    # Raw text for parsing
    rawMarkerSet    = ''
    rawFileSet      = ''
    rawJumpSet      = ''
    rawExportSet    = ''
    rawExportRTFSet = ''    
    rawTemplate     = ''
    
    flagInsideMarkerSet    = False
    flagInsideJumpSet      = False
    flagInsideFileSet      = False
    flagInsideExportSet    = False
    flagInsideTemplate     = False
    flagInsideExportRTFSet = False
    
    for l in fc.split("\n") :
      # Market Set
      if l.startswith("\\+" + Metadata.METADATA_FM_MARKER_SET) :
        flagInsideMarkerSet = True
        rawMarkerSet = "%s\n%s" % (rawMarkerSet, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_MARKER_SET) :
        flagInsideMarkerSet = False
        rawMarkerSet = "%s\n%s" % (rawMarkerSet, l)
      elif flagInsideMarkerSet :
        rawMarkerSet = "%s\n%s" % (rawMarkerSet, l)

      # Jump Set
      elif l.startswith("\\+" + Metadata.METADATA_FM_JUMP_SET) :
        flagInsideJumpSet = True
        rawJumpSet = "%s\n%s" % (rawJumpSet, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_JUMP_SET) :
        flagInsideJumpSet = False
        rawJumpSet = "%s\n%s" % (rawJumpSet, l)
      elif flagInsideJumpSet :
        rawJumpSet = "%s\n%s" % (rawJumpSet, l)

      # File Set
      elif l.startswith("\\+" + Metadata.METADATA_FM_FILE_SET) :
        flagInsideFileSet = True
        rawFileSet = "%s\n%s" % (rawFileSet, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_FILE_SET) :
        flagInsideFileSet = False
        rawFileSet = "%s\n%s" % (rawFileSet, l)
      elif flagInsideFileSet :
        rawFileSet = "%s\n%s" % (rawFileSet, l)

      # Export Set
      elif l.startswith("\\+" + Metadata.METADATA_FM_EXPORT_SET) :
        flagInsideExportSet = True
        rawExportSet = "%s\n%s" % (rawExportSet, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_EXPORT_SET) :
        flagInsideExportSet = False
        rawExportSet = "%s\n%s" % (rawExportSet, l)
      elif flagInsideExportSet :
        rawExportSet = "%s\n%s" % (rawExportSet, l)

      # RTF Export Set
      elif l.startswith("\\+" + Metadata.METADATA_FM_EXPORT_RTF_SET) :
        flagInsideExportRTFSet = True
        rawExportRTFSet = "%s\n%s" % (rawExportRTFSet, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_EXPORT_RTF_SET) :
        flagInsideExportRTFSet = False
        rawExportRTFSet = "%s\n%s" % (rawExportRTFSet, l)
      elif flagInsideExportRTFSet :
        rawExportRTFSet = "%s\n%s" % (rawExportRTFSet, l)        

      # Template
      elif l.startswith("\\+" + Metadata.METADATA_FM_TEMPLATE) :
        flagInsideTemplate = True
        rawTemplate = "%s\n%s" % (rawTemplate, l)
      elif l.startswith("\\-" + Metadata.METADATA_FM_TEMPLATE) :
        flagInsideTemplate = False
        rawTemplate = "%s\n%s" % (rawTemplate, l)
      elif flagInsideTemplate :
        rawTemplate = "%s\n%s" % (rawTemplate, l)                
        
      elif l.startswith("\\") :
        mo1 = re.match(r"\\(.*?) (.*)", l)
        mo2 = re.match(r"\\([A-Za-z][A-Za-z0-9_-]*)", l)
        if mo1 :
          fm = mo1.group(1)
          fv = mo1.group(2)
          md.addField(fm, fv)
        elif mo2 :
          fm = mo2.group(1)
          md.addField(fm, True)
      else :
        pass

    # TODO: Abstract common logic
    # Deal with template
    # Deal with jump set
    # Deal with file set
    
    # Deal with marker metadata
    for l in rawMarkerSet.split("\n") :
      mo = re.match(r"\\(.*?) (.*)", l)
      if mo :
        fm = mo.group(1)
        fd = mo.group(2)
        if fm == Metadata.METADATA_FM_DEFAULT_LANGUAGE :
          md.setDefaultLanguage(fd)
        elif fm == Metadata.METADATA_FM_HEAD_FIELD :
          md.setHeadFieldMarker(fd)
    regex = r"\\\+mkr +([a-zA-Z][a-zA-Z0-9_-]*)\n(.*?)\\\-mkr"
    reo = re.compile(regex, re.DOTALL)
    for mo in reo.findall(rawMarkerSet) :
      fieldMarker = mo[0]
      rawText = mo[1]
      mmp = MarkerMetadataParser(rawText)
      mmd = mmp.parse(fieldMarker)
      md.addMarkerMetadata(mmd)
    return md



# ---------------------------------------------
# CLASS:  Metadata
# DESC:   Class for storing Shoebox metadata
# ---------------------------------------------

class Metadata :

  METADATA_FM_DEFAULT_LANGUAGE = 'lngDefault'
  METADATA_FM_VERSION          = 'ver'
  METADATA_FM_HEAD_FIELD       = 'mkrRecord'
  METADATA_FM_TEMPLATE         = 'template'
  METADATA_FM_MARKER_SET       = 'mkrset'
  METADATA_FM_JUMP_SET         = 'jmpset'
  METADATA_FM_FILE_SET         = 'filset'
  METADATA_FM_EXPORT_SET       = 'expset'
  METADATA_FM_EXPORT_RTF_SET   = 'expRTF'  
  
  def __init__(self) :
    self._markerSet = {}
    self._fields    = {}

  def getFields(self) :
    return self._fields
  
  def addField(self, fieldMarker, fieldValue) :
    self._fields[fieldMarker] = fieldValue

  def getFieldData(self, fieldMarker) :
    try :
      return self._fields[fieldMarker]
    except :
      return None
    
  def setFileContent(self, fileContent) :
    self._fileContent = fileContent

  def getFileContent(self) :
    return self._fileContent

  def getMarkerSet(self) :
    return self._markerSet

  def setMarkerSet(self, markerSet) :
    self._markerSet = markerSet

  def getMarkerMetadata(self, fieldMarker) :
    try :
      return self._markerSet[fieldMarker]
    except :
      return None

  def addMarkerMetadata(self, markerMetadata) :
    self._markerSet[markerMetadata.getFieldMarker()] = markerMetadata

  def setHeadFieldMarker(self, headFieldMarker) :
    self.addField(Metadata.METADATA_FM_HEAD_FIELD, headFieldMarker)

  def getHeadFieldMarker(self) :
    return self.getFieldData(Metadata.METADATA_FM_HEAD_FIELD)

  def setDefaultLanguage(self, headFieldMarker) :
    self.addField(Metadata.METADATA_FM_DEFAULT_LANGUAGE, headFieldMarker)
    
  def getDefaultLanguage(self) :
    return self.getFieldData(Metadata.METADATA_FM_DEFAULT_LANGUAGE)

  def getVersion(self) :
    return self.getFieldData(Metadata.METADATA_FM_VERSION)



# ---------------------------------------------
# CLASS:  MarkerMetadataParser
# DESC:   Class for parsing a chunk of raw text
#         from a Shoebox type file into a
#         marker metadata object.
# ---------------------------------------------

class MarkerMetadataParser :

  def __init__(self, rawText) :
    self._rawText = rawText
    
  def getRawText(self) :
    return self._rawText

  def parse(self, fieldMarker) :
    rawText = self.getRawText()
    mmd = MarkerMetadata()
    mmd.setFieldMarker(fieldMarker)

    # TODO : Deal with Font Information
    reo = re.compile(r"\\\+fnt.*\\\-fnt", re.DOTALL)
    content = reo.sub("", rawText)

    # Deal with other parameters
    for l in content.split("\n") :
      mo1 = re.match(r"\\(.*?) (.*)", l)
      mo2 = re.match(r"\\([A-Za-z][A-Za-z0-9_-]*)", l)
      if mo1 :
        fm = mo1.group(1)
        fv = mo1.group(2)
        #print "[%s][%s]" % (fm, fv)
        mmd.addField(fm, fv)
      elif mo2 :
        fm = mo2.group(1)
        mmd.addField(fm, True)
    return mmd



# ---------------------------------------------
# CLASS:  Metadata
# DESC:   Class for storing Shoebox metadata
# ---------------------------------------------

class MarkerMetadata :

  FM_METADATA_NO_WORD_WRAP   = 'NoWordWrap'
  FM_METADATA_SINGLE_WORD    = 'SingleWord'
  FM_METADATA_MUST_HAVE_DATA = 'MustHaveData'
  FM_METADATA_PARENT_FM      = 'mkrOverThis'
  FM_METADATA_NEXT_FM        = 'mkrFollowingThis'
  FM_METADATA_NAME           = 'nam'
  FM_METADATA_LANGUAGE       = 'lng'
  FM_METADATA_DESCRIPTION    = 'desc'
  FM_METADATA_RANGE_SET      = 'rngset'

  def __init__(self) :
    self._metadata = {}
    self._fieldMarker = None

  def __str__(self) :
    pass
    #for f in self.getFields() :
      #print f
      
  def getFieldMarker(self) :
    return self._fieldMarker

  def setFieldMarker(self, fieldMarker) :
    self._fieldMarker = fieldMarker

  def getFields(self) :
    keys = self._metadata.keys()
    keys.sort()
    return keys
  
  def addField(self, fieldMarker, fieldData) :
    self._metadata[fieldMarker] = fieldData
    
  def getFieldData(self, fieldMarker) :
    try :
      return self._metadata[fieldMarker]
    except :
      return None

  def getMustHaveData(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_MUST_HAVE_DATA)
  
  def getIsNoWordWrap(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_NO_WORD_WRAP)
    
  def getIsSingleWord(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_SINGLE_WORD)

  def getLanguage(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_LANGUAGE)

  def getName(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_NAME)

  def getParentFieldMarker(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_PARENT_FM)

  def getDescription(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_DESCRIPTION)

  def getRangeSet(self) :
    try :
      return self.getFieldData(MarkerMetadata.FM_METADATA_RANGE_SET).split()
    except :
      return None
    
  def getNextFieldMarker(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_NEXT_FM)

  def getMustHaveData(self) :
    return self.getFieldData(MarkerMetadata.FM_METADATA_MUST_HAVE_DATA)



# ---------------------------------------------
# CLASS:  ShoeboxValidator
# DESC:   Class for validating Shoebox entry
#         using metadata
# ---------------------------------------------

class ShoeboxValidator :

  def __init__(self) :
    self._metadata = None
    self._shoebox  = None
        
  def getMetadata(self) :
    return self._metadata

  def setMetadata(self, metadata) :
    self._metadata = metadata

  def getShoebox(self) :
    return self._shoebox

  def setShoebox(self, shoebox) :
    self._shoebox = shoebox

  def validate(self) :
    for e in self.getShoebox().getEntries() :
      for fm in e.getFields() :
        fvs = e.getFieldValuesByFieldMarker(fm)
        for fv in fvs :
          fmm = self.getMetadata().getMarkerMetadata(fm)
          f = Field(fm, fv)
          if not fmm :
            raise NoMetadataFound(f)
          if fmm.getMustHaveData() and not fv :
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_MUST_HAVE_DATA, e, f, fmm)
          if fmm.getIsSingleWord() and " " in fv : 
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_SINGLE_WORD, e, f, fmm)
          if fmm.getRangeSet() and not fv in fmm.getRangeSet() :
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_RANGE_SET, e, f, fmm)
          if fmm.getIsNoWordWrap() and "\n" in fv :
            raise BadFieldValue(BadFieldValue.FIELD_VALUE_ERROR_NO_WORD_WRAP, e, f, fmm)



# ---------------------------------------------
# CLASS:  ValidationError
# DESC:   ???
# ---------------------------------------------

class ValidationError :

  def __init__(self) :
    pass

  def setField(self, field) :
    self._field = field
    
  def getField(self) :
    return self._field



# ---------------------------------------------
# CLASS:  NoMetadataFound
# DESC:   ???
# ---------------------------------------------

class NoMetadataFound(ValidationError) :

  def __init__(self, field) :
    self._field = field



# ---------------------------------------------
# CLASS:  BadFieldValue
# DESC:   ???
# ---------------------------------------------

class BadFieldValue(ValidationError) :
  
  FIELD_VALUE_ERROR_RANGE_SET    = '1'
  FIELD_VALUE_ERROR_NO_WORD_WRAP = '2'
  FIELD_VALUE_ERROR_EMPTY_VALUE  = '3'
  FIELD_VALUE_ERROR_SINGLE_WORD  = '4'
  
  errorTypes = {
    '1' : "Range Set",
    '2' : "No Word Wrap",
    '3' : "Empty Value",
    '4' : "Single Word"
    }

  def __init__(self, errorType, entry, field, fmMetadata) :
    self._entry       = entry
    self._errorType   = errorType
    self._field       = field
    self._fmMetadata  = fmMetadata

  def __str__(self) :
    e   = self.getEntry()
    f   = self.getField()
    typ = self.getErrorDescription()
    s = "'%s' error in '\\%s' field of record %i!\nRecord:\n%s" % (typ, f.getMarker(), e.getNumber(), e.getRawText())
    return s

  def getFieldMarkerMetadata(self) :
    return self._fmMetadata

  def setFieldMarkerMetadata(self, fmMetadata) :
    self._fmMetadata = fmMetadata

  def getErrorDescription(self) :
    try :
      return self.errorTypes[self.getErrorType()]
    except :
      return None
    
  def getErrorType(self) :
    return self._errorType

  def setErrorType(self, errorType) :
    self._errorType = errorType
    
  def getEntry(self) :
    return self._entry

  def setEntry(self, entry) :
    self._entry = entry
