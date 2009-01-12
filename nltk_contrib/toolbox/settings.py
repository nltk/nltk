#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Settings Parser
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Stuart Robinson <stuart@zapata.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides functionality for reading settings files for Toolbox. 
Settings files provide information (metadata) concerning lexicons and texts, 
such as which fields are found within them and what kind of values those 
fields can have.
"""

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

    def get_field_marker_hierarchy(self) :
        # Find root field marker
        root = None
        for fm in self.get_markers() :
            fmmd = self.get_metadata_by_marker(fm)            
            if not fmmd.get_parent_marker() :
                root = fm

        # Build tree for field markers
        builder = TreeBuilder()
        builder.start(root, {})
        self.build_tree(root, builder)
        builder.end(root)
        return builder.close()
        
    def build_tree(self, mkr, builder) :
        markers = self.get_markers()
        markers.sort()
        for tmpmkr in markers :
            fmmd = self.get_metadata_by_marker(tmpmkr)
            # Field is child of current field
            if fmmd.get_parent_marker() == mkr :
                # Handle rangeset
                rangeset = fmmd.get_rangeset()
                if rangeset :
                    builder.start("rangeset", {})
                    for rsi in rangeset :
                        builder.start("value", {})
                        builder.data(rsi)
                        builder.end("value")
                    builder.end("rangeset")

                # Handle rangeset
                name = fmmd.get_name()
                if not name :
                    name = ""
                desc = fmmd.get_description()
                if not desc :
                    desc = ""
                d = {"name" : name,
                     "desc" : desc}
                #print fmmd.get_language()
                #print fmmd.is_multiword()
                #print fmmd.requires_value()
                builder.start(tmpmkr, d)
                self.build_tree(tmpmkr, builder)
                builder.end(tmpmkr)
        return builder
        
        
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
                 marker     = None,
                 name       = None,
                 desc       = None,
                 lang       = None,
                 rangeset   = None,
                 multiword  = None,
                 required   = None,
                 parent_mkr = None) :
        self._marker     = marker
        self._name       = name
        self._desc       = desc
        self._lang       = lang
        self._rangeset   = rangeset
        self._parent_mkr = parent_mkr
        self._multiword  = multiword
        self._required   = required
        
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
    
    def get_parent_marker(self) :
        """Obtain the marker for the parent of this field (e.g., 'lx').
        @returns: marker for parent field
        @rtype: string
        """
        return self._parent_mkr

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


class LexiconSettings(ToolboxSettings) :
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
            fm = FieldMetadata(marker     = mkr.text,
                               name       = self.__parse_value(mkr, "nam"),
                               desc       = self.__parse_value(mkr, "desc"),
                               lang       = self.__parse_value(mkr, "lng"),
                               rangeset   = rangeset,
                               multiword  = self.__parse_boolean(mkr, "MultipleWordItems"),
                               required   = self.__parse_boolean(mkr, "MustHaveData"),
                               parent_mkr = self.__parse_value(mkr, "mkrOverThis"))
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

class InterlinearProcess :
    """This class represents a process for text interlinearization."""

    def __init__(self,
                 from_mkr        = None,
                 to_mkr          = None,
                 out_mkr         = None,
                 gloss_sep       = None,
                 fail_mark       = None,
                 parse_proc      = None,
                 show_fail_mark  = None,
                 show_root_guess = None) :
        self.__from_mkr        = from_mkr
        self.__to_mkr          = to_mkr
        self.__out_mkr         = out_mkr
        self.__gloss_sep       = gloss_sep
        self.__fail_mark       = fail_mark
        self.__parse_proc      = parse_proc
        self.__show_fail_mark  = show_fail_mark
        self.__show_root_guess = show_root_guess

    def get_output_marker(self) :
        return self.__out_mkr
    
    def get_from_marker(self) :
        """The marker searched for in the lookup process."""
        return self.__from_mkr

    def get_to_marker(self) :
        """The marker found in the lookup process."""
        return self.__to_mkr

    def get_gloss_separator(self) :
        """???"""
        return self.__gloss_sep

    def get_failure_marker(self) :
        """The string used in the case of lookup failure,""" 
        return self.__fail_mark

    def is_parse_process(self) :
        """Determine whether this process is a parse process (as opposed to a lookup process)."""
        return self.__parse_proc

    def show_failure_marker(self) :
        """???"""
        return self.__show_fail_mark

    def show_root_guess(self) :
        """???"""
        return self.__show_root_guess


class LookupProcess(InterlinearProcess) :
    pass


class ParseProcess(InterlinearProcess) :
    pass


class TextSettings(ToolboxSettings) :
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

        # Handle interlinear process list
        for proc in self._tree.findall("intprclst/intprc") :
            parseProcess  = self.__parse_boolean(proc, "bParseProc")
            showRootGuess = self.__parse_boolean(proc, "bShowRootGuess")
            showFailMark  = self.__parse_boolean(proc, "bShowFailMark")
            fromMkr       = self.__parse_value(proc, "mkrFrom")
            outMkr        = self.__parse_value(proc, "mkrOut")
            toMkr         = self.__parse_value(proc, "mkrTo").strip()
            glossSep      = self.__parse_value(proc, "GlossSeparator")
            failMark      = self.__parse_value(proc, "FailMark")
            ip = ParseProcess(from_mkr        = fromMkr,
                              to_mkr          = toMkr,
                              gloss_sep       = glossSep,
                              fail_mark       = failMark,
                              parse_proc      = parseProcess,
                              show_fail_mark  = showFailMark,
                              show_root_guess = showRootGuess,
                              out_mkr         = outMkr)                
            if parseProcess :
                pass
            else :
                pass

            print "----- Interlinear Process -----"
            print "  FROM:            [%s]" % ip.get_from_marker()
            print "  TO:              [%s]" % ip.get_to_marker()
            print "  GLOSS SEP:       [%s]" % ip.get_gloss_separator()
            print "  FAIL MARK:       [%s]" % ip.get_failure_marker()
            print "  SHOW FAIL MARK:  [%s]" % ip.show_failure_marker()
            print "  SHOW ROOT GUESS: [%s]" % ip.show_root_guess()
            print "  PARSE PROCESS:   [%s]" % ip.is_parse_process()            

            trilook = proc.find("triLook")
            if trilook :
                print "  -- trilook --"
                print "    DB TYPE:       [%s]" % self.__parse_value(trilook, "dbtyp")            
                print "    MKR OUTPUT:    [%s]" % self.__parse_value(trilook, "mkrOut")

            tripref = proc.find("triPref")
            if tripref :
                print "  -- tripref --"
                print "    DB TYPE:       [%s]" % self.__parse_value(tripref, "dbtyp")            
                print "    MKR OUTPUT:    [%s]" % self.__parse_value(tripref, "mkrOut")
                try :
                    for d in tripref.findall("drflst/drf") :
                        print "    DB:            [%s]" % self.__parse_value(d, "File")
                except :
                    pass
                try :
                    for d in tripref.find("mrflst") :
                        print "    MKR:           [%s]" % d.text
                except :
                    pass

            triroot = proc.find("triRoot")
            if triroot :
                print "  -- triroot --"
                print "    DB TYPE:       [%s]" % self.__parse_value(triroot, "dbtyp")
                print "    MKR OUTPUT:    [%s]" % self.__parse_value(triroot, "mkrOut")
                try :
                    for d in triroot.findall("drflst/drf") :
                        print "    DB:            [%s]" % self.__parse_value(d, "File")
                except :
                    pass
                try :
                    for d in triroot.find("mrflst") :
                        print "    MKR:           [%s]" % d.text
                except :
                    pass

            print ""
            
        # Handle metadata for field markers (aka, marker set)
        for mkr in self._tree.findall('mkrset/mkr') :
            rangeset = None
            if self.__parse_value(mkr, "rngset") :
                rangeset = self.__parse_value(mkr, "rngset").split()
            fm = FieldMetadata(marker     = mkr.text,
                               name       = self.__parse_value(mkr, "nam"),
                               desc       = self.__parse_value(mkr, "desc"),
                               lang       = self.__parse_value(mkr, "lng"),
                               rangeset   = rangeset,
                               multiword  = self.__parse_boolean(mkr, "MultipleWordItems"),
                               required   = self.__parse_boolean(mkr, "MustHaveData"),
                               parent_mkr = self.__parse_value(mkr, "mkrOverThis"))
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

    def get_version(self) :
        return self._tree.find('ver').text

    def get_description(self) :
        return self._tree.find('desc').text    

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
    pass

if __name__ == '__main__':
    demo()
