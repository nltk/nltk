# Natural Language Toolkit: Treeabank Corpus Reader
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

import os.path, re
from nltk.corpus import CorpusReaderI, get_basedir
from nltk.tokenreader import *

class TreebankCorpusReader(CorpusReaderI):
    """
    A corpus reader implementation for the Treebank.
    """
    # Default token readers.
    _ws_reader = WhitespaceSeparatedTokenReader(SUBTOKENS='WORDS')
    _tb_reader = TreebankFileTokenReader(SUBTOKENS='WORDS')
    _tag_reader = TreebankTaggedTokenReader(SUBTOKENS='WORDS')
    
    def __init__(self, name, rootdir, treebank_2=False,
                 description_file=None, license_file=None,
                 copyright_file=None):
        self._name = name
        self._original_rootdir = rootdir
        self._description_file = description_file
        self._license_file = license_file
        self._copyright_file = copyright_file

        if treebank_2:
            # 3 groups:
            self._groups = ('tagged', 'parsed', 'merged')
            self._group_directory = { 
                'tagged':'tagged/pos', 'parsed':'parsed/prd',
                'merged':'parsed/mrg' }
            self._group_mask = { 'tagged':r'.*\.pos',
                'parsed':r'.*\.prd', 'merged':'.*\.mrg' }
        else:
            # 4 groups:
            self._groups = ('raw', 'tagged', 'parsed', 'merged')
            self._group_directory = dict([(g, g) for g in self._groups])
            self._group_mask = dict([(g, r'.*') for g in self._groups])

        # Are the merged items "virtual" (i.e., constructed on the
        # fly from the parsed & tagged items)?  This is true iff the
        # treebank corpus doesn't contain a "merged" subdirectory.
        self._virtual_merged = 0
        
        # Postpone actual initialization until the corpus is accessed;
        # this gives the user a chance to call set_basedir(), and
        # prevents "import nltk.corpus" from raising an exception.
        # We'll also want to re-initialize the corpus if basedir
        # ever changes.
        self._basedir = None
        self._description = None
        self._license = None
        self._copyright = None
        self._items = None
        self._group_items = None
        self._initialized = False

    #////////////////////////////////////////////////////////////
    #// Initialization
    #////////////////////////////////////////////////////////////
    def _initialize(self):
        "Make sure that we're initialized."
        # If we're already initialized, then do nothing.
        if self._initialized: return

        # Make sure the corpus is installed.
        basedir = get_basedir()
        if not os.path.isabs(self._original_rootdir):
            if not os.path.isdir(os.path.join(basedir, self._original_rootdir)):
                raise IOError('%s is not installed' % self._name)
            self._basedir = basedir
            self._rootdir = os.path.join(basedir, self._original_rootdir)
        else:
            if not os.path.isdir(self._original_rootdir):
                raise IOError('%s is not installed' % self._name)
            self._basedir = '' # empty
            self._rootdir = self._original_rootdir

        # Check the directory for 'merged', and change it to
        # 'combined' if appropriate.
        if 'merged' in self._groups:
            if os.path.isdir(os.path.join(self._rootdir, 'combined')):
                self._group_directory['merged'] = 'combined'

        # Get the list of items in each group.
        self._group_items = {}
        for group in self._groups:
            self._find_items(group)
        if not self._group_items.has_key('merged'):
            self._virtual_merged = 1
            self._find_virtual_merged_items()

        # Get the overall list of items
        self._items = []
        for items in self._group_items.values():
            self._items += items

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

        self._initialized = True

    def _find_items(self, group):
        directory = self._group_directory.get(group)
        mask = self._group_mask.get(group)
        if directory:
            self._group_items[group] = []
            path = os.path.join(self._rootdir, directory)
            for dir_path, dir_names, file_names in os.walk(path):
                for file_name in file_names:
                    if re.match(mask + r'$', file_name) and \
                       not file_name.startswith('readme'):
                        self._group_items[group].append(
                            os.path.join(dir_path, file_name))

    def _find_virtual_merged_items(self):
        # Check to make sure we have both the .tagged and the .parsed files.
        self._group_items['merged'] = merged = []
        is_tagged = {}
        for item in self._group_items.get('tagged', []):
            basename = os.path.basename(item).split('.')[0]
            is_tagged[basename] = 1
        for item in self._group_items.get('parsed', []):
            basename = os.path.basename(item).split('.')[0]
            if is_tagged.get(basename):
                merged.append(os.path.join('merged', '%s.mrg' % basename))

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

    def rootdir(self):
        """
        @return: The path to the root directory for this corpus.
        @rtype: C{string}
        """
        self._initialize()
        return self._rootdir

    #////////////////////////////////////////////////////////////
    #// Data access (items)
    #////////////////////////////////////////////////////////////
    def items(self, group=None):
        self._initialize()
        if group is None: return self._items
        else: return tuple(self._group_items.get(group)) or ()

    def read(self, item, *reader_args, **reader_kwargs):
        source = '%s/%s' % (self._name, item)
        text = self.raw_read(item)
        reader = self._token_reader(item)
        return reader.read_token(text, source=source,
                                 *reader_args, **reader_kwargs)

    def xread(self, item, *reader_args, **reader_kwargs):
        # Default: no iterators.
        return self.read(item, *reader_args, **reader_kwargs)

    def path(self, item):
        self._initialize()
        if self._virtual_merged and item.startswith('merged'):
            estr = 'The given item is virtual; it has no path'
            raise NotImplementedError, estr
        else:
            return os.path.join(self._rootdir, item)

    def open(self, item):
        return open(self.path(item))

    def raw_read(self, item):
        if self._virtual_merged and item.startswith('merged'):
            basename = os.path.basename(item).split('.')[0]
            tagged_item = os.path.join('tagged', '%s.pos' % basename)
            parsed_item = os.path.join('parsed', '%s.prd' % basename)
            tagged = self.read(tagged_item)
            parsed = self.read(parsed_item)
            return self.merge(tagged, parsed)
        else:
            return self.open(item).read()

    def _token_reader(self, item):
        self._initialize()
        if item in self._group_items['merged']:
            return self._tb_reader
        elif item in self._group_items['tagged']:
            return self._tag_reader
        elif item in self._group_items['parsed']:
            return self._tb_reader
        elif item in self._group_items['raw']:
            return self._ws_reader
        else:
            raise ValueError, 'Unknown item %r' % (item,)

    #////////////////////////////////////////////////////////////
    #// Parsed/Tagged Merging
    #////////////////////////////////////////////////////////////
    def merge(self, tagged, parsed):
        """
        Create a merged treebank file (containing both parse and
        part-of-speech tagging information), given the parsed contents
        and the part-of-speech tagged contents for that file.

        This merge procedure is somewhat robust.  In particular:
          - It handles brace conversions (eg C{'('} -> C{'-LRB-'}).  It
            also accepts the (incorrect?) variants C{'*LRB*'} etc., and
            automatically convers the to the standard C{'-LRB-'} forms.
          - It complains but does not fail if the parse file drops
            the last word or the last quote mark.
          - It handles traces & other null elements in the parse.
          - It handles extra elements in the parse that are not present
            in the tagged text.  (E.g. in C{'(WHP-1 0)'}.

        This is enough robustness to handle wsj_0001 through wsj_0099;
        It hasn't yet been tested on the rest of the treebank.

        @param tagged: The part-of-speech tagged contents of the file
            to merge.
        @type tagged: C{string}
        @param parsed: The parse contents of the file to merge.
        @type parsed: C{string}
        @return: The merged contents of the treebank file.
        @rtype: C{string}

        @todo: Increase the robustness of this method.
        """
        # Clean up the tagged contents of the file.
        tagged = tagged.replace('[', ' ').replace(']', ' ')
        tagged = re.sub('={10,}', '', tagged) # >=10 equals signs
        tagged = tagged.replace('{', '-LCB-')
        tagged = tagged.replace('}', '-RCB-')
        tagged = tagged.replace('(', '-LRB-')
        tagged = tagged.replace(')', '-RRB-')

        # Divide the tagged contents into a list of words.  Reverse
        # it, so we can use pop() to remove one word at a time.
        self._tagged_words = tagged.split()

        # Use re.sub to replace words with tagged words.  The regexp
        # we're using will only match words, not part-of-speech tags.
        # Use a helper method (_merge_tag) to find the replacement for
        # each match.
        try:
            self._mismatches = 0
            self._first_mismatch = None
            self._tagged_index = 0
            merged = re.sub(r'\s([^\s\(\)]+)', self._merge_tag, parsed)
        except IndexError:
            raise ValueError('Merge failed: more words in the parsed '+
                             'contents than in the tagged contents')

        # Check that we used all tagged words.
        if self._tagged_index != len(self._tagged_words):
            if (self._tagged_index == (len(self._tagged_words)-1) and
                self._tagged_words[-1] == "''/''"):
                print 'Warning: dropped close quote'
            elif self._tagged_index == (len(self._tagged_words)-1):
                print ('Warning: dropped last word (%r)' %
                       self._tagged_words[-1])
            else:
                print self._tagged_index, len(self._tagged_words)
                print self._tagged_words[-5:]
                raise ValueError('Merge failed: more words in the tagged '+
                                 'contents than in the parsed contents')
        
        return merged

    def _merge_tag(self, match):
        """
        A helper function for L{merge}, that is used as the C{repl}
        argument for a regular expression substitution.  Given the
        regexp match for a word in the treebank, return the
        corresponding tagged word.
        """
        # Get the next parsed word
        parseword = match.group(1)

        # Annoying clean-up
        if parseword[:1] == '*' and parseword[-1:] == '*':
            if re.match(r'\*[LR][CRS]B\*', parseword):
                parseword = '-' + parseword[1:-1] + '-'

        # Get the next tagged word.
        taggedword = self._tagged_words[self._tagged_index]
        split = taggedword.rfind('/')
        if split == -1:
            raise ValueError('Merge failed: untagged word %s' % taggedword)
        word = taggedword[:split].replace('\\', '')
        tag = taggedword[split+1:]

        # If they don't match, then try returning the parse word, and
        # continuing.
        if word != parseword:
            if not parseword.startswith('*'):
                self._mismatches += 1
                if self._mismatches == 1:
                    self._first_mismatch = '%r vs. %r' % (word, parseword)
                if self._mismatches > 5:
                    print self._tagged_words[self._tagged_index:
                                             self._tagged_index+5]
                    raise ValueError("Merge failed: tagged & parsed files "+
                                     "don't match:\n  "+ self._first_mismatch)
            return word
            
        # If they match, then return the tagged word, expressed as a
        # tree constituant.
        self._mismatches = 0
        self._tagged_index += 1
        return ' (%s %s)' % (tag, word)
        
    #////////////////////////////////////////////////////////////
    #// Structure access (groups)
    #////////////////////////////////////////////////////////////

    def groups(self):
        return self._groups


