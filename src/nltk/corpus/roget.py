from nltk.token import *
from nltk.corpus import CorpusReaderI, get_basedir
from nltk.tokenreader import *
import os.path, re

#################################################################
# Corpus Implementation for Roget's Thesaurus
#################################################################

class RogetCorpusReader(CorpusReaderI):
    """
    A C{CorpusReader} implementation for Roget's Thesaurus.  Each
    corpus item corresponds to a single thesaurus item.  These
    items are all read from a single thesaurus file.
    """
    def __init__(self, name, rootdir, data_file):
        self._name = name
        self._original_rootdir = rootdir
        self._data_file = data_file
        self._token_reader=WhitespaceSeparatedTokenReader(SUBTOKENS='WORDS')
 
        # Postpone actual initialization until the corpus is accessed;
        # this gives the user a chance to call set_basedir(), and
        # prevents "import nltk.corpus" from raising an exception.
        # We'll also want to re-initialize the corpus if basedir
        # ever changes.
        self._basedir = None
        self._items = None
        self._rootdir = None
        self._groups = None
        self._description = None
        self._licence = None
        self._copyright = None

    #////////////////////////////////////////////////////////////
    #// Initialization
    #////////////////////////////////////////////////////////////
    LICENSE_RE = re.compile(r'\*+START\*+THE SMALL PRINT[^\n]' +
                            r'(.*?)' +
                            r'\*+END\*+THE SMALL PRINT', re.DOTALL)
    
    DESCRIPTION_RE = re.compile('(' + r'\*'*60 + r'.*?' +
                                r'='*60+'\s+-->)', re.DOTALL)

    ITEM_RE = re.compile(r'^     #(\w+)\.\s+(' + #r'(([^-]*)\s--' +
                          r'.*?\n)',
                          re.DOTALL | re.MULTILINE)
    
    def _initialize(self):
        # If we're already initialized, then do nothing.
        if self._basedir == get_basedir(): return

        # Make sure the corpus is installed.
        basedir = get_basedir()
        if not os.path.isdir(os.path.join(basedir, self._original_rootdir)):
            raise IOError('%s is not installed' % self._name)
        self._basedir = basedir
        self._rootdir = os.path.join(basedir, self._original_rootdir)

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

        # Divide the thesaurus into items.
        items = re.split('\n     #', data)

        self._itemlist = []
        self._items = {}
        for item in items[1:]:
            (key, contents) = item.split('--', 1)
            key = ' '.join(key.split()) # Normalize the key.
            self._itemlist.append(key)
            self._items[key] = contents.strip()
        self._itemlist = tuple(self._itemlist)

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
        return self._itemlist

    def read(self, item):
        source = '%s/%s' % (self._name, item)
        text = self.raw_read(item)
        return self._token_reader.read_token(text, source=source)

    def xread(self, item):
        # Default: no iterators.
        return self.read(item)

    def path(self, item):
        "Not implemented by the Roget corpus."
        raise NotImplementedError, 'roget does not implement path()'
    
    def open(self, item):
        "Not implemented by the Roget corpus."
        raise NotImplementedError, 'roget does not implement open()'

    def raw_read(self, item):
        self._initialize()
        return self._items[item]

    #////////////////////////////////////////////////////////////
    #// Structure access (groups)
    #////////////////////////////////////////////////////////////

    def groups(self):
        return []

