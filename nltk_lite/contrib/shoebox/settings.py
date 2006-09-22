#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Shoebox Settings Parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>/Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module provides functionality for reading Shoebox settings files,
which provide metadata for Shoebox lexicons and texts.
"""

from elementtree import ElementTree
from nltk_lite.corpora.shoebox import ShoeboxFile

class Settings(ShoeboxFile):
    """This class is the base class for Shoebox settings files."""
    
    def __init__(self):
        super(Settings, self).__init__()

    def parse(self, encoding=None):
        """Parses a Shoebox settings file using ElementTree.
        @param encoding: encoding used by settings file
        @type  encoding: string
        """
        builder = ElementTree.TreeBuilder()
        for mkr, value in self.fields(encoding, unwrap=False):
            # Check whether the first char of the field marker
            # indicates a block start (+) or end (-)
            block=mkr[0]
            if block in ("+", "-"):
                mkr=mkr[1:]
            else:
                block=None
            # Build tree on the basis of block char
            if block == "+":
                builder.start(mkr, {})
                builder.data(value)
            elif block == '-':
                builder.end(mkr)
            else:
                builder.start(mkr, {})
                builder.data(value)
                builder.end(mkr)
        return ElementTree.ElementTree(builder.close())


class MarkerSet :
    """This class is a container for FieldMetadata objects."""
    
    def __init__(self) :
        self._dict = {}

    def get_markers(self) :
        """Obtain a list of all of the field markers for the marker set.
        @returns: list of field markers
        @rtype: list of strings"""
        return self._dict.keys()

    def add_field_metadata(self, fmeta) :
        """Add FieldMetadata object to dictionary of marker sets, keyed by field marker.
        @param fmeta: field metadata to be added to collection for marker set
        @type  fmeta: FieldMetadata"""
        self._dict[fmeta.get_marker()] = fmeta
        
    def get_metadata_by_marker(self, mkr) :
        """Obtain a FieldMetadata object for the field marker provided.
        @param mkr: field to obtain metadata for
        @type  mkr: string
        @returns: metadata for field type associated with marker
        @rtype: FieldMetadata"""
        return self._dict[mkr]

        
class FieldMetadata :
    """This class is a container for metadata concerning a field type, including
    the field marker, name, description, language, and parent of the field. In a
    settings file, the raw data looks something like this::

      \\+mkr dx
      \\nam Dialect
      \\desc dialects in which lexeme is found
      \\lng Default
      \\rngset Aita Atsilima Central Pipipaia
      \\mkrOverThis lx
      \\-mkr
    """
    
    def __init__(self,
                 marker    = None,
                 name      = None,
                 desc      = None,
                 lang      = None,
                 rangeset  = None,
                 multiword = None,
                 required  = None,
                 parent    = None) :
        self._marker    = marker
        self._name      = name
        self._desc      = desc
        self._lang      = lang
        self._rangeset  = rangeset
        self._parent    = parent
        self._multiword = multiword
        self._required  = required
        
    def get_marker(self) :
        """Obtain the marker for this field (e.g., 'dx').
        @returns: marker for field
        @rtype: string
        """
        return self._marker

    def get_name(self) :
        """Obtain the name for this field (e.g., 'Dialect').
        @returns: name of field
        @rtype: string
        """
        return self._name

    def get_description(self) :
        """Obtain the marker for this field (e.g., 'dialects in which lexeme is found').
        @returns: description of field
        @rtype: string
        """
        return self._desc

    def get_language(self) :
        """Obtain language in which field is encoded (e.g., 'Default').
        @returns: name of language used for field
        @rtype: string
        """
        return self._lang

    def get_rangeset(self) :
        """Obtain range set for field (e.g., ['Aita', 'Atsilima', 'Central', 'Pipipaia']).
        @returns: list of possible values for field
        @rtype: list of strings
        """
        return self._rangeset

    def set_rangeset(self, rangeset) :
        """Set list of valid values for field.
        @param rangeset: list of valid values for the field
        @type  rangeset: list
        """
        self._rangeset = rangeset
    
    def get_parent(self) :
        """Obtain the marker for the parent of this field (e.g., 'lx').
        @returns: marker for parent field
        @rtype: string
        """
        return self._parent

    def is_multiword(self) :
        """Determine whether the value of the field consits of multiple words.
        @returns: whether field values can be multiword
        @rtype: boolean
        """
        return self._multiword

    def requires_value(self) :
        """Determine whether the field requires a value.
        @returns: whether field requires a value
        @rtype: boolean
        """
        return self._required


class LexiconSettings(Settings) :
    """This class is used to parse and manipulate settings file for
    lexicons in Shoebox SFM."""

    def __init__(self, file):
        self._file      = file
        self._markerset = MarkerSet()
        self._tree      = None
        
    def parse(self, encoding=None) :
        """Parse a Shoebox settings file with lexicon metadata."""
        s = Settings()
        s.open(self._file)
        self._tree = s.parse(encoding=encoding)
        s.close()
        
        # Handle metadata for field markers (aka, marker set)
        for mkr in self._tree.findall('mkrset/mkr') :
            rangeset = None
            if parse_value(mkr, "rngset") :
                rangeset = parse_value(mkr, "rngset").split()
            fm = FieldMetadata(marker    = mkr.text,
                               name      = parse_value(mkr, "nam"),
                               desc      = parse_value(mkr, "desc"),
                               lang      = parse_value(mkr, "lng"),
                               rangeset  = rangeset,
                               multiword = parse_boolean(mkr, "MultipleWordItems"),
                               required  = parse_boolean(mkr, "MustHaveData"),
                               parent    = parse_value(mkr, "mkrOverThis"))
            self._markerset.add_field_metadata(fm)

        # Handle range sets defined outside of marker set
        # WARNING: Range sets outside the marker set override those inside the
        #          marker set
        for rs in self._tree.findall("rngset") :
            mkr = rs.findtext("mkr")
            fm = self._markerset.get_metadata_by_marker(mkr)
            fm.set_rangeset([d.text for d in rs.findall("dat") ])
            self._markerset.add_field_metadata(fm)
            
    def get_record_marker(self) :
        return self._tree.find('mkrset/mkrRecord').text

    def get_marker_set(self) :
        return self._markerset

def parse_boolean(mkr, name) :
    if mkr.find(name) == None :
        return False
    else :
        return True

def parse_value(mkr, name) :
    try :
        return mkr.find(name).text
    except :
        return None

def demo():
    settings = Settings()
    settings.open('MDF_AltH.typ')
    tree = settings.parse(encoding='gbk')
    print tree.find('expset/expMDF/rtfPageSetup/paperSize').text
    tree.write('test.xml')

if __name__ == '__main__':
    demo()
