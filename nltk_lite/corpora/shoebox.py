# Natural Language Toolkit: Shoebox Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Stuart Robinson <Stuart.Robinson@mpi.nl>
#         Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating Shoebox databases.
"""

import os, re
from nltk_lite.corpora import get_basedir
from string import split
from itertools import imap
from StringIO import StringIO

class ShoeboxFile(object):
    """Base class for Shoebox database and settings files."""

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

    def fields(self, strip=True, unwrap=True, encoding=None, unicode_fields=None):
        """Return an iterator for the fields in the SFM file.
        
        @param strip: strip trailing whitespace from the last line of each field
        @type strip: boolean
        @param unwrap: Convert newlines in a field to spaces.
        @type unwrap: boolean
        @param encoding: Name of an encoding to use. If it is specified then 
            C{fields} method returns unicode strings rather than non unicode 
            strings.
        @type encoding: string or None
        @param unicode_fields: Set of marker names whose values are in 
            unicode. Ignored if encoding is None.
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
                if mkr in unicode_fields:
                    val = val.decode('utf8')
                else:
                    val = val.decode(encoding)
                mkr = mkr.decode(encoding)
            if unwrap:
                val = unwrap_pat.sub(' ', val)
            if strip:
                val = val.rstrip()
            yield (mkr, val)

    def close(self):
        """Close a previously opened SFM file."""
        self._file.close()
        try:
            del self.line_num
        except AttributeError:
            pass


def _parse_record(s):
    """
    @param s: shoebox record as a string
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
    @param files: One or more shoebox files to be processed
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
        path = os.path.join(get_basedir(), "shoebox", file)
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
    @param files: One or more shoebox files to be processed
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
    @param files: One or more shoebox files to be processed
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
    from nltk_lite.corpora import shoebox
    from itertools import islice
    from pprint import pprint

    print 'Raw:'
    pprint(list(islice(shoebox.raw(), 3)))

    print 'Dictionary:'
    pprint(list(islice(shoebox.dictionary(), 3)))

    print 'Dictionary-List:'
    pprint(list(islice(shoebox.dict_list(), 3)))

    print 'Complex test cases, no header'
    pprint(list(shoebox.raw("test.dic")))

    print 'Complex test cases, no header, dictionary'
    pprint(list(shoebox.dictionary("test.dic")))

    print 'Complex test cases, no header, dictionary list'
    pprint(list(shoebox.dict_list("test.dic")))

    print 'Complex test cases, with header'
    pprint(list(shoebox.raw("test.dic", include_header=True)))

if __name__ == '__main__':
    demo()
