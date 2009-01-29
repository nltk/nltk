# Natural Language Toolkit (NLTK) Coreference Feature Functions
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk> (modifications)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import math
import nltk


from nltk.corpus import names, gazetteers

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

USCITIES = set(gazetteers.words('uscities.txt'))

# [XX] contains some non-ascii chars
COUNTRIES = set([country for filename in ('isocountries.txt','countries.txt')
                 for country in gazetteers.words(filename)])

# States in North America
NA_STATES = set([state.lower() for filename in
                 ('usstates.txt','mexstates.txt','caprovinces.txt') for state in
                 gazetteers.words(filename)])
                     
US_STATE_ABBREVIATIONS = set(gazetteers.words('usstateabbrev.txt'))

NATIONALITIES = set(gazetteers.words('nationalities.txt'))
                     
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
                
RE_PUNCT = '[-!"#$%&\'\(\)\*\+,\./:;<=>^\?@\[\]\\\_`{\|}~]'

RE_NUMERIC = '(\d{1,3}(\,\d{3})*|\d+)(\.\d+)?'

RE_NUMBER = '(%s)(\s+(%s))*' % ('|'.join(NUMBERS), '|'.join(NUMBERS))

RE_QUOTE = '[\'"`]'

RE_ROMAN = 'M?M?M?(CM|CD|D?C?C?C?)(XC|XL|L?X?X?X?)(IX|IV|V?I?I?I?)'

RE_INITIAL = '[A-Z]\.'

RE_TLA = '([A-Z0-9][\.\-]?){2,}'

RE_ALPHA = '[A-Za-z]+'

RE_DATE = '\d+\/\d+(\/\d+)?'

RE_CURRENCY = '\$\s*(%s)?' % RE_NUMERIC

RE_PERCENT = '%s\s*' % RE_NUMERIC + '%'

RE_YEAR = '(\d{4}s?|\d{2}s)'

RE_TIME = '\d{1,2}(\:\d{2})?(\s*[aApP]\.?[mM]\.?)?'

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
    
def contains_title_case_sequence(s):
    words = s.split()
    count = sum([int(is_title_case(word)) for word in words])
    return (count / len(words)) > 0.5

def is_mixed_case(s):
    return s.isalpha() and not \
        (is_lower_case(s) or is_upper_case(s) or is_title_case(s))

def is_alpha_numeric(s):
    return s.isalnum()

def is_roman_numeral(s):
    return re_is(RE_ROMAN, s)
    
def contains_roman_numeral(s):
    return contains(is_roman_numeral, s)

def is_initial(s):
    return re_is(RE_INITIAL, s)
    
def contains_initial(s):
    return re_contains(RE_INITIAL, s)

def is_tla(s):
    return re_is(RE_TLA, s) and re_contains(RE_ALPHA, s)
    
def contains_tla(s):
    return re_contains(RE_TLA, s)

def is_name(s):
    return s.lower() in NAMES

def contains_name(s):
    return contains(is_name, s)

def contains_name_sequence(s):
    count = 0.0
    words = s.split()
    for word in words:
        if is_person_prefix(word) or is_name(word) or is_initial(word) or \
           is_person_suffix(word) or is_roman_numeral(word):
            count += 1
    return (count / len(words)) > 0.5
        
def is_city(s):
    return s.lower() in USCITIES

def contains_city(s):
    if contains(is_city, s):
        return True
    for city in USCITIES:
        if city in s.lower():
            return True
    return False

def part_of_city(s):
    for city in USCITIES:
        if s.lower() in city:
            return True
    return False
    
def is_state(s):
    return s.lower() in NA_STATES or s in US_STATE_ABBREVIATIONS

def contains_state(s):
    if contains(is_state, s):
        return True
    for state in NA_STATES:
        if state in s.lower():
            return True
    return False

def is_person_prefix(s):
    return s.replace('.', '').lower() in PERSON_PREFIXES

def startswith_person_prefix(s):
    return startswith(is_person_prefix, s)

def contains_person_prefix(s):
    return contains(is_person_prefix, s)

def is_person_suffix(s):
    return s.replace('.', '').lower() in PERSON_SUFFIXES

def endswith_person_suffix(s):
    return endswith(is_person_suffix, s)
    
def contains_person_suffix(s):
    return contains(is_person_suffix, s)

def is_org_suffix(s):
    return s.replace('.', '').lower() in ORG_SUFFIXES
    
def endswith_org_suffix(s):
    return endswith(is_org_suffix, s)

def contains_org_suffix(s):
    return contains(is_org_suffix, s)

def is_day(s):
    return s.lower() in DAYS

def contains_day(s):
    return contains(is_day, s)

def is_month(s):
    return s.lower().replace('.', '') in MONTHS

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
        
    if s.lower() in COUNTRIES:
        return True
    else:
        country_name = _country_name(s)
        for country in COUNTRIES:
            if country_name.lower() == _country_name(country).lower():
                return True
    return False

def contains_country(s):
    if contains(is_country, s):
        return True
    for country in COUNTRIES:
        if country in s.lower():
            return True
    return False

def is_nationality(s):
    return s.lower() in NATIONALITIES or \
           s.lower()[:-1] in NATIONALITIES or \
           s.lower()[:-2] in NATIONALITIES

def contains_nationality(s):
    return contains(is_nationality, s)

def log_length(s):
    return int(math.log(len(s)))
    
def word_count(s):
    return len(s.split())

def contains_of_location(s):
    for words in re.split(r'\s+of\s+', s)[1:]:
        if is_city(words) or is_country(words) or is_state(words):
            return True
    return False
    
def is_location(s):
    return is_city(s) or is_country(s) or is_state(s)

def contains_location(s):
    if contains(is_location, s):
        return True
    for location in USCITIES.union(COUNTRIES).union(NA_STATES):
        if location in s.lower():
            return True
    return False

def is_year(s):
    return re_is(RE_YEAR, s)

def contains_year(s):
    return re_contains(RE_YEAR, s)
    
def is_time(s):
    return re_is(RE_TIME, s)

def contains_time(s):
    return re_contains(RE_TIME, s)

def is_pronoun(s):
    return s.lower() in ENGLISH_PRONOUNS
    
def word_type(word):
    if not word:
        return ()

    word_type = []
    if contains_person_prefix(word) or contains_person_suffix(word):
        word_type.append('PERSON')
    if contains_org_suffix(word):
        word_type.append('ORG')
    if contains_name(word):
        word_type.append('NAME')
    if contains_nationality(word):
        word_type.append('NATIONALITY')
    if contains_location(word):
        word_type.append('LOCATION')
    if contains_roman_numeral(word):
        word_type.append('ROMAN_NUMERAL')
    if contains_tla(word):
        word_type.append('TLA')
    if contains_initial(word):
        word_type.append('INITIAL')
    if contains_currency(word):
        word_type.append('CURRENCY')
    if contains_percent(word):
        word_type.append('PERCENT')
    if contains_numeric(word) or contains_number(word) or \
       contains_ordinal(word) or is_digit(word):
        word_type.append('NUMBER')
    if contains_day(word) or contains_month(word) or \
       contains_date(word) or contains_year(word):
        word_type.append('DATE')
    if contains_time(word):
        word_type.append('TIME')
    if is_suffix(word):
        word_type.append('SUFFIX')
    if is_prefix(word):
        word_type.append('PREFIX')
    if contains_title_case_sequence(word):
        word_type.append('TITLE_CASE')
    if contains_punct(word):
        word_type.append('PUNCT')

    return tuple(word_type[:3])




def demo():
    from nltk.corpus import treebank
    for word in treebank.words('wsj_0034.mrg'):
        wt = word_type(word)
        if len(wt) == 0: wt = None
        if '*' in word: continue
        print "%-20s\t%s" % (word, wt)
        
if __name__ == '__main__':
    demo()

