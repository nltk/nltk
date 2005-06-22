import re, string
from utilities import SequentialDictionary

# ---------------------------------------------
# CLASS:  Field
# DESC:   Tuple that holds a field marker and
#         its field value
# ---------------------------------------------
class Field :

  def __init__(self, fieldMarker, fieldValue) :
    self._field = (fieldMarker, fieldValue)

  def __str__(self) :
    return "\\%s %s" % (self.getMarker(), self.getValue())
  
  def getMarker(self) :
    return self._field[0]

  def getValue(self) :
    return self._field[1]


# ---------------------------------------------
# CLASS:  StandardFormatFileParser
# DESC:   Class for parsing a file in Standard
#         Format (SF) into a manipulable data
#         structure.
# ---------------------------------------------

class StandardFormatFileParser :

  def __init__(self, filePath) :
    self._entries = []
    self._rawHeader = None
    self._headFieldMarker = None
    self._filePath = filePath

  def setFileContent(self, fileContent) :
    self._fileContent = fileContent

  def getFileContent(self) :
    return self._fileContent

  def setFilePath(self, filePath) :
    self._filePath = filePath

  def getFilePath(self) :
    return self._filePath

  def setHeadFieldMarker(self, headFieldMarker) :
    self._headFieldMarker = headFieldMarker

  def getHeadFieldMarker(self) :
    return self._headFieldMarker

  def parseComment(self, rawText) :
    #print "[%s]" % rawText
    return
  
  def parse(self) :
    sf = StandardFormatFile()

    # Get file contents
    fo = open(self.getFilePath(), 'rU')
    sbFc = fo.read()
    fo.close()
    self.setFileContent(sbFc)
    fc = self.getFileContent()

    # Handle header
    header = self.extractHeader()
    sf.setHeader(header)

    # Extract cooked entries
    i = 0
    for ce in self.extractCookedEntries() :
      i = i + 1
      ce.setNumber(i)
      sf.addEntry(ce)
    return sf

  def extractHeader(self) :
    header = None
    fc = self.getFileContent()
    header = fc.split("\n\n")[0]
    #print "[%s]" % header
    return header
  
  def extractCookedEntries(self) :
    cookedEntries = []
    rawEntries = self.extractRawEntries()
    for re in rawEntries :
      ep = EntryParser(re, self.getHeadFieldMarker())
      self._entries.append(ep.parse())
    return self._entries
    
  def extractRawEntries(self) :
    fc = self.getFileContent()

    # Try to guess what the head field is
    if not self.getHeadFieldMarker() :
      mo = re.search(r"\\([A-Za-z][A-Za-z0-9]*)", fc)
      headField = mo.group(1)
      #print "[%s]" % headField
      self.setHeadFieldMarker(headField)

    # Extract lines of text
    rawLines = fc.split("\n")
    rawEntries = []
    rawEntry = None
    for i in range(0, len(rawLines)) :
      line = rawLines[i]
      #print "%04i [%s]" % (i, line)

      if line.startswith("\\_") :
        self.parseComment(line)
      elif line.startswith("\\" + self.getHeadFieldMarker()) :
        if rawEntry :
          rawEntries.append(rawEntry)
        rawEntry = line
      elif rawEntry :
          rawEntry = "%s\n%s" % (rawEntry, line)

    if rawEntry :
      rawEntries.append(rawEntry)
    return rawEntries



# ---------------------------------------------
# CLASS:  EntryParser
# DESC:   Class for parsing an entry from a
#         file in Standard Format (SF) into
#         a dictionary in which each key-value
#         pair is a field marker and an array of
#         associated values.
# ---------------------------------------------

class EntryParser :

  def __init__(self, rawText=None, headFieldMarker=None) :
    self._entires = {}
    self._rawText = rawText
    self._headFieldMarker = headFieldMarker

  def getHeadFieldMarker(self) :
    return self._headFieldMarker

  def setHeadFieldMarker(self, headFieldMarker) :
    self._headFieldMarker = headFieldMarker
    
  def setRawText(self, rawText) :
    self._rawText = rawText

  def getRawText(self) :
    return self._rawText

  def parse(self) :
    e = Entry()
    rawText = self.getRawText()
    e.setRawText(rawText)
    regex = r"\\([a-zA-Z]+) +(.*)(?!\\)"
    reo = re.compile(regex)
    for mo in reo.findall(rawText) :
      fieldMarker = mo[0]
      fieldData   = mo[1]
      if fieldMarker == self.getHeadFieldMarker() :
        hf = (fieldMarker, fieldData)
        e.setHeadField(hf)
      else :
        e.addField(fieldMarker, fieldData)
    return e



# ---------------------------------------------
# CLASS:  StandardFormatFile
# DESC:   Class for representing a file in
#         Standard Format
# ---------------------------------------------

class StandardFormatFile :

  def __init__(self) :
    self._filename = ''
    self._header   = ''
    self._entries  = []
    
  def __str__(self) :
    s = "%s\n" % self.getHeader()
    for e in self.getEntries() :
      s = "%s%s\n" % (s, e)
    return s
    
  def setHeader(self, header) :
    self._header = header

  def getHeader(self) :
    return self._header

  def getEntries(self) :
    return self._entries

  def addEntry(self, entry) :
    self._entries.append(entry)



# ---------------------------------------------
# CLASS:  Entry
# DESC:   Class for representing an entry in
#         a Standard Format (SF) file.
# ---------------------------------------------

class Entry :

  def __init__(self) :
    self._fields    = SequentialDictionary()
    self._rawText   = ""
    self._number    = None
    self._headField = None

  def __str__(self) :
    s = ""
    hf = self.getHeadField()
    s = s + "\n\\%s %s" % (hf[0], hf[1])
    fields = self.getFields()
    for fm, fvs in fields.items() :
      for fv in fvs :
        s = s + "\n\\%s %s" % (fm, fv)          
    return s
    
  def setRawText(self, rawText) :
    self._rawText = rawText

  def getRawText(self) :
    return self._rawText

  def setNumber(self, number) :
    self._number = number

  def getNumber(self) :
    return self._number
  
  def getFields(self) :
    return self._fields

  def getFieldMarkers(self) :
    return self._fields.keys()

  def getFieldValuesByFieldMarkerAsString(self, fieldMarker, separator=" ") :
    try :
      return separator.join(self._fields[fieldMarker])
    except KeyError :
      return ""
    
  def getFieldValuesByFieldMarker(self, fieldMarker) :
    try :
      return self._fields[fieldMarker]
    except KeyError :
      return None

  def getHeadField(self) :
    return self._headField

  def setHeadField(self, headField) :
    self._headField = headField
    
  def setField(self, fieldMarker, fieldData) :
    fvs = []
    fvs.append(fieldData)
    self._fields[fieldMarker] = fvs

  def setFieldValues(self, fieldMarker, fieldValues) :
    self._fields[fieldMarker] = fieldValues
  
  def addField(self, fieldMarker, fieldData) :
    if self._fields.has_key(fieldMarker) :
      fvs = self._fields[fieldMarker]
      fvs.append(fieldData)
    else :
      fvs = []
      fvs.append(fieldData)
    self._fields[fieldMarker] = fvs

  def removeField(self, fieldMarker) :
    if self._fields.has_key(fieldMarker) :
      del self._fields[fieldMarker]
