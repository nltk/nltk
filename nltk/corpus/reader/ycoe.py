# -*- coding: iso-8859-1 -*-

# Natural Language Toolkit: York-Toronto-Helsinki Parsed Corpus of Old English Prose (YCOE)
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Selina Dennis <selina@tranzfusion.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for the York-Toronto-Helsinki Parsed Corpus of Old
English Prose (YCOE), a 1.5 million word syntactically-annotated
corpus of Old English prose texts. The corpus is distributed by the
Oxford Text Archive: http://www.ota.ahds.ac.uk/ It is not included
with NLTK.

The YCOE corpus is divided into 100 files, each representing
an Old English prose text. Tags used within each text complies
to the YCOE standard: http://www-users.york.ac.uk/~lang22/YCOE/YcoeHome.htm
"""

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk import tokenize, tree
from nltk.corpus.reader.bracket_parse import BracketParseCorpusReader
from nltk.corpus.reader.tagged import TaggedCorpusReader
from string import split
import os, re
from nltk.utilities import deprecated

class YCOECorpusReader(CorpusReader):
    """
    Corpus reader for the York-Toronto-Helsinki Parsed Corpus of Old
    English Prose (YCOE), a 1.5 million word syntactically-annotated
    corpus of Old English prose texts.

    
    """
    def __init__(self, root):
        self._root = root
        self._psd_reader = YCOEParseCorpusReader(
            os.path.join(root, 'psd'), '.*', '.psd')
        self._pos_reader = YCOETaggedCorpusReader(
            os.path.join(root, 'pos'), '.*', '.pos')

        # Make sure we have a consistent set of items:
        if set(self._psd_reader.items) != set(self._pos_reader.items):
            raise ValueError('Items in "psd" and "pos" '
                             'subdirectories do not match.')
        self.items = self._psd_reader.items

    # Delegate to one of our two sub-readers:
    def words(self, items=None):
        return self._pos_reader.words(items)
    def sents(self, items=None):
        return self._pos_reader.sents(items)
    def paras(self, items=None):
        return self._pos_reader.paras(items)
    def tagged_words(self, items=None):
        return self._pos_reader.tagged_words(items)
    def tagged_sents(self, items=None):
        return self._pos_reader.tagged_sents(items)
    def tagged_paras(self, items=None):
        return self._pos_reader.tagged_paras(items)
    def parsed_sents(self, items=None):
        return self._psd_reader.parsed_sents(items)

    #{ Deprecated since 0.8
    @deprecated("Use .raw() or .words() or .tagged_words() or "
                ".parsed_sents() instead.")
    def read(self, items=None, format='parsed'):
        if format == 'parsed': return self.parsed_sents(items)
        if format == 'raw': return self.raw(items)
        if format == 'tokenized': return self.words(items)
        if format == 'tagged': return self.tagged_words(items)
        if format == 'chunked': raise ValueError('no longer supported')
        raise ValueError('bad format %r' % format)
    @deprecated("Use .parsed_sents() instead.")
    def parsed(self, items=None):
        return self.parsed_sents(items)
    @deprecated("Use .words() instead.")
    def tokenized(self, items=None):
        return self.words(items)
    @deprecated("Use .tagged_words() instead.")
    def tagged(self, items=None):
        return self.tagged_words(items)
    @deprecated("Operation no longer supported.")
    def chunked(self, items=None):
        raise ValueError('format "chunked" no longer supported')
    #}

class YCOEParseCorpusReader(BracketParseCorpusReader):
    """Specialized version of the standard bracket parse corpus reader
    that strips out (CODE ...) and (ID ...) nodes."""
    def _parse(self, t):
        t = re.sub(r'(?u)\((CODE|ID)[^\)]*\)', '', t)
        if re.match(r'\s*\(\s*\)\s*$', t): return None
        return BracketParseCorpusReader._parse(self, t)

class YCOETaggedCorpusReader(TaggedCorpusReader):
    def __init__(self, root, items, extension):
        gaps_re = r'(?u)\(?<=/\.)\s+|\s*\S*_CODE\s*|\s*\S*_ID\s*'
        sent_tokenizer = RegexpTokenizer(gaps_re, gaps=True)
        TaggedCorpusReader.__init__(self, root, items, extension, sep='_',
                                    sent_tokenizer=sent_tokenizer)
        
#: A list of all documents and their titles in ycoe.
documents = {
    'coadrian.o34': 'Adrian and Ritheus',
    'coaelhom.o3': '�lfric, Supplemental Homilies',
    'coaelive.o3': '�lfric\'s Lives of Saints',
    'coalcuin': 'Alcuin De virtutibus et vitiis',
    'coalex.o23': 'Alexander\'s Letter to Aristotle',
    'coapollo.o3': 'Apollonius of Tyre',
    'coaugust': 'Augustine',
    'cobede.o2': 'Bede\'s History of the English Church',
    'cobenrul.o3': 'Benedictine Rule',
    'coblick.o23': 'Blickling Homilies',
    'coboeth.o2': 'Boethius\' Consolation of Philosophy',
    'cobyrhtf.o3': 'Byrhtferth\'s Manual',
    'cocanedgD': 'Canons of Edgar (D)',
    'cocanedgX': 'Canons of Edgar (X)',
    'cocathom1.o3': '�lfric\'s Catholic Homilies I',
    'cocathom2.o3': '�lfric\'s Catholic Homilies II',
    'cochad.o24': 'Saint Chad',
    'cochdrul': 'Chrodegang of Metz, Rule',
    'cochristoph': 'Saint Christopher',
    'cochronA.o23': 'Anglo-Saxon Chronicle A',
    'cochronC': 'Anglo-Saxon Chronicle C',
    'cochronD': 'Anglo-Saxon Chronicle D',
    'cochronE.o34': 'Anglo-Saxon Chronicle E',
    'cocura.o2': 'Cura Pastoralis',
    'cocuraC': 'Cura Pastoralis (Cotton)',
    'codicts.o34': 'Dicts of Cato',
    'codocu1.o1': 'Documents 1 (O1)',
    'codocu2.o12': 'Documents 2 (O1/O2)',
    'codocu2.o2': 'Documents 2 (O2)',
    'codocu3.o23': 'Documents 3 (O2/O3)',
    'codocu3.o3': 'Documents 3 (O3)',
    'codocu4.o24': 'Documents 4 (O2/O4)',
    'coeluc1': 'Honorius of Autun, Elucidarium 1',
    'coeluc2': 'Honorius of Autun, Elucidarium 1',
    'coepigen.o3': '�lfric\'s Epilogue to Genesis',
    'coeuphr': 'Saint Euphrosyne',
    'coeust': 'Saint Eustace and his companions',
    'coexodusP': 'Exodus (P)',
    'cogenesiC': 'Genesis (C)',
    'cogregdC.o24': 'Gregory\'s Dialogues (C)',
    'cogregdH.o23': 'Gregory\'s Dialogues (H)',
    'coherbar': 'Pseudo-Apuleius, Herbarium',
    'coinspolD.o34': 'Wulfstan\'s Institute of Polity (D)',
    'coinspolX': 'Wulfstan\'s Institute of Polity (X)',
    'cojames': 'Saint James',
    'colacnu.o23': 'Lacnunga',
    'colaece.o2': 'Leechdoms',
    'colaw1cn.o3': 'Laws, Cnut I',
    'colaw2cn.o3': 'Laws, Cnut II',
    'colaw5atr.o3': 'Laws, �thelred V',
    'colaw6atr.o3': 'Laws, �thelred VI',
    'colawaf.o2': 'Laws, Alfred',
    'colawafint.o2': 'Alfred\'s Introduction to Laws',
    'colawger.o34': 'Laws, Gerefa',
    'colawine.ox2': 'Laws, Ine',
    'colawnorthu.o3': 'Northumbra Preosta Lagu',
    'colawwllad.o4': 'Laws, William I, Lad',
    'coleofri.o4': 'Leofric',
    'colsigef.o3': '�lfric\'s Letter to Sigefyrth',
    'colsigewB': '�lfric\'s Letter to Sigeweard (B)',
    'colsigewZ.o34': '�lfric\'s Letter to Sigeweard (Z)',
    'colwgeat': '�lfric\'s Letter to Wulfgeat',
    'colwsigeT': '�lfric\'s Letter to Wulfsige (T)',
    'colwsigeXa.o34': '�lfric\'s Letter to Wulfsige (Xa)',
    'colwstan1.o3': '�lfric\'s Letter to Wulfstan I',
    'colwstan2.o3': '�lfric\'s Letter to Wulfstan II',
    'comargaC.o34': 'Saint Margaret (C)',
    'comargaT': 'Saint Margaret (T)',
    'comart1': 'Martyrology, I',
    'comart2': 'Martyrology, II',
    'comart3.o23': 'Martyrology, III',
    'comarvel.o23': 'Marvels of the East',
    'comary': 'Mary of Egypt',
    'coneot': 'Saint Neot',
    'conicodA': 'Gospel of Nicodemus (A)',
    'conicodC': 'Gospel of Nicodemus (C)',
    'conicodD': 'Gospel of Nicodemus (D)',
    'conicodE': 'Gospel of Nicodemus (E)',
    'coorosiu.o2': 'Orosius',
    'cootest.o3': 'Heptateuch',
    'coprefcath1.o3': '�lfric\'s Preface to Catholic Homilies I',
    'coprefcath2.o3': '�lfric\'s Preface to Catholic Homilies II',
    'coprefcura.o2': 'Preface to the Cura Pastoralis',
    'coprefgen.o3': '�lfric\'s Preface to Genesis',
    'copreflives.o3': '�lfric\'s Preface to Lives of Saints',
    'coprefsolilo': 'Preface to Augustine\'s Soliloquies',
    'coquadru.o23': 'Pseudo-Apuleius, Medicina de quadrupedibus',
    'corood': 'History of the Holy Rood-Tree',
    'cosevensl': 'Seven Sleepers',
    'cosolilo': 'St. Augustine\'s Soliloquies',
    'cosolsat1.o4': 'Solomon and Saturn I',
    'cosolsat2': 'Solomon and Saturn II',
    'cotempo.o3': '�lfric\'s De Temporibus Anni',
    'coverhom': 'Vercelli Homilies',
    'coverhomE': 'Vercelli Homilies (E)',
    'coverhomL': 'Vercelli Homilies (L)',
    'covinceB': 'Saint Vincent (Bodley 343)',
    'covinsal': 'Vindicta Salvatoris',
    'cowsgosp.o3': 'West-Saxon Gospels',
    'cowulf.o34': 'Wulfstan\'s Homilies'
    }

