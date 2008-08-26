"""
Two functions are not yet implemented
    - morph_fraction: numeric fraction to text
    - morph_numeric: integer number to text
"""

import lexicon

def _is_vowel(char):
    return char in ['o', 'e', 'i', 'a', 'y']


def pluralize(word):
    """
    Handles word sring ending with 'ch', 'sh', 'o',
    's', 'x', 'y', 'z'

    >>> print pluralize('copy')
    copies
    >>> print pluralize('cat')
    cats
    >>> print pluralize('language')
    languages
    """

    assert word
    assert isinstance(word, basestring)
    assert len(word) > 0

    second_last = word[-2]
    last = word[-1]
    if last in ['s', 'z','x']:
        return word + "es"
    elif last == 'h':
        if second_last in ['s', 'c']:
            return word + "es"
        else:
            return word + 's'
    elif last == 'o':
        if not _is_vowel(second_last):
            return word + "es"
        else: 
            return word + 's'
    elif last == 'y':
        if not _is_vowel(second_last):
            return word[:-1] + "ies"
        else:
            return word + 's'
    else:
        return word + 's'

            
def morph_fraction(lex, num, den, digit):
    """
    Return the string representation of a fraction
    """
    raise NotImplementedError

def morph_numeric(lex, ord_or_card, value, digit):
    """
    Convert a number into text form
    """
    raise NotImplementedError

def form_ing(word):
    """
    Adding 'ing to the word dropping the final 'e if any,
    handlies duplication of final consonat and special cases.
    """

    # last char of the word
    last = word[-1]

    if last == 'e':
        return word[:-1] + 'ing'
    elif last == 'r':
        if word[-2] == 'a': 
            return word + "ring"
    elif last in ['b', 'd', 'g', 'm', 'n', 'p', 't']:
        if _is_vowel(word[-2]) and not (_is_vowel(word[-3])):
            return word + word[-1] + "ing"

    return word + "ing" 
        
def form_past(word):
    """
    Form past tense of the word by adding 'ed to it.
    Handles duplication of final consonant and special values
    """

    last = word[-1]
    assert word
    assert isinstance(word, basestring)

    if last == 'e':
        return word + 'd'
    elif last == 'y':
        if _is_vowel(word[-2]):
            return word + "ed"
        else: 
            return word[:-1] + "ied"
    elif last == 'r':
        if word[-2] == 'a':
            return word + word[-1] + 'ed'
        else:
            return word + 'ed'
    elif last in ['b', 'd', 'g', 'm', 'n', 't', 'p']:
        if _is_vowel(word[-2]) and not _is_vowel(word[-3]):
            return word + word[-1] + 'ed'
    return word + 'ed'

def _is_first_person(person):
    return person in ['I', 'i', 'We', 'we'] or person == 'first'

def _is_second_person(person):
    return person in ['You', 'you'] or person == 'second'

def _is_third_person(person):
    return person in ['He', 'She', 'he', 'she', 'they', "They"] or person == 'third'

def _is_singular(number):
    return number == 'one' or number == 'sing' or number == 'singular'

def _is_dual(number):
    return number == 'two' or number == 'dual'

def _is_plural(number):
    return not (_is_singular(number) or _is_dual(number)) or number == 'plural'

def form_present_verb(word, number, person):
    """
    Forms the suffix for the present tense of the verb WORD
    """
    assert word
    assert isinstance(word, basestring)
    if _is_first_person(person) or _is_second_person(person):
        return word
    elif _is_third_person(person):
        if _is_singular(number):
            return pluralize(word)
        if _is_dual(number) or _is_plural(number): 
            return word
    return None
    
def morph_be(number, person, tense):
    if tense == 'present':
        if _is_singular(number):
            if _is_first_person(person):
                return 'am'
            elif _is_second_person(person):
                return 'are'
            elif _is_third_person(person):
                return 'is'
            else:
                return 'are'
    elif tense == 'past':
        if _is_singular(number):
            if _is_first_person(person):
                return 'was'
            elif _is_second_person(person):
                return 'were'
            elif _is_third_person(person):
                return 'was'
            else:
                return 'were'
    elif tense == 'present-participle':
        return 'being'
    elif tense == 'past-participle':
        return 'been'


def morph_verb(word, ending, number, person, tense):
    """
    Adds the proper suffix to the verb root taking into 
    account ending, number, person, and tense.
    """

    if ending == 'root':
        return word
    if ending == 'infinitive': 
        return "to %s" % word
    if word == 'be':
        # what 'internal' does no one knows... 
        if ending == "internal":
            return morph_be(number, person, ending)
        else:
            return morph_be(number, person, tense)
    if ending == 'present-participle':
        # if the verb is irregular 
        # it should be in the lexicon fetch it and return it
        # otherwise it is not irregular, so add 'ing' to it.
        if word in lexicon.IRREG_VERBS:
            return lexicon.IRREG_VERBS[word]['present-participle']
        else:
            return form_ing(word)
    if ending == 'past-participle':
        if word in lexicon.IRREG_VERBS:
            return lexicon.IRREG_VERBS[word]['past-participle']
        else:
            return form_past(word)
    if tense == 'present' and person == 'third' and number == 'singular' and word in lexicon.IRREG_VERBS:
        return lexicon.IRREG_VERBS[word]['present-third-person-singular']
    if tense == 'present':
        return form_present_verb(word, number, person)
    if tense == 'past':
        return form_past(word)
    return None

def form_adj(word, ending):
    """
    changes in spelling:
    1. final base consonants are doubled when preceding vowel is stressed and
    spelled with a single letter: big-bigger-biggest; sad-sadder-saddest.
    2. bases ending in a consonant+y, final y changed to i
    angry-angrier-angriest.
    3. base ends in a mute -e, dropped before inflectional suffix:
        pure-purer-purest
        free-freer-freest
            """
    last = word[-1]
    if last == 'e':
        return word[:-1] + ending
    if last in ['b', 'd', 'g', 'm', 'n', 'p', 't'] and _is_vowel(word[-2]) and not _is_vowel(word[-3]):
        return word + last + ending

    if last == 'y' and not _is_vowel(word[-2]):
        return word[:-1] + 'i' + ending
    return word + ending


def morph_adj(word, superlative, comparative, inflection):
    ending = None
    if superlative == 'no':
        if not comparative == 'no':
            ending = None
        else:
            ending = 'comparative'
    else:
        ending = 'superlative'
    
    if inflection == 'no' or not ending: 
        return word
    else:
        if word in lexicon.IRREG_SUPER_COMPARATIVES:
            return lexicon.IRREG_SUPER_COMPARATIVES[word][ending]
        elif ending == 'superlative':
            return form_adj(word, 'est')
        else:
            return form_adj(word, 'er')

def morph_pronoun(lex, pronoun_type, case, gender, number, distance, animate,
                  person, restrictive):
    """
    Returns the correct pronoun given the features
    """
    if lex and isinstance(lex, basestring) and not (lex in ['none', 'nil']):
        return lex
    if pronoun_type == 'personal':
        # start with the 'he' then augmen by person, then, by number, 
        # gender and finally by case
        # this is a port of the hack in the morphology.scm code
        if (not animate) or (gender == 'feminine'):
            anime = 'yes'
        if animate == 'no':
            gender = 'neuter'
        
        lex = 'he'
        if person and not (person == 'third'):
            lex = lexicon.PRONOUNS_PERSON[person]
        if number and not (number == 'masculine'):
            lex = lexicon.PROUNOUNS_NUMBER[number]
        if gender and not (gender == 'masculine'):
            lex = lexicon.PRONOUNS_GENDER[gender]
        if case and not (case == 'subjective'):
            lex = lexicon.PRONOUNS_CASE[case]
    else:
        return lex

    if pronoun-type and pronoun-type == 'demonstrative':
        if not (number in ['first', 'second']):
            if distance == 'far':
                return 'those'
            else:
                return 'these'
        elif distance == 'far':
            return 'that'
    else: 
        return 'this'

    if pronoun-type == 'relative':
        if not animate:
            animate = 'no'
        if animate == 'no':
            gender = 'neuter'
        if restrictive == 'yes':
            return 'that'
        elif case == 'possessive':
            return 'whose'
        elif case == 'objective':
            if gender == 'neuter':
                return 'which'
            else:
                return 'whom'
        elif gender == 'neuter':
            return 'which'
        elif animate == 'no':
            return 'which'
        else:
            return 'who'
    
    if pronoun-type == 'question':
        # this is the conversion of another hack in FUF morphology
        # start at line 76 in morphology.scm
        if not animate:
            animate == 'no'
        if animate == 'no':
            gender == 'neuter'
        if restrictive == 'yes':
            return 'which'
        elif case == 'possessive':
            return 'whose'
        elif case == 'objective':
            if gender == 'neuter':
                return 'what'
            else:
                return 'whom'
        elif gender == 'neuter':
            return 'what'
        elif animate == 'no':
            return 'what'
        else:
            return 'who'
    
    if pronoun-type == 'quantified':
        return lex


def morph_number(word, number):
    """
    Adds the plural suffix to work if number is 
    plural. Note: the default is singular
    """

    if (not number) or (number == ''): 
        return word
    elif not word:
        return word
    elif number not in ['first', 'second'] or number == 'plural':
        if word in lexicon.IRREG_PLURALS:
            return lexicon.IRREG_PLURALS[word]
        else:
            pluralize(word)
    else:
        return word

# markers, not sure what they are used for
# the original code is not very well documented.

PLURAL_MARKER = "****"
INDEFINITE_ARTICLE = 'a**'
A_AN_MARKER = '***'

def mark_noun_as_plural(word):
    return PLURAL_MARKER +  word

def unmark_noun_as_plural(word):
    return word[PLURAL_MARKER:]

def is_noun_marked_as_plural(word):
    return  (word[:len(PLURAL_MARKER)] == PLURAL_MARKER)

def mark_noun_as_an(word):
    return A_AN_MARKER + word

def unmark_noun_as_an(word):
    return word[A_AN_MAKER:]

def is_noun_maked_as_an(word):
    return (word[:len(A_AN_MARKER)] == A_AN_MARKER)

def is_final_punctuation(letter):
    return (letter in ['.', ';', '!', ':', '?'])

def morph_noun(word, number, a_an, feature):
    """If feature is possessive, then return the apostrephised form of the noun
    appropriate to the number.
    If a_an is 'an mark noun with mark-noun-as-an to agree with determiner.
    If noun is plural and ends with 's', mark noun as plural to let it agree
    with possessive mark that may follow it (single apostrophe or 's).
    Return word with number suffix."""
    word = morph_number(word, number)
    if not (number in ['first', 'second']) and word[-1] == 's':
        return mark_noun_as_plural(word)
    else:
        return word

    if a_an == 'an':
        return mark_noun_as_an(word)
    else:
        return word
