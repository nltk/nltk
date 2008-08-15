# Natural Language Toolkit (NLTK) Coreference Feature Functions
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org/
# For license information, see LICENSE.TXT

import re
import math

from nltk.corpus import CorpusReader, WordListCorpusReader
from nltk.corpus.util import LazyCorpusLoader

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
          'august', 'september', 'october', 'novemeber', 'december']

NAMES = set([name.lower() for name in
    LazyCorpusLoader('names', WordListCorpusReader,
                     r'(?!\.svn).*\.txt').words()])

CITIES = set([name.lower() for name in
    LazyCorpusLoader('gazetteers', WordListCorpusReader,
                     r'(?!\.svn)uscities.txt').words()])

COUNTRIES = set([name.lower() for name in
    LazyCorpusLoader('gazetteers', WordListCorpusReader,
                     r'(?!\.svn)countries.txt').words()])
                     
NATIONALITIES = set([name.lower() for name in
    LazyCorpusLoader('gazetteers', WordListCorpusReader,
                     r'(?!\.svn)nationalities.txt').words()])                     
                     
PERSON_PREFIXES = ['mr', 'mrs', 'ms', 'miss', 'dr', 'rev', 'judge',
                   'justice', 'honorable', 'hon', 'rep', 'sen', 'sec',
                   'minister', 'chairman', 'succeeding', 'says', 'president']

PERSON_SUFFIXES = ['sr', 'jr', 'phd', 'md']

ORG_SUFFIXES = ['ltd', 'inc', 'co', 'corp', 'plc', 'llc', 'llp', 'gmbh',
                'corporation', 'associates', 'partners', 'committee',
                'institute', 'commission', 'university', 'college',
                'airlines', 'magazine']

CURRENCY_UNITS = ['dollar', 'cent', 'pound', 'euro']
                
RE_PUNCT = '[-!"#$%&\'\(\)\*\+,\./:;<=>^\?@\[\]\\\_`{\|}~]'

RE_NUMERIC = '(\d{1,3}(\,\d{3})*|\d+)(\.\d+)?'

RE_NUMBER = '(%s)(\s+(%s))*' % ('|'.join(NUMBERS), '|'.join(NUMBERS))

RE_QUOTE = '[\'"`]'

RE_ROMAN = 'M?M?M?(CM|CD|D?C?C?C?)(XC|XL|L?X?X?X?)(IX|IV|V?I?I?I?)'

RE_INITIAL = '[A-Z]\.'

RE_TLA = '([A-Z0-9][\.\-]?){2,}'

RE_ALPHA = '[A-Za-z]+'

RE_DATE = '\d+\/\d+(\/\d+)?'

RE_CURRENCY = '\$\s*%s' % RE_NUMERIC

RE_PERCENT = '%s\s*' % RE_NUMERIC + '%'

def contains(is_method, s):
    for word in s.split():
        if is_method(word):
            return True
    return False

def startswith(is_method, s):
    return is_method(s.split()[0])

def endswith(is_method, s):
    return is_method(s.split()[-1])
    
def re_contains(regex, s):
    return bool(re.match(r'.*%s.*' % regex, s))

def re_is(regex, s):
    return bool(re.match(r'^%s$' % regex, s))

def re_startswith(regex, s):
    return bool(re.match(r'^%s' % regex, s))
    
def re_endswith(regex, s):
    return bool(re.match(r'%s$' % regex, s))

def contains_period(s):
    return '.' in s
    
def contains_hyphen(s):
    return '-' in s

def is_punct(s):
    return re_is(RE_PUNCT, s)

def contains_punct(s):
    return re_contains(RE_PUNCT, s)
    
def is_numeric(s):
    return re_is(RE_NUMERIC, s)

def contains_numeric(s):
    return re_contains(RE_NUMERIC, s)

def is_number(s):
    return re_is(RE_NUMBER, s)

def contains_number(s):
    return re_contains(RE_NUMBER, s)

def is_currency(s):
    if re_is(RE_CURRENCY, s):
        return True
    else:
        for cu in CURRENCY_UNITS:
            if cu in s.lower():
                return True
    return False

def contains_currency(s):
    return contains(is_currency, s)
    
def is_percent(s):
    return bool(re.match(r'^%s$' % RE_PERCENT, s))

def contains_percent(s):
    return contains(is_percent, s)

def is_quote(s):
    return bool(re.match(r'^%s$' % RE_QUOTE, s))

def contains_quote(s):
    return bool(re.match(r'.*%s.*' % RE_QUOTE, s))

def is_digit(s):
    return s.isdigit()

def is_upper_case(s):
    return s.isupper()

def is_lower_case(s):
    return s.islower()

def is_title_case(s):
    return s.istitle()

def is_mixed_case(s):
    return s.isalpha() and not \
        (is_lower_case(s) or is_upper_case(s) or is_title_case(s))

def is_alpha_numeric(s):
    return s.isalnum()

def is_roman_numeral(s):
    return re_is(RE_ROMAN, s)
    
def contains_roman_numeral(s):
    return re_contains(RE_ROMAN, s)

def is_initial(s):
    return re_is(RE_INITIAL, s)
    
def contains_initial(s):
    return re_contains(RE_INITIAL, s)

def is_tla(s):
    return re_is(RE_TLA, s) and re_contains(RE_ALPHA, s)
    
def contains_tla(s):
    return re_contains(RE_TLA, s)

def is_name(s):
    return is_title_case(s) and s.lower() in NAMES

def contains_name(s):
    return contains(is_name, s)

def is_city(s):
    return is_title_case(s) and s.lower() in CITIES

def contains_city(s):
    return contains(is_city, s)

def part_of_city(s):
    for city in CITIES:
        if s.lower() in city:
            return True
    return False

def is_person_prefix(s):
    return is_title_case(s) and s.replace('.', '').lower() in PERSON_PREFIXES

def startswith_person_prefix(s):
    return startswith(is_person_prefix, s)
    
def endswith_person_prefix(s):
    return startswith(is_person_prefix, s)    

def contains_person_prefix(s):
    return contains(is_person_prefix, s)

def is_person_suffix(s):
    return is_title_case(s) and s.replace('.', '').lower() in PERSON_SUFFIXES

def startswith_person_suffix(s):
    return startswith(is_person_suffix, s)

def endswith_person_suffix(s):
    return endswith(is_person_suffix, s)
    
def contains_person_suffix(s):
    return contains(is_person_suffix, s)

def is_org_suffix(s):
    return is_title_case(s) and s.replace('.', '').lower() in ORG_SUFFIXES

def startswith_org_suffix(s):
    return startswith(is_org_suffix, s)
    
def endswith_org_suffix(s):
    return endswith(is_org_suffix, s)

def contains_org_suffix(s):
    return contains(is_org_suffix, s)

def is_day(s):
    return is_title_case(s) and s.lower() in DAYS

def contains_day(s):
    return contains(is_day, s)

def is_month(s):
    return is_title_case(s) and \
        (s.lower() in MONTHS or s.lower()[:3] in [mon[:3] for mon in MONTHS])

def contains_month(s):
    return contains(is_month, s)

def is_date(s):
    return re_is(RE_DATE, s)

def contains_date(s):
    return re_contains(RE_DATE, s)

def is_ordinal(s):
    if s.lower() in ORDINALS or s.endswith('teenth'):
        return True
    elif (s.lower()[:4] in [n[:4] for n in NUMBERS] or s[:1].isdigit()) and \
        s[-2:] in ['st', 'nd', 'rd', 'th']:
        return True
    return False

def contains_ordinal(s):
    return contains(is_ordinal, s)

def is_prefix(s):
    return s.startswith('-')

def is_suffix(s):
    return s.endswith('-')

def is_country(s):
    def _country_name(s):
        stop_words = ['islands', 'saint', 'and', 'republic', 'virgin',
                      'united', 'south', 'of', 'new', 'the']                      
        words = []
        for word in s.split():
            word = re.sub(r'%s' % RE_PUNCT, '', word)            
            if word.lower() not in stop_words:
                words.append(word)
        return ' '.join(words) or s
        
    if is_title_case(s) and s.lower() in COUNTRIES:
        return True
    else:
        country_name = _country_name(s)
        if is_title_case(country_name):
            for country in COUNTRIES:
                if country_name.lower() == _country_name(country).lower():
                    return True
    return False

def contains_country(s):
    return contains(is_country, s)

def is_nationality(s):
    return s.lower() in NATIONALITIES or \
           s.lower()[:-1] in NATIONALITIES or \
           s.lower()[:-2] in NATIONALITIES

def contains_nationality(s):
    return contains(is_nationality, s)

def log_length(s):
    return int(math.log(len(s)))
    
def word_type(word):
    if not word:
        return ()

    word_type = []
    if contains_person_prefix(word) or contains_person_suffix(word):
        word_type.append('PERSON')
    if contains_org_suffix(word):
        word_type.append('ORG')
    if is_name(word):
        word_type.append('NAME')
    if is_nationality(word):
        word_type.append('NATIONALITY')
    if is_city(word) or is_country(word):
        word_type.append('LOCATION')
    if is_roman_numeral(word):
        word_type.append('ROMAN_NUMERAL')
    if is_tla(word):
        word_type.append('TLA')
    if is_initial(word):
        word_type.append('INITIAL')
    if contains_currency(word):
        word_type.append('CURRENCY')
    if contains_percent(word):
        word_type.append('PERCENT')
    if contains_numeric(word) or contains_number(word) or \
       contains_ordinal(word) or is_digit(word):
        word_type.append('NUMBER')
    if contains_day(word) or contains_month(word) or \
       contains_date(word):
        word_type.append('DATE')
    if is_suffix(word):
        word_type.append('SUFFIX')
    if is_prefix(word):
        word_type.append('PREFIX')
    if is_title_case(word):
        word_type.append('TITLE_CASE')
    if is_punct(word):
        word_type.append('PUNCT')

    return tuple(word_type[:3])
