# Natural Language Toolkit: Shoebox Text
#
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Functionality for parsing and manipulating the contents of a Shoebox
text without reference to its metadata.
"""

import re
from utilities import Field, SequentialDictionary
from nltk_lite.corpora import shoebox
from shoebox import ShoeboxFile


# --------------------------------------------------------
# CLASS: Word
# DESC:  Object that represents a word.
# --------------------------------------------------------

class Word:
    """
    This class defines a word object, which consists of fixed number
    of attributes: a wordform, a gloss, a part of speech, and a list
    of morphemes.
    """

    def __init__(self):
        self._form = None
        self._gloss = None
        self._morphemes = None
        self._partOfSpeech = None
        self._rawGloss = None
        self._rawMorphemes = None
        self._rawPartOfSpeech = None
        return

    def get_form(self):
        return self._form

    def set_form(self, form):
        self._form = form

    def get_gloss(self):
        return self._gloss

    def set_gloss(self, gloss):
        self._gloss = gloss

    def get_morphemes(self):
        return self._morphemes

    def set_morphemes(self, morphemes):
        self._morphemes = morphemes

    def get_part_of_speech(self):
        return self._partOfSpeech

    def set_part_of_speech(self, partOfSpeech):
      self._partOfSpeech = partOfSpeech

    def get_raw_gloss(self):
      return self._rawGloss

    def set_raw_gloss(self, rawGloss):
        self._rawGloss = rawGloss

    def get_raw_morphemes(self):
        return self._rawMorphemes

    def set_raw_morphemes(self, rawMorphemes):
        self._rawMorphemes = rawMorphemes

    def get_raw_part_of_speech(self):
        return self._rawPartOfSpeech

    def set_raw_part_of_speech(self, rawPartOfSpeech):
        self._rawPartOfSpeech = rawPartOfSpeech


# --------------------------------------------------------
# CLASS: Morpheme
# DESC:  Object that represents a morpheme.
# --------------------------------------------------------

class Morpheme:
    """
    This class defines a morpheme object, which consists of fixed number
    of attributes: a surface form, an underlying form, a gloss, and a
    part of speech.
    """
  
    def __init__(self):
        self._form = None
        self._gloss = None
        self._partOfSpeech = None
        return

    def get_form(self):
        return self._form

    def set_form(self, form):
        self._form = form

    def get_gloss(self):
        return self._gloss

    def set_gloss(self, gloss):
        self._gloss = gloss

    def get_part_of_speech(self):
        return self._partOfSpeech

    def set_part_of_speech(self, partOfSpeech):
        self._partOfSpeech = partOfSpeech


# --------------------------------------------------------
# CLASS: Line
# DESC:  Object that represents a line from an interlinear
#         text.
# --------------------------------------------------------

class Line:
    """
    This class defines a line of interlinear glossing, which consists
    of a line of raw text and a sequential dictionary with all of its
    associated fields (some interlinearized, some not).
    """
    
    def __init__(self, label=None):
        self._fields = SequentialDictionary()
        self._label = label
        return

    def add_field(self, field):
        """Add field to line."""
        fm = field.get_marker()
        fv = field.get_values()
        self._fields[fm] = fv

    def get_field_markers(self):
        """Obtain list of unique fields for the line."""
        return self._fields.keys()

    def get_field_values_by_field_marker(self, field_marker, sep=None):
        """Obtain all fields for a line, given a field marker."""
        try:
            values = self._fields[field_marker]
            if sep == None:
                return values
            else:
                return sep.join(values)
        except KeyError:
            return None

  #   def getField(self, field_marker):
  #     try:
  #       return self._fields[field_marker]
  #     except:
  #       return None
      
    def get_field_values(self):
        """Obtain list of field values for the line."""
        return self._fields.values()

    def get_label(self):
        """Obtain identifier for line."""
        return self._label

    def get_raw_text(self):
        """Obtain original line of text."""
        return self._rawtext

    def set_label(self, label):
        """Set identifier for line."""
        self._label = label

    def set_raw_text(self, rawtext):
        """Set original line of text."""
        self._rawtext = rawtext

    def get_morphemes(self):
        """Obtain a list of morpheme objects for the line."""
        morphemes = []
        indices = getIndices(self.getFieldValueByFieldMarker("m"))
        print "%s" % indices
        morphemeFormField = self.getFieldValueByFieldMarker("m")
        morphemeGlossField = self.getFieldValueByFieldMarker("g")
        morphemeFormSlices = getSlicesByIndices(morphemeFormField, indices)
        morphemeGlossSlices = getSlicesByIndices(morphemeGlossField, indices)
        for i in range(0, len(morphemeFormSlices)):
            m = Morpheme()
            m.set_form(morphemeFormSlices[i].strip(" ").strip("-"))
            m.set_gloss(morphemeGlossSlices[i].strip(" ").strip("-"))
            morphemes.append(m)
        return morphemes
      
    def get_words(self, flagParseMorphemes=True):
        """Obtain a list of word objects for the line."""
        words = []

        # Obtain raw field values
        lineWordFormField      = self.get_field_values_by_field_marker("t")
        lineMorphemeFormField  = self.get_field_values_by_field_marker("m")
        lineMorphemeGlossField = self.get_field_values_by_field_marker("g")
        linePOSField           = self.get_field_values_by_field_marker("p")

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
            w.set_form(wordForm.strip(" ").strip("-"))
            w.set_raw_morphemes(wordMorphemeForms.strip(" ").strip("-"))
            w.set_raw_gloss(wordMorphemeGlosses.strip(" ").strip("-"))
            w.set_part_of_speech(wordPOS.strip(" ").strip("-"))

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
                    m.set_form(morphemeForm)
                    m.set_gloss(morphemeGloss)
                    m.set_part_of_speech(morphemePOS)
                    
                    # Add cooked morpheme to temporary collection for word
                    morphemes.append(m)

                # Inflate word with cooked morphemes
                w.set_morphemes(morphemes)

            words.append(w)
        return words

    def get_field_value_by_field_marker_and_column(self, field_marker, columnIndex):
        """Get values, given a field and column index,  for line."""
        fv = self.getFieldValueByFieldMarker(field_marker)
        field_markers = self.getFieldMarkers()
        sliceFieldMarker = field_markers[columnIndex-1]    
        indices = getIndices(self.getFieldValueByFieldMarker(field_marker))
        slices = getSlicesByIndices(fv, indices)
        return slices[columnIndex-1]


# --------------------------------------------------------
# CLASS: Paragraph
# DESC:  Object that represents a paragraph (i.e., a unit
#         larger than a line) from an interlinear text.
# --------------------------------------------------------

class Paragraph:
    """
    This class defines a unit of analysis above the line and below
    the text. Every text will have at least one paragraph and some
    will have more.
    """

    def __init__(self, label=None):
        self._lines = []
        self._label = label
        return

    def add_line(self, line):
        """Add line object to list of line objects for paragraph."""
        self._lines.append(line)

    def get_label(self):
        """Obtain identifier for paragraph."""
        return self._label

    def get_lines(self):
        """Get list of line objects for paragraph."""
        return self._lines
    
    def set_label(self, label):
        """Set identifier for paragraph."""
        self._label = label


# --------------------------------------------------------
# CLASS: InterlinearText
# DESC:  Object that represents an interlinear text and
#         provides functionality for its querying and
#         manipulation.
# --------------------------------------------------------

class Text(ShoeboxFile) :
    """
    This class defines an interlinearized text.
    """
  
    def __init__(self,
                 file              = None,
                 fm_line           = "ref",
                 fm_paragraph      = "id",
                 fm_morpheme       = "m",
                 fm_morpheme_gloss = "g",
                 fm_word           = "w"
                 ):
        """Constructor for Text object. All arguments are optional. By default,
        the fields used to parse the Shoebox file are the following:
        @param file: filepath
        @type file: str
        @param fm_line: field marker identifying line (default: 'ref')
        @type fm_line: str
        @param fm_paragraph: field marker identifying paragraph (default: 'id')
        @type fm_paragraph: str
        @param fm_morpheme: field marker identifying morpheme tier (default: 'm')
        @type fm_morpheme: str
        @param fm_morpheme_gloss: field marker identifying morpheme gloss tier (default: 'g')
        @type fm_morpheme_gloss: str
        @param fm_word: field marker identifying word tier (???)
        @type fm_word: str 
        """
        self._file              = file
        self._fm_line           = fm_line
        self._fm_paragraph      = fm_paragraph
        self._fm_morpheme       = "m"
        self._fm_morpheme_gloss = "g"
        self._fm_word           = "w"
        #self._rawtext = rawtext
        self._paragraphs        = []
        return

    def get_lines(self):
        """Obtain a list of line objects (ignoring paragraph structure)."""
        lines = []
        for p in self.get_paragraphs():
            for l in p.get_lines():
                lines.append(l)
        return lines
        
    def get_paragraphs(self):
        """Obtain a list of paragraph objects."""
        return self._paragraphs

#     def set_paragraphs(self, paragraphs):
#       self._paragraphs = paragraphs

    def add_paragraph(self, paragraph):
        self._paragraphs.append(paragraph)
      
#     def getRawText(self):
#       return self._rawtext

#     def setRawText(self, rawtext):
#       self._rawtext = rawtext

    def getLineHeadFieldMarker(self):
        return self._fm_line

    def setLineHeadFieldMarker(self, lineHeadFieldMarker):
        self._fm_line = lineHeadFieldMarker

    def getParagraphHeadFieldMarker(self):
        return self._fm_paragraph
  
    def setParagraphHeadFieldMarker(self, paragraphHeadFieldMarker):
        self._fm_paragraph = paragraphHeadFieldMarker

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

    def parse(self) :
        """Parse specified Shoebox file into Text object."""
        # Use low-level functionality to get raw fields and walk through them
        self.open(self._file)
        p, l = None, None
        for f in self.raw_fields() :
            fmarker, fvalue = f
            if fmarker == self.getParagraphHeadFieldMarker() :
                if p :
                    self.add_paragraph(p)
                p = Paragraph(fvalue)
            elif fmarker == self.getLineHeadFieldMarker() :
                if l :
                    p.add_line(l)
                l = Line(fvalue)
            else :
                if l :
                    l.add_field(Field(fmarker, fvalue))
        p.add_line(l)
        self.add_paragraph(p)


# -------------------------------------------------------------
# FUNCTION: getIndices
# NOTES:    Given the field \um, this function will find the
#           indices identifing leftmost word boundaries, as
#           follows:
#
#               0    5  8   12              <- indices
#               |    |  |   |               
#               |||||||||||||||||||||||||||
#           \sf dit  is een goede           <- surface form
#           \um dit  is een goed      -e    <- underlying morphemes
#           \mg this is a   good      -ADJ  <- morpheme gloss
#           \gc DEM  V  ART ADJECTIVE -SUFF <- grammatical categories
#           \ft This is a good explanation. <- free translation
#
#           The function walks through the line char by char:
# 
#           c   flag.before  flag.after  index?
#           --  -----------  ----------  ------
#           0   1            0           yes
#           1   0            1           no
#           2   1            0           no
#           3   0            1           no
#           4   1            0           no   
#           5   1            0           yes
#           ... ...          ...         ...
#           ...         
# ------------------------------------------------------------
def getIndices(str):
    """This method finds the indices for each leftmost word
    boundary in a line of morpheme-aligned text.
           
    @param str: morpheme-aligned text
    @type str: string
    """
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


# -------------------------------------------------------------
# FUNCTION: getSlicesByIndices
# NOTES:    Given the arguments 
#             'antidisestablishmentarianism', [4, 7, 16, 20, 25]
#           this function returns
#             ['anti', 'dis', 'establish', 'ment', arian', 'ism']
# -------------------------------------------------------------
def getSlicesByIndices(str, indices):
    """Given a string a list of indices, this function returns
    a list the substrings defined by those indices."""
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
