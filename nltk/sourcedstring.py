# Natural Language Toolkit: Sourced Strings
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
X{Sourced strings} are strings that are annotated with information
about the location in a document where they were originally found.
Sourced strings are subclassed from Python strings.  As a result, they
can usually be used anywhere a normal Python string can be used.

  >>> newt_contents = '''\
  ... She turned me into a newt!
  ... I got better.'''
  >>> newt_doc = SourcedString(newt_contents, 'newt.txt')
  >>> print repr(newt_doc)
  'She turned me into a newt!\nI got better.'@[0:40]
  >>> newt = newt_doc.split()[5] # Find the sixth word.
  >>> print repr(newt)
  'newt!'@[21:26]
"""

import re, sys
from nltk.internals import slice_bounds, abstract

__all__ = [
    'StringSource', 
    'ConsecutiveCharStringSource', 'ContiguousCharStringSource',
    'SourcedString', 'SourcedStringStream', 'SourcedStringRegexp',
    'SimpleSourcedString', 'CompoundSourcedString',
    'SimpleSourcedByteString', 'SimpleSourcedUnicodeString', 
    'CompoundSourcedByteString', 'CompoundSourcedUnicodeString',
    ]

#//////////////////////////////////////////////////////////////////////
# String Sources
#//////////////////////////////////////////////////////////////////////

class StringSource(object):
    """
    A description of the location of a string in a document.  Each
    C{StringSource} consists of a document identifier, along with
    information about the begin and end offsets of each character in
    the string.  These offsets are typically either byte offsets or
    character offsets.  (Note that for unicode strings, byte offsets
    and character offsets are not the same thing.)

    C{StringSource} is an abstract base class.  Two concrete
    subclasses are used depending on the properties of the string
    whose source is being described:

      - L{ConsecutiveCharStringSource} describes the source of strings
        whose characters have consecutive offsets (in particular, byte
        strings w/ byte offsets; and unicode strings with character
        offsets).
        
      - L{ContiguousCharStringSource} describes the source of strings
        whose characters are contiguous, but do not necessarily have
        consecutive offsets (in particular, unicode strings with byte
        offsets).
        
    @ivar docid: An identifier (such as a filename) that specifies
        which document contains the string.

    @ivar offsets: A list of offsets specifying the location of each
        character in the document.  The C{i}th character of the string
        begins at offset C{offsets[i]} and ends at offset
        C{offsets[i+1]}.  The length of the C{offsets} list is one
        greater than the list of the string described by this
        C{StringSource}.
    
    @ivar begin: The document offset where the string begins.  (I.e.,
        the offset of the first character in the string.)
        C{source.begin} is always equal to C{source.offsets[0]}.
    
    @ivar end: The document offset where the string ends.  (For
        character offsets, one plus the offset of the last character;
        for byte offsets, one plus the offset of the last byte that
        encodes the last character).  C{source.end} is always equal
        to C{source.offsets[-1]}.
    """
    def __new__(cls, docid, *args, **kwargs):
        # If the StringSource constructor is called directly, then
        # choose one of its subclasses to delegate to.
        if cls is StringSource:
            if args:
                raise TypeError("Specifcy either begin and end, or "
                                 "offsets, using keyword arguments")
            if 'begin' in kwargs and 'end' in kwargs and 'offsets' not in kwargs:
                cls = ConsecutiveCharStringSource
            elif ('begin' not in kwargs and 'end' not in kwargs and
                  'offsets' in kwargs):
                cls = ContiguousCharStringSource
            else:
                raise TypeError("Specify either begin and end, or offsets "
                                 "(but not both)")
        # Construct the object.
        return object.__new__(cls)

    def __init__(self, docid, **kwargs):
        """
        Create a new C{StringSource}.  When the C{StringSource}
        constructor is called directly, it automatically delegates to
        one of its two subclasses:

            - If C{begin} and C{end} are specified, then a
              L{ConsecutiveCharStringSource} is returned.
            - If C{offsets} is specified, then a 
              L{ContiguousCharStringSource} is returned.
              
        In both cases, the arguments must be specified as keyword
        arguments (not positional arguments).
        """
    
    def __getitem__(self, index):
        """
        Return a L{StringSource} describing the location where the
        specified character was found.  In particular, if C{s} is the
        string that this source describes, then return a
        L{StringSource} describing the location of C{s[index]}.
        
        @raise IndexError: If index is out of range.
        """
        if isinstance(index, slice):
            start, stop = slice_bounds(self, index)
            return self.__getslice__(start, stop)
        else:
            if index < 0: index += len(self)
            if index < 0 or index >= len(self):
                raise IndexError('StringSource index out of range')
            return self.__getslice__(index, index+1)

    @abstract
    def __getslice__(self, start, stop):
        """
        Return a L{StringSource} describing the location where the
        specified substring was found.  In particular, if C{s} is the
        string that this source describes, then return a
        L{StringSource} describing the location of C{s[start:stop]}.
        """

    @abstract
    def __len__(self):
        """
        Return the length of the string described by this
        C{StringSource}.  Note that this may not be equal to
        C{self.end-self.begin} for unicode strings described using
        byte offsets.
        """
        
    def __str__(self):
        if self.end == self.begin+1:
            return '@%s[%s]' % (self.docid, self.begin,)
        else:
            return '@%s[%s:%s]' % (self.docid, self.begin, self.end)

    def __cmp__(self, other):
        return (cmp(self.docid, self.docid) or
                cmp([(charloc.begin, charloc.end) for charloc in self],
                    [(charloc.begin, charloc.end) for charloc in other]))

    def __hash__(self):
        # Cache hash values.
        if not hasattr(self, '_hash'):
            self._hash = hash( (self.docid,
                                tuple((charloc.begin, charloc.end)
                                      for charloc in self)) )
        return self._hash

class ConsecutiveCharStringSource(StringSource):
    """
    A L{StringSource} that specifies the source of strings whose
    characters have consecutive offsets.  In particular, the following
    two properties must hold for all valid indices:

      - source[i].end == source[i].begin + 1
      - source[i].end == source[i+1].begin

    These properties allow the source to be stored using just a start
    offset and an end offset (along with a docid).
    
    This C{StringSource} can be used to describe byte strings that are
    indexed using byte offsets or character offsets; or unicode
    strings that are indexed using character offsets.
    """
    def __init__(self, docid, begin, end):
        if not isinstance(begin, (int, long)):
            raise TypeError("begin attribute expected an integer")
        if not isinstance(end, (int, long)):
            raise TypeError("end attribute expected an integer")
        if not  end >= begin:
            raise ValueError("begin must be less than or equal to end")
        self.docid = docid
        self.begin = begin
        self.end = end

    @property
    def offsets(self):
        return tuple(range(self.begin, self.end+1))

    def __len__(self):
        return self.end-self.begin

    def __getslice__(self, start, stop):
        start = max(0, min(len(self), start))
        stop = max(start, min(len(self), stop))
        return ConsecutiveCharStringSource(
            self.docid, self.begin+start, self.begin+stop)

    def __cmp__(self, other):
        if isinstance(other, ConsecutiveCharStringSource):
            return (cmp(self.docid, other.docid) or
                    cmp(self.begin, other.begin) or
                    cmp(self.end, other.end))
        else:
            return StringSource.__cmp__(self, other)

    def __repr__(self):
        return 'StringSource(%r, begin=%r, end=%r)' % (
            self.docid, self.begin, self.end)

class ContiguousCharStringSource(StringSource):
    """
    A L{StringSource} that specifies the source of strings whose
    character are contiguous, but do not necessarily have consecutive
    offsets.  In particular, each character's end offset must be equal
    to the next character's start offset:

      - source[i].end == source[i+1].begin
    
    This property allow the source to be stored using a list of
    C{len(source)+1} offsets (along with a docid).
    
    This C{StringSource} can be used to describe unicode strings that
    are indexed using byte offsets.
    """
    CONSTRUCTOR_CHECKS_OFFSETS = False
    def __init__(self, docid, offsets):
        offsets = tuple(offsets)
        if len(offsets) == 0:
            raise ValueError("at least one offset must be specified")
        if self.CONSTRUCTOR_CHECKS_OFFSETS:
            for i in range(len(offsets)):
                if not isinstance(offsets[i], (int,long)):
                    raise TypeError("offsets must be integers")
                if i>0 and offsets[i-1]>offsets[i]:
                    raise TypeError("offsets must be monotonic increasing")
        self.docid = docid
        self.offsets = offsets

    @property
    def begin(self): return self.offsets[0]

    @property
    def end(self): return self.offsets[-1]

    def __len__(self):
        return len(self.offsets)-1

    def __getslice__(self, start, stop):
        start = max(0, min(len(self), start))
        stop = max(start, min(len(self), stop))
        return ContiguousCharStringSource(
            self.docid, self.offsets[start:stop+1])

    def __cmp__(self, other):
        if isinstance(other, ConsecutiveCharStringSource):
            return (cmp(self.docid, other.docid) or
                    cmp(self.offsets, other._offsets))
        else:
            return StringSource.__cmp__(self, other)

    def __repr__(self):
        return 'StringSource(%r, offsets=%r)' % (self.docid, self.offsets)
    
#//////////////////////////////////////////////////////////////////////
# Base Class for Sourced Strings.
#//////////////////////////////////////////////////////////////////////

class SourcedString(basestring):
    """
    A string that is annotated with information about the location in
    a document where it was originally found.  Sourced strings are
    subclassed from Python strings.  As a result, they can usually be
    used anywhere a normal Python string can be used.

    There are two types of sourced strings: L{SimpleSourcedString}s,
    which correspond to a single substring of a document; and
    L{CompoundSourcedString}s, which are constructed by concatenating
    strings from multiple sources.  Each of these types has two
    concrete subclasses: one for unicode strings (subclassed from
    ``unicode``), and one for byte strings (subclassed from ``str``).

    Two sourced strings are considered equal if their contents are
    equal, even if their sources differ.  This fact is important in
    ensuring that sourced strings act like normal strings.  In
    particular, it allows sourced strings to be used with code that
    was originally intended to process plain Python strings.

    If you wish to determine whether two sourced strings came from the
    same location in the same document, simply compare their
    L{sources} attributes.  If you know that both sourced strings are
    L{SimpleSourcedStrings}, then you can compare their L{source}
    attribute instead.

    String operations that act on sourced strings will preserve
    location information whenever possible.  However, there are a few
    types of string manipulation that can cause source information to
    be discarded.  The most common examples of operations that will
    lose source information are:

      - ``str.join()``, where the joining string is not sourced.
      - ``str.replace()``, where the original string is not sourced.
      - String formatting (the ``%`` operator).
      - Regular expression substitution.

    @ivar sources: A sorted tuple of C{(index, source)} pairs.  Each
        such pair specifies that the source of
        C{self[index:index+len(source)]} is C{source}.  Any characters
        for which no source is specified are sourceless (e.g., plain
        Python characters that were concatenated to a sourced string).

        When working with simple sourced strings, it's usually easier
        to use the L{source} attribute instead; however, the
        C{sources} attribute is defined for both simple and compound
        sourced strings.
    """
    def __new__(cls, contents, source):
        # If the SourcedString constructor is called directly, then
        # choose one of its subclasses to delegate to.
        if cls is SourcedString:
            if isinstance(contents, str):
                cls = SimpleSourcedByteString
            elif isinstance(contents, unicode):
                cls = SimpleSourcedUnicodeString
            else:
                raise TypeError("Expected 'contents' to be a unicode "
                                "string or a byte string")

        # Create the new object using the appropriate string class's
        # __new__, which takes just the contents argument.
        return cls._stringtype.__new__(cls, contents)

    _stringtype = None
    """A class variable, defined by subclasses of L{SourcedString},
       determining what type of string this class contains.  Its
       value must be either C{str} or C{unicode}."""

    #//////////////////////////////////////////////////////////////////////
    #{ Splitting & Stripping Methods
    #//////////////////////////////////////////////////////////////////////
    
    def lstrip(self, chars=None):
        s = self._stringtype.lstrip(self, chars)
        return self[len(self)-len(s):]
    
    def rstrip(self, chars=None):
        s = self._stringtype.rstrip(self, chars)
        return self[:len(s)]
    
    def strip(self, chars=None):
        return self.lstrip(chars).rstrip(chars)

    _WHITESPACE_RE = re.compile(r'\s+')
    def split(self, sep=None, maxsplit=None):
        # Check for unicode/bytestring mismatches:
        if self._mixed_string_types(sep, maxsplit):
            return self._decode_and_call('split', sep, maxsplit)
        # Use a regexp to split self.
        if sep is None: sep_re = self._WHITESPACE_RE
        else: sep_re = re.compile(re.escape(sep))
        if maxsplit is None: return sep_re.split(self)
        else: return sep_re.split(self, maxsplit)

    def rsplit(self, sep=None, maxsplit=None):
        # Check for unicode/bytestring mismatches:
        if self._mixed_string_types(sep, maxsplit):
            return self._decode_and_call('rsplit', sep, maxsplit)
        # Split on whitespace use a regexp.
        if sep is None:
            seps = list(self._WHITESPACE_RE.finditer(self))
            if maxsplit: seps = seps[-maxsplit:]
            if not seps: return [self]
            result = [self[:seps[0].start()]]
            for i in range(1, len(seps)):
                result.append(self[seps[i-1].end():seps[i].start()])
            result.append(self[seps[-1].end():])
            return result
        # Split on a given string: use rfind.
        else:
            result = []
            piece_end = len(self)
            while maxsplit != 0:
                sep_pos = self.rfind(sep, 0, piece_end)
                if sep_pos < 0: break
                result.append(self[sep_pos+len(sep):piece_end])
                piece_end = sep_pos
                if maxsplit is not None: maxsplit -= 1
            if piece_end > 0:
                result.append(self[:piece_end])
            return result[::-1]

    def partition(self, sep):
        head, sep, tail = self._stringtype.partition(self, sep)
        i, j = len(head), len(head)+len(sep)
        return (self[:i], self[i:j], self[j:])
    
    def rpartition(self, sep):
        head, sep, tail = self._stringtype.rpartition(self, sep)
        i, j = len(head), len(head)+len(sep)
        return (self[:i], self[i:j], self[j:])
    
    _NEWLINE_RE = re.compile(r'\n')
    _LINE_RE = re.compile(r'.*\n?')
    def splitlines(self, keepends=False):
        if keepends:
            return self._LINE_RE.findall(self)
        else:
            return self._NEWLINE_RE.split(self)

    #//////////////////////////////////////////////////////////////////////
    #{ String Concatenation Methods
    #//////////////////////////////////////////////////////////////////////

    @staticmethod
    def concat(substrings):
        """
        Return a sourced string formed by concatenating the given list
        of substrings.  Adjacent substrings will be merged when
        possible.

        Depending on the types and values of the supplied substrings,
        the concatenated string's value may be a Python string (C{str}
        or C{unicode}), a L{SimpleSourcedString}, or a
        L{CompoundSourcedString}.
        """
        # Flatten nested compound sourced strings, and merge adjacent
        # strings where possible:
        merged = []
        for substring in substrings:
            SourcedString.__add_substring_to_list(substring, merged)

        # Return the concatenated string.
        if len(merged) == 0:
            return ''
        elif len(merged) == 1:
            return merged[0]
        else:
            return CompoundSourcedString(merged)

    def __add__(self, other):
        return SourcedString.concat([self, other])

    def __radd__(self, other):
        return SourcedString.concat([other, self])

    def __mul__(self, other):
        if other <= 0:
            return self._stringtype('')
        else:
            result = self
            for i in range(1, other):
                result += self
            return result

    def __rmul__(self, other):
        return self.__mul__(other)

    def join(self, sequence):
        seq_iter = iter(sequence)
        # Add the first element; but if sequence is empty, return an
        # empty string.
        try:
            s = seq_iter.next()
        except StopIteration:
            return self._stringtype('')

        # Add the remaining elements, separated by self.
        for elt in seq_iter:
            s += self
            s += elt
        return s

    @staticmethod
    def __add_substring_to_list(substring, result):
        """
        Helper for L{concat()}: add C{substring} to the end of the
        list of substrings in C{result}.  If C{substring} is compound,
        then add its own substrings instead.  Merge adjacent
        substrings whenever possible.  Discard empty un-sourced
        substrings.
        """
        # Flatten nested compound sourced strings.
        if isinstance(substring, CompoundSourcedString):
            for s in substring.substrings:
                SourcedString.__add_substring_to_list(s, result)

        # Discard empty Python substrings.
        elif len(substring) == 0 and not isinstance(substring, SourcedString):
            pass # discard.
        
        # Merge adjacent simple sourced strings (when possible).
        elif (result and isinstance(result[-1], SimpleSourcedString) and
              isinstance(substring, SimpleSourcedString) and
              result[-1].end == substring.begin and
              result[-1].docid == substring.docid):
            result[-1] = SourcedString.__merge_simple_substrings(
                result[-1], substring)

        # Merge adjacent Python strings.
        elif (result and not isinstance(result[-1], SourcedString) and
              not isinstance(substring, SourcedString)):
            result[-1] += substring

        # All other strings just get appended to the result list.
        else:
            result.append(substring)

    @staticmethod
    def __merge_simple_substrings(lhs, rhs):
        """
        Helper for L{__add_substring_to_list()}: Merge C{lhs} and
        C{rhs} into a single simple sourced string, and return it.
        """
        contents = lhs._stringtype.__add__(lhs, rhs)
        if (isinstance(lhs.source, ConsecutiveCharStringSource) and
            isinstance(rhs.source, ConsecutiveCharStringSource)):
            source = ConsecutiveCharStringSource(
                lhs.source.docid, lhs.source.begin, rhs.source.end)
        else:
            source = ContiguousCharStringSource(
                lhs.source.docid, lhs.source.offsets+rhs.source.offsets[1:])
        return SourcedString(contents, source)

    #//////////////////////////////////////////////////////////////////////
    #{ Justification Methods
    #//////////////////////////////////////////////////////////////////////

    def center(self, width, fillchar=' '):
        return (fillchar * ((width-len(self))/2)  + self +
                fillchar * ((width-len(self)+1)/2))

    def ljust(self, width, fillchar=' '):
        return self + fillchar * (width-len(self))
        
    def rjust(self, width, fillchar=' '):
        return fillchar * (width-len(self)) + self

    def zfill(self, width):
        return self.rjust(width, '0')

    #//////////////////////////////////////////////////////////////////////
    #{ Replacement Methods
    #//////////////////////////////////////////////////////////////////////

    # [xx] There's no reason in principle why this can't preserve
    # location information.  But for now, it doesn't.
    def __mod__(self, other):
        return self._stringtype.__mod__(self, other)

    def replace(self, old, new, count=0):
        # Check for unicode/bytestring mismatches:
        if self._mixed_string_types(old, new, count):
            return self._decode_and_call('replace', old, new, count)
        # Use a regexp to find all occurences of old, and replace them w/ new.
        result = ''
        pos = 0
        for match in re.finditer(re.escape(old), self):
            result += self[pos:match.start()]
            result += new
            pos = match.end()
        result += self[pos:]
        return result

    def expandtabs(self, tabsize=8):
        if len(self) == 0: return self
        pieces = re.split(r'([\t\n])', self)
        result = ''
        offset = 0
        for piece in pieces:
            if piece == '\t':
                spaces = 8 - (offset % tabsize)
                # Each inserted space's source is the same as the
                # source of the tab character that generated it.
                result += spaces * SourcedString(' ', piece.source)
                offset = 0
            else:
                result += piece
                if piece == '\n': offset = 0
                else: offset += len(piece)
        return result
        
    def translate(self, table, deletechars=''):
        # Note: str.translate() and unicode.translate() have
        # different interfaces.
        if isinstance(self, unicode):
            if deletechars:
                raise TypeError('The unicode version of translate() does not '
                                'accept the deletechars parameter')
            return SourcedString.concat(
                [SourcedString(table.get(c,c), c.source)
                 for c in self if table.get(c,c) is not None])
        else:
            if len(table) != 256:
                raise ValueError('translation table must be 256 characters long')
            return SourcedString.concat(
                [SourcedString(table[ord(c)], c.source)
                 for c in self if c not in deletechars])

    #//////////////////////////////////////////////////////////////////////
    #{ Unicode
    #//////////////////////////////////////////////////////////////////////

    # Unicode string -> byte string
    def encode(self, encoding=None, errors='strict'):
        if encoding is None: encoding = sys.getdefaultencoding()
        if isinstance(self, str):
            return self.decode().encode(encoding, errors)

        # Encode characters one at a time.
        result = []
        for i, char in enumerate(self):
            char_bytes = self._stringtype.encode(char, encoding, errors)
            for char_byte in char_bytes:
                if isinstance(char, SimpleSourcedString):
                    result.append(SourcedString(char_byte, char.source))
                else:
                    assert not isinstance(char, CompoundSourcedString)
                    result.append(char_byte)
        return SourcedString.concat(result)

    # Byte string -> unicode string.
    def decode(self, encoding=None, errors='strict'):
        if encoding is None: encoding = sys.getdefaultencoding()
        if isinstance(self, unicode):
            return self.encode().decode(encoding, errors)

        # Decode self into a plain unicode string.
        unicode_chars = self._stringtype.decode(self, encoding, errors)

        # Special case: if the resulting string has the same length
        # that the source string does, then we can safely assume that
        # each character is encoded with one byte; so we can just
        # reuse our source.
        if len(unicode_chars) == len(self):
            return self._decode_one_to_one(unicode_chars)

        # Otherwise: re-encode the characters, one at a time, to
        # determine how long their encodings are.
        result = []
        first_byte = 0
        for unicode_char in unicode_chars:
            char_width = len(unicode_char.encode(encoding, errors))
            last_byte = first_byte + char_width - 1
            if (isinstance(self[first_byte], SourcedString) and
                isinstance(self[last_byte], SourcedString)):
                begin = self[first_byte].begin
                end = self[last_byte].end
                if end-begin == 1:
                    source = StringSource(docid=self[first_byte].docid,
                                          begin=begin, end=end)
                else:
                    source = StringSource(docid=self[first_byte].docid,
                                          offsets=[begin, end])
                result.append(SourcedString(unicode_char, source))
            else:
                result.append(unicode_char)
                    
            # First byte of the next char is 1+last byte of this char.
            first_byte = last_byte+1
        if last_byte+1 != len(self):
            raise AssertionError("SourcedString.decode() does not support "
                                 "encodings that are not symmetric.")

        return SourcedString.concat(result)
    
    @abstract
    def _decode_one_to_one(unicode_chars):
        """
        Helper for L{self.decode()}.  Returns a unicode-decoded
        version of this L{SourcedString}.  C{unicode_chars} is the
        unicode-decoded contents of this L{SourcedString}.

        This is used in the special case where the decoded string has
        the same length that the source string does.  As a result, we
        can safely assume that each character is encoded with one
        byte; so we can just reuse our source.  E.g., this will happen
        when decoding an ASCII string with utf-8.
        """

    def _mixed_string_types(self, *args):
        """
        Return true if the list (self,)+args contains at least one
        unicode string and at least one byte string.  (If this is the
        case, then all byte strings should be converted to unicode by
        calling decode() before the operation is performed.  You can
        do this automatically using L{_decode_and_call()}.
        """
        any_unicode = isinstance(self, unicode)
        any_bytestring = isinstance(self, str)
        for arg in args:
            any_unicode = any_unicode or isinstance(arg, unicode)
            any_bytestring = any_bytestring or isinstance(arg, str)
        return any_unicode and any_bytestring

    def _decode_and_call(self, op, *args):
        """
        If self or any of the values in args is a byte string, then
        convert it to unicode by calling its decode() method.  Then
        return the result of calling self.op(*args).  C{op} is
        specified using a string, because if C{self} is a byte string,
        then it will change type when it is decoded.
        """
        # Make sure all args are decoded to unicode.
        args = list(args)
        for i in range(len(args)):
            if isinstance(args[i], str):
                args[i] = args[i].decode()
        # Make sure self is decoded to unicode.
        if isinstance(self, str):
            self = self.decode()
        # Retry the operation.
        method = getattr(self, op)
        return method(*args)
    
    #//////////////////////////////////////////////////////////////////////
    #{ Display
    #//////////////////////////////////////////////////////////////////////

    def pprint(self, vertical=False, wrap=70):
        """
        Return a string containing a pretty-printed display of this
        sourced string.

        @param vertical: If true, then the returned display string will
            have vertical orientation, rather than the default horizontal
            orientation.
            
        @param wrap: Controls when the pretty-printed output is wrapped
            to the next line.  If C{wrap} is an integer, then lines are
            wrapped when they become longer than C{wrap}.  If C{wrap} is
            a string, then lines are wrapped immediately following that
            string.  If C{wrap} is C{None}, then lines are never wrapped.
        """
        if len(self) == 0: return '[Empty String]'
        if vertical == 1: return self._pprint_vertical() # special-cased

        max_digits = len(str(max(max(getattr(c, 'begin', 0),
                                     getattr(c, 'end', 0)) for c in self)))
        if not isinstance(wrap, (basestring, int, long, type(None))):
            raise TypeError("Expected wrap to be a sring, int, or None.")

        result = []
        prev_offset = None # most recently displayed offset.
        prev_docid = None
        docid_line = ''
        output_lines = [''] * (max_digits+2)

        for pos, char in enumerate(self):
            char_begin = getattr(char, 'begin', None)
            char_end = getattr(char, 'end', None)
            char_docid = getattr(char, 'docid', None)

            # If the docid changed, then display the docid for the
            # previous segment.
            if char_docid != prev_docid:
                width = len(output_lines[0]) - len(docid_line)
                docid_line += self._pprint_docid(width, prev_docid)
                prev_docid = char_docid

            # Put a cap on the beginning of sourceless strings
            elif not output_lines[0] and char_begin is None:
                self._pprint_offset(' ', output_lines)
                
            # Display the character.
            if char_begin != prev_offset:
                self._pprint_offset(char_begin, output_lines)
            self._pprint_char(char, output_lines)
            self._pprint_offset(char_end, output_lines)
            prev_offset = char_end
            
            # Decide whether we're at the end of the line or not.
            line_len = len(output_lines[0])
            if ( (isinstance(wrap, basestring) and
                  self[max(0,pos-len(wrap)+1):pos+1] == wrap) or 
                 (isinstance(wrap, (int,long)) and line_len>=wrap) or
                 pos == len(self)-1):

                # Put a cap on the end of sourceless strings
                if char_end is None:
                    self._pprint_offset(' ', output_lines)

                # Filter out any empty output lines.
                output_lines = [l for l in output_lines if l.strip()]

                # Draw the docid line
                width = len(output_lines[0]) - len(docid_line)
                docid_line += self._pprint_docid(width, prev_docid)
                result.append(docid_line)

                # Draw the output lines
                for output_line in reversed(output_lines):
                    result.append(output_line)
                result.append(output_lines[1])

                # Reset variables for the next line.
                prev_offset = None
                prev_docid = None
                docid_line = ''
                output_lines = [''] * (max_digits+2)
                
        return '\n'.join(result)

    def _pprint_vertical(self):
        result = []
        prev_offset = None
        max_digits = len(str(max(max(getattr(c, 'begin', 0),
                                     getattr(c, 'end', 0)) for c in self)))
        for pos, char in enumerate(self):
            char_begin = getattr(char, 'begin', None)
            char_end = getattr(char, 'end', None)
            char_docid = getattr(char, 'docid', None)

            if char_begin is None:
                assert char_end is None
                if pos == 0: result.append('+-----+')
                result.append(':%s:' % 
                              self._pprint_char_repr(char).center(5))
                if pos == len(self)-1: result.append('+-----+')
                prev_offset = None
            else:
                if char_begin != prev_offset:
                    result.append('+-----+ %s [%s]' % (
                        str(char_begin).rjust(max_digits), char_docid))
                result.append('|%s| %s [%s]' % (
                    self._pprint_char_repr(char).center(5),
                    ' '*max_digits, char_docid))
                result.append('+-----+ %s [%s]' % (
                    str(char_end).rjust(max_digits), char_docid))
            prev_offset = char_end
        return '\n'.join(result)

    _PPRINT_CHAR_REPRS = {'\n': r'\n', '\r': r'\r',
                          '\a': r'\a', '\t': r'\t'}
    
    def _pprint_docid(self, width, docid):
        if docid is None: return ' '*width
        else: return '[%s]' % (docid[:width-2].center(width-2, '='))

    def _pprint_char_repr(self, char):
        # Decide how to represent this character.
        if 32 <= ord(char) <= 127:
            return str(char)
        elif char in self._PPRINT_CHAR_REPRS:
            return self._PPRINT_CHAR_REPRS[char]
        elif isinstance(char, str):
            return r'\x%02x' % ord(char)
        else:
            return r'\u%04x' % ord(char)
            
    def _pprint_char(self, char, output_lines):
        """Helper for L{pprint()}: add a character to the
        pretty-printed output."""
        char_repr = self._pprint_char_repr(char)
        output_lines[0] += char_repr
        # Add fillers to the offset lines.
        output_lines[1] += '-'*len(char_repr)
        for i in range(2, len(output_lines)):
            output_lines[i] += ' '*len(char_repr)

    def _pprint_offset(self, offset, output_lines):
        """Helper for L{pprint()}: add an offset marker to the
        pretty-printed output."""
        if offset is None: return
        output_lines[0] += '|'
        output_lines[1] += '+'
        offset_rep = str(offset).rjust(len(output_lines)-2)
        for digit in range(len(offset_rep)):
            output_lines[-digit-1] += offset_rep[digit]

#//////////////////////////////////////////////////////////////////////
# Simple Sourced String
#//////////////////////////////////////////////////////////////////////

class SimpleSourcedString(SourcedString):
    """
    A single substring of a document, annotated with information about
    the location in the document where it was originally found.  See
    L{SourcedString} for more information.
    """
    def __new__(cls, contents, source):
        # If the SimpleSourcedString constructor is called directly,
        # then choose one of its subclasses to delegate to.
        if cls is SimpleSourcedString:
            if isinstance(contents, str):
                cls = SimpleSourcedByteString
            elif isinstance(contents, unicode):
                cls = SimpleSourcedUnicodeString
            else:
                raise TypeError("Expected 'contents' to be a unicode "
                                "string or a byte string")

        # Create the new object using the appropriate string class's
        # __new__, which takes just the contents argument.
        return cls._stringtype.__new__(cls, contents)
        
    def __init__(self, contents, source):
        """
        Construct a new sourced string.

        @param contents: The string contents of the new sourced string.
        @type contents: C{str} or C{unicode}
        @param source: The source for the new string.  If C{source} is
            a string, then it is used to automatically construct a new
            L{ConsecutiveCharStringSource} with a begin offset of
            C{0} and an end offset of C{len(contents)}.  Otherwise,
            C{source} shoulde be a L{StringSource} whose length matches
            the length of C{contents}.
        """
        if not isinstance(source, StringSource):
            source = ConsecutiveCharStringSource(source, 0, len(contents))
        elif len(source) != len(contents):
            raise ValueError("Length of source (%d) must match length of "
                             "contents (%d)" % (len(source), len(contents)))
        
        self.source = source
        """A L{StringLocation} specifying the location where this string
           occured in the source document."""

    @property
    def begin(self):
        """
        The document offset where the string begins.  (I.e.,
        the offset of the first character in the string.)"""
        return self.source.begin

    @property
    def end(self):
        """The document offset where the string ends.  (For character
        offsets, one plus the offset of the last character; for byte
        offsets, one plus the offset of the last byte that encodes the
        last character)."""
        return self.source.end
    
    @property
    def docid(self):
        """
        An identifier (such as a filename) that specifies the document
        where the string was found.
        """
        return self.source.docid

    @property
    def sources(self):
        return ((0, self.source),)

    def __repr__(self):
        if self.end == self.begin+1:
            source_repr =  '@[%s]' % (self.begin,)
        else:
            source_repr = '@[%s:%s]' % (self.begin, self.end)
        return self._stringtype.__repr__(self) + source_repr

    def __getitem__(self, index):
        result = self._stringtype.__getitem__(self, index)
        if isinstance(index, slice):
            if index.step not in (None, 1):
                return result
            else:
                start, stop = slice_bounds(self, index)
                return self.__getslice__(start, stop)
        else:
            return SourcedString(result, self.source[index])
    
    def __getslice__(self, start, stop):
        # Negative indices get handled *before* __getslice__ is
        # called.  Restrict start/stop to be within the range of the
        # string, to prevent negative indices from being adjusted
        # twice.
        start = max(0, min(len(self), start))
        stop = max(start, min(len(self), stop))
        
        return SourcedString(
            self._stringtype.__getslice__(self, start, stop),
            self.source[start:stop])
    
    def capitalize(self):
        result = self._stringtype.capitalize(self)
        return SourcedString(result, self.source)
    
    def lower(self):
        result = self._stringtype.lower(self)
        return SourcedString(result, self.source)
    
    def upper(self):
        result = self._stringtype.upper(self)
        return SourcedString(result, self.source)
    
    def swapcase(self):
        result = self._stringtype.swapcase(self)
        return SourcedString(result, self.source)
    
    def title(self):
        result = self._stringtype.title(self)
        return SourcedString(result, self.source)

    def _decode_one_to_one(self, unicode_chars):
        return SourcedString(unicode_chars, self.source)
    
#//////////////////////////////////////////////////////////////////////
# Compound Sourced String
#//////////////////////////////////////////////////////////////////////

class CompoundSourcedString(SourcedString):
    """
    A string constructed by concatenating substrings from multiple
    sources, and annotated with information about the locations where
    those substrings were originally found.  See L{SourcedString} for
    more information.

    @ivar substrings: The tuple of substrings that compose this
        compound sourced string.  Every compound sourced string is
        required to have at least two substrings; and the substrings
        themselves may never be CompoundSourcedStrings.
    """
    def __new__(cls, substrings):
        # If the CompoundSourcedString constructor is called directly,
        # then choose one of its subclasses to delegate to.
        if cls is CompoundSourcedString:
            # Decide whether to use a unicode string or a byte string.
            use_unicode = sum(1 for substring in substrings
                              if isinstance(substring, unicode))
            if use_unicode:
                cls = CompoundSourcedUnicodeString
            else:
                cls = CompoundSourcedByteString
            
        # Build the concatenated string using str.join(), which will
        # return a str or unicode object; never a sourced string.
        contents = ''.join(substrings)

        # Create the new object using the appropriate string class's
        # __new__, which takes just the contents argument.
        return cls._stringtype.__new__(cls, contents)

    def __init__(self, substrings):
        """
        Construct a new compound sourced string that combines the
        given list of substrings.

        Typically, compound sourced strings should not be constructed
        directly; instead, use L{SourcedString.concat()}, which
        flattens nested compound sourced strings, and merges adjacent
        substrings when possible.

        @raise ValueError: If C{len(substrings)  < 2}
        @raise ValueError: If C{substrings} contains any
            C{CompoundSourcedString}s.
        """
        if len(substrings) < 2:
            raise ValueError("CompoundSourcedString requires at least "
                             "two substrings")
        
        # Don't nest compound sourced strings.
        for substring in substrings:
            if isinstance(substring, CompoundSourcedString):
                raise ValueError("substrings may not contain "
                                 "CompoundSourcedStrings.")

        self.substrings = tuple(substrings)

    @property
    def sources(self):
        index = 0
        source_list = []
        for substring in self.substrings:
            if isinstance(substring, SourcedString):
                source_list.append( (index, substring.source) )
            index += len(substring)
        return tuple(source_list)

    def __repr__(self):
        sources = [self._source_repr(s) for s in self.substrings]
        source_str = '@[%s]' % ','.join(sources)
        return self._stringtype.__repr__(self) + source_str

    def _source_repr(self, substring):
        if isinstance(substring, SimpleSourcedString):
            return '%s:%s' % (substring.begin, substring.end)
        else:
            return '...'

    def __getitem__(self, index):
        if isinstance(index, slice):
            if index.step not in (None, 1):
                return self._stringtype.__getitem__(self, index)
            else:
                start, stop = slice_bounds(self, index)
                return self.__getslice__(start, stop)
        else:
            if index < 0: index += len(self)
            if index < 0 or index >= len(self):
                raise IndexError('StringSource index out of range')
            return self.__getslice__(index, index+1)

    def __getslice__(self, start, stop):
        # Bounds checking.
        start = max(0, min(len(self), start))
        stop = max(start, min(len(self), stop))

        # Construct a source list for the resulting string.
        result_substrings = []
        offset = 0
        for substring in self.substrings:
            if offset+len(substring) > start:
                s, e = max(0, start-offset), stop-offset
                result_substrings.append(substring[s:e])
            offset += len(substring)
            if offset >= stop: break

        # Concatentate the resulting substrings.
        if len(result_substrings) == 0:
            return ''
        elif len(result_substrings) == 1:
            return result_substrings[0]
        else:
            return SourcedString.concat(result_substrings)

    def capitalize(self):
        return SourcedString.concat([s.capitalize() for s in self.substrings])
    
    def lower(self):
        return SourcedString.concat([s.lower() for s in self.substrings])
    
    def upper(self):
        return SourcedString.concat([s.upper() for s in self.substrings])
    
    def swapcase(self):
        return SourcedString.concat([s.swapcase() for s in self.substrings])
    
    def title(self):
        return SourcedString.concat([s.title() for s in self.substrings])

    def encode(self, encoding=None, errors='strict'):
        return SourcedString.concat([s.encode(encoding, errors)
                                     for s in self.substrings])

    def _decode_one_to_one(self, unicode_chars):
        index = 0
        result = []
        for substring in self.substrings:
            decoded_substring = unicode_chars[index:index+len(substring)]
            if isinstance(substring, SourcedString):
                result.append(SourcedString(decoded_substring, substring.source))
            else:
                result.append(decoded_substring)
            index += len(substring)
        return SourcedString.concat(result)

#//////////////////////////////////////////////////////////////////////
# Concrete Sourced String Classes
#//////////////////////////////////////////////////////////////////////

class SimpleSourcedByteString(SimpleSourcedString, str):
    _stringtype = str
class SimpleSourcedUnicodeString(SimpleSourcedString, unicode):
    _stringtype = unicode
class CompoundSourcedByteString(CompoundSourcedString, str):
    _stringtype = str
class CompoundSourcedUnicodeString(CompoundSourcedString, unicode):
    _stringtype = unicode
    def __init__(self, substrings):
        # If any substrings have type 'str', then decode them to unicode.
        for i in range(len(substrings)):
            if not isinstance(substrings[i], unicode):
                substrings[i] = substrings[i].decode()
        CompoundSourcedString.__init__(self, substrings)

#//////////////////////////////////////////////////////////////////////
# Sourced String Regexp
#//////////////////////////////////////////////////////////////////////

_original_re_compile = re.compile
_original_re_sub = re.sub
_original_re_subn = re.subn

class SourcedStringRegexp(object):
    """
    Wrapper for regexp pattern objects that cause the L{sub} and
    L{subn} methods to return sourced strings.
    """
    def __init__(self, pattern, flags=0):
        if isinstance(pattern, basestring):
            pattern = _original_re_compile(pattern, flags)
        self.pattern = pattern
    def __getattr__(self, attr):
        return getattr(self.pattern, attr)

    def subn(self, repl, string, count=0):
        if (isinstance(repl, SourcedString) or
            isinstance(string, SourcedString)):
            result = ''
            pos = 0
            n = 0
            for match in self.pattern.finditer(string):
                result += string[pos:match.start()]
                result += repl
                pos = match.end()
                n += 1
                if count and n==count: break
            result += string[pos:]
            return result, n
        else:
            return self.pattern.subn(repl, string, count)
 
    def sub(self, repl, string, count=0):
        return self.subn(repl, string, count)[0]

    @staticmethod
    def patch_re_module():
        """
        Modify the standard C{re} module by installing new versions of
        the functions C{re.compile}, C{re.sub}, and C{re.subn},
        causing regular expression substitutions to return
        C{SourcedString}s when called with C{SourcedString}s
        arguments.

        Use this function only if necessary: it potentially affects
        all Python modules that use regular expressions!
        """
        def new_re_sub(pattern, repl, string, count=0):
            return re.compile(pattern).sub(repl, string, count)
        def new_re_subn(pattern, repl, string, count=0):
            return re.compile(pattern).subn(repl, string, count)
        re.compile = SourcedStringRegexp
        re.sub = new_re_sub
        re.subn = new_re_subn

    @staticmethod
    def unpatch_re_module():
        """
        Restore the standard C{re} module to its original state
        (undoing the work that was done by L{patch_re_module()}).
        """
        re.compile = _original_re_compile
        re.sub = _original_re_sub
        re.subn = _original_re_subn


#//////////////////////////////////////////////////////////////////////
# Sourced String Stream
#//////////////////////////////////////////////////////////////////////

class SourcedStringStream(object):
    """
    Wrapper for a read-only stream that causes C{read()} (and related
    methods) to return L{sourced string <SourcedStringBase>}s.
    L{seek()} and L{tell()} are supported, but (currently) there are
    some restrictions on the values that may be passed to L{seek()}.
    """
    def __init__(self, stream, docid=None, byte_offsets=False):
        self.stream = stream
        """The underlying stream."""

        self.docid = docid
        """The docid attribute for sourced strings"""

        self.charpos = 0
        """The current character (not byte) position"""

        assert not byte_offsets, 'not supported yet!'

    #/////////////////////////////////////////////////////////////////
    # Read methods
    #/////////////////////////////////////////////////////////////////

    def read(self, size=None):
        if size is None: return self._sourced_string(self.stream.read())
        else: return self._sourced_string(self.stream.read(size))

    def readline(self, size=None):
        if size is None:  return self._sourced_string(self.stream.readline())
        else: return self._sourced_string(self.stream.readline(size))

    def readlines(self, sizehint=None, keepends=True):
        """
        Read this file's contents, decode them using this reader's
        encoding, and return it as a list of unicode lines.

        @rtype: C{list} of C{unicode}
        @param sizehint: Ignored.
        @param keepends: If false, then strip newlines.
        """
        return self.read().splitlines(keepends)

    def next(self):
        """Return the next decoded line from the underlying stream."""
        line = self.readline()
        if line: return line
        else: raise StopIteration

    def __iter__(self):
        """Return self"""
        return self

    def xreadlines(self):
        """Return self"""
        return self

    def _sourced_string(self, contents):
        """Turn the given string into an sourced string, and update
           charpos."""
        # [xx] currently we only support character offsets, not byte
        # offsets!
        source = ConsecutiveCharStringSource(self.docid, self.charpos,
                                             self.charpos+len(contents))
        self.charpos += len(contents)
        return SourcedString(contents, source)

    #/////////////////////////////////////////////////////////////////
    # Pass-through methods & properties
    #/////////////////////////////////////////////////////////////////
    
    closed = property(lambda self: self.stream.closed, doc="""
        True if the underlying stream is closed.""")

    name = property(lambda self: self.stream.name, doc="""
        The name of the underlying stream.""")

    mode = property(lambda self: self.stream.mode, doc="""
        The mode of the underlying stream.""")

    def close(self):
        """Close the underlying stream."""
        self.stream.close()

    #/////////////////////////////////////////////////////////////////
    # Seek and tell
    #/////////////////////////////////////////////////////////////////

    class SourcedStringStreamPos(int):
        def __new__(cls, bytepos, charpos):
            self = int.__new__(cls, bytepos)
            self.charpos = charpos
            return self
    
    def seek(self, offset, whence=0):
        if whence == 0:
            if isinstance(offset, self.SourcedStringStreamPos):
                self.stream.seek(offset)
                self.charpos = offset.charpos
            elif offset == 0:
                self.stream.seek(0)
                self.charpos = 0
            else:
                raise TypeError('seek() must be called with a value that '
                                'was returned by tell().')
        elif whence == 1:
            raise TypeError('Relative seek not supported for '
                            'SourcedStringStream.')
        elif whence == 2:
            raise TypeError('Seek-from-end not supported for '
                            'SourcedStringStream.')
        else:
            raise ValueError('Bad whence value %r' % whence)

    def tell(self):
        bytepos = self.stream.tell()
        return self.SourcedStringStreamPos(bytepos, self.charpos)

                
        
