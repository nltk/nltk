#!/usr/bin/env python

# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating 
Toolbox databases and settings files.
"""

import os, re, codecs
from StringIO import StringIO
from nltk.etree.ElementTree import TreeBuilder, Element
from nltk.data import PathPointer,  ZipFilePathPointer

class StandardFormat(object):
    """
    Class for reading and processing standard format marker files and strings.
    """
    def __init__(self, filename=None, encoding=None):
        self._encoding = encoding
        if filename is not None:
            self.open(filename)

    def open(self, sfm_file):
        """Open a standard format marker file for sequential reading. 
        
        @param sfm_file: name of the standard format marker input file
        @type sfm_file: string
        """
        if isinstance(sfm_file, PathPointer):
            # [xx] We don't use 'rU' mode here -- do we need to?
            #      (PathPointer.open doesn't take a mode option)
            self._file = sfm_file.open(self._encoding)
        else:
            self._file = codecs.open(sfm_file, 'rU', self._encoding)

    def open_string(self, s):
        """Open a standard format marker string for sequential reading. 
        
        @param s: string to parse as a standard format marker input file
        @type s: string
        """
        self._file = StringIO(s)

    def raw_fields(self):
        """Return an iterator for the fields in the standard format marker
        file.
        
        @return: an iterator that returns the next field in a (marker, value) 
            tuple. Linebreaks and trailing white space are preserved except 
            for the final newline in each field.
        @rtype: iterator over C{(marker, value)} tuples
        """
        join_string = '\n'
        line_regexp = r'^%s(?:\\(\S+)\s*)?(.*)$'
        first_line_pat = re.compile(line_regexp % u'\ufeff?')
        line_pat = re.compile(line_regexp % '')
        # need to get first line outside the loop for correct handling
        # of the first marker if it spans multiple lines
        file_iter = iter(self._file)
        line = file_iter.next()
        mobj = re.match(first_line_pat, line)
        mkr, line_value = mobj.groups()
        value_lines = [line_value,]
        self.line_num = 0
        for line in file_iter:
            self.line_num += 1
            mobj = re.match(line_pat, line)
            line_mkr, line_value = mobj.groups()
            if line_mkr:
                yield (mkr, join_string.join(value_lines))
                mkr = line_mkr
                value_lines = [line_value,]
            else:
                value_lines.append(line_value)
        self.line_num += 1
        yield (mkr, join_string.join(value_lines))

    def fields(self, strip=True, unwrap=True, encoding=None, errors='strict', unicode_fields=None):
        """Return an iterator for the fields in the standard format marker file.
        
        @param strip: strip trailing whitespace from the last line of each field
        @type strip: boolean
        @param unwrap: Convert newlines in a field to spaces.
        @type unwrap: boolean
        @param encoding: Name of an encoding to use. If it is specified then 
            the C{fields} method returns unicode strings rather than non 
            unicode strings.
        @type encoding: string or None
        @param errors: Error handling scheme for codec. Same as the C{decode} 
        inbuilt string method.
        @type errors: string
        @param unicode_fields: Set of marker names whose values are UTF-8 encoded.
            Ignored if encoding is None. If the whole file is UTF-8 encoded set 
            C{encoding='utf8'} and leave C{unicode_fields} with its default
            value of None.
        @type unicode_fields: set or dictionary (actually any sequence that 
            supports the 'in' operator).
        @return: an iterator that returns the next field in a C{(marker, value)} 
            tuple. C{marker} and C{value} are unicode strings if an C{encoding} was specified in the 
            C{fields} method. Otherwise they are nonunicode strings.
        @rtype: iterator over C{(marker, value)} tuples
        """
        if encoding is None and unicode_fields is not None:
            raise ValueError, 'unicode_fields is set but not encoding.'
        unwrap_pat = re.compile(r'\n+')
        for mkr, val in self.raw_fields():
            if encoding:
                if unicode_fields is not None and mkr in unicode_fields:
                    val = val.decode('utf8', errors)
                else:
                    val = val.decode(encoding, errors)
                mkr = mkr.decode(encoding, errors)
            if unwrap:
                val = unwrap_pat.sub(' ', val)
            if strip:
                val = val.rstrip()
            yield (mkr, val)

    def close(self):
        """Close a previously opened standard format marker file or string."""
        self._file.close()
        try:
            del self.line_num
        except AttributeError:
            pass

class ToolboxData(StandardFormat):
    def parse(self, *args, **kwargs):
        return self._record_parse(*args, **kwargs)

    def _record_parse(self, key=None, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file with
        all markers at the same level.
       
        Thus the following Toolbox database::
            \_sh v3.0  400  Rotokas Dictionary
            \_DateStampHasFourDigitYear
            
            \lx kaa
            \ps V.A
            \ge gag
            \gp nek i pas
            
            \lx kaa
            \ps V.B
            \ge strangle
            \gp pasim nek

        after parsing will end up with the same structure (ignoring the extra 
        whitespace) as the following XML fragment after being parsed by 
        ElementTree::
            <toolbox_data>
                <header>
                    <_sh>v3.0  400  Rotokas Dictionary</_sh>
                    <_DateStampHasFourDigitYear/>
                </header>
    
                <record>
                    <lx>kaa</lx>
                    <ps>V.A</ps>
                    <ge>gag</ge>
                    <gp>nek i pas</gp>
                </record>
                
                <record>
                    <lx>kaa</lx>
                    <ps>V.B</ps>
                    <ge>strangle</ge>
                    <gp>pasim nek</gp>
                </record>
            </toolbox_data>

        @param key: Name of key marker at the start of each record. If set to 
        None (the default value) the first marker that doesn't begin with an 
        underscore is assumed to be the key.
        @type key: string
        @param kwargs: Keyword arguments passed to L{StandardFormat.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   ElementTree._ElementInterface
        @return:  contents of toolbox data divided into header and records
        """
        builder = TreeBuilder()
        builder.start('toolbox_data', {})
        builder.start('header', {})
        in_records = False
        for mkr, value in self.fields(**kwargs):
            if key is None and not in_records and mkr[0] != '_':
                key = mkr
            if mkr == key:
                if in_records:
                    builder.end('record')
                else:
                    builder.end('header')
                    in_records = True
                builder.start('record', {})
            builder.start(mkr, {})
            builder.data(value)
            builder.end(mkr)
        if in_records:
            builder.end('record')
        else:
            builder.end('header')
        builder.end('toolbox_data')
        return builder.close()

_is_value = re.compile(r"\S")

def to_sfm_string(tree, encoding=None, errors='strict', unicode_fields=None):
    """Return a string with a standard format representation of the toolbox
    data in tree (tree can be a toolbox database or a single record).
    
    @param tree: flat representation of toolbox data (whole database or single record)
    @type tree: ElementTree._ElementInterface
    @param encoding: Name of an encoding to use.
    @type encoding: string
    @param errors: Error handling scheme for codec. Same as the C{encode} 
        inbuilt string method.
    @type errors: string
    @param unicode_fields:
    @type unicode_fields: string
    @rtype:   string
    @return:  string using standard format markup
    """
    if tree.tag == 'record':
        root = Element('toolbox_data')
        root.append(tree)
        tree = root

    if tree.tag != 'toolbox_data':
        raise ValueError, "not a toolbox_data element structure"
    if encoding is None and unicode_fields is not None:
        raise ValueError, \
            "if encoding is not specified then neither should unicode_fields"
    l = []
    for rec in tree:
        l.append('\n')
        for field in rec:
            mkr = field.tag
            value = field.text
            if encoding is not None:
                if unicode_fields is not None and mkr in unicode_fields:
                    cur_encoding = 'utf8'
                else:
                    cur_encoding = encoding
                if re.search(_is_value, value):
                    l.append((u"\\%s %s\n" % (mkr, value)).encode(cur_encoding, errors))
                else:
                    l.append((u"\\%s%s\n" % (mkr, value)).encode(cur_encoding, errors))
            else:
                if re.search(_is_value, value):
                    l.append("\\%s %s\n" % (mkr, value))
                else:
                    l.append("\\%s%s\n" % (mkr, value))
    return ''.join(l[1:])

class ToolboxSettings(StandardFormat):
    """This class is the base class for settings files."""
    
    def __init__(self):
        super(ToolboxSettings, self).__init__()

    def parse(self, encoding=None, errors='strict', **kwargs):
        """Parses a settings file using ElementTree.
        
        @param encoding: encoding used by settings file
        @type  encoding: string        
        @param errors: Error handling scheme for codec. Same as C{.decode} inbuilt method.
        @type errors: string
        @param kwargs: Keyword arguments passed to L{StandardFormat.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   ElementTree._ElementInterface
        @return:  contents of toolbox settings file with a nested structure
        """
        builder = TreeBuilder()
        for mkr, value in self.fields(encoding=encoding, errors=errors, **kwargs):
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
        return builder.close()

def to_settings_string(tree, encoding=None, errors='strict', unicode_fields=None):
    # write XML to file
    l = list()
    _to_settings_string(tree.getroot(), l, encoding=encoding, errors=errors, unicode_fields=unicode_fields)
    return ''.join(l)

def _to_settings_string(node, l, **kwargs):
    # write XML to file
    tag = node.tag
    text = node.text
    if len(node) == 0:
        if text:
            l.append('\\%s %s\n' % (tag, text))
        else:
            l.append('\\%s\n' % tag)
    else:
        if text:
            l.append('\\+%s %s\n' % (tag, text))
        else:
            l.append('\\+%s\n' % tag)
        for n in node:
            _to_settings_string(n, l, **kwargs)
        l.append('\\-%s\n' % tag)
    return
    
def demo():
    from itertools import islice

    zip_path = os.path.join(os.environ['NLTK_DATA'], 'corpora',  'toolbox.zip')
    lexicon = ToolboxData(ZipFilePathPointer(zip_path, entry='toolbox/rotokas.dic')).parse()
    print 'first field in fourth record:'
    print lexicon[3][0].tag
    print lexicon[3][0].text
    
    print '\nfields in sequential order:'
    for field in islice(lexicon.find('record'), 10):
        print field.tag, field.text

    print '\nlx fields:'
    for field in islice(lexicon.findall('record/lx'), 10):
        print field.text

    from nltk.etree.ElementTree import ElementTree
    
    settings = ToolboxSettings()
    # need a more general solution for the following line
    settings.open(ZipFilePathPointer(zip_path, entry='toolbox/MDF/MDF_AltH.typ'))
    tree = settings.parse(unwrap=False, encoding='cp1252')
    print tree.find('expset/expMDF/rtfPageSetup/paperSize').text
    settings_tree = ElementTree(tree)
    print to_settings_string(settings_tree).encode('utf8')

if __name__ == '__main__':
    demo()
