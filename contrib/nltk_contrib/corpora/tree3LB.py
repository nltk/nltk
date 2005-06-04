# Natural Language Toolkit: Tree Corpus Reader
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Carlos Rodriguez hacking  original code by Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
"""
CATALAN AND SPANISH TREEBANKS:

>>> from nltk_contrib.corpora.tree3LB import *

>>> LB
<Corpus: 3LB (contains 489 items; 2 groups)>

>>> LB.groups()
('cas', 'cat')

>>> LB.items('cas')[:18]
('cas//a1-0.tbf', 'cas//a1-1.tbf', 'cas//a1-2.tbf', 'cas//a1-3.tbf', 'cas//a1-4.tbf',
'cas//a1-5.tbf', 'cas//a1-6.tbf', 'cas//a1-7.tbf', 'cas//a2-0.tbf', 'cas//a12-0.tbf', 'cas//a12-1.tbf',
'cas//a12-2.tbf', 'cas//a12-3.tbf', 'cas//a12-4.tbf', 'cas//a14-0.tbf', 'cas//a14-1.tbf', 'cas//a14-2.tbf',
'cas//a14-3.tbf')

>>> LB.read('cas//a12-1.tbf')[8]
<TREE=(S.co: (S: (sn-SUJ: (espec.fs: <La/da0fs0>) (grup.nom.fs: <rata/ncfs000>)) (gv: <es/vsip3s0>)
(sn-ATR: (espec.ms: <un/di0ms0>) (grup.nom.ms: <animal/ncms000> (s.a.ms: <clasista/aq0cs0>)))
(sp-CC: (prep: <por/sps00>) (sn: (grup.nom.fs: <naturaleza/ncfs000>)))) <,/Fc> (S: (sp-CC: (prep: <hasta/sps00>)
(sp: (prep: <en/sps00>) (sn: (grup.nom.s: <eso/pd0ns000>)))) <\\*-0-\\*/sn.e-SUJ> (gv: <es/vsip3s0>)
(sa-ATR: <asquerosa/aq0fs0>)) <./Fp>), WORDS=[<La/da0fs0>, <rata/ncfs000>, <es/vsip3s0>, <un/di0ms0>,
<animal/ncms000>, <clasista/aq0cs0>, <por/sps00>, <naturaleza/ncfs000>, <,/Fc>, <hasta/sps00>,
<en/sps00>, <eso/pd0ns000>, <\\*-0-\\*/sn.e-SUJ>, <es/vsip3s0>, <asquerosa/aq0fs0>, <./Fp>]>

>>> LB.read_lemma('cas//a12-1.tbf')[8]
<TREE=(S.co: (S: (sn-SUJ: (espec.fs: <LEMMA='el', POS='da0fs0', TEXT='La'>) (grup.nom.fs: <LEMMA='rata',
POS='ncfs000', TEXT='rata'>)) (gv: <LEMMA='ser', POS='vsip3s0', TEXT='es'>) (sn-ATR: (espec.ms: <LEMMA='uno',
POS='di0ms0', TEXT='un'>) (grup.nom.ms: <LEMMA='animal', POS='ncms000', TEXT='animal'> (s.a.ms: <LEMMA='clasista',
POS='aq0cs0', TEXT='clasista'>))) ...."""
import os.path, re
from nltk.corpus import CorpusReaderI, get_basedir
#from nltk.tokenreader import *
from nltk_contrib.corpora.treebank3LB import *
#from nltk.tokenizer.treebank3LB import TreebankTokenReader3LB

class Treebank3LBCorpusReader(CorpusReaderI):
    """
    A corpus reader implementation for the 3LB Treebank.
    """
    # Default token readers.
    _3LB_reader = TreebankTokenReader3LB(preterminal_tags=True,
                                          SUBTOKENS='WORDS', TAG='POS',LEMMA='LEMMA')
    
    def __init__(self, name, rootdir, description_file=None,
                 license_file=None, copyright_file=None):
        self._name = name
        self._original_rootdir = rootdir
        self._description_file = description_file
        self._license_file = license_file
        self._copyright_file = copyright_file
        self._groups = ('cat','cas')
        self._group_directory = dict([(g, g) for g in self._groups])
        self._group_mask = dict([(g, r'.*') for g in self._groups])
     
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
        if self._basedir == get_basedir(): return

        # Make sure the corpus is installed.
        basedir = get_basedir()
        if not os.path.isdir(os.path.join(basedir, self._original_rootdir)):
            raise IOError('%s is not installed' % self._name)
        self._basedir = basedir
        self._rootdir = os.path.join(basedir, self._original_rootdir)
        # Get the list of items in each group.
        self._group_items = {}
        for group in self._groups:
            #print "group",group
            self._group_items[group] = self._find_items(self._rootdir,group)
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
    def groups(self):
        self._initialize()
        return tuple(self._group_items.keys())
    def _find_items(self,rootdir,groupdir, prefix='//'):
        path = rootdir+groupdir
        filelist = []
        for name in os.listdir(path):
            #print "name",name
            filepath = os.path.join(path, name)
            if os.path.isfile(filepath):
                filelist.append('%s%s%s' % (groupdir,prefix, name))
            elif os.path.isdir(filepath):
                filelist += self._find_files(filepath,
                                             '%s%s%s/' % (groupdir,prefix, name))
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
        return reader.read_tokens(text, source=source,add_lemmas=False
                                 *reader_args, **reader_kwargs)
    def read_lemma(self, item, *reader_args, **reader_kwargs):
        source = '%s/%s' % (self._name, item)
        text = self.raw_read(item)
        reader = self._token_reader(item)
        return reader.read_tokens(text, source=source,
                                 *reader_args, **reader_kwargs)

    def xread(self, item, *reader_args, **reader_kwargs):
        # Default: no iterators.
        return self.read(item, *reader_args, **reader_kwargs)

    def path(self, item):
        self._initialize()
##        if self._virtual_merged and item.startswith('combined'):
##            estr = 'The given item is virtual; it has no path'
##            raise NotImplementedError, estr
##        else:
        return os.path.join(self._rootdir, item)

    def open(self, item):
        return open(self.path(item))

    def raw_read(self, item):
##        if self._virtual_merged and item.startswith('combined'):
##            basename = os.path.basename(item).split('.')[0]
##            tagged_item = os.path.join('tagged', '%s.pos' % basename)
##            parsed_item = os.path.join('parsed', '%s.prd' % basename)
##            tagged = self.read(tagged_item)
##            parsed = self.read(parsed_item)
##            return self.merge(tagged, parsed)
##        else:
        return self.open(item).read()

    def _token_reader(self, item):
        self._initialize()
        if item in self._group_items['cat']:
            return self._3LB_reader
        elif item in self._group_items['cas']:
            return self._3LB_reader


LB = Treebank3LBCorpusReader('3LB', "3LB/",description_file="LEEME",license_file="LICENCIA")
