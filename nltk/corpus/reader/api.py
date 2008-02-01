# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

import os, re
from nltk import defaultdict
from nltk.internals import deprecated
import nltk.corpus.reader.util

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
    def __init__(self, root, files):
        """
        @param root: The root directory for this corpus.
        @param files: A list of the files that make up this corpus.
            This list can either be specified explicitly, as a list of
            strings; or implicitly, as a regular expression over file
            paths.  The absolute path for each file will be constructed
            by joining the reader's root to each file name.
        """
        if not os.path.isdir(root):
            raise ValueError('Root directory %r not found!' % root)
        if isinstance(files, basestring):
            files = nltk.corpus.reader.find_corpus_files(root, files)
            
        self._files = tuple(files)
        """A list of the relative paths for the files that make up
        this corpus."""
        
        self._root = root
        """The root directory for this corpus."""
        
    def __repr__(self):
        return '<%s in %r>' % (self.__class__.__name__, self._root)

    def files(self):
        """
        Return a list of file identifiers for the files that make up
        this corpus.
        """
        return self._files

    def abspath(self, file):
        """
        Return the absolute path for the given file.
        """
        return os.path.join(self._root, file)

    def abspaths(self, files=None):
        """
        Return a list of the absolute paths for all files in this corpus;
        or for the given list of files, if specified.
        """
        if files is None:
            return [os.path.join(self._root, f) for f in self._files]
        elif isinstance(files, basestring):
            return [os.path.join(self._root, files)]
        else:
            return [os.path.join(self._root, f) for f in files]
        
    def _get_root(self): return self._root
    root = property(_get_root, doc="""
        The directory where this corpus is stored.""")

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

      * Call L{__init__()} to set up the mapping.
        
      * Override all view methods to accept a C{categories} parameter,
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
            for line in open(os.path.join(self.root, self._file)).readlines():
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

