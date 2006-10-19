# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
#         Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating Toolbox databases.
"""

import os, re
from nltk_lite.corpora import get_basedir
from string import split
from itertools import imap
from StringIO import StringIO
from nltk_lite.etree import ElementTree

class StandardFormat(object):
    """Base class for Standard Format files."""

    def open(self, sfm_file):
        """Open a standard format marker file for sequential reading. 
        
        @param sfm_file: name of the standard format marker input file
        @type sfm_file: string
        """
        self._file = file(sfm_file, 'rU')

    def open_string(self, s):
        """Open a standard format marker file for sequential reading. 
        
        @param s: string to parse as a standard format marker input file
        @type s: string
        """
        self._file = StringIO(s)

    def raw_fields(self):
        """Return an iterator for the fields in the SFM file.
        
        @return: an iterator that returns the next field in a (marker, value) 
            tuple. Linebreaks and trailing white space are preserved except 
            for the final newline in each field.
        @rtype: iterator over C{(marker, value)} tuples
        """
        join_string = '\n'
        line_pat = re.compile(r'^(?:\\(\S+)\s*)?(.*)$')
        # need to get first line outside the loop for correct handling
        # of the first marker if it spans multiple lines
        file_iter = iter(self._file)
        line = file_iter.next()
        mobj = re.match(line_pat, line)
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
        """Return an iterator for the fields in the SFM file.
        
        @param strip: strip trailing whitespace from the last line of each field
        @type strip: boolean
        @param unwrap: Convert newlines in a field to spaces.
        @type unwrap: boolean
        @param encoding: Name of an encoding to use. If it is specified then 
            C{fields} method returns unicode strings rather than non unicode 
            strings.
        @type encoding: string or None
        @param errors: Error handling scheme for codec. Same as C{.decode} inbuilt method.
        @type errors: string
        @param unicode_fields: Set of marker names whose values are UTF-8 encoded.
            Ignored if encoding is None. If the whole file is UTF-8 encoded leave
            as the default value of None.
        @type unicode_fields: set or dictionary (actually any sequence that 
            supports the 'in' operator).
        @return: an iterator that returns the next field in a (marker, value) 
            tuple. C{marker} and C{value} are unicode strings if an C{encoding} was specified in the 
            C{open} method. Otherwise they are nonunicode strings.
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
        """Close a previously opened Standard Format file."""
        self._file.close()
        try:
            del self.line_num
        except AttributeError:
            pass

class ToolboxData(StandardFormat):
    def __init__(self):
        super(ToolboxData, self).__init__()

    def parse(self, *args, **kwargs):
        return self._record_parse(*args, **kwargs)

    def _record_parse(self, key, **kwargs):
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

        @param key: Name of key marker at the start of each record
        @type key: string
        @param kwargs: Keyword arguments passed to L{StandardFormat.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   ElementTree._ElementInterface
        @return:  contents of toolbox data divided into header and records
        """
        builder = ElementTree.TreeBuilder()
        builder.start('toolbox_data', {})
        builder.start('header', {})
        in_records = False
        for mkr, value in self.fields(**kwargs):
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


def parse_corpus(file_name, key=None, **kwargs):
    """
    Return an element tree resulting from parsing the toolbox datafile.
    
    A convenience function that creates a ToolboxData object, opens and parses 
    the toolbox data file. The data file is assumed to be in the toolbox 
    subdirectory of the directory where NLTK looks for corpora, 
    see L{corpora.get_basedir()}.
    @param file_name: Name of file in toolbox corpus directory
    @type file_name: string
    @param key: marker at the start of each record
    @type key: string
    @param kwargs: Keyword arguments passed to L{ToolboxData.parse()}
    @type kwargs: keyword arguments dictionary
    @rtype:   ElementTree._ElementInterface
    @return:  contents of toolbox data divided into header and records
    """ 
    db = ToolboxData()
    db.open(os.path.join(get_basedir(), 'toolbox', file_name))
    return db.parse(key, **kwargs)

import re

_is_value = re.compile(r"\S")

def to_sfm_string(tree, encoding=None, errors='strict', unicode_fields=None):
    """Return a string with a standard format representation of the toolbox
    data in tree.
    
    @type tree: ElementTree._ElementInterface
    @param tree: flat representation of toolbox data
    @rtype:   string
    @return:  string using standard format markup
    """
    # todo encoding, unicode fields, errors?
    if tree.tag != 'toolbox_data':
        raise ValueError, "not a toolbox_data element structure"
    l = list()
    for rec in tree:
        l.append('\n')
        for field in rec:
            value = field.text
            if re.search(_is_value, value):
                l.append("\\%s %s\n" % (field.tag, value))
            else:
                l.append("\\%s%s\n" % (field.tag, value))
    return ''.join(l[1:])

def _parse_record(s):
    """
    @param s: toolbox record as a string
    @type  s: L{string}
    @rtype: iterator over L{list(string)}
    """

    s = "\n" + s                                         # Fields (even first) must start w/ a carriage return 
    if s.endswith("\n") : s = s[:-1]                     # Remove single extra carriage return
    for field in split(s, sep="\n\\")[1:] :              # Parse by carriage return followed by backslash
        parsed_field = split(field, sep=" ", maxsplit=1) # Split properly delineated field
        try :
            yield (parsed_field[0], parsed_field[1])
        except IndexError :
            yield (parsed_field[0], '')


def raw(files='rotokas.dic', include_header=False, head_field_marker=None):
    """
    @param files: One or more toolbox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: flag that determines whether to treat header as record (default is no)
    @type include_header: boolean
    @param head_field_marker: option for explicitly setting which marker to use as the head field
                              when parsing the file (default is automatically determining it from
                              the first field of the first record)
    @type head_field_marker: string
    @rtype: iterator over L{list(string)}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str : files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "toolbox", file)
        fc = open(path, "U").read()
        if fc.strip().startswith(r"\_") :
            (header, body) = split(fc, sep="\n\n", maxsplit=1)
            if include_header:
                yield list(_parse_record(header))
        else :
            body = fc
            
        # Deal with head field marker
        if head_field_marker :
            hfm_with_backslash = "\\" + hfm
        else :
            ff = split(body, sep="\n", maxsplit=1)[0]                # first field
            hfm_with_backslash = split(ff, sep=" ", maxsplit=1)[0]   # raw marker of first field
        recordsep = "\n\n"+hfm_with_backslash                        # separates records from one another
        
        # Parse records
        for r in split("\n\n"+body, sep=recordsep)[1:] : 
            yield list(_parse_record(hfm_with_backslash + r))

# assumes headwords are unique
def dictionary(files='rotokas.dic', include_header=False) :
    """
    @param files: One or more toolbox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: treat header as entry?
    @type include_header: boolean
    @rtype: iterator over L{dict}
    """       
    return imap(dict, raw(files, include_header))

def _dict_list_entry(entry):
    d = {}
    for field in entry:
        if len(field) == 2:
            name, value = field
            if name not in d:
                d[name] = []
            d[name].append(value)
    return d

# if two entries have the same headword this key maps to a list of entries
def dict_list(files='rotokas.dic', include_header=False) :
    """
    @param files: One or more toolbox files to be processed
    @type files: L{string} or L{tuple(string)}
    @param include_header: treat header as entry?
    @type include_header: boolean
    @rtype: iterator over L{dict}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str : files = (files,)

    for entry in raw(files, include_header) :
        yield _dict_list_entry(entry)

def demo():
    from nltk_lite.corpora import toolbox
    from itertools import islice
    from pprint import pprint

    print 'Raw:'
    pprint(list(islice(toolbox.raw(), 3)))

    print 'Dictionary:'
    pprint(list(islice(toolbox.dictionary(), 3)))

    print 'Dictionary-List:'
    pprint(list(islice(toolbox.dict_list(), 3)))

    print 'Complex test cases, no header'
    pprint(list(toolbox.raw("test.dic")))

    print 'Complex test cases, no header, dictionary'
    pprint(list(toolbox.dictionary("test.dic")))

    print 'Complex test cases, no header, dictionary list'
    pprint(list(toolbox.dict_list("test.dic")))

    print 'Complex test cases, with header'
    pprint(list(toolbox.raw("test.dic", include_header=True)))

if __name__ == '__main__':
    demo()
