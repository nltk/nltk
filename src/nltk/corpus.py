# Natural Language Toolkit: Corpus Access
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

"""
Access to NLTK's standard distribution of corpora.  Each of corpus is
encoded as an instance of the C{Corpus} class.  For information about
using these corpora, see the reference documentation for L{Corpus}.

@group Data Types: Corpus
@group Corpora: twenty_newsgroups, treebank, wordlist, reuters
@var twenty_newsgroups: A collection of approximately 20,000
     newsgroup documents, partitioned (nearly) evenly across 20
     different newsgroups.
@var treebank: A collection of hand-annotated parse trees for
     english text.
@var wordlist: A list of English words.
@var reuters: A collection of documents that appeared on Reuters
     newswire in 1987.
      
@todo: Add more corpora.
@todo: Set the default tokenizer for the treebank corpus.
@todo: Add default basedir for OS-X?

@variable _BASEDIR: The base directory for NLTK's standard distribution
    of corpora.  This is read from the environment variable
    C{NLTK_CORPERA}, if it exists; otherwise, it is given a
    system-dependant default value.  C{_BASEDIR}'s value can be changed
    with the L{set_basedir()} function.
@type _BASEDIR: C{string}
"""

import sys, os.path
from nltk.tokenizer import WSTokenizer

#################################################################
# Base Directory for Corpora
#################################################################
def set_basedir(dir):
    """
    Change the base directory for NLTK's standard distribution of
    corpora.
    """
    global _BASEDIR
    _BASEDIR = dir

# Find the base directory.
if os.environ.has_key('NLTK_CORPERA'):
    set_basedir(os.environ['NLTK_CORPERA'])
elif sys.platform.startswith('win'):
    if os.path.isdir(os.path.join(sys.prefix, 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'nltk'))
    elif os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'lib', 'nltk'))
    else:
        set_basedir(os.path.join(sys.prefix, 'nltk'))
elif os.path.isdir('/usr/lib/nltk'):
    set_basedir('/usr/lib/nltk')
elif os.path.isdir('/usr/local/lib/nltk'):
    set_basedir('/usr/local/lib/nltk')
elif os.path.isdir('/usr/share/nltk'):
    set_basedir('/usr/share/nltk')
else:
    set_basedir('/usr/lib/nltk')

#################################################################
# Corpus data class
#################################################################

class Corpus:
    """
    A collection of natural language data.  Each corpus consists of a
    set of subcorpora and/or files.  The L{subcorpora()} method
    returns a corpus's subcorpora; and the L{filenames()} method
    returns the names of its files.  The contents of a corpus's files
    are accesed by name, using the file access methods.
    
    The following example demonstrates the use of a C{Corpus}:

        >>> for newsgroup in twenty_newsgroups:
        ...    for file in newsgroup.filenames():
        ...        process(newsgroup.tokenize(file), newsgroup.name())

    @group File Access: open, read, readlines, tokenize
    @group Subgroup Access: subgroups
    @group Information: name, description, __str__, __repr__
    @sort: open, read, readlines, tokenize,
           name, description, __str__, __repr__
    """
    def __init__(self, name, directory, description=None,
                 default_tokenizer=WSTokenizer()):
        """
        Define a new corpus.  The contents of the new corpus are
        automatically generated from the corpus's X{root directory},
        which specifies where the files for the corpus are stored.  In
        particular, each subdirectory of the root directory defines a
        subcorpus; and each file in the root directory is a file in
        the corpus.

        @param name: The name of the corpus.
        @type name: C{string}
        @param directory: The corpus's root directory.  If
            C{directory} is a relative path, then it is interpreted
            relative to L{_BASEDIR} (which specifies the base directory
            for NLTK's standard distribution of corpora).
        @type directory: C{string}
        @param description: A description of the corpus.  This
            description should specify what kind of supcorpora and
            files the corpus contains, and what format those files are
            in.  The description should include the name of the
            corpus itself, since the same description will be re-used
            for subcorpora.  If no description is given, then the
            file C{I{directory}/I{name}.readme} will be checked for
            a description.
        @type default_tokenizer: L{TokenizierI<nltk.tokenizer.TokenizerI>}
        @param default_tokenizer: The default tokenizer for the
            L{tokenize()} file access method.
        """
        self._name = name

        # Find the corpus's root directory.
        if not os.path.isabs(directory):
            directory = os.path.join(_BASEDIR, directory)
        self._directory = directory

        # Get the description
        if description is None:
            try: self._description = open(directory+'.readme').read().strip()
            except: self._description = None
        else:
            self._description = description.strip()

        # Defaults for file access methods
        self._default_tokenizer = default_tokenizer

        # Postpone initialization of these, for two reasons:
        #   1. initialization can be slow; we only want to initialize
        #      the corpora that they'll actually be using.
        #   2. If a corpus is not installed, we want to signal an
        #      error when they try to access it, not when they import
        #      the nltk.copus module.
        self._filenames = None
        self._subcorpora = None

    def __initialize(self):
        """
        Initialize C{self._filenames} and C{self._subcorpora}, if they
        have not already been initialized.
        """
        if self._filenames is not None: return
        directory = self._directory
        name = self._name
        descr = self._description
        
        try: contents = [(f, os.path.join(directory, f))
                         for f in os.listdir(directory)]
        except: raise IOError('%s is not installed' % self._name)

        self._filenames = []
        self._subcorpora = []
        for (f,p) in contents:
            if os.path.isfile(p):
                self._filenames.append(f)
            elif os.path.isdir(p):
                tok = self._default_tokenizer
                self._subcorpora.append(Corpus(f, p, descr, tok))

    #////////////////////////////////////////////////////////////
    #// Subcorpus access function
    #////////////////////////////////////////////////////////////

    def subcorpora(self):
        """
        @return: A list of the subcorpora contained in this corpus.
        @rtype: C{list} of L{Corpus}
        """
        self.__initialize()
        return self._subcorpora

    #////////////////////////////////////////////////////////////
    #// File access functions
    #////////////////////////////////////////////////////////////

    def filenames(self):
        """
        @return: A list containing the names of the files contained in
            this corpus.
        @rtype: C{list} of C{string}
        """
        self.__initialize()
        return self._filenames

    def open(self, filename):
        """
        @return: A read-mode C{file} object for the given file.
        @param filename: The filename of the file to read.
        @rtype: C{file}
        """
        path = os.path.join(self._directory, filename)
        if os.path.isfile(path):
            return open(path, 'r')
        else:
            raise KeyError, 'Unknown filename %r' % filename

    def read(self, filename):
        """
        @return: A string containing the contents of the given file.
        @param filename: The filename of the file to read.
        @rtype: C{string}
        """
        return self.open(filename).read()

    def readlines(self, filename):
        """
        @return: A list of the contents of each line in the given
            file.  Trailing newlines are included.
        @param filename: The filename of the file to read.
        @rtype: C{list} of C{string}
        """
        return self.open(filename).readlines()

    def tokenize(self, filename, tokenizer=None):
        """
        @return: A list of the tokens in the given file.
        @param filename: The filename of the file to read.
        @param tokenizer: The tokenizer that should be used to
            tokenize the file.  If no tokenizer is specified, then the
            default tokenizer for this corpus is used.
        @rtype: C{list} of L{Token<nltk.token.Token>}
        """
        if tokenizer is None: tokenizer = self._default_tokenizer
        return tokenizer.tokenize(self.read(filename))
                          
    #////////////////////////////////////////////////////////////
    #// Corpus Information
    #////////////////////////////////////////////////////////////

    def name(self):
        """
        @return: The name of this corpus.
        @rtype: C{string}
        """
        return self._name

    def description(self):
        """
        @return: A description of the contents of this corpus.  (If
            this is a subcorpus of another corpus, then the
            description of the parent corpus is returned.)
        @rtype: C{string}
        """
        return self._description

    def __repr__(self):
        """
        @return: A single-line description of this corpus.
        """
        str = self._name
        try:
            filenames = self.filenames()
            subcorpora = self.subcorpora()
            if filenames:
                if subcorpora:
                    str += (' (contains %d files and %d subcorpora)' %
                            (len(filenames), len(subcorpora)))
                else:
                    str += ' (contains %d files)' % len(filenames)
            elif subcorpora:
                str += ' (contains %d subcorpora)' % len(subcorpora)
        except:
            str += ' (not installed)'

        return '<Corpus: %s>' % str

    def __str__(self):
        """
        @return: A multi-line description of this corpus.
        """
        str = repr(self)[9:-1]
        if self._description:
            str += ':\n'
            str += '\n'.join(['  '+line for line
                              in self._description.split('\n')])
        return str

#################################################################
# Standard Corpora
#################################################################
from nltk.tree import TreebankTokenizer

twenty_newsgroups = Corpus('20 Newsgroups', '20_newsgroups')
treebank = Corpus('Treebank', 'treebank',
                  default_tokenizer=TreebankTokenizer())
wordlist = Corpus('Wordlist', 'wordlist')
reuters = Corpus('Reuters-21578', 'reuters-21578')

# URL for reuters corpus:
# <http://www.daviddlewis.com/resources/testcollections/reuters21578/>

#################################################################
# Testing/Example use
#################################################################

if __name__ == '__main__':
    from nltk.corpus import twenty_newsgroups
    print '-'*70
    print `twenty_newsgroups`
    print '-'*70
    print twenty_newsgroups
    print '-'*70
    for newsgroup in twenty_newsgroups.subcorpora()[:3]:
        print newsgroup.name(), newsgroup.filenames()[:5], '...'
    print '-'*70
    newsgroup = twenty_newsgroups.subcorpora()[0]
    filename = newsgroup.filenames()[0]
    print `newsgroup.read(filename)[:50]`, '...'
    print '-'*70
    print newsgroup.tokenize(filename)[:4], '...'
    print '-'*70
    
