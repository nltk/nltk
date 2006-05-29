# Natural Language Toolkit: Shoebox Text
#
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
TODO
"""

import re
from utilities import FieldParser, SequentialDictionary


# --------------------------------------------------------
# CLASS: Word
# DESC:  Object that represents a word.
# --------------------------------------------------------

class Word:

  def __init__(self):
    self._form = None
    self._gloss = None
    self._morphemes = None
    self._partOfSpeech = None
    self._rawGloss = None
    self._rawMorphemes = None
    self._rawPartOfSpeech = None
    return

  def getForm(self):
    return self._form

  def setForm(self, form):
    self._form = form

  def getGloss(self):
    return self._gloss

  def setGloss(self, gloss):
    self._gloss = gloss

  def getMorphemes(self):
    return self._morphemes

  def setMorphemes(self, morphemes):
    self._morphemes = morphemes

  def getPartOfSpeech(self):
    return self._partOfSpeech

  def setPartOfSpeech(self, partOfSpeech):
    self._partOfSpeech = partOfSpeech

  def getRawGloss(self):
    return self._rawGloss

  def setRawGloss(self, rawGloss):
    self._rawGloss = rawGloss

  def getRawMorphemes(self):
    return self._rawMorphemes

  def setRawMorphemes(self, rawMorphemes):
    self._rawMorphemes = rawMorphemes

  def getRawPartOfSpeech(self):
    return self._rawPartOfSpeech

  def setRawPartOfSpeech(self, rawPartOfSpeech):
    self._rawPartOfSpeech = rawPartOfSpeech



# --------------------------------------------------------
# CLASS: Morpheme
# DESC:  Object that represents a morpheme.
# --------------------------------------------------------

class Morpheme:

  def __init__(self):
    self._form = None
    self._gloss = None
    return

  def getForm(self):
    return self._form

  def setForm(self, form):
    self._form = form

  def getGloss(self):
    return self._gloss

  def setGloss(self, gloss):
    self._gloss = gloss

  def getPartOfSpeech(self):
    return self._partOfSpeech

  def setPartOfSpeech(self, partOfSpeech):
    self._partOfSpeech = partOfSpeech


# --------------------------------------------------------
# CLASS: Line
# DESC:  Object that represents a line from an interlinear
#         text.
# --------------------------------------------------------

class Line:

  def __init__(self, rawtext):
    self._fields = SequentialDictionary()
    self._label = None
    self._rawtext = rawtext
    return

  def addField(self, field):
    fm = field.getMarker()
    fv = field.getValue()
    self._fields[fm] = fv

  def getFieldMarkers(self):
    return self._fields.keys()

  def get_field_values_by_field_marker(self, fieldMarker, sep=None):
    try:
      values = self._fields[fieldMarker]
      if sep == None:
        return values
      else:
        return sep.join(values)
    except KeyError:
      return None

#   def getField(self, fieldMarker):
#     try:
#       return self._fields[fieldMarker]
#     except:
#       return None
    
  def getFieldValues(self):
    return self._fields.values()

  def getLabel(self):
    return self._label

  def getRawText(self):
    return self._rawtext

  def setLabel(self, label):
    self._label = label

  def setRawText(self, rawtext):
    self._rawtext = rawtext

  def getMorphemes(self):
    morphemes = []
    indices = getIndices(self.getFieldValueByFieldMarker("m"))
    print "%s" % indices
    morphemeFormField = self.getFieldValueByFieldMarker("m")
    morphemeGlossField = self.getFieldValueByFieldMarker("g")
    morphemeFormSlices = getSlicesByIndices(morphemeFormField, indices)
    morphemeGlossSlices = getSlicesByIndices(morphemeGlossField, indices)
    for i in range(0, len(morphemeFormSlices)):
      m = Morpheme()
      m.setForm(morphemeFormSlices[i].strip(" ").strip("-"))
      m.setGloss(morphemeGlossSlices[i].strip(" ").strip("-"))
      morphemes.append(m)
    return morphemes
    
  def getWords(self, flagParseMorphemes=True):
    words = []

    # Obtain raw field values
    lineWordFormField      = self.getFieldValueByFieldMarker("t")
    lineMorphemeFormField  = self.getFieldValueByFieldMarker("m")
    lineMorphemeGlossField = self.getFieldValueByFieldMarker("g")
    linePOSField           = self.getFieldValueByFieldMarker("p")

    wordIndices = getIndices(lineWordFormField)
    
    # Slice raw field values by indices
    lineWordFormSlices      = getSlicesByIndices(lineWordFormField,      wordIndices)
    lineMorphemeFormSlices  = getSlicesByIndices(lineMorphemeFormField,  wordIndices)
    lineMorphemeGlossSlices = getSlicesByIndices(lineMorphemeGlossField, wordIndices)
    linePOSSlices           = getSlicesByIndices(linePOSField,           wordIndices)
      
    # Go through each slice
    for i in range(0, len(lineWordFormSlices)):
      wordForm            = lineWordFormSlices[i]
      wordMorphemeForms   = lineMorphemeFormSlices[i]
      wordMorphemeGlosses = lineMorphemeGlossSlices[i]
      wordPOS             = linePOSSlices[i]

      # Initialize word object and set raw fields
      w = Word()
      w.setForm(wordForm.strip(" ").strip("-"))
      w.setRawMorphemes(wordMorphemeForms.strip(" ").strip("-"))
      w.setRawGloss(wordMorphemeGlosses.strip(" ").strip("-"))
      w.setPartOfSpeech(wordPOS.strip(" ").strip("-"))

      # Should the word be inflated with morpheme objects?
      # If so, build morpheme object for each morpheme in word
      if flagParseMorphemes:
        morphemes = []

        # Get indices from morpheme-breakdown line in order to make slices
        morphemeIndices     = getIndices(wordMorphemeForms)
        morphemeFormSlices  = getSlicesByIndices(wordMorphemeForms,   morphemeIndices)
        morphemeGlossSlices = getSlicesByIndices(wordMorphemeGlosses, morphemeIndices)
        morphemePOSSlices   = getSlicesByIndices(wordPOS,             morphemeIndices)

        # Go through each morpheme
        for i in range(0, len(morphemeFormSlices)):
          morphemeForm  = morphemeFormSlices[i].strip(" ")
          morphemeGloss = morphemeGlossSlices[i].strip(" ")
          morphemePOS   = morphemePOSSlices[i].strip(" ")

          # Construct morpheme object from slices
          m = Morpheme()
          m.setForm(morphemeForm)
          m.setGloss(morphemeGloss)
          m.setPartOfSpeech(morphemePOS)

          # Add cooked morpheme to temporary collection for word
          morphemes.append(m)

        # Inflate word with cooked morphemes
        w.setMorphemes(morphemes)

      words.append(w)
    return words

    
  def getFieldValueByFieldMarkerAndColumn(self, fieldMarker, columnIndex):
    fv = self.getFieldValueByFieldMarker(fieldMarker)
    fieldMarkers = self.getFieldMarkers()
    sliceFieldMarker = fieldMarkers[columnIndex-1]    
    indices = getIndices(self.getFieldValueByFieldMarker(fieldMarker))
    slices = getSlicesByIndices(fv, indices)
    return slices[columnIndex-1]


    
# --------------------------------------------------------
# CLASS: LineParser
# DESC:  Parses a raw line of text into a line object.
# --------------------------------------------------------

class LineParser:

  def __init__(self, rawtext):
    self._rawtext = rawtext
    self._fields = {}
    return

  def getRawText(self):
    return self._rawtext

  def setRawText(self, rawtext):
    self._rawtext = rawtext

  def parse(self):
    # Get raw fields from raw text
    rawText = self.getRawText()
    lines = rawText.split("\n")
    rawField = None
    rawFields = []
    for i in range(0, len(lines)):
      line = lines[i]
      if line.startswith("\\"):
        if rawField:
          rawFields.append(rawField)
        rawField = line
      elif rawField:
          rawField = rawField + "\n" + line
    if rawField:
      rawFields.append(rawField)

    # Parse raw fields into field objects
    l = Line(rawText)
    for rawField in rawFields:
      fp = FieldParser(rawField)
      f = fp.parse()
      l.addField(f)
    return l


# --------------------------------------------------------
# CLASS: Paragraph
# DESC:  Object that represents a paragraph (i.e., a unit
#         larger than a line) from an interlinear text.
# --------------------------------------------------------

class Paragraph:

  def __init__(self, rawtext):
    self._rawtext = rawtext
    self._lines = []
    self._label = None
    return

  def addLine(self, line):
    self._lines.append(line)

  def getLabel(self):
    return self._label

  def getLines(self):
    return self._lines

  def getRawText(self):
    return self._rawtext
    
  def setLabel(self, label):
    self._label = label

  def setRawText(self, rawtext):
    self._rawtext = rawtext


# --------------------------------------------------------
# CLASS: ParagraphParser
# DESC:  Parses a raw text paragraph into a paragraph
#         object.
# --------------------------------------------------------

class ParagraphParser:

  def __init__(self, rawtext,
               lineHeadFieldMarker="ref",
               paragraphHeadFieldMarker="id"):
    self._rawtext = rawtext
    self._lineHeadFieldMarker = lineHeadFieldMarker
    self._paragraphHeadFieldMarker = paragraphHeadFieldMarker
    return

  def getLineHeadFieldMarker(self):
    return self._lineHeadFieldMarker

  def setLineHeadFieldMarker(self, lineHeadFieldMarker):
    self._lineHeadFieldMarker = lineHeadFieldMarker

  def getParagraphHeadFieldMarker(self):
    return self._paragraphHeadFieldMarker

  def setParagraphHeadFieldMarker(self, paragraphHeadFieldMarker):
    self._paragraphHeadFieldMarker = paragraphHeadFieldMarker

  def getRawText(self):
    return self._rawtext

  def setRawText(self, rawtext):
    self._rawtext = rawtext

  def extractRawLines(self, fileContents):
    lines = fileContents.split("\n")
    rawLines = []
    rawLine = None
    for i in range(0, len(lines)):
      line = lines[i]
      if line.startswith("\\" + self.getLineHeadFieldMarker()):
        if rawLine:
          rawLines.append(rawLine)
        rawLine = line
      elif rawLine:
          rawLine = "%s\n%s" % (rawLine, line)
    if rawLine:
      rawLines.append(rawLine)
    return rawLines

  def extractCookedLines(self, rawLines):
    cookedLines = []
    for rl in rawLines:
      lp = LineParser(rl)
      l = lp.parse()
      cookedLines.append(l)
    return cookedLines
  
  def parse(self):
    # Extract and parse raw text
    rawText = self.getRawText()
    regex = r"\\" + self.getParagraphHeadFieldMarker() + " (.*)"
    mo = re.search(regex, rawText)
    label = mo.group(1)
    rawLines = self.extractRawLines(rawText)
    cookedLines = self.extractCookedLines(rawLines)

    # Create paragraph object from cooked lines
    p = Paragraph(rawText)
    p.setLabel(label)
    for cl in cookedLines:
      p.addLine(cl)
    return p


# --------------------------------------------------------
# CLASS: InterlinearText
# DESC:  Object that represents an interlinear text and
#         provides functionality for its querying and
#         manipulation.
# --------------------------------------------------------

class Text:

  def __init__(self, rawtext):
    self._rawtext = rawtext
    self._paragraphs = []
    return

  def getLines(self):
    lines = []
    for p in self.getParagraphs():
      for l in p.getLines():
        lines.append(l)
    return lines
      
  def getParagraphs(self):
    return self._paragraphs

  def setParagraphs(self, paragraphs):
    self._paragraphs = paragraphs

  def addParagraph(self, paragraph):
    self._paragraphs.append(paragraph)
    
  def getRawText(self):
    return self._rawtext

  def setRawText(self, rawtext):
    self._rawtext = rawtext


# --------------------------------------------------------
# CLASS: TextParser
# DESC:  Parser that takes an interlinear text file and
#         returns an Text object.
# --------------------------------------------------------

class TextParser:

  def __init__(self, filePath):
    self._filePath                 = filePath
    self._lineHeadFieldMarker      = "ref"
    self._paragraphHeadFieldMarker = "id"
    self._morphemeFieldMarker      = "m"
    self._morphemeGlossFieldMarker = "g"
    self._wordFieldMarker          = "w"
    return

  def getLineHeadFieldMarker(self):
    return self._lineHeadFieldMarker

  def setLineHeadFieldMarker(self, lineHeadFieldMarker):
    self._lineHeadFieldMarker = lineHeadFieldMarker

  def getParagraphHeadFieldMarker(self):
    return self._paragraphHeadFieldMarker

  def setParagraphHeadFieldMarker(self, paragraphHeadFieldMarker):
    self._paragraphHeadFieldMarker = paragraphHeadFieldMarker

  def getWordFieldMarker(self):
    return self._wordFieldMarker

  def setWordFieldMarker(self, wordFieldMarker):
    self._wordFieldMarker = wordFieldMarker

  def getMorphemeFieldMarker(self):
    return self._morphemeFieldMarker

  def setMorphemeFieldMarker(self, morphemeFieldMarker):
    self._morphemeFieldMarker = morphemeFieldMarker

  def getMorphemeGlossFieldMarker(self):
    return self._morphemeGlossFieldMarker

  def setMorphemeGlossFieldMarker(self, morphemeGlossFieldMarker):
    self._morphemeGlossFieldMarker = morphemeGlossFieldMarker    

  def getFilePath(self):
    return self._filePath

  def setFilePath(self, filePath):
    self._filePath = filePath

  def extractRawParagraphs(self, fileContents):
    rawLines = fileContents.split("\n")
    rawParagraphs = []
    rawParagraph = None
    for i in range(0, len(rawLines)):
      line = rawLines[i]
      paragraphFieldMarker = "\\" + self.getParagraphHeadFieldMarker()
      if line.startswith(paragraphFieldMarker):
        if rawParagraph:
          rawParagraphs.append(rawParagraph)
        rawParagraph = line
      elif rawParagraph:
          rawParagraph = "%s\n%s" % (rawParagraph, line)
    if rawParagraph:
      rawParagraphs.append(rawParagraph)      
    return rawParagraphs

  def extractCookedParagraphs(self, rawParagraphs):
    cookedParagraphs = []
    for rp in rawParagraphs:
      pp = ParagraphParser(rp)
      pp.setLineHeadFieldMarker(self.getLineHeadFieldMarker())
      pp.setParagraphHeadFieldMarker(self.getParagraphHeadFieldMarker())
      p = pp.parse()
      cookedParagraphs.append(p)
    return cookedParagraphs
  
  def parse(self):
    fo = open(self.getFilePath(), 'rU')
    fileContents = fo.read()
    fo.close()
    ilt = Text(fileContents)
    rawParagraphs = self.extractRawParagraphs(fileContents)
    cookedParagraphs = self.extractCookedParagraphs(rawParagraphs)
    for cp in cookedParagraphs:
      ilt.addParagraph(cp)
    return ilt



# --------------------------------------------------------
# UTILITY FUNCTIONS
# --------------------------------------------------------


# -------------------------------------------------------------
# FUNCTION: getIndices 
# DESC:     Given a line of text that is morpheme aligned, the
#            indices for each left word boundary is returned.
#
#         0    5  8   12              <- indices
#         |    |  |   |               
#         |||||||||||||||||||||||||||
#     \sf dit  is een goede           <- surface form
#     \um dit  is een goed      -e    <- underlying morphemes
#     \mg this is a   good      -ADJ  <- morpheme gloss
#     \gc DEM  V  ART ADJECTIVE -SUFF <- grammatical categories
#     \ft This is a good explanation. <- free translation
# 
#            c  flag.before  flag.after  index?
#            -- -----------  ----------  ------
#            0  1            0           yes
#            1  0            1           no
#            2  1            0           no
#            3  0            1           no
#            4  1            0           no   
#            5  1            0           yes
#            ...         
# ------------------------------------------------------------
def getIndices(str):
  indices = []
  flag = 1
  for i in range(0, len(str)):
    c = str[i]
    if flag and c != ' ':
      indices.append(i)
      flag = 0
    elif not flag and c == ' ':
      flag = 1
  return indices


# --------------------------------------------------------
# FUNCTION: getSlicesByIndices
# DESC:     Given a string a list of indices, this
#            function returns a list the substrings
#            defined by those indices.
#            For example, given the arguments 
#             'antidisestablishmentarianism',
#             [4, 7, 16, 20, 25]
#            this function returns
#             ['anti', 'dis', 'establish', 'ment',
#              arian', 'ism']
# --------------------------------------------------------
def getSlicesByIndices(str, indices):
  slices = []
  for i in range(0, len(indices)):
    slice = None
    start = indices[i]
    if i == len(indices)-1:
      slice = str[start: ]
    else:
      finish = indices[i+1]
      slice = str[start: finish]
    slices.append(slice)
  return slices
