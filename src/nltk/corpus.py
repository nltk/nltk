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
#  3. we want corpus access to be portable (eg not dependant on where
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
encoded as an instance of the C{Corpus} class.  For information about
using these corpora, see the reference documentation for L{CorpusI}.
The following corpora are currently defined:

  - L{twenty_newsgroups}: A collection of approximately 20,000
     Usenet newsgroup documents, partitioned (nearly) evenly across 20
     different newsgroups.
     
  - L{brown}: Approximately 1,000,000 words of part-of-speech tagged
    text.  The text consists of exerpts from 500 English prose
    documents, all printed in the United States in 1961.  Each exerpt
    is approximately 2000 words long.  The experts are grouped into 15
    topical categories that cover a wide range of genres and styles.
  
  - L{gutenberg}: A collection fourteen public-domain English etexts
    from Project Gutenberg.  The texts are taken from seven different
    authors, and range from 7,500 words to 800,000 words.
  
  - L{roget}: The 11th edition of Roget's Thesaurus of English Words
    and Phrases, from Project Guttenberg.  Each entry in this corpus
    corresponds to a single thesaurus entries from Roget's thesaurus.
  
  - L{wordlist}: A list of about 45,000 unique words and word forms.
    The word list contains mostly English words and names, but also
    contains some non-English words that occur frequently in English
    text.
  
  - L{ppattatch}: Information about approximately 30,000 instances
    of potentially ambigous prepositional phrase attatchments.  For
    each instance, the corpus specifies the verb and noun that the
    prepositional phrase might potentially attatch to; and the
    preposition and head noun of the prepositional phrase.  I{The
    interface to this corpus is not implemented yet.}

  - L{reuters}: A collection of approximately 21,500 documents that
    appeared on the Reuters newswire in 1987.  The documents were
    assembled and indexed with categories by Reuters.  I{The interface
    to this corpus is corpus is not implemented yet.}

  - L{treebank}: A collection of hand-annotated parse trees for
    Englsih text.  I{This corpus can only be distributed through
    LDC; it is therefore not included as part of the standard NLTK
    corpus set.  However, the C{treebank} object will provide access
    to this corpus, if it is installed.}
  
@group Corpora: twenty_newsgroups, treebank, wordlist, reuters
@var twenty_newsgroups: A collection of approximately 20,000
     Usenet newsgroup documents, partitioned (nearly) evenly across 20
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
    C{NLTK_CORPORA}, if it exists; otherwise, it is given a
    system-dependant default value.  C{_BASEDIR}'s value can be changed
    with the L{set_basedir()} function.
@type _BASEDIR: C{string}
"""

import sys, os.path, re
from nltk.tokenizer import WSTokenizer

#################################################################
# Base Directory for Corpora
#################################################################
def set_basedir(path):
    """
    Set the path to the directory where NLTK looks for corpora.
    
    @type dir: C{string}
    @param dir: The path to the directory where NLTK should look for
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
# Corpus Interface
#################################################################
class CorpusI:
    """
    A collection of natural language data.  This collection is
    organized as a set of named X{entries}.  Typically, each entry
    corresponds to a single file, and contains a single coherent text;
    but some corpora are divided into entries along different lines.

    A corpus can optionally contain a set of X{groups}, or collections
    of related entries.  These groups are often (but not always)
    mutually exclusive.  For a description of the groups that are
    available for a specific corpus, see the corpus's description.

    The L{groups} method returns a list of the groups that are defined
    for a corpus.  The L{entries()} method returns a list of the names
    of the entries in a group or corpus.  The X{entry reader} methods
    (listed below) are used to read the contents of individual
    entries.  The following example demonstrates the use of a
    C{Corpus}:

        >>> for newsgroup in twenty_newsgroups.groups():
        ...    for entry in twenty_newsgroup.entries(newsgroup):
        ...        do_something(newsgroup.tokenize(entry), newsgroup)

    Some corpora do not implement all of the entry reader methods; if
    a corpus doesn't implement an entry reader method, then that
    method will raise a C{NotImplementedError}.  Some corpora define
    new entry reader methods, for reading their contents in specific
    formats; see the documentation for individual implementations of
    the C{CorpusI} interface for information about new entry reader
    methods.

    @group Entry Access: open, read, readlines, tokenize
    @group Subcorpus Access: subcorpora
    @group Metadata: name, description, licence, copyright,
        __str__, __repr__
    @sort: open, read, readlines, tokenize,
           name, description, __str__, __repr__
    """

    #////////////////////////////////////////////////////////////
    #// Corpus Information/Metadata
    #////////////////////////////////////////////////////////////

    def name(self):
        """
        @return: The name of this corpus.
        @rtype: C{string}
        """
        raise AssertionError, 'CorpusI is an abstract class'

    def description(self):
        """
        @return: A description of the contents of this corpus; or
            C{None} if no description is available.
        @rtype: C{string} or C{None}
        """
        return None

    def license(self):
        """
        @return: Information about the license governing the use of
            this corpus; or C{None} if no license information is
            available.
        @rtype: C{string}
        """
        return None

    def copyright(self):
        """
        @return: A copyright notice for this corpus; or C{None} if no
            copyright information is available.
        @rtype: C{string}
        """
        return None

    #////////////////////////////////////////////////////////////
    #// Data access (entries)
    #////////////////////////////////////////////////////////////
    def entries(self):
        """
        @return: A list containing the names of the entries contained in
            this corpus.
        @rtype: C{list} of C{string}
        """
        raise AssertionError, 'CorpusI is an abstract class'

    def open(self, entry):
        """
        @return: A read-mode C{entry} object for the given entry.
        @param entry: The name of the entry to read.
        @rtype: C{entry}
        """
        raise NotImplementedError, 'This corpus does not implement open()'

    def read(self, entry):
        """
        @return: A string containing the contents of the given entry.
        @param entry: The name of the entry to read.
        @rtype: C{string}
        """
        raise NotImplementedError, 'This corpus does not implement read()'

    def readlines(self, entry):
        """
        @return: A list of the contents of each line in the given
            entry.  Trailing newlines are included.
        @param entry: The name of the entry to read.
        @rtype: C{list} of C{string}
        """
        raise NotImplementedError, 'This corpus does not implement readlines()'

    def tokenize(self, entry, tokenizer=None):
        """
        @return: A list of the tokens in the given entry.
        @param entry: The name of the entry to read.
        @param tokenizer: The tokenizer that should be used to
            tokenize the entry.  If no tokenizer is specified, then the
            default tokenizer for this corpus is used.
        @rtype: C{list} of L{Token<nltk.token.Token>}
        """
        raise NotImplementedError, 'This corpus does not implement tokenize()'
                          
    #////////////////////////////////////////////////////////////
    #// Structure access (groups)
    #////////////////////////////////////////////////////////////

    def subcorpora(self):
        """
        @return: A list of the subcorpora contained in this corpus.
        @rtype: C{list} of L{Corpus}
        """
        raise AssertionError, 'CorpusI is an abstract class'

    def subcorpus(self, name):
        """
        @return: The subcorpus with the given name.
        @rtype: C{Corpus}
        """

    #////////////////////////////////////////////////////////////
    #// Printing
    #////////////////////////////////////////////////////////////

    def __repr__(self):
        """
        @return: A single-line description of this corpus.
        """
        str = self._name
        try:
            entries = self.entries()
            groups = self.groups()
            if entries:
                if groups:
                    str += (' (contains %d entries; %d groups)' %
                            (len(entries), len(groups)))
                else:
                    str += ' (contains %d entries)' % len(entries)
            elif groups:
                str += ' (contains %d groups)' % len(groups)
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
# General-purpose Corpus Implementation
#################################################################
class SimpleCorpus(CorpusI):
    """
    A general-purpose implementation of the Corpus interface that
    defines the set of entries and the contents of groups with regular
    expressions over filenames.  The C{SimpleCorpus} implementation is
    suitable for defining corpora where:
    
        - Each entry consists of the text in a single file.
        - Every entry has the same format.
        - The filenames of entries can be distinguished from the
          filenames of metadata files with a regular expression.
        - The set entries in each group can be distinguished with
          a single regular expression.

    For the purposes of defining regular expressions over path names,
    use the forward-slash character (C{'/'}) to delimit directories.
    C{SimpleCorpus} will automatically convert this to the appropriate
    path delimiter for the operating system.
    """
    def __init__(self,
                 # Basic Information
                 name, rootdir, entries_regexp,
                 # Grouping
                 groups=None,
                 # Meta-data
                 description=None, description_file=None, 
                 license=None, license_file=None,
                 copyright=None, copyright_file=None,
                 # Formatting meta-data
                 default_tokenizer=WSTokenizer()):
        """
        Construct a new corpus.  The parameters C{description},
        C{description_file}, C{license}, C{license_file},
        C{copyright}, and C{copyright_file} specify optional metadata.
        For each type of metadata, you should use either the string
        version or the filename version, but not both.

        @group Basic Information: name, rootdir, entries_regexp
        @group Grouping: groups
        @group Meta-data: description, license, copyright,
            description_file, license_file, copyright_file
        @group Formatting Meta-data: default_tokenizer

        @type name: C{string}
        @param name: The name of this corpus.  This name is used for
            printing the corpus, and for constructing locations.  It
            should usually be identical to the name of the variable
            that holds the corpus.
        @type name: C{string}
        @param rootdir: The path to the root directory for this
            corpus.  If C{rootdir} is a relative path, then it is
            interpreted relative to the C{nltk.corpus} base directory
            (as returned by L{nltk.corpus.basedir()}).
        @type name: C{regexp} or C{string}
        @param entries_regexp: A regular expression over paths that
            defines the set of files that should be listed as
            entities for this corpus.  The paths that this is tested
            against are all relative to the corpus's root directory.
            Use the forward-slash character (C{'/'} to delimit
            subdirectories; C{SimpleCorpus} will automatically convert
            this to the appropriate path delimiter for the operating
            system.
        @type groups: C{list} of C{(string, regexp)} tuples
        @param groups: A list specifying the groups for this corpus.
            Each element in this list should be a pair
            C{(M{groupname}, M{regexp})}, where C{M{groupname}} is the
            name of a group; and C{M{regexp}} is a regular expression
            over paths that defines the set of files that should be
            listed as entities for that group.  The paths that these
            regular expressions are tested against are all relative
            to the corpus's root directory.  Use the forward-slash
            character (C{'/'} to delimit subdirectories;
            C{SimpleCorpus} will automatically convert this to the
            appropriate path delimiter for the operating system.
        @type description: C{string}
        @param description: A description of this corpus.
        @type license: C{string}
        @param license: Licensing information about this corpus.
        @type copyright: C{string}
        @param copyright: A copyright notice for this corpus.
        @type description_file: C{string}
        @param description_file: The path to a file containing a
            description of this corpus.  If this is a relative path,
            then it is interpreted relative to the corpus's root
            directory.
        @type license_file: C{string}
        @param license_file: The path to a file containing licensing
            information about this corpus.  If this is a relative
            path, then it is interpreted relative to the corpus's root
            directory.
        @type copyright_file: C{string}
        @param copyright_file: The path to a file containing a
            copyright notice for this corpus.  If this is a relative
            path, then it is interpreted relative to the corpus's root
            directory.
        @type default_tokenizer: L{TokenizerI}
        @param default_tokenizer: The default tokenizer that should be
            used for this corpus's L{tokenize} method.
        """
        # Compile regular expressions.
        if isinstance(entries_regexp, type('')):
            entries_regexp = re.compile(entries_regexp)
        if groups is None: groups = []
        else: groups = groups[:]
        for i in range(len(groups)):
            if isinstance(groups[i][1], type('')):
                groups[i] = (groups[i][0], re.compile(groups[i][1]))

        # Save parameters
        self._name = name
        self._original_rootdir = rootdir
        self._entries_regexp = entries_regexp
        self._grouplists = groups
        self._description = description
        self._description_file = description_file
        self._license = license
        self._license_file = license_file
        self._copyright = copyright
        self._copyright_file = copyright_file
        self._default_tokenizer = default_tokenizer

        # Postpone actual initialization until the corpus is accessed;
        # this gives the user a chance to call set_basedir(), and
        # prevents "import nltk.corpus" from raising an exception.
        # We'll also want to re-initialize the corpus if basedir
        # ever changes.
        self._basedir = None
        self._rootdir = None
        self._entries = None
        self._groups = None

    def _initialize(self):
        "Make sure that we're initialized."

        # If we're already initialized, then do nothing.
        if self._basedir == get_basedir() and self._entries is not None:
            return

        # Make sure the corpus is installed.
        self._basedir = get_basedir()
        self._rootdir = os.path.join(get_basedir(), self._original_rootdir)
        if not os.path.isdir(self._rootdir):
            raise IOError('%s is not installed' % self._name)

        # Build a filelist for the corpus
        filelist = self._find_files(self._rootdir)
        filelist = [os.path.join(*(file.split('/')))
                    for file in filelist]

        # Find the files that are entries
        self._entries = [f for f in filelist
                         if self._entries_regexp.match(f)]

        # Find the files for each group.
        self._groups = {}
        for (groupname, regexp) in self._grouplists:
            self._groups[groupname] = [f for f in filelist
                                       if regexp.match(f)]

        # Read metadata from files
        if self._description is None and self._description_file is not None:
            path = os.path.join(self._rootdir, self._description_file)
            self._description = open(path).read()
        if self._license is None and self._license_file is not None:
            path = os.path.join(self._rootdir, self._license_file)
            self._license = open(path).read()
        if self._copyright is None and self._copyright_file is not None:
            path = os.path.join(self._rootdir, self._copyright_file)
            self._copyright = open(path).read()

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

    def entries(self, group=None):
        self._initialize()
        if group is None: return self._entries
        else: return self._groups.get(group) or []

    def open(self, entry):
        self._initialize()
        return open(os.path.join(self._rootdir, entry))

    def read(self, entry):
        return self.open(entry).read()

    def readlines(self, entry):
        return self.open(entry).readlines()

    def tokenize(self, entry, tokenizer=None):
        if tokenizer is None: tokenizer = self._default_tokenizer
        source = '%s/%s' % (self._name, entry)
        return tokenizer.tokenize(self.read(entry), source=source)

    def groups(self):
        self._initialize()
        return self._groups.keys()

#################################################################
# Corpus Implementation for Roget's Thesaurus
#################################################################

class RogetCorpus(CorpusI):
    def __init__(self, name, rootdir, data_file):
        self._name = name
        self._original_rootdir = rootdir
        self._data_file = data_file

        # Postpone actual initialization until the corpus is accessed;
        # this gives the user a chance to call set_basedir(), and
        # prevents "import nltk.corpus" from raising an exception.
        # We'll also want to re-initialize the corpus if basedir
        # ever changes.
        self._basedir = None
        self._entries = None
        self._rootdir = None
        self._groups = None
        self._description = None
        self._licence = None
        self._copyright = None

    LICENSE_RE = re.compile(r'\*+START\*+THE SMALL PRINT[^\n]' +
                            r'(.*?)' +
                            r'\*+END\*+THE SMALL PRINT', re.DOTALL)
    
    DESCRIPTION_RE = re.compile('(' + r'\*'*60 + r'.*?' +
                                r'='*60+'\s+-->)', re.DOTALL)

    ENTRY_RE = re.compile(r'^     #(\w+)\.\s+(' + #r'(([^-]*)\s--' +
                          r'.*?\n)',
                          re.DOTALL | re.MULTILINE)
    
    def _initialize(self):
        # If we're already initialized, then do nothing.
        if self._basedir == get_basedir() and self._entries is not None:
            return

        # Make sure the corpus is installed.
        self._basedir = get_basedir()
        self._rootdir = os.path.join(get_basedir(), self._original_rootdir)
        if not os.path.isdir(self._rootdir):
            raise IOError('%s is not installed' % self._name)

        # Read in the data file.
        datapath = os.path.join(self._rootdir, self._data_file)
        data = open(datapath).read()

        # Extract the license
        self._license = self.LICENSE_RE.search(data).group(1)

        # Extract the description
        self._description = self.DESCRIPTION_RE.search(data).group(1)

        # Remove line number markings and other comments
        data = re.sub(r'<--\s+.*?-->', '', data)
        #p\.\s+\d+\s+-->', '', data)
        #data = re.sub(r'<--\s+p\.\s+\d+\s+-->', '', data)

        # Divide the thesaurus into entries.
        entries = re.split('\n     #', data)

        self._entrylist = []
        self._entries = {}
        for entry in entries[1:]:
            (key, contents) = entry.split('--', 1)
            key = ' '.join(key.split()) # Normalize the key.
            self._entrylist.append(key)
            self._entries[key] = contents.strip()

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

    def entries(self, group=None):
        self._initialize()
        return self._entrylist

    #def open(self, entry):
    #    self._initialize()
    #    return open(os.path.join(self._rootdir, entry))

    def read(self, entry):
        return self._entries[entry]

    def readlines(self, entry):
        return self._entries[entry].splitlines()

    def tokenize(self, entry, tokenizer=WSTokenizer()):
        source = '%s/%s' % (self._name, entry)
        return tokenizer.tokenize(self.read(entry), source=source)

    def groups(self):
        return []

#################################################################
# Corpus Implementation for the PP Attatchment Corpus
#################################################################

# Not implemented yet    

#################################################################
# Corpus Implementation for Reuters
#################################################################

# Not implemented yet    

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
twenty_newsgroups = SimpleCorpus(
    '20_newsgroups', '20_newsgroups/', '.*/.*', groups,
    description_file='../20_newsgroups.readme')

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
brown = SimpleCorpus(
    'brown', 'brown/', r'c\w\d\d', groups, description_file='README')
 
###################################################
## Gutenberg
groups = [('austen', 'austen-.*'), ('bible', 'bible-.*'),
          ('blake', 'blake-.*'), ('chesterton', 'chesterton-.*'),
          ('milton', 'milton-.*'), ('shakespeare', 'shakespeare-.*'),
          ('whitman', 'whitman-.*')]
gutenberg = SimpleCorpus(
    'gutenberg', 'gutenberg/', r'.*\.txt', groups, description_file='README')

###################################################
## PP Attatchment

# Not supported yet

###################################################
## Roget

roget = RogetCorpus('roget', 'roget15a', 'roget15a.txt')

###################################################
## Words corpus (just English at this point)

words = SimpleCorpus(
    'words', 'words/', r'words') #, description_file='README')


###################################################
## Treebank (not distributed with NLTK)
from nltk.tree import TreebankTokenizer
description = '''
A collection of hand-annotated parse trees for english text.
'''.strip()

treebank = SimpleCorpus(
    'treebank', 'treebank/', r'parsed/.*\.prd', description = description,
    default_tokenizer=TreebankTokenizer())

###################################################
## Reuters corpus

# Not supported yet

#################################################################
# Testing/Example use
#################################################################

def _truncate_repr(obj, n):
    s = repr(obj)
    if len(s) < n: return s
    else: return s[:n-3] + '...'

def _test_corpus(corpus):
    print '='*70
    print corpus.name().center(70)
    print '-'*70
    print 'description() = ' + _truncate_repr(corpus.description(), 70-16)
    print 'license()     = ' + _truncate_repr(corpus.license(), 70-16)
    print 'copyright()   = ' + _truncate_repr(corpus.copyright(), 70-16)
    print 'entries()     = ' + _truncate_repr(corpus.entries(), 70-16)
    print 'groups()      = ' + _truncate_repr(corpus.groups(), 70-16)
    entry = corpus.entries()[0]
    contents = corpus.read(entry)
    print 'read(e0)      = ' + _truncate_repr(contents, 70-16)
    if len(contents) > 50000: return
    print 'tokenize(e0)  = ' + _truncate_repr(corpus.tokenize(entry), 70-16)

def demo():
    _test_corpus(twenty_newsgroups)
    _test_corpus(brown)
    _test_corpus(gutenberg)
    _test_corpus(roget)
    _test_corpus(wordlist)
    print '='*70
    
if __name__ == '__main__':
    demo()
