# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

import os, re
from nltk import defaultdict
from nltk.internals import deprecated
import nltk.corpus.reader.util
from nltk.data import PathPointer, FileSystemPathPointer, ZipFilePathPointer

class CorpusReader(object):
    """
    A base class for X{corpus reader} classes, each of which can be
    used to read a specific corpus format.  Each individual corpus
    reader instance is used to read a specific corpus, consisting of
    one or more files under a common root directory.  Each file is
    identified by its C{file identifier}, which is the relative path
    to the file from the root directory.

    A separate subclass is be defined for each corpus format.  These
    subclasses define one or more methods that provide 'views' on the
    corpus contents, such as C{words()} (for a list of words) and
    C{parsed_sents()} (for a list of parsed sentences).  Called with
    no arguments, these methods will return the contents of the entire
    corpus.  For most corpora, these methods define one or more
    selection arguments, such as C{files} or C{categories}, which can
    be used to select which portion of the corpus should be returned.
    """
    def __init__(self, root, files, encoding=None, tag_mapping_function=None):
        """
        @type root: L{PathPointer} or C{str}
        @param root: A path pointer identifying the root directory for
            this corpus.  If a string is specified, then it will be
            converted to a L{PathPointer} automatically.
        @param files: A list of the files that make up this corpus.
            This list can either be specified explicitly, as a list of
            strings; or implicitly, as a regular expression over file
            paths.  The absolute path for each file will be constructed
            by joining the reader's root to each file name.
        @param encoding: The default unicode encoding for the files
            that make up the corpus.  C{encoding}'s value can be any
            of the following:
            
              - B{A string}: C{encoding} is the encoding name for all
                files.
              - B{A dictionary}: C{encoding[file_id]} is the encoding
                name for the file whose identifier is C{file_id}.  If
                C{file_id} is not in C{encoding}, then the file
                contents will be processed using non-unicode byte
                strings.
              - B{A list}: C{encoding} should be a list of C{(regexp,
                encoding)} tuples.  The encoding for a file whose
                identifier is C{file_id} will be the C{encoding} value
                for the first tuple whose C{regexp} matches the
                C{file_id}.  If no tuple's C{regexp} matches the
                C{file_id}, the file contents will be processed using
                non-unicode byte strings.
              - C{None}: the file contents of all files will be
                processed using non-unicode byte strings.
        @param tag_mapping_function: A function for normalizing or
                simplifying the POS tags returned by the tagged_words()
                or tagged_sents() methods.
        """
        # Convert the root to a path pointer, if necessary.
        if isinstance(root, basestring):
            m = re.match('(.*\.zip)/?(.*)$|', root)
            zipfile, zipentry = m.groups()
            if zipfile:
                root = ZipFilePathPointer(zipfile, zipentry)
            else:
                root = FileSystemPathPointer(root)
        elif not isinstance(root, PathPointer):
            raise TypeError('CorpusReader: expected a string or a PathPointer')

        # If `files` is a regexp, then expand it.
        if isinstance(files, basestring):
            files = nltk.corpus.reader.find_corpus_files(root, files)
            
        self._files = tuple(files)
        """A list of the relative paths for the files that make up
        this corpus."""
        
        self._root = root
        """The root directory for this corpus."""

        # If encoding was specified as a list of regexps, then convert
        # it to a dictionary.
        if isinstance(encoding, list):
            encoding_dict = {}
            for fileid in self._files:
                for x in encoding:
                    (regexp, enc) = x
                    if re.match(regexp, fileid):
                        encoding_dict[fileid] = enc
                        break
            encoding = encoding_dict

        self._encoding = encoding
        """The default unicode encoding for the files that make up
           this corpus.  If C{encoding} is C{None}, then the file
           contents are processed using byte strings (C{str})."""
        self._tag_mapping_function = tag_mapping_function
        
    def __repr__(self):
        if isinstance(self._root, ZipFilePathPointer):
            path = '%s/%s' % (self._root.zipfile.filename, self._root.entry)
        else:
            path = '%s' % self._root.path
        return '<%s in %r>' % (self.__class__.__name__, path)

    def files(self):
        """
        Return a list of file identifiers for the files that make up
        this corpus.
        """
        return self._files

    def abspath(self, file):
        """
        Return the absolute path for the given file.

        @type file: C{str}
        @param file: The file identifier for the file whose path
            should be returned.
            
        @rtype: L{PathPointer}
        """
        return self._root.join(file)

    def abspaths(self, files=None, include_encoding=False):
        """
        Return a list of the absolute paths for all files in this corpus;
        or for the given list of files, if specified.

        @type files: C{None} or C{str} or C{list}
        @param files: Specifies the set of files for which paths should
            be returned.  Can be C{None}, for all files; a list of
            file identifiers, for a specified set of files; or a single
            file identifier, for a single file.  Note that the return
            value is always a list of paths, even if C{files} is a
            single file identifier.
            
        @param include_encoding: If true, then return a list of
            C{(path_pointer, encoding)} tuples.

        @rtype: C{list} of L{PathPointer}
        """
        if files is None:
            files = self._files
        elif isinstance(files, basestring):
            files = [files]

        paths = [self._root.join(f) for f in files]

        if include_encoding:            
            return zip(paths, [self.encoding(f) for f in files])
        else:
            return paths

    def open(self, file):
        """
        Return an open stream that can be used to read the given file.
        If the file's encoding is not C{None}, then the stream will
        automatically decode the file's contents into unicode.

        @param file: The file identifier of the file to read.
        """
        encoding = self.encoding(file)
        return self._root.join(file).open(encoding)

    def encoding(self, file):
        """
        Return the unicode encoding for the given corpus file, if known.
        If the encoding is unknown, or if the given file should be
        processed using byte strings (C{str}), then return C{None}.
        """
        if isinstance(self._encoding, dict):
            return self._encoding.get(file)
        else:
            return self._encoding
        
    def _get_root(self): return self._root
    root = property(_get_root, doc="""
        The directory where this corpus is stored.

        @type: L{PathPointer}""")

    #{ Deprecated since 0.9.1
    @deprecated("Use corpus.files() instead")
    def _get_items(self): return self.files()
    items = property(_get_items)

    @deprecated("Use corpus.abspaths() instead")
    def filenames(self, items=None): return self.abspaths(items)
    #}

######################################################################
#{ Corpora containing categorized items
######################################################################

class CategorizedCorpusReader(object):
    """
    A mixin class used to aid in the implementation of corpus readers
    for categorized corpora.  This class defines the method
    L{categories()}, which returns a list of the categories for the
    corpus or for a specified set of files; and overrides L{files()}
    to take a C{categories} argument, restricting the set of files to
    be returned.

    Subclasses are expected to:

      - Call L{__init__()} to set up the mapping.
        
      - Override all view methods to accept a C{categories} parameter,
        which can be used *instead* of the C{files} parameter, to
        select which files should be included in the returned view.
    """

    def __init__(self, kwargs):
        """
        Initialize this mapping based on keyword arguments, as
        follows:

          - cat_pattern: A regular expression pattern used to find the
            category for each file identifier.  The pattern will be
            applied to each file identifier, and the first matching
            group will be used as the category label for that file.
            
          - cat_map: A dictionary, mapping from file identifiers to
            category labels.
            
          - cat_file: The name of a file that contains the mapping
            from file identifiers to categories.  The argument
            C{cat_delimiter} can be used to specify a delimiter.

        The corresponding argument will be deleted from C{kwargs}.  If
        more than one argument is specified, an exception will be
        raised.
        """
        self._f2c = None #: file-to-category mapping
        self._c2f = None #: category-to-file mapping
        
        self._pattern = None #: regexp specifying the mapping
        self._map = None #: dict specifying the mapping
        self._file = None #: filename of file containing the mapping
        self._delimiter = None #: delimiter for L{self._file}

        if 'cat_pattern' in kwargs:
            self._pattern = kwargs['cat_pattern']
            del kwargs['cat_pattern']
        elif 'cat_map' in kwargs:
            self._map = kwargs['cat_map']
            del kwargs['cat_map']
        elif 'cat_file' in kwargs:
            self._file = kwargs['cat_file']
            del kwargs['cat_file']
            if 'cat_delimiter' in kwargs:
                self._delimiter = kwargs['cat_delimiter']
                del kwargs['cat_delimiter']
        else:
            raise ValueError('Expected keyword argument cat_pattern or '
                             'cat_map or cat_file.')


        if ('cat_pattern' in kwargs or 'cat_map' in kwargs or
            'cat_file' in kwargs):
            raise ValueError('Specify exactly one of: cat_pattern, '
                             'cat_map, cat_file.')

    def _init(self):
        self._f2c = defaultdict(list)
        self._c2f = defaultdict(list)
        
        if self._pattern is not None:
            for file_id in self._files:
                category = re.match(self._pattern, file_id).group(1)
                self._add(file_id, category)
                
        elif self._map is not None:
            for (file_id, categories) in self._map.items():
                for category in categories:
                    self._add(file_id, category)

        elif self._file is not None:
            for line in self.open(self._file).readlines():
                line = line.strip()
                file_id, categories = line.split(self._delimiter, 1)
                if file_id not in self.files():
                    raise ValueError('In category mapping file %s: %s '
                                     'not found' % (catfile, file_id))
                for category in categories.split(self._delimiter):
                    self._add(file_id, category)

    def _add(self, file_id, category):
        self._f2c[file_id].append(category)
        self._c2f[category].append(file_id)

    def categories(self, files=None):
        """
        Return a list of the categories that are defined for this corpus,
        or for the file(s) if it is given.
        """
        if self._f2c is None: self._init()
        if files is None:
            return sorted(self._c2f)
        if isinstance(files, basestring):
            files = [files]
        return sorted(sum((self._f2c[d] for d in files), []))

    def files(self, categories=None):
        """
        Return a list of file identifiers for the files that make up
        this corpus, or that make up the given category(s) if specified.
        """
        if categories is None:
            return super(CategorizedCorpusReader, self).files()
        elif isinstance(categories, basestring):
            if self._f2c is None: self._init()
            return sorted(self._c2f[categories])
        else:
            if self._f2c is None: self._init()
            return sorted(sum((self._c2f[c] for c in categories), []))

