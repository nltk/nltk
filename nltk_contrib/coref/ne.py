# Natural Language Toolkit (NLTK) Coreference Named Entity Components
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import os
import optparse

import nltk

from nltk.data import load
from nltk.util import LazyMap, LazyZip, LazyConcatenation, LazyEnumerate

from nltk.chunk.util import ChunkScore

from nltk.corpus import names, gazetteers
from nltk.corpus.util import LazyCorpusLoader
from nltk.corpus.reader.conll import ConllCorpusReader

from nltk.tag import TaggerI, ClassifierBasedTagger
from nltk.classify.maxent import MaxentClassifier, ClassifierI

from nltk_contrib.coref import *
from nltk_contrib.coref.tag import TreebankTaggerCorpusReader
from nltk_contrib.coref.train import train_model
from nltk_contrib.coref.chunk import ChunkTagger, \
    ChunkTaggerFeatureDetector
from nltk_contrib.coref.muc import MUCCorpusReader

MUC6_NER = \
    'nltk:taggers/maxent_muc6_ner/muc6.ner.pickle'


TREEBANK_CLOSED_CATS = set(['CC', 'DT', 'MD', 'POS', 'PP$', 'RP', 'TO', 'WDT',
                            'WP$', 'EX', 'IN', 'PDT', 'PRP', 'WP', 'WRB'])

NUMBERS = ['one', 'two', 'three', 'four', 'five', 'six', 'seven',
           'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
           'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
           'nineteen', 'twenty', 'thirty', 'fourty', 'fifty',
           'sixty', 'seventy', 'eighty', 'ninety', 'hundred',
           'thousand', 'million', 'billion', 'trillion']

ORDINALS = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 
            'seventh', 'eighth', 'ninth', 'tenth', 'eleventh', 'twelfth']

DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 
        'friday', 'saturday', 'sunday']

MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july',
          'august', 'september', 'october', 'november', 'december',
          'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept',
          'oct', 'nov', 'dec']

                     
NAMES = set([name.lower() for filename in ('male.txt', 'female.txt') for name
             in names.words(filename)])

US_CITIES = set([city.lower() for city in gazetteers.words('uscities.txt')])

# [XX] contains some non-ascii chars
COUNTRIES = set([country.lower() for filename in ('isocountries.txt','countries.txt')
                 for country in gazetteers.words(filename)])

# States in North America
NA_STATES = set([state.lower() for filename in
                 ('usstates.txt','mexstates.txt','caprovinces.txt') for state in
                 gazetteers.words(filename)])
                     
US_STATE_ABBREVIATIONS = set([state.lower() for state in gazetteers.words('usstateabbrev.txt')])

NATIONALITIES = set([nat.lower() for nat in gazetteers.words('nationalities.txt')])
                     
PERSON_PREFIXES = ['mr', 'mrs', 'ms', 'miss', 'dr', 'rev', 'judge',
                   'justice', 'honorable', 'hon', 'rep', 'sen', 'sec',
                   'minister', 'chairman', 'succeeding', 'says', 'president']

PERSON_SUFFIXES = ['sr', 'jr', 'phd', 'md']

ORG_SUFFIXES = ['ltd', 'inc', 'co', 'corp', 'plc', 'llc', 'llp', 'gmbh',
                'corporation', 'associates', 'partners', 'committee',
                'institute', 'commission', 'university', 'college',
                'airlines', 'magazine']

CURRENCY_UNITS = ['dollar', 'cent', 'pound', 'euro']

ENGLISH_PRONOUNS = ['i', 'you', 'he', 'she', 'it', 'we', 'you', 'they']

NUMERIC = r'(\d{1,3}(\,\d{3})*|\d+)(\.\d+)?'
RE_PUNCT = re.compile(r'[-!"#$%&\'\(\)\*\+,\./:;<=>^\?@\[\]\\\_`{\|}~]')
RE_NUMERIC = re.compile(NUMERIC)
RE_NUMBER = re.compile(r'(%s)(\s+(%s))*' % ('|'.join(NUMBERS), '|'.join(NUMBERS)), re.I)
RE_QUOTE = re.compile(r'[\'"`]', re.I)
RE_ROMAN = re.compile(r'M?M?M?(CM|CD|D?C?C?C?)(XC|XL|L?X?X?X?)(IX|IV|V?I?I?I?)', re.I)
RE_INITIAL = re.compile(r'[A-Z]\.', re.I)
RE_TLA = re.compile(r'([A-Z0-9][\.\-]?){2,}', re.I)
RE_ALPHA = re.compile(r'[A-Za-z]+', re.I)
RE_DATE = re.compile(r'\d+\/\d+(\/\d+)?')
RE_CURRENCY = re.compile(r'\$\s*(%s)?' % NUMERIC)
RE_PERCENT = re.compile(r'%s\s*' % NUMERIC + '%')
RE_YEAR = re.compile(r'(\d{4}s?|\d{2}s)')
RE_TIME = re.compile(r'\d{1,2}(\:\d{2})?(\s*[aApP]\.?[mM]\.?)?', re.I)
RE_ORDINAL = re.compile(r'%s' % ('|'.join(ORDINALS)))
RE_DAY = re.compile(r'%s' % ('|'.join(DAYS)))
RE_MONTH = re.compile(r'%s' % ('|'.join(MONTHS)))
RE_PERSON_PREFIX = re.compile(r'%s' % ('|'.join(PERSON_PREFIXES)))
RE_PERSON_SUFFIX = re.compile(r'%s' % ('|'.join(PERSON_SUFFIXES)))
RE_ORG_SUFFIX = re.compile(r'%s' % ('|'.join(ORG_SUFFIXES)))

class NERChunkTaggerFeatureDetector(dict):
    def __init__(self, tokens, index=0, history=None, **kwargs):
        dict.__init__(self)
        window = kwargs.get('window', 2)        
        spelling, pos = tokens[index][:2]

        self['spelling'] = spelling
        self['word'] = spelling.lower()
        self['pos'] = pos
        self['isupper'] = spelling.isupper()
        self['islower'] = spelling.islower()
        self['istitle'] = spelling.istitle()
        self['isalnum'] = spelling.isalnum() 
        for i in range(1, 4):
            self['prefix_%d' % i] = spelling[:i]
            self['suffix_%d' % i] = spelling[-i:]
        self['isclosedcat'] = pos in TREEBANK_CLOSED_CATS        
        
        self['ispunct'] = bool(RE_PUNCT.match(spelling))
        self['ispercent'] = bool(RE_PERCENT.match(spelling))
        self['isnumber'] = bool(RE_PERCENT.match(spelling))
        self['isnumeric'] = bool(RE_NUMERIC.match(spelling))
        self['isquote'] = bool(RE_QUOTE.match(spelling))   
        self['isroman'] = bool(RE_ROMAN.match(spelling))
        self['isinitial'] = bool(RE_INITIAL.match(spelling))
        self['istla'] = bool(RE_TLA.match(spelling))
        self['isdate'] = bool(RE_DATE.match(spelling))
        self['iscurrency'] = bool(RE_CURRENCY.match(spelling))
        self['isyear'] = bool(RE_YEAR.match(spelling))
        self['istime'] = bool(RE_TIME.match(spelling))
        self['isordinal'] = bool(RE_ORDINAL.match(spelling))
        self['isday'] = bool(RE_DAY.match(spelling)) 
        self['ismonth'] = bool(RE_MONTH.match(spelling))        
        self['isname'] = spelling.lower() in NAMES
        self['iscity'] = spelling.lower() in US_CITIES
        self['isstateabbrev'] = spelling.lower() in US_STATE_ABBREVIATIONS
        self['isnastate'] = spelling.lower() in NA_STATES     
        self['isnationality'] = spelling.lower() in NATIONALITIES       
        self['personprefix'] = bool(RE_PERSON_PREFIX.match(spelling))
        self['personsuffix'] = bool(RE_PERSON_PREFIX.match(spelling))                                                                       
        self['orgsuffix'] = bool(RE_ORG_SUFFIX.match(spelling))

        if window > 0 and index > 0:
            prev_feats = \
                self.__class__(tokens, index - 1, history, window=window - 1)
            for key, val in prev_feats.items():
                if not key.startswith('next_'):
                    self['prev_%s' % key] = val

        if window > 0 and index < len(tokens) - 1:
            next_feats = self.__class__(tokens, index + 1, window=window - 1)        
            for key, val in next_feats.items():
                if not key.startswith('prev_'):
                    self['next_%s' % key] = val        

        if 'prev_pos' in self:
            self['prev_pos_pair'] = '%s/%s' % \
                (self.get('prev_pos'), self.get('pos'))

        if history and index > 0:
            self['prev_tag'] = history[index - 1]     

def maxent_classifier_builder(labeled_featuresets):
    return MaxentClassifier.train(
        labeled_featuresets,
        algorithm='megam',
        gaussian_prior_sigma=10,
        count_cutoff=1,
        min_lldelta=1e-7)

def train_muc6_ner(num_train_sents, num_test_sents, **kwargs):
    def __zipzip(a, b):
        return LazyMap(lambda (x, y): zip(x, y), LazyZip(a, b))
    def __word_pos_iob(iob_sents, tagged_sents):
        return LazyMap(lambda sent: [y + x[-1:] for x, y in sent], __zipzip(iob_sents, tagged_sents))
    model_file = kwargs.get('model_file')
    muc6 = LazyCorpusLoader('muc6/', MUCCorpusReader, r'.*\.ne\..*\.sgm')
    muc6 = TreebankTaggerCorpusReader(muc6)
    muc6_iob_sents = muc6.iob_sents()
    muc6_tagged_sents = muc6.tagged_sents()
    muc6_sents = __word_pos_iob(muc6_iob_sents, muc6_tagged_sents)
    max_train_sents = int(len(muc6_sents)*0.9)
    max_test_sents = len(muc6_sents) - max_train_sents
    num_train_sents = min((num_train_sents or max_train_sents, max_train_sents))
    num_test_sents = min((num_test_sents or max_test_sents, max_test_sents))                
    muc6_train_sequence = \
        muc6_sents[:num_train_sents]
    muc6_test_sequence = \
        muc6_sents[num_train_sents:num_train_sents + num_test_sents]
    # Import ChunkTagger and ChunkTaggerFeatureDetector because we want 
    # train_model() and the pickled object to use the full class names.
    from nltk_contrib.coref.chunk import ChunkTagger   
    from nltk_contrib.coref.ne import NERChunkTaggerFeatureDetector
    ner = train_model(ChunkTagger, 
                      muc6_train_sequence, 
                      muc6_test_sequence,
                      model_file,
                      num_train_sents,
                      num_test_sents,
                      feature_detector=NERChunkTaggerFeatureDetector,
                      classifier_builder=maxent_classifier_builder,
                      verbose=kwargs.get('verbose'))
    if kwargs.get('verbose'):
        ner.show_most_informative_features(25)
    return ner

def demo(verbose=False):
    import nltk
    from nltk.corpus import treebank    
    from nltk_contrib.coref import NLTK_COREF_DATA
    nltk.data.path.insert(0, NLTK_COREF_DATA)
    from nltk_contrib.coref.ne import MUC6_NER
    ner = nltk.data.load(MUC6_NER)
    for sent in treebank.tagged_sents()[:5]:
        print ner.parse(sent)
        print
    
if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-d', '--demo', action='store_true', dest='demo',
                      default=True, help='run demo')
    parser.add_option('-t', '--train-chunker', action='store_true',
                      default=False, dest='train', 
                      help='train MUC6 named entity recognizer')
    parser.add_option('-f', '--model-file', metavar='FILE',
                      dest='model_file', help='save model to FILE')
    parser.add_option('-e', '--num-test-sents', metavar='NUM_TEST',
                      dest='num_test_sents', type=int, 
                      help='number of test sentences')
    parser.add_option('-r', '--num-train-sents', metavar='NUM_TRAIN',
                      dest='num_train_sents', type=int, 
                      help='number of training sentences')
    parser.add_option('-l', '--local-models', action='store_true',
                      dest='local_models', default=False,
                      help='use models from nltk_contrib.coref')
    parser.add_option('-p', '--psyco', action='store_true',
                      default=False, dest='psyco',
                      help='use Psyco JIT, if available')
    parser.add_option('-v', '--verbose', action='store_true',
                      default=False, dest='verbose',
                      help='verbose')
    (options, args) = parser.parse_args()
    
    if options.local_models:
        nltk.data.path.insert(0, NLTK_COREF_DATA)
        
    if options.psyco:
        try:
            import psyco
            psyco.profile(memory=256)
        except:
            pass
    
    if options.train:
        chunker = train_muc6_ner(options.num_train_sents, 
                                 options.num_test_sents,
                                 model_file=options.model_file, 
                                 verbose=options.verbose)  
                       
    elif options.demo:
        demo(options.verbose)

    else:
        demo(options.verbose)