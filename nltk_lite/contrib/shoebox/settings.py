#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Shoebox Settings Parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>/Stuart Robinson <stuart@zapata.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module provides functionality for reading settings files for Shoebox/Toolbox. Settings files provides information (metadata) concerning lexicons and texts, such as which fields are found within them and what kind of values those fields can have.
"""

from elementtree import ElementTree
from nltk_lite.corpora.shoebox import ShoeboxFile

class Settings(ShoeboxFile):
    """This class is the base class for settings files."""
    
    def __init__(self):
        super(Settings, self).__init__()

    def parse(self, encoding=None, errors='strict'):
        """Parses a settings file using ElementTree.
        
        @param encoding: encoding used by settings file
        @type  encoding: string        
        @param errors: Error handling scheme for codec. Same as C{.decode} inbuilt method.
        @type errors: string
        """
        builder = ElementTree.TreeBuilder()
        for mkr, value in self.fields(unwrap=False, encoding=encoding, errors=errors):
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
    """This class is a container for FieldMetadata objects. A marker set
    contains a list of the fields in a database together with information
    about those files.

    The raw SFB looks like this::

        \\+mkrset 
        \\lngDefault Default
        \\mkrRecord lx

        \\+mkr dt
        \\nam Date Last Edited
        \\lng Default
        \\mkrOverThis lx
        \\-mkr

        \\+mkr lx
        \\nam Rotokas Word
        \\lng Rotokas
        \\-mkr
        \\-mkrset
        """             
    
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
    """This class is a container for information about a field, including its marker, name,
    description, language, range set (valid values), and parent marker.

    The raw field metadata looks like this::

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
        """Determine whether the value of the field consists of multiple words.
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
    lexicons."""

    def __init__(self, file):
        self._file      = file
        self._markerset = MarkerSet()
        self._tree      = None
        
    def parse(self, encoding=None) :
        """Parse a settings file with lexicon metadata."""
        s = Settings()
        s.open(self._file)
        self._tree = s.parse(encoding=encoding)
        s.close()
        
        # Handle metadata for field markers (aka, marker set)
        for mkr in self._tree.findall('mkrset/mkr') :
            rangeset = None
            if self.__parse_value(mkr, "rngset") :
                rangeset = self.__parse_value(mkr, "rngset").split()
            fm = FieldMetadata(marker    = mkr.text,
                               name      = self.__parse_value(mkr, "nam"),
                               desc      = self.__parse_value(mkr, "desc"),
                               lang      = self.__parse_value(mkr, "lng"),
                               rangeset  = rangeset,
                               multiword = self.__parse_boolean(mkr, "MultipleWordItems"),
                               required  = self.__parse_boolean(mkr, "MustHaveData"),
                               parent    = self.__parse_value(mkr, "mkrOverThis"))
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

    def __parse_boolean(self, mkr, name) :
        if mkr.find(name) == None :
            return False
        else :
            return True

    def __parse_value(self, mkr, name) :
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
