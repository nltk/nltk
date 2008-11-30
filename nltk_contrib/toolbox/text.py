# Natural Language Toolkit: Shoebox Text
#
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides tools for parsing and manipulating the contents
of a Shoebox text without reference to its metadata.
"""

import re
from utilities import Field, SequentialDictionary
from nltk.corpus.reader.toolbox import StandardFormat


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

    def __init__(self,
                 form         = None,
                 gloss        = None,
                 morphemes    = None,
                 partOfSpeech = None):
        """Constructor that initializes Word object.

        @param form: the surface form for a word
        @type form: string
        @param gloss: the gloss for a word
        @type gloss: string
        @param morphemes: list of Morpheme objects for a word
        @type morphemes: list
        @param partOfSpeech: the part of speech for a word
        @type partOfSpeech: string
        """
        self._form            = form
        self._gloss           = gloss
        self._morphemes       = morphemes
        self._partOfSpeech    = partOfSpeech
        self._rawGloss        = None
        self._rawMorphemes    = None
        self._rawPartOfSpeech = None
        return

    def get_form(self):
        """Gives the surface form of a word."""
        return self._form

    def set_form(self, form):
        """Changes the surface form of a word."""
        self._form = form

    def get_gloss(self):
        """Gives the gloss for a word as a string (without alignment spacing)."""
        return self._gloss

    def set_gloss(self, gloss):
        """Change the gloss for a word."""
        self._gloss = gloss

    def get_morphemes(self):
        """Gives a list of Morpheme objects for a word."""
        return self._morphemes

    def set_morphemes(self, morphemes):
        """Change a list of Morpheme objects for a word."""
        self._morphemes = morphemes

    def get_part_of_speech(self):
        """Gives the part of speech for a word as a string (without alignment spacing)."""
        return self._partOfSpeech

    def set_part_of_speech(self, partOfSpeech):
        """Change the part of speech for a word."""
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
  
    def __init__(self,
                 form         = None,
                 gloss        = None,
                 partOfSpeech = None):
        """Constructor that creates Morpheme object."""        
        self._form = form
        self._gloss = gloss
        self._partOfSpeech = partOfSpeech
        return

    def get_form(self):
        """Returns form for morpheme."""
        return self._form

    def set_form(self, form):
        """Change form for morpheme."""
        self._form = form

    def get_gloss(self):
        """Returns gloss for morpheme."""        
        return self._gloss

    def set_gloss(self, gloss):
        """Change gloss for morpheme."""        
        self._gloss = gloss

    def get_part_of_speech(self):
        """Returns part of speech for morpheme."""        
        return self._partOfSpeech

    def set_part_of_speech(self, partOfSpeech):
        """Change part of speech for morpheme."""
        self._partOfSpeech = partOfSpeech


# --------------------------------------------------------
# CLASS: Line
# DESC:  Object that represents a line from an interlinear
#         text.
# --------------------------------------------------------

class Line:
    """This class defines a line of interlinear glossing, such as::

        \\ref 9
        \\t Vigei    avapaviei                           atarisia.
        \\m vigei    ava -pa       -vi        -ei        atari -sia
        \\g 1.PL.INC go  -PROG     -1.PL.INCL -PRES      fish  -PURP
        \\p PRO.PERS V.I -SUFF.V.3 -SUFF.VI.4 -SUFF.VI.5 V.I   -SUFF.V.4
        \\fp Yumi bai go kisim pis.
        \\fe We're going fishing.

    The tiers of a line are saved as a sequential dictionary with
    all of its associated fields. Identified by the field marker \\ref
    by default."""
    
    def __init__(self,
                 label=None):
        """Constructor that initializes Line object."""
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
        indices = get_indices(self.getFieldValueByFieldMarker("m"))
        print "%s" % indices
        morphemeFormField = self.getFieldValueByFieldMarker("m")
        morphemeGlossField = self.getFieldValueByFieldMarker("g")
        morphemeFormSlices = get_slices_by_indices(morphemeFormField, indices)
        morphemeGlossSlices = get_slices_by_indices(morphemeGlossField, indices)
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

        wordIndices = get_indices(lineWordFormField)
      
        # Slice raw field values by indices
        lineWordFormSlices      = get_slices_by_indices(lineWordFormField,      wordIndices)
        lineMorphemeFormSlices  = get_slices_by_indices(lineMorphemeFormField,  wordIndices)
        lineMorphemeGlossSlices = get_slices_by_indices(lineMorphemeGlossField, wordIndices)
        linePOSSlices           = get_slices_by_indices(linePOSField,           wordIndices)
          
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
                morphemeIndices     = get_indices(wordMorphemeForms)
                morphemeFormSlices  = get_slices_by_indices(wordMorphemeForms,   morphemeIndices)
                morphemeGlossSlices = get_slices_by_indices(wordMorphemeGlosses, morphemeIndices)
                morphemePOSSlices   = get_slices_by_indices(wordPOS,             morphemeIndices)

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
        """Get values for line, given a field and column index."""
        fv = self.getFieldValueByFieldMarker(field_marker)
        field_markers = self.getFieldMarkers()
        sliceFieldMarker = field_markers[columnIndex-1]    
        indices = getIndices(self.getFieldValueByFieldMarker(field_marker))
        slices = get_slices_by_indices(fv, indices)
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
    will have more. Identified by the field marker \id by default.
    """

    def __init__(self,
                 label=None):
        """Constructor that initializes Paragraph object."""
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

class Text(StandardFormat) :
    """
    This class defines an interlinearized text, which consists of a collection of Paragraph objects.
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
        """Add paragraph object to list of paragraph objects.
        @param paragraph: paragraph to be added to text
        @type paragraph: Paragraph
        """
        self._paragraphs.append(paragraph)
      
#     def getRawText(self):
#       return self._rawtext

#     def setRawText(self, rawtext):
#       self._rawtext = rawtext

    def getLineFM(self):
        """Get field marker that identifies a new line."""
        return self._fm_line

    def setLineFM(self, lineHeadFieldMarker):
        """Change default field marker that identifies new line."""
        self._fm_line = lineHeadFieldMarker

    def getParagraphFM(self):
        """Get field marker that identifies a new paragraph."""
        return self._fm_paragraph
  
    def setParagraphFM(self, paragraphHeadFieldMarker):
        """Change default field marker that identifies new paragraph."""
        self._fm_paragraph = paragraphHeadFieldMarker

    def getWordFM(self):
        """Get field marker that identifies word tier."""
        return self._wordFieldMarker

    def setWordFM(self, wordFieldMarker):
        """Change default field marker that identifies word tier."""
        self._wordFieldMarker = wordFieldMarker

    def getMorphemeFM(self):
        """Get field marker that identifies morpheme tier."""
        return self._morphemeFieldMarker

    def setMorphemeFM(self, morphemeFieldMarker):
        """Change default field marker that identifies morpheme tier."""
        self._morphemeFieldMarker = morphemeFieldMarker

    def getMorphemeGlossFM(self):
        """Get field marker that identifies morpheme gloss tier."""
        return self._morphemeGlossFieldMarker

    def setMorphemeGlossFM(self, morphemeGlossFieldMarker):
        """Change default field marker that identifies morpheme gloss tier."""
        self._morphemeGlossFieldMarker = morphemeGlossFieldMarker    

    def get_file(self):
        """Get file path as string."""
        return self._file

    def set_file(self, file):
        """Change file path set upon initialization."""
        self._file = file

    def parse(self) :
        """Parse specified Shoebox file into Text object."""
        # Use low-level functionality to get raw fields and walk through them
        self.open(self._file)
        p, l = None, None
        for f in self.raw_fields() :
            fmarker, fvalue = f
            if fmarker == self.getParagraphFM() :
                if p :
                    self.add_paragraph(p)
                p = Paragraph(fvalue)
            elif fmarker == self.getLineFM() :
                if l :
                    p.add_line(l)
                l = Line(fvalue)
            else :
                if l :
                    l.add_field(Field(fmarker, fvalue))
        p.add_line(l)
        self.add_paragraph(p)


# -------------------------------------------------------------
# FUNCTION: get_indices
# ------------------------------------------------------------
def get_indices(str):
    """This method finds the indices for the leftmost boundaries
    of the units in a line of aligned text.

    Given the field \um, this function will find the
    indices identifing leftmost word boundaries, as
    follows::

            0    5  8   12              <- indices
            |    |  |   |               
            |||||||||||||||||||||||||||
        \sf dit  is een goede           <- surface form
        \um dit  is een goed      -e    <- underlying morphemes
        \mg this is a   good      -ADJ  <- morpheme gloss
        \gc DEM  V  ART ADJECTIVE -SUFF <- grammatical categories
        \ft This is a good explanation. <- free translation

    The function walks through the line char by char::
  
        c   flag.before  flag.after  index?
        --  -----------  ----------  ------
        0   1            0           yes
        1   0            1           no
        2   1            0           no
        3   0            1           no
        4   1            0           no   
        5   1            0           yes

    @param str: aligned text
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
# FUNCTION: get_slices_by_indices
# -------------------------------------------------------------
def get_slices_by_indices(str, indices):
    """Given a string and a list of indices, this function returns
    a list of the substrings defined by those indices. For example,
    given the arguments::
        str='antidisestablishmentarianism', indices=[4, 7, 16, 20, 25]
    this function returns the list::
        ['anti', 'dis', 'establish', 'ment', arian', 'ism']

    @param str: text
    @type str: string
    @param indices: indices 
    @type indices: list of integers
    """
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
