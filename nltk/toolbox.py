#!/usr/bin/env python

# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2009 NLTK Project
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
from nltk.etree.ElementTree import TreeBuilder, Element, SubElement
from nltk.data import PathPointer, ZipFilePathPointer
from nltk import data

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
        @type sfm_file: C{string}
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
        @type s: C{string}
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
        @type strip: C{boolean}
        @param unwrap: Convert newlines in a field to spaces.
        @type unwrap: C{boolean}
        @param encoding: Name of an encoding to use. If it is specified then 
            the C{fields} method returns unicode strings rather than non 
            unicode strings.
        @type encoding: C{string} or C{None}
        @param errors: Error handling scheme for codec. Same as the C{decode} 
        inbuilt string method.
        @type errors: C{string}
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
    def parse(self, grammar=None,  **kwargs):
        if grammar:
            return self._chunk_parse(grammar=grammar,  **kwargs)
        else:
            return self._record_parse(**kwargs)

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
        @type key: C{string}
        @param kwargs: Keyword arguments passed to L{StandardFormat.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   C{ElementTree._ElementInterface}
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

    def _tree2etree(self, parent):
        from nltk.parse import Tree

        root = Element(parent.node)
        for child in parent:
            if isinstance(child, Tree):
                root.append(self._tree2etree(child))
            else:
                text, tag = child
                e = SubElement(root, tag)
                e.text = text
        return root

    def _chunk_parse(self, grammar=None, top_node='record', trace=0, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file
        parsed according to the chunk grammar.
        
        @type grammar: C{string}
        @param grammar: Contains the chunking rules used to parse the 
        database.  See L{chunk.RegExp} for documentation.
        @type top_node: C{string}
        @param top_node: The node value that should be used for the
            top node of the chunk structure.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            higher will generate verbose tracing output.
        @type kwargs: C{dictionary}
        @param kwargs: Keyword arguments passed to L{toolbox.StandardFormat.fields()}
        @rtype:   C{ElementTree._ElementInterface}
        @return:  Contents of toolbox data parsed according to the rules in grammar
        """
        from nltk import chunk
        from nltk.parse import Tree

        cp = chunk.RegexpParser(grammar, top_node=top_node, trace=trace)
        db = self.parse(**kwargs)
        tb_etree = Element('toolbox_data')
        header = db.find('header')
        tb_etree.append(header)
        for record in db.findall('record'):
            parsed = cp.parse([(elem.text, elem.tag) for elem in record])
            tb_etree.append(self._tree2etree(parsed))
        return tb_etree

_is_value = re.compile(r"\S")

def to_sfm_string(tree, encoding=None, errors='strict', unicode_fields=None):
    """Return a string with a standard format representation of the toolbox
    data in tree (tree can be a toolbox database or a single record).
    
    @param tree: flat representation of toolbox data (whole database or single record)
    @type tree: C{ElementTree._ElementInterface}
    @param encoding: Name of an encoding to use.
    @type encoding: C{string}
    @param errors: Error handling scheme for codec. Same as the C{encode} 
        inbuilt string method.
    @type errors: C{string}
    @param unicode_fields:
    @type unicode_fields: C{dictionary} or C{set} of field names
    @rtype:   C{string}
    @return:  C{string} using standard format markup
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
        @type  encoding: C{string}        
        @param errors: Error handling scheme for codec. Same as C{.decode} inbuilt method.
        @type errors: C{string}
        @param kwargs: Keyword arguments passed to L{StandardFormat.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   C{ElementTree._ElementInterface}
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
    
def remove_blanks(elem):
    """Remove all elements and subelements with no text and no child elements.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    """
    out = list()
    for child in elem:
        remove_blanks(child)
        if child.text or len(child) > 0:
            out.append(child)
    elem[:] = out

def add_default_fields(elem, default_fields):
    """Add blank elements and subelements specified in default_fields.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param default_fields: fields to add to each type of element and subelement
    @type default_fields: dictionary of tuples
    """
    for field in default_fields.get(elem.tag,  []):
        if elem.find(field) is None:
            ET.SubElement(elem, field)
    for child in elem:
        add_default_fields(child, default_fields)

def sort_fields(elem, field_orders):
    """Sort the elements and subelements in order specified in field_orders.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param field_orders: order of fields for each type of element and subelement
    @type field_orders: dictionary of tuples
    """
    order_dicts = dict()
    for field, order in field_orders.items():
        order_dicts[field] = order_key = dict()
        for i, subfield in enumerate(order):
            order_key[subfield] = i 
    _sort_fields(elem, order_dicts)

def _sort_fields(elem, orders_dicts):
    """sort the children of elem"""
    try:
        order = orders_dicts[elem.tag]
    except KeyError:
        pass
    else:
        tmp = [((order.get(child.tag, 1e9), i), child) for i, child in enumerate(elem)]
        tmp.sort()
        elem[:] = [child for key, child in tmp]
    for child in elem:
        if len(child):
            _sort_fields(child, orders_dicts)

def add_blank_lines(tree, blanks_before, blanks_between):
    """Add blank lines before all elements and subelements specified in blank_before.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param blank_before: elements and subelements to add blank lines before
    @type blank_before: dictionary of tuples
    """
    try:
        before = blanks_before[tree.tag]
        between = blanks_between[tree.tag]
    except KeyError:
        for elem in tree:
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
    else:
        last_elem = None
        for elem in tree:
            tag = elem.tag
            if last_elem is not None and last_elem.tag != tag:
                if tag in before and last_elem is not None:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            else:
                if tag in between:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
            last_elem = elem

def demo():
    from itertools import islice

#    zip_path = data.find('corpora/toolbox.zip')
#    lexicon = ToolboxData(ZipFilePathPointer(zip_path, 'toolbox/rotokas.dic')).parse()
    file_path = data.find('corpora/toolbox/rotokas.dic')
    lexicon = ToolboxData(file_path).parse()
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
    file_path = data.find('corpora/toolbox/MDF/MDF_AltH.typ')
    settings.open(file_path)
#    settings.open(ZipFilePathPointer(zip_path, entry='toolbox/MDF/MDF_AltH.typ'))
    tree = settings.parse(unwrap=False, encoding='cp1252')
    print tree.find('expset/expMDF/rtfPageSetup/paperSize').text
    settings_tree = ElementTree(tree)
    print to_settings_string(settings_tree).encode('utf8')

if __name__ == '__main__':
    demo()
