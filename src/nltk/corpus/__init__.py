# Natural Language Toolkit: Corpus Access
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

# Goals for this module:
#
#  1. we want corpus access to be easy.  In particular, we don't want
#     people to need to think about file formats, or which tokenizers
#     etc to use.
#
#  2. we want corpus access to be consistant (each corpus is accessed
#     using the same basic system).
#
#  3. we want corpus access to be portable (eg not dependent on where
#     files are installed).
#
#  4. we want to make it easy to tell NLTK about new corpera
#
#     4a. it should be possible to tell NLTK about an existing corpus
#         without moving the corpus, or editing its contents in any way.
#
#  5. we want to be able to handle a wide variety of formats, including
#     formats where mutliple files are used to represent the same data
#     (eg standoff annotation). 

"""
Access to NLTK's standard distribution of corpora.  Each corpus is
accessed by an instance of a C{CorpusReader} class.  For information
about using these corpora, see the reference documentation for
L{CorpusReaderI}.  The following corpus readers are currently defined:

  - L{twenty_newsgroups}: A collection of approximately 20,000
     Usenet newsgroup documents, partitioned (nearly) evenly across 20
     different newsgroups.
     
  - L{brown}: Approximately 1,000,000 words of part-of-speech tagged
    text.  The text consists of exerpts from 500 English prose
    documents, all printed in the United States in 1961.  Each exerpt
    is approximately 2000 words long.  The experts are grouped into 15
    topical categories that cover a wide range of genres and styles.
  
  - L{genesis}: A collection of six translations of the book of Genesis.
    The texts are taken from several different languages,
    and range from 1,500 words to 4,000 words each.
  
  - L{gutenberg}: A collection of fourteen public-domain English etexts
    from Project Gutenberg.  The texts are taken from seven different
    authors, and range from 7,500 words to 800,000 words.
  
  - L{roget}: The 11th edition of Roget's Thesaurus of English Words
    and Phrases, from Project Guttenberg.  Each item in this corpus
    corresponds to a single thesaurus entry from Roget's thesaurus.
  
  - L{words}: A list of about 45,000 unique words and word forms.
    The word list contains mostly English words and names, but also
    contains some non-English words that occur frequently in English
    text.
  
  - L{chunking}: A collection of 11,000 chunked, tagged sentences from
    the CoNLL 2000 chunking evaluation.
  
  - L{ppattatch}: Information about approximately 30,000 instances
    of potentially ambigous prepositional phrase attatchments.  For
    each instance, the corpus specifies the verb and noun that the
    prepositional phrase might potentially attatch to; and the
    preposition and head noun of the prepositional phrase.  I{The
    reader for this corpus is not implemented yet.}

  - L{reuters}: A collection of approximately 21,500 documents that
    appeared on the Reuters newswire in 1987.  The documents were
    assembled and indexed with categories by Reuters.  I{The reader
    for this corpus is corpus is not implemented yet.}

  - L{treebank}: A collection of hand-annotated parse trees for
    Englsih text.  I{This corpus can only be distributed through
    LDC; it is therefore not included as part of the standard NLTK
    corpus set.  However, the C{treebank} object will provide access
    to this corpus, if it is installed.}

  - L{semcor}: A tagged corpora of approximately 200,000 words, where
    each word type is tagged with its part of speech and sense
    identifier in WordNet.
                                                                                
  - L{senseval}: A set of corpora, each containing a set of contexts
    in which a specific ambiguous word appears. Each instance is tagged
    with a sense identifier. The ambiguous words used are line/N,
    interest/N, hard/A and serve/V.

  - L{levin}: The index from Beth Levin's verb classification text,
    indicating in which sections a given verb appears. The sectioning of
    her text corresponds to different generalisations over verbs.
  
@group Corpus Readers: twenty_newsgroups, treebank, words, reuters,
     ppatttach, brown, gutenberg
@var twenty_newsgroups: A collection of approximately 20,000
     Usenet newsgroup documents, partitioned (nearly) evenly across 20
     different newsgroups.
@var treebank: A collection of hand-annotated parse trees for
     english text.
@var words: A list of English words and word forms.
@var reuters: A collection of documents that appeared on Reuters
     newswire in 1987.
@var ppattach: Information about potentially ambiguous prepositional
     phrase attatchments.
@var brown: Approximately 1,000,000 words of part-of-speech tagged
     text.
@var gutenberg: A collection fourteen public-domain English etexts
     from Project Gutenberg.
@var semcor: A corpus of 200,000 words, each tagged with its WordNet sense.
@var senseval: A collection of texts, each consisting of a set of instances
     of a given ambiguous word, along tagged with its correct sense.
@var levin: The index from Beth Levin's verb classification text,
    indicating in which sections a given verb appears. 
      
@todo: Add default basedir for OS-X?

@variable _BASEDIR: The base directory for NLTK's standard distribution
    of corpora.  This is read from the environment variable
    C{NLTK_CORPORA}, if it exists; otherwise, it is given a
    system-dependant default value.  C{_BASEDIR}'s value can be changed
    with the L{set_basedir()} function.
@type _BASEDIR: C{string}
"""

import sys, os.path, re
from nltk.token import *
from nltk.tokenizer import RegexpTokenizer
from nltk.tokenreader import *

#################################################################
# Base Directory for Corpora
#################################################################
def set_basedir(path):
    """
    Set the path to the directory where NLTK looks for corpora.
    
    @type path: C{string}
    @param path: The path to the directory where NLTK should look for
        corpora.
    """
    global _BASEDIR
    _BASEDIR = path

def get_basedir():
    """
    @return: The path of the directory where NLTK looks for corpora.
    @rtype: C{string}
    """
    return _BASEDIR

# Find a default base directory.
if os.environ.has_key('NLTK_CORPORA'):
    set_basedir(os.environ['NLTK_CORPORA'])
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
# Corpus Reader Interface
#################################################################
class CorpusReaderI:
    """
    An accessor for a collection of natural language data.  This
    collection is organized as a set of named X{items}.  Typically,
    each item corresponds to a single file, and contains a single
    coherent text; but some corpora are divided into items along
    different lines.

    A corpus can optionally contain a set of X{groups}, or collections
    of related items.  The items within a single group all have
    the same format; but different groups may have different formats.
    The set of a corpus's groups are often (but not always) mutually
    exclusive.  For a description of the groups that are available for
    a specific corpus, use the L{description()} method.

    The L{groups} method returns a list of the groups that are defined
    for a C{CorpusReader}'s corpus.  The L{items()} method returns a
    list of the names of the items in a group or corpus.  The
    X{item reader} methods (listed below) are used to read the
    contents of individual items.  The following example
    demonstrates the use of a C{Corpus}:

        >>> for newsgroup in twenty_newsgroups.groups():
        ...    for item in twenty_newsgroup.items(newsgroup):
        ...        do_something(newsgroup.tokenize(item), newsgroup)

    Some corpora do not implement all of the item reader methods; if
    a corpus doesn't implement an item reader method, then that
    method will raise a C{NotImplementedError}.  Some corpora define
    new item reader methods, for reading their contents in specific
    formats; see the documentation for individual implementations of
    the C{CorpusReaderI} interface for information about new item reader
    methods.

    @group Basic Item Access: items, read, tokenize, xread, xtokenize
    @group Raw Item Access: path, open, raw_read, raw_tokenize,
        raw_xtokenize
    @group Structured Groups: groups
    @group Metadata: name, description, licence, copyright,
        __str__, __repr__
    """

    #////////////////////////////////////////////////////////////
    #// Corpus Information/Metadata
    #////////////////////////////////////////////////////////////
    def name(self):
        """
        @return: The name of this C{CorpusReader}'s corpus.
        @rtype: C{string}
        """
        raise AssertionError, 'CorpusReaderI is an abstract interface'

    def description(self):
        """
        @return: A description of the contents of this
            C{CorpusReader}'s corpus; or C{None} if no description is
            available.
        @rtype: C{string} or C{None}
        """
        return None

    def license(self):
        """
        @return: Information about the license governing the use of
            this C{CorpusReader}'s corpus.
        @rtype: C{string}
        """
        return 'Unknown'

    def copyright(self):
        """
        @return: A copyright notice for this C{CorpusReader}'s corpus.
        @rtype: C{string}
        """
        return 'Unknown'

    def installed(self):
        """
        @return: True if this corpus is installed.
        @rtype: C{boolean}
        """
        raise AssertionError, 'CorpusReaderI is an abstract interface'

    #////////////////////////////////////////////////////////////
    #// Data access (items)
    #////////////////////////////////////////////////////////////
    def items(self, group=None):
        """
        @return: A list of the names of the items contained in the
            specified group, or in the entire corpus if no group is
            specified.
        @rtype: C{list} of C{string}
        """
        raise AssertionError, 'CorpusReaderI is an abstract interface'

    def read(self, item):
        """
        @return: A token containing the contents of the given item.
        @param item: The name of the item to read.
        @rtype: L{Token<nltk.token.Token>}
        """
        raise NotImplementedError, 'This corpus does not implement read()'

    def xread(self, item):
        """
        @return: A token containing the contents of the given item,
            with properties stored as iterators (where applicable).
        @param item: The name of the item to read.
        @rtype: L{Token<nltk.token.Token>}
        """
        raise NotImplementedError, 'This corpus does not implement read()'

    #////////////////////////////////////////////////////////////
    #// Raw Item access
    #////////////////////////////////////////////////////////////
    def path(self, item):
        """
        @return: The path of a file containing the given item.
        @param item: The name of the requested item
        @rtype: C{string}
        """
        raise NotImplementedError, 'This corpus does not implement path()'

    def open(self, item):
        """
        @return: A read-mode C{file} object for the given item.
        @param item: The name of the item to read.
        @rtype: C{file}
        """
        raise NotImplementedError, 'This corpus does not implement open()'

    def raw_read(self, item):
        """
        @return: A string containing the contents of the given item.
        @param item: The name of the item to read.
        @rtype: C{string}
        """
        raise NotImplementedError, 'This corpus does not implement raw_read()'

    #////////////////////////////////////////////////////////////
    #// Structure access (groups)
    #////////////////////////////////////////////////////////////
    def groups(self):
        """
        @return: A list of the names of the groups contained in this
            C{CorpusReader}'s corpus.
        @rtype: C{list} of L{string}
        """
        raise AssertionError, 'CorpusReaderI is an abstract interface'

    #////////////////////////////////////////////////////////////
    #// Printing
    #////////////////////////////////////////////////////////////
    def __repr__(self):
        """
        @return: A single-line description of this corpus.
        """
        str = self._name
        try:
            items = self.items()
            groups = self.groups()
            if items:
                if groups:
                    str += (' (contains %d items; %d groups)' %
                            (len(items), len(groups)))
                else:
                    str += ' (contains %d items)' % len(items)
            elif groups:
                str += ' (contains %d groups)' % len(groups)
        except IOError:
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
# General-purpose Corpus Implementation
#################################################################
class SimpleCorpusReader(CorpusReaderI):
    """
    A general-purpose implementation of the C{CorpusReader} interface
    that defines the set of items and the contents of groups with
    regular expressions over filenames.  The C{SimpleCorpusReader}
    implementation is suitable for defining corpus readers for corpora
    where:
    
        - Each item consists of the text in a single file.
        - Every item has the same format.
        - The filenames of items can be distinguished from the
          filenames of metadata files with a regular expression.
        - The set items in each group can be distinguished with
          a single regular expression.

    For the purposes of defining regular expressions over path names,
    use the forward-slash character (C{'/'}) to delimit directories.
    C{SimpleCorpusReader} will automatically convert this to the
    appropriate path delimiter for the operating system.
    """
    def __init__(self,
                 # Basic Information
                 name, rootdir, items_regexp,
                 # Grouping
                 groups=None,
                 # Meta-data
                 description=None, description_file=None, 
                 license_file=None,
                 copyright_file=None,
                 # Formatting meta-data
                 token_reader=None,
                 property_names={}):
        """
        Construct a new corpus reader.  The parameters C{description},
        C{description_file}, C{license_file}, and C{copyright_file}
        specify optional metadata.  For the corpus reader's
        description, you should use C{description} or
        C{description_file}, but not both.

        @group Basic Information: name, rootdir, items_regexp
        @group Grouping: groups
        @group Meta-data: description, license, copyright,
            description_file, license_file, copyright_file
        @group Formatting Meta-data: token_reader

        @type name: C{string}
        @param name: The name of the corpus.  This name is used for
            printing the corpus reader, and for constructing
            locations.  It should usually be identical to the name of
            the variable that holds the corpus reader.
        @type rootdir: C{string}
        @param rootdir: The path to the root directory for the
            corpus.  If C{rootdir} is a relative path, then it is
            interpreted relative to the C{nltk.corpus} base directory
            (as returned by L{nltk.corpus.get_basedir()}).
        @type items_regexp: C{regexp} or C{string}
        @param items_regexp: A regular expression over paths that
            defines the set of files that should be listed as
            entities for the corpus.  The paths that this is tested
            against are all relative to the corpus's root directory.
            Use the forward-slash character (C{'/'} to delimit
            subdirectories; C{SimpleCorpusReader} will automatically convert
            this to the appropriate path delimiter for the operating
            system.
        @type groups: C{list} of C{(string, regexp)} tuples
        @param groups: A list specifying the groups for the corpus.
            Each element in this list should be a pair
            C{(M{groupname}, M{regexp})}, where C{M{groupname}} is the
            name of a group; and C{M{regexp}} is a regular expression
            over paths that defines the set of files that should be
            listed as entities for that group.  The paths that these
            regular expressions are tested against are all relative
            to the corpus's root directory.  Use the forward-slash
            character (C{'/'} to delimit subdirectories;
            C{SimpleCorpusReader} will automatically convert this to the
            appropriate path delimiter for the operating system.
        @type description: C{string}
        @param description: A description of the corpus.
        @type description_file: C{string}
        @param description_file: The path to a file containing a
            description of the corpus.  If this is a relative path,
            then it is interpreted relative to the corpus's root
            directory.
        @type license_file: C{string}
        @param license_file: The path to a file containing licensing
            information about the corpus.  If this is a relative
            path, then it is interpreted relative to the corpus's root
            directory.
        @type copyright_file: C{string}
        @param copyright_file: The path to a file containing a
            copyright notice for the corpus.  If this is a relative
            path, then it is interpreted relative to the corpus's root
            directory.
        @type token_reader: L{TokenReaderI<nltk.token.TokenReaderI>}
        @param token_reader: The default token_reader that should be
            used for the corpus reader's L{read_token} method.
        """
        if token_reader is None:
            token_reader = WhitespaceSeparatedTokenReader(
                SUBTOKENS='WORDS')
        # Compile regular expressions.
        if isinstance(items_regexp, type('')):
            items_regexp = re.compile(items_regexp)
        if groups is None: groups = []
        else: groups = groups[:]
        for i in range(len(groups)):
            if isinstance(groups[i][1], type('')):
                groups[i] = (groups[i][0], re.compile(groups[i][1]))

        # Save parameters
        self._name = name
        self._original_rootdir = rootdir
        self._items_regexp = items_regexp
        self._grouplists = groups
        self._description = description
        self._description_file = description_file
        self._license = None
        self._license_file = license_file
        self._copyright = None
        self._copyright_file = copyright_file
        self._token_reader = token_reader
        self._property_names = property_names

        # Postpone actual initialization until the corpus is accessed;
        # this gives the user a chance to call set_basedir(), and
        # prevents "import nltk.corpus" from raising an exception.
        # We'll also want to re-initialize the corpus if basedir
        # ever changes.
        self._basedir = None
        self._rootdir = None
        self._items = None
        self._groups = None

    #////////////////////////////////////////////////////////////
    #// Initialization
    #////////////////////////////////////////////////////////////
    def _initialize(self):
        "Make sure that we're initialized."
        # If we're already initialized, then do nothing.
        if self._basedir == get_basedir(): return

        # Make sure the corpus is installed.
        basedir = get_basedir()
        if not os.path.isdir(os.path.join(basedir, self._original_rootdir)):
            raise IOError('%s is not installed' % self._name)
        self._basedir = basedir
        self._rootdir = os.path.join(basedir, self._original_rootdir)

        # Build a filelist for the corpus
        filelist = self._find_files(self._rootdir)
        filelist = [os.path.join(*(file.split('/')))
                    for file in filelist]

        # Find the files that are items
        self._items = [f for f in filelist
                         if self._items_regexp.match(f)]

        # Find the files for each group.
        self._groups = {}
        for (groupname, regexp) in self._grouplists:
            self._groups[groupname] = [f for f in filelist
                                       if regexp.match(f)]

        # Read metadata from files
        if self._description is None and self._description_file is not None:
            path = os.path.join(self._rootdir, self._description_file)
            try: self._description = open(path).read()
            except IOError: pass
        if self._license is None and self._license_file is not None:
            path = os.path.join(self._rootdir, self._license_file)
            try: self._license = open(path).read()
            except IOError: pass
        if self._copyright is None and self._copyright_file is not None:
            path = os.path.join(self._rootdir, self._copyright_file)
            try: self._copyright = open(path).read()
            except IOError: pass

    def _find_files(self, path, prefix=''):
        filelist = []
        for name in os.listdir(path):
            filepath = os.path.join(path, name)
            if os.path.isfile(filepath):
                filelist.append('%s%s' % (prefix, name))
            elif os.path.isdir(filepath):
                filelist += self._find_files(filepath,
                                             '%s%s/' % (prefix, name))
        return filelist

    #////////////////////////////////////////////////////////////
    #// Corpus Information/Metadata
    #////////////////////////////////////////////////////////////
    def name(self):
        return self._name

    def description(self):
        self._initialize()
        return self._description

    def license(self):
        self._initialize()
        return self._license

    def copyright(self):
        self._initialize()
        return self._copyright

    def installed(self):
        try: self._initialize()
        except IOError: return 0
        return 1

    #////////////////////////////////////////////////////////////
    #// Data access (items)
    #////////////////////////////////////////////////////////////
    def items(self, group=None):
        self._initialize()
        if group is None: return self._items
        else: return tuple(self._groups.get(group)) or ()

    def read(self, item):
        source = '%s/%s' % (self._name, item)
        text = self.raw_read(item)
        return self._token_reader.read_token(text, source=source)

    def xread(self, item):
        # Default: no iterators.
        return self.read(item)

    def path(self, item):
        self._initialize()
        return os.path.join(self._rootdir, item)

    def open(self, item):
        self._initialize()
        return open(self.path(item))

    def raw_read(self, item):
        return self.open(item).read()

    #////////////////////////////////////////////////////////////
    #// Structure access (groups)
    #////////////////////////////////////////////////////////////

    def groups(self):
        self._initialize()
        return self._groups.keys()

#################################################################
# The standard corpora
#################################################################

###################################################
## 20 Newsgroups
groups = [(ng, ng+'/.*') for ng in '''
    alt.atheism rec.autos sci.space comp.graphics rec.motorcycles
    soc.religion.christian comp.os.ms-windows.misc rec.sport.baseball
    talk.politics.guns comp.sys.ibm.pc.hardware rec.sport.hockey
    talk.politics.mideast comp.sys.mac.hardware sci.crypt
    talk.politics.misc comp.windows.x sci.electronics
    talk.religion.misc misc.forsale sci.med'''.split()]
twenty_newsgroups = SimpleCorpusReader(
    '20_newsgroups', '20_newsgroups/', '.*/.*', groups,
    description_file='../20_newsgroups.readme')
del groups # delete temporary variable

###################################################
## Brown
groups = [('press: reportage', r'ca\d\d'), ('press: editorial', r'cb\d\d'),
          ('press: reviews', r'cc\d\d'), ('religion', r'cd\d\d'),
          ('skill and hobbies', r'ce\d\d'), ('popular lore', r'cf\d\d'),
          ('belles-lettres', r'cg\d\d'),
          ('miscellaneous: government & house organs', r'ch\d\d'),
          ('learned', r'cj\d\d'), ('fiction: general', r'ck\d\d'),
          ('fiction: mystery', r'cl\d\d'), ('fiction: science', r'cm\d\d'),
          ('fiction: adventure', r'cn\d\d'), ('fiction: romance', r'cp\d\d'),
          ('humor', r'cr\d\d')]
brown = SimpleCorpusReader(
    'brown', 'brown/', r'c\w\d\d', groups, description_file='README',
    token_reader=TaggedTokenReader(SUBTOKENS='WORDS'))
del groups # delete temporary variable
 
###################################################
## Genesis
genesis = SimpleCorpusReader(
    'genesis', 'genesis/', r'.*\.txt', description_file='README')

###################################################
## Gutenberg
groups = [('austen', 'austen-.*'), ('bible', 'bible-.*'),
          ('blake', 'blake-.*'), ('chesterton', 'chesterton-.*'),
          ('milton', 'milton-.*'), ('shakespeare', 'shakespeare-.*'),
          ('whitman', 'whitman-.*')]
gutenberg = SimpleCorpusReader(
    'gutenberg', 'gutenberg/', r'.*\.txt', groups, description_file='README')
del groups # delete temporary variable

###################################################
## PP Attachment

ppattach = '''\
[CORPUS READER NOT IMPLEMENTED YET]

Information about approximately 30,000 instances of potentially
ambigous prepositional phrase attachments.  For each instance, the
corpus specifies the verb and noun that the prepositional phrase might
potentially attach to; and the preposition and head noun of the
prepositional phrase.'''

###################################################
## Roget

from nltk.corpus.roget import RogetCorpusReader
roget = RogetCorpusReader('roget', 'roget/', 'roget15a.txt')

###################################################
## Words corpus (just English at this point)

words = SimpleCorpusReader(
    'words', 'words/', r'words', description_file='README')

###################################################
## Stopwords corpus

stopwords = SimpleCorpusReader(
    'stopwords', 'stopwords/', r'[a-z]+', description_file='README')

###################################################
## CONLL 2000 Chunking data corpus

chunking = SimpleCorpusReader(
    'chunking', 'chunking/', r'.*\.txt', None, description_file='README',
    token_reader=TokenizerBasedTokenReader(
                             RegexpTokenizer(r'\n\s*?\n', negative=1)))

###################################################
## IEER Named Entity data corpus

groups = [('APW', 'APW_\d*'), ('NYT', 'NYT_\d*')]
ieer = SimpleCorpusReader(
    'ieer', 'ieer/', r'(APW|NYT)_\d+', groups, description_file='README',
    token_reader=IeerTokenReader())
del groups # delete temporary variable

###################################################
## Treebank (fragment distributed with NLTK)

from nltk.corpus.treebank import TreebankCorpusReader
treebank = TreebankCorpusReader('treebank', 'treebank/', False,
                                description_file='README')

###################################################
## Semcor corpus
#from nltk.sense import SemcorTokenizer

description = """
WordNet semantic concordance data. This is comprised of extracts from the
Brown corpus, with each word tagged with its WordNet 1.7 tag.
"""

semcor = None
#semcor = SimpleCorpusReader(
#    'semcor', 'semcor1.7/', r'brown./tagfiles/.*', description=description,
#    default_tokenizer = SemcorTokenizer())
    
###################################################
## Senseval corpus
#from nltk.sense import SensevalTokenizer

senseval = None
#senseval = SimpleCorpusReader(
#    'senseval', 'senseval/', r'.*\.pos', description_file='README',
#    default_tokenizer = SensevalTokenizer())

###################################################
## Names corpus

names = SimpleCorpusReader(
    'names', 'names/', r'.*\.txt', description_file='README',
    token_reader = NewlineSeparatedTokenReader(SUBTOKENS='NAMES'))

###################################################
## Reuters corpus

reuters = '''\
[CORPUS READER NOT IMPLEMENTED YET]

A collection of approximately 21,500 documents that appeared on the
Reuters newswire in 1987.  The documents were assembled and indexed
with categories by Reuters.'''

# Not supported yet

###################################################
## Levin corpus

levin = None
# class _LevinTokenizer(TokenizerI):
#     # [XX] addlocs & addcontexts are ignored!
#     def tokenize(self, token, addlocs=False, addcontexts=False):
#         token['VERB_DICT'] = {}
#         for line in token['TEXT'].split('\n'):
#             items = line.split(':')
#             if len(items) == 2:
#                 verb, indices = items
#                 indices = filter(lambda x: x, re.split(r'[,\s]*', indices))
#                 token['VERB_DICT'][verb.strip()] = indices

# levin = SimpleCorpusReader(
#     'levin', 'levin/', 'verbs', description_file='README',
#     default_tokenizer = _LevinTokenizer())

#################################################################
# Demonstration
#################################################################

def _truncate_repr(obj, width, indent, lines=1):
    n = width-indent
    s = repr(obj)
    if len(s) > n*lines:
        s = s[:n*lines-3] + '...'
    s = re.sub('(.{%d})' % n, '\\1\n'+' '*indent, s)
    return s.rstrip()

def _xtokenize_repr(token, width, indent, lines=1):
    n = width-indent
    s = '<'+'['
    for subtok in token['SUBTOKENS']:
        s += '%r, ' % subtok
        if len(s) > n*lines:
            s = s[:n*lines-3]+'...'
            break
    else: s = s[:-2] + ']'+'>'
    s = re.sub('(.{%d})' % n, '\\1\n'+' '*indent, s)
    return s.rstrip()

def _test_corpus(corpus):
    if corpus is None:
        print '(skipping None)'
        return
    print '='*70
    print corpus.name().center(70)
    print '-'*70
    print 'description() => ' + _truncate_repr(corpus.description(), 70,17)
    print 'license()     => ' + _truncate_repr(corpus.license(), 70,17)
    print 'copyright()   => ' + _truncate_repr(corpus.copyright(), 70,17)
    print 'items()       => ' + _truncate_repr(corpus.items(), 70,17)
    print 'groups()      => ' + _truncate_repr(corpus.groups(), 70,17)
    item = corpus.items()[0]
    contents = corpus.read(item)
    print 'read(e0)      => ' + _truncate_repr(contents, 70,17)
#    try:
#        tokrepr = _xtokenize_repr(corpus.xtokenize(item), 70,17,2)
#        print 'xtokenize(e0) => ' + tokrepr
#    except NotImplementedError:
#        tokrepr = _truncate_repr(corpus.tokenize(item), 70,17,2)
#        print 'tokenize(e0)  => ' + tokrepr

def _test_treebank():
    _test_corpus(treebank)
    print '-'*70
    print "r, t, p, m = [treebank.items(group)[0] for group in"
    print "              'raw', 'tagged', 'parsed', 'merged']"
    r = treebank.items('raw')[0]
    t = treebank.items('tagged')[0]
    p = treebank.items('parsed')[0]
    m = treebank.items('merged')[0]
    for (name, item) in zip('rtpm', (r, t, p, m)):
        contents = treebank.read(item)
        print 'read(%s)       => %s' % (name, _truncate_repr(contents, 70,17))
        #try:
        #    tok = treebank.xtokenize(item)
        #    tokrepr = _xtokenize_repr(tok.exclude('LOC'), 70,17,2)
        #    print 'xtokenize(%s)  => %s' % (name, tokrepr)
        #except NotImplementedError:
        #    tok = treebank.tokenize(item)
        #    tokrepr = _truncate_repr(tok.exclude('LOC'), 70,17,2)
        #    print 'tokenize(%s)   => %s' % (name, tokrepr)

def demo():
    """
    Demonstrate corpus access for each of the defined corpora.
    """
    _test_corpus(twenty_newsgroups)
    _test_corpus(brown)
    _test_corpus(gutenberg)
    _test_corpus(roget)
    _test_corpus(words)
    _test_corpus(semcor)
    _test_corpus(senseval)
    _test_treebank()
    print '='*70
    
if __name__ == '__main__':
    demo()
