# -*- coding: utf-8 -*-
# Natural Language Toolkit:
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pidong Wang, Josh Schroeder, Ondrej Bojar, based on code by Philipp Koehn
# Contributors: Liling Tan, Martijn Pieters, Wiktor Stribizew
#
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

from __future__ import print_function
import re
from six import text_type

from nltk.tokenize.api import TokenizerI
from nltk.tokenize.util import is_cjk
from nltk.corpus import perluniprops, nonbreaking_prefixes


class MosesTokenizer(TokenizerI):
    """
    This is a Python port of the Moses Tokenizer from
    https://github.com/moses-smt/mosesdecoder/blob/master/scripts/tokenizer/tokenizer.perl

    >>> tokenizer = MosesTokenizer()
    >>> text = u'This, is a sentence with weird\xbb symbols\u2026 appearing everywhere\xbf'
    >>> expected_tokenized = u'This , is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
    >>> tokenized_text = tokenizer.tokenize(text, return_str=True)
    >>> tokenized_text == expected_tokenized
    True
    >>> tokenizer.tokenize(text) == [u'This', u',', u'is', u'a', u'sentence', u'with', u'weird', u'\xbb', u'symbols', u'\u2026', u'appearing', u'everywhere', u'\xbf']
    True

    The nonbreaking prefixes should tokenize the final fullstop.

    >>> m = MosesTokenizer()
    >>> m.tokenize('abc def.')
    [u'abc', u'def', u'.']
    """

    # Perl Unicode Properties character sets.
    IsN = text_type(''.join(perluniprops.chars('IsN')))
    IsAlnum = text_type(''.join(perluniprops.chars('IsAlnum')))
    IsSc = text_type(''.join(perluniprops.chars('IsSc')))
    IsSo = text_type(''.join(perluniprops.chars('IsSo')))
    IsAlpha = text_type(''.join(perluniprops.chars('IsAlpha')))
    IsLower = text_type(''.join(perluniprops.chars('IsLower')))

    # Remove ASCII junk.
    DEDUPLICATE_SPACE = r'\s+', r' '
    ASCII_JUNK = r'[\000-\037]', r''

    # Neurotic Perl heading space, multi-space and trailing space chomp.
    # These regexes are kept for reference purposes and shouldn't be used!!
    MID_STRIP = r" +", r" "     # Use DEDUPLICATE_SPACE instead.
    LEFT_STRIP = r"^ ", r""     # Uses text.lstrip() instead.
    RIGHT_STRIP = r" $", r""    # Uses text.rstrip() instead.

    # Pad all "other" special characters not in IsAlnum.
    PAD_NOT_ISALNUM = u'([^{}\s\.\'\`\,\-])'.format(IsAlnum), r' \1 '

    # Splits all hypens (regardless of circumstances), e.g.
    # 'foo -- bar' -> 'foo @-@ @-@ bar' , 'foo-bar' -> 'foo @-@ bar'
    AGGRESSIVE_HYPHEN_SPLIT = u'([{alphanum}])\-(?=[{alphanum}])'.format(alphanum=IsAlnum), r'\1 \@-\@ '

    # Make multi-dots stay together.
    REPLACE_DOT_WITH_LITERALSTRING_1 = r'\.([\.]+)', ' DOTMULTI\1'
    REPLACE_DOT_WITH_LITERALSTRING_2 = r'DOTMULTI\.([^\.])', 'DOTDOTMULTI \1'
    REPLACE_DOT_WITH_LITERALSTRING_3 = r'DOTMULTI\.', 'DOTDOTMULTI'

    # Separate out "," except if within numbers (5,300)
    # e.g.  A,B,C,D,E > A , B,C , D,E
    # First application uses up B so rule can't see B,C
    # two-step version here may create extra spaces but these are removed later
    # will also space digit,letter or letter,digit forms (redundant with next section)
    COMMA_SEPARATE_1 = u'([^{}])[,]'.format(IsN), r'\1 , '
    COMMA_SEPARATE_2 = u'[,]([^{}])'.format(IsN), r' , \1'

    # Attempt to get correct directional quotes.
    DIRECTIONAL_QUOTE_1 = r'^``',               r'`` '
    DIRECTIONAL_QUOTE_2 = r'^"',                r'`` '
    DIRECTIONAL_QUOTE_3 = r'^`([^`])',          r'` \1'
    DIRECTIONAL_QUOTE_4 = r"^'",                r'`  '
    DIRECTIONAL_QUOTE_5 = r'([ ([{<])"',        r'\1 `` '
    DIRECTIONAL_QUOTE_6 = r'([ ([{<])``',       r'\1 `` '
    DIRECTIONAL_QUOTE_7 = r'([ ([{<])`([^`])',  r'\1 ` \2'
    DIRECTIONAL_QUOTE_8 = r"([ ([{<])'",        r'\1 ` '

    # Replace ... with _ELLIPSIS_
    REPLACE_ELLIPSIS = r'\.\.\.',       r' _ELLIPSIS_ '
    # Restore _ELLIPSIS_ with ...
    RESTORE_ELLIPSIS = r'_ELLIPSIS_',   r'\.\.\.'

    # Pad , with tailing space except if within numbers, e.g. 5,300
    # These are used in nltk.tokenize.moses.penn_tokenize()
    COMMA_1 = u'([^{numbers}])[,]([^{numbers}])'.format(numbers=IsN), r'\1 , \2'
    COMMA_2 = u'([{numbers}])[,]([^{numbers}])'.format(numbers=IsN), r'\1 , \2'
    COMMA_3 = u'([^{numbers}])[,]([{numbers}])'.format(numbers=IsN), r'\1 , \2'

    # Pad unicode symbols with spaces.
    SYMBOLS = u'([;:@#\$%&{}{}])'.format(IsSc, IsSo), r' \1 '

    # Separate out intra-token slashes.  PTB tokenization doesn't do this, so
    # the tokens should be merged prior to parsing with a PTB-trained parser.
    # e.g. "and/or" -> "and @/@ or"
    INTRATOKEN_SLASHES = u'([{alphanum}])\/([{alphanum}])'.format(alphanum=IsAlnum), r'$1 \@\/\@ $2'

    # Splits final period at end of string.
    FINAL_PERIOD = r"""([^.])([.])([\]\)}>"']*) ?$""", r'\1 \2\3'
    # Pad all question marks and exclamation marks with spaces.
    PAD_QUESTION_EXCLAMATION_MARK = r'([?!])', r' \1 '

    # Handles parentheses, brackets and converts them to PTB symbols.
    PAD_PARENTHESIS = r'([\]\[\(\){}<>])', r' \1 '
    CONVERT_PARENTHESIS_1 = r'\(', '-LRB-'
    CONVERT_PARENTHESIS_2 = r'\)', '-RRB-'
    CONVERT_PARENTHESIS_3 = r'\[', '-LSB-'
    CONVERT_PARENTHESIS_4 = r'\]', '-RSB-'
    CONVERT_PARENTHESIS_5 = r'\{', '-LCB-'
    CONVERT_PARENTHESIS_6 = r'\}', '-RCB-'

    # Pads double dashes with spaces.
    PAD_DOUBLE_DASHES = r'--', ' -- '

    # Adds spaces to start and end of string to simplify further regexps.
    PAD_START_OF_STR = r'^', ' '
    PAD_END_OF_STR = r'$', ' '

    # Converts double quotes to two single quotes and pad with spaces.
    CONVERT_DOUBLE_TO_SINGLE_QUOTES = r'"', " '' "
    # Handles single quote in possessives or close-single-quote.
    HANDLES_SINGLE_QUOTES = r"([^'])' ", r"\1 ' "

    # Pad apostrophe in possessive or close-single-quote.
    APOSTROPHE = r"([^'])'", r"\1 ' "

    # Prepend space on contraction apostrophe.
    CONTRACTION_1 = r"'([sSmMdD]) ", r" '\1 "
    CONTRACTION_2 = r"'ll ", r" 'll "
    CONTRACTION_3 = r"'re ", r" 're "
    CONTRACTION_4 = r"'ve ", r" 've "
    CONTRACTION_5 = r"n't ", r" n't "
    CONTRACTION_6 = r"'LL ", r" 'LL "
    CONTRACTION_7 = r"'RE ", r" 'RE "
    CONTRACTION_8 = r"'VE ", r" 'VE "
    CONTRACTION_9 = r"N'T ", r" N'T "

    # Informal Contractions.
    CONTRACTION_10 = r" ([Cc])annot ",  r" \1an not "
    CONTRACTION_11 = r" ([Dd])'ye ",    r" \1' ye "
    CONTRACTION_12 = r" ([Gg])imme ",   r" \1im me "
    CONTRACTION_13 = r" ([Gg])onna ",   r" \1on na "
    CONTRACTION_14 = r" ([Gg])otta ",   r" \1ot ta "
    CONTRACTION_15 = r" ([Ll])emme ",   r" \1em me "
    CONTRACTION_16 = r" ([Mm])ore$text =~ s='n ",  r" \1ore 'n "
    CONTRACTION_17 = r" '([Tt])is ",    r" '\1 is "
    CONTRACTION_18 = r" '([Tt])was ",   r" '\1 was "
    CONTRACTION_19 = r" ([Ww])anna ",   r" \1an na "

    # Clean out extra spaces
    CLEAN_EXTRA_SPACE_1 = r'  *', r' '
    CLEAN_EXTRA_SPACE_2 = r'^ *', r''
    CLEAN_EXTRA_SPACE_3 = r' *$', r''

    # Neurotic Perl regexes to escape special characters.
    # These XML escaping regexes are kept such that tokens generated from
    # NLTK's implementation is consistent with Moses' tokenizer's output.
    # Outside of the MosesTokenizer function, it's strongly encouraged to use
    # nltk.tokenize.util.xml_escape() function instead.
    ESCAPE_AMPERSAND = r'&', r'&amp;'
    ESCAPE_PIPE = r'\|', r'&#124;'
    ESCAPE_LEFT_ANGLE_BRACKET = r'<', r'&lt;'
    ESCAPE_RIGHT_ANGLE_BRACKET = r'>', r'&gt;'
    ESCAPE_SINGLE_QUOTE = r"\'", r"&apos;"
    ESCAPE_DOUBLE_QUOTE = r'\"', r'&quot;'
    ESCAPE_LEFT_SQUARE_BRACKET = r"\[", r"&#91;"
    ESCAPE_RIGHT_SQUARE_BRACKET = r"]", r"&#93;"

    EN_SPECIFIC_1 = u"([^{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    EN_SPECIFIC_2 = u"([^{alpha}{isn}])[']([{alpha}])".format(alpha=IsAlpha, isn=IsN), r"\1 ' \2"
    EN_SPECIFIC_3 = u"([{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    EN_SPECIFIC_4 = u"([{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1 '\2"
    EN_SPECIFIC_5 = u"([{isn}])[']([s])".format(isn=IsN), r"\1 '\2"

    ENGLISH_SPECIFIC_APOSTROPHE = [EN_SPECIFIC_1, EN_SPECIFIC_2, EN_SPECIFIC_3,
                                   EN_SPECIFIC_4, EN_SPECIFIC_5]

    FR_IT_SPECIFIC_1 = u"([^{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_2 = u"([^{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_3 = u"([{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_4 = u"([{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1' \2"

    FR_IT_SPECIFIC_APOSTROPHE = [FR_IT_SPECIFIC_1, FR_IT_SPECIFIC_2,
                                 FR_IT_SPECIFIC_3, FR_IT_SPECIFIC_4]

    NON_SPECIFIC_APOSTROPHE = r"\'", r" \' "

    MOSES_PENN_REGEXES_1 = [DEDUPLICATE_SPACE, ASCII_JUNK, DIRECTIONAL_QUOTE_1,
                              DIRECTIONAL_QUOTE_2, DIRECTIONAL_QUOTE_3,
                              DIRECTIONAL_QUOTE_4, DIRECTIONAL_QUOTE_5,
                              DIRECTIONAL_QUOTE_6, DIRECTIONAL_QUOTE_7,
                              DIRECTIONAL_QUOTE_8, REPLACE_ELLIPSIS, COMMA_1,
                              COMMA_2, COMMA_3, SYMBOLS, INTRATOKEN_SLASHES,
                              FINAL_PERIOD, PAD_QUESTION_EXCLAMATION_MARK,
                              PAD_PARENTHESIS, CONVERT_PARENTHESIS_1,
                              CONVERT_PARENTHESIS_2, CONVERT_PARENTHESIS_3,
                              CONVERT_PARENTHESIS_4, CONVERT_PARENTHESIS_5,
                              CONVERT_PARENTHESIS_6, PAD_DOUBLE_DASHES,
                              PAD_START_OF_STR, PAD_END_OF_STR,
                              CONVERT_DOUBLE_TO_SINGLE_QUOTES,
                              HANDLES_SINGLE_QUOTES, APOSTROPHE, CONTRACTION_1,
                              CONTRACTION_2, CONTRACTION_3, CONTRACTION_4,
                              CONTRACTION_5, CONTRACTION_6, CONTRACTION_7,
                              CONTRACTION_8, CONTRACTION_9, CONTRACTION_10,
                              CONTRACTION_11, CONTRACTION_12, CONTRACTION_13,
                              CONTRACTION_14, CONTRACTION_15, CONTRACTION_16,
                              CONTRACTION_17, CONTRACTION_18, CONTRACTION_19]

    MOSES_PENN_REGEXES_2 = [RESTORE_ELLIPSIS, CLEAN_EXTRA_SPACE_1,
                        CLEAN_EXTRA_SPACE_2, CLEAN_EXTRA_SPACE_3,
                        ESCAPE_AMPERSAND, ESCAPE_PIPE,
                        ESCAPE_LEFT_ANGLE_BRACKET, ESCAPE_RIGHT_ANGLE_BRACKET,
                        ESCAPE_SINGLE_QUOTE, ESCAPE_DOUBLE_QUOTE]

    MOSES_ESCAPE_XML_REGEXES = [ESCAPE_AMPERSAND, ESCAPE_PIPE,
                                ESCAPE_LEFT_ANGLE_BRACKET,
                                ESCAPE_RIGHT_ANGLE_BRACKET,
                                ESCAPE_SINGLE_QUOTE, ESCAPE_DOUBLE_QUOTE,
                                ESCAPE_LEFT_SQUARE_BRACKET,
                                ESCAPE_RIGHT_SQUARE_BRACKET]

    def __init__(self, lang='en'):
        # Initialize the object.
        super(MosesTokenizer, self).__init__()
        self.lang = lang
        # Initialize the language specific nonbreaking prefixes.
        self.NONBREAKING_PREFIXES = nonbreaking_prefixes.words(lang)
        self.NUMERIC_ONLY_PREFIXES = [w.rpartition(' ')[0] for w in
                                      self.NONBREAKING_PREFIXES if
                                      self.has_numeric_only(w)]



    def replace_multidots(self, text):
        text = re.sub(r'\.([\.]+)', r' DOTMULTI\1', text)
        while re.search(r'DOTMULTI\.', text):
            text = re.sub(r'DOTMULTI\.([^\.])', r'DOTDOTMULTI \1', text)
            text = re.sub(r'DOTMULTI\.', 'DOTDOTMULTI', text)
        return text

    def restore_multidots(self, text):
        while re.search(r'DOTDOTMULTI', text):
            text = re.sub(r'DOTDOTMULTI', r'DOTMULTI.', text)
        return re.sub(r'DOTMULTI', r'.', text)

    def islower(self, text):
        return not set(text).difference(set(self.IsLower))

    def isalpha(self, text):
        return not set(text).difference(set(self.IsAlpha))

    def has_numeric_only(self, text):
        return bool(re.search(r'(.*)[\s]+(\#NUMERIC_ONLY\#)', text))

    def handles_nonbreaking_prefixes(self, text):
        # Splits the text into tokens to check for nonbreaking prefixes.
        tokens = text.split()
        num_tokens = len(tokens)
        for i, token in enumerate(tokens):
            # Checks if token ends with a fullstop.
            token_ends_with_period = re.search(r'^(\S+)\.$', token)
            if token_ends_with_period:
                prefix = token_ends_with_period.group(1)
                # Checks for 3 conditions if
                # i.   the prefix contains a fullstop and
                #      any char in the prefix is within the IsAlpha charset
                # ii.  the prefix is in the list of nonbreaking prefixes and
                #      does not contain #NUMERIC_ONLY#
                # iii. the token is not the last token and that the
                #      next token contains all lowercase.
                if ( ('.' in prefix and self.isalpha(prefix)) or
                     (prefix in self.NONBREAKING_PREFIXES and
                      prefix not in self.NUMERIC_ONLY_PREFIXES) or
                     (i != num_tokens-1 and self.islower(tokens[i+1])) ):
                    pass # No change to the token.
                # Checks if the prefix is in NUMERIC_ONLY_PREFIXES
                # and ensures that the next word is a digit.
                elif (prefix in self.NUMERIC_ONLY_PREFIXES and
                      re.search(r'^[0-9]+', tokens[i+1])):
                    pass # No change to the token.
                else: # Otherwise, adds a space after the tokens before a dot.
                    tokens[i] = prefix + ' .'
        return " ".join(tokens) # Stitch the tokens back.

    def escape_xml(self, text):
        for regexp, substitution in self.MOSES_ESCAPE_XML_REGEXES:
            text = re.sub(regexp, substitution, text)
        return text

    def penn_tokenize(self, text, return_str=False):
        """
        This is a Python port of the Penn treebank tokenizer adapted by the Moses
        machine translation community. It's a little different from the
        version in nltk.tokenize.treebank.
        """
        # Converts input string into unicode.
        text = text_type(text)
        # Perform a chain of regex substituitions using MOSES_PENN_REGEXES_1
        for regexp, substitution in self.MOSES_PENN_REGEXES_1:
            text = re.sub(regexp, substitution, text)
        # Handles nonbreaking prefixes.
        text = self.handles_nonbreaking_prefixes(text)
        # Restore ellipsis, clean extra spaces, escape XML symbols.
        for regexp, substitution in self.MOSES_PENN_REGEXES_2:
            text = re.sub(regexp, substitution, text)
        return text if return_str else text.split()

    def tokenize(self, text, agressive_dash_splits=False, return_str=False):
        """
        Python port of the Moses tokenizer.

        >>> mtokenizer = MosesTokenizer()
        >>> text = u'Is 9.5 or 525,600 my favorite number?'
        >>> print (mtokenizer.tokenize(text, return_str=True))
        Is 9.5 or 525,600 my favorite number ?
        >>> text = u'The https://github.com/jonsafari/tok-tok/blob/master/tok-tok.pl is a website with/and/or slashes and sort of weird : things'
        >>> print (mtokenizer.tokenize(text, return_str=True))
        The https : / / github.com / jonsafari / tok-tok / blob / master / tok-tok.pl is a website with / and / or slashes and sort of weird : things
        >>> text = u'This, is a sentence with weird\xbb symbols\u2026 appearing everywhere\xbf'
        >>> expected = u'This , is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
        >>> assert mtokenizer.tokenize(text, return_str=True) == expected

        :param tokens: A single string, i.e. sentence text.
        :type tokens: str
        :param agressive_dash_splits: Option to trigger dash split rules .
        :type agressive_dash_splits: bool
        """
        # Converts input string into unicode.
        text = text_type(text)

        # De-duplicate spaces and clean ASCII junk
        for regexp, substitution in [self.DEDUPLICATE_SPACE, self.ASCII_JUNK]:
            text = re.sub(regexp, substitution, text)
        # Strips heading and trailing spaces.
        text = text.strip()
        # Separate special characters outside of IsAlnum character set.
        regexp, substitution = self.PAD_NOT_ISALNUM
        text = re.sub(regexp, substitution, text)
        # Aggressively splits dashes
        if agressive_dash_splits:
            regexp, substitution = self.AGGRESSIVE_HYPHEN_SPLIT
            text = re.sub(regexp, substitution, text)
        # Replaces multidots with "DOTDOTMULTI" literal strings.
        text = self.replace_multidots(text)
        # Separate out "," except if within numbers e.g. 5,300
        for regexp, substitution in [self.COMMA_SEPARATE_1, self.COMMA_SEPARATE_2]:
            text = re.sub(regexp, substitution, text)

        # (Language-specific) apostrophe tokenization.
        if self.lang == 'en':
            for regexp, substitution in self.ENGLISH_SPECIFIC_APOSTROPHE:
                 text = re.sub(regexp, substitution, text)
        elif self.lang in ['fr', 'it']:
            for regexp, substitution in self.FR_IT_SPECIFIC_APOSTROPHE:
                text = re.sub(regexp, substitution, text)
        else:
            regexp, substitution = self.NON_SPECIFIC_APOSTROPHE
            text = re.sub(regexp, substitution, text)

        # Handles nonbreaking prefixes.
        text = self.handles_nonbreaking_prefixes(text)
        # Cleans up extraneous spaces.
        regexp, substitution = self.DEDUPLICATE_SPACE
        text = re.sub(regexp,substitution, text).strip()
        # Restore multidots.
        text = self.restore_multidots(text)
        # Escape XML symbols.
        text = self.escape_xml(text)

        return text if return_str else text.split()


class MosesDetokenizer(TokenizerI):
    """
    This is a Python port of the Moses Detokenizer from
    https://github.com/moses-smt/mosesdecoder/blob/master/scripts/tokenizer/detokenizer.perl

    >>> tokenizer = MosesTokenizer()
    >>> text = u'This, is a sentence with weird\xbb symbols\u2026 appearing everywhere\xbf'
    >>> expected_tokenized = u'This , is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
    >>> tokenized_text = tokenizer.tokenize(text, return_str=True)
    >>> tokenized_text == expected_tokenized
    True
    >>> detokenizer = MosesDetokenizer()
    >>> expected_detokenized = u'This, is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
    >>> detokenized_text = detokenizer.detokenize(tokenized_text.split(), return_str=True)
    >>> detokenized_text == expected_detokenized
    True

    >>> from nltk.tokenize.moses import MosesTokenizer, MosesDetokenizer
    >>> t, d = MosesTokenizer(), MosesDetokenizer()
    >>> sent = "This ain't funny. It's actually hillarious, yet double Ls. | [] < > [ ] & You're gonna shake it off? Don't?"
    >>> expected_tokens = [u'This', u'ain', u'&apos;t', u'funny', u'.', u'It', u'&apos;s', u'actually', u'hillarious', u',', u'yet', u'double', u'Ls', u'.', u'&#124;', u'&#91;', u'&#93;', u'&lt;', u'&gt;', u'&#91;', u'&#93;', u'&amp;', u'You', u'&apos;re', u'gonna', u'shake', u'it', u'off', u'?', u'Don', u'&apos;t', u'?']
    >>> expected_detokens = "This ain't funny. It's actually hillarious, yet double Ls. | [] < > [] & You're gonna shake it off? Don't?"
    >>> tokens = t.tokenize(sent)
    >>> tokens == expected_tokens
    True
    >>> detokens = d.detokenize(tokens)
    >>> " ".join(detokens) == expected_detokens
    True
    """
    # Currency Symbols.
    IsAlnum = text_type(''.join(perluniprops.chars('IsAlnum')))
    IsAlpha = text_type(''.join(perluniprops.chars('IsAlpha')))
    IsSc = text_type(''.join(perluniprops.chars('IsSc')))

    AGGRESSIVE_HYPHEN_SPLIT = r' \@\-\@ ', r'-'

    # Merge multiple spaces.
    ONE_SPACE = re.compile(r' {2,}'), ' '

    # Unescape special characters.
    UNESCAPE_FACTOR_SEPARATOR = r'&#124;', r'|'
    UNESCAPE_LEFT_ANGLE_BRACKET = r'&lt;', r'<'
    UNESCAPE_RIGHT_ANGLE_BRACKET = r'&gt;', r'>'
    UNESCAPE_DOUBLE_QUOTE = r'&quot;', r'"'
    UNESCAPE_SINGLE_QUOTE = r"&apos;", r"'"
    UNESCAPE_SYNTAX_NONTERMINAL_LEFT = r'&#91;', r'['
    UNESCAPE_SYNTAX_NONTERMINAL_RIGHT = r'&#93;', r']'
    UNESCAPE_AMPERSAND = r'&amp;', r'&'
    # The legacy regexes are used to support outputs from older Moses versions.
    UNESCAPE_FACTOR_SEPARATOR_LEGACY = r'&bar;', r'|'
    UNESCAPE_SYNTAX_NONTERMINAL_LEFT_LEGACY = r'&bra;', r'['
    UNESCAPE_SYNTAX_NONTERMINAL_RIGHT_LEGACY = r'&ket;', r']'


    MOSES_UNESCAPE_XML_REGEXES = [UNESCAPE_FACTOR_SEPARATOR_LEGACY,
                        UNESCAPE_FACTOR_SEPARATOR, UNESCAPE_LEFT_ANGLE_BRACKET,
                        UNESCAPE_RIGHT_ANGLE_BRACKET,
                        UNESCAPE_SYNTAX_NONTERMINAL_LEFT_LEGACY,
                        UNESCAPE_SYNTAX_NONTERMINAL_RIGHT_LEGACY,
                        UNESCAPE_DOUBLE_QUOTE, UNESCAPE_SINGLE_QUOTE,
                        UNESCAPE_SYNTAX_NONTERMINAL_LEFT,
                        UNESCAPE_SYNTAX_NONTERMINAL_RIGHT, UNESCAPE_AMPERSAND]

    FINNISH_MORPHSET_1 = [u'N', u'n', u'A', u'a', u'\xc4', u'\xe4', u'ssa',
                         u'Ssa', u'ss\xe4', u'Ss\xe4', u'sta', u'st\xe4',
                         u'Sta', u'St\xe4', u'hun', u'Hun', u'hyn', u'Hyn',
                         u'han', u'Han', u'h\xe4n', u'H\xe4n', u'h\xf6n',
                         u'H\xf6n', u'un', u'Un', u'yn', u'Yn', u'an', u'An',
                         u'\xe4n', u'\xc4n', u'\xf6n', u'\xd6n', u'seen',
                         u'Seen', u'lla', u'Lla', u'll\xe4', u'Ll\xe4', u'lta',
                         u'Lta', u'lt\xe4', u'Lt\xe4', u'lle', u'Lle', u'ksi',
                         u'Ksi', u'kse', u'Kse', u'tta', u'Tta', u'ine', u'Ine']

    FINNISH_MORPHSET_2 = [u'ni', u'si', u'mme', u'nne', u'nsa']

    FINNISH_MORPHSET_3 = [u'ko', u'k\xf6', u'han', u'h\xe4n', u'pa', u'p\xe4',
                         u'kaan', u'k\xe4\xe4n', u'kin']

    FINNISH_REGEX = u'^({})({})?({})$'.format(text_type('|'.join(FINNISH_MORPHSET_1)),
                                               text_type('|'.join(FINNISH_MORPHSET_2)),
                                               text_type('|'.join(FINNISH_MORPHSET_3)))


    def __init__(self, lang='en'):
        super(MosesDetokenizer, self).__init__()
        self.lang = lang


    def unescape_xml(self, text):
        for regexp, substitution in self.MOSES_UNESCAPE_XML_REGEXES:
            text = re.sub(regexp, substitution, text)
        return text


    def tokenize(self, tokens, return_str=False):
        """
        Python port of the Moses detokenizer.

        :param tokens: A list of strings, i.e. tokenized text.
        :type tokens: list(str)
        :return: str
        """
        # Convert the list of tokens into a string and pad it with spaces.
        text = u" {} ".format(" ".join(tokens))
        # Converts input string into unicode.
        text = text_type(text)
        # Detokenize the agressive hyphen split.
        regexp, substitution = self.AGGRESSIVE_HYPHEN_SPLIT
        text = re.sub(regexp, substitution, text)
        # Unescape the XML symbols.
        text = self.unescape_xml(text)
        # Keep track of no. of quotation marks.
        quote_counts = {u"'":0 , u'"':0, u"``":0, u"`":0, u"''":0}

        # The *prepend_space* variable is used to control the "effects" of
        # detokenization as the function loops through the list of tokens and
        # changes the *prepend_space* accordingly as it sequentially checks
        # through the language specific and language independent conditions.
        prepend_space = " "
        detokenized_text = ""
        tokens = text.split()
        # Iterate through every token and apply language specific detokenization rule(s).
        for i, token in enumerate(iter(tokens)):
            # Check if the first char is CJK.
            if is_cjk(token[0]):
                # Perform left shift if this is a second consecutive CJK word.
                if i > 0 and is_cjk(token[-1]):
                    detokenized_text += token
                # But do nothing special if this is a CJK word that doesn't follow a CJK word
                else:
                    detokenized_text += prepend_space + token
                prepend_space = " "

            # If it's a currency symbol.
            elif token in self.IsSc:
                # Perform right shift on currency and other random punctuation items
                detokenized_text += prepend_space + token
                prepend_space = ""

            elif re.search(r'^[\,\.\?\!\:\;\\\%\}\]\)]+$', token):
                # In French, these punctuations are prefixed with a non-breakable space.
                if self.lang == 'fr' and re.search(r'^[\?\!\:\;\\\%]$', token):
                    detokenized_text += " "
                # Perform left shift on punctuation items.
                detokenized_text += token
                prepend_space = " "

            elif (self.lang == 'en' and i > 0
                  and re.search(u"^[\'][{}]".format(self.IsAlpha), token)):
                  #and re.search(u'[{}]$'.format(self.IsAlnum), tokens[i-1])):
                # For English, left-shift the contraction.
                detokenized_text += token
                prepend_space = " "

            elif (self.lang == 'cs' and i > 1
                  and re.search(r'^[0-9]+$', tokens[-2]) # If the previous previous token is a number.
                  and re.search(r'^[.,]$', tokens[-1]) # If previous token is a dot.
                  and re.search(r'^[0-9]+$', token)): # If the current token is a number.
                # In Czech, left-shift floats that are decimal numbers.
                detokenized_text += token
                prepend_space = " "

            elif (self.lang in ['fr', 'it'] and i <= len(tokens)-2
                  and re.search(u'[{}][\']$'.format(self.IsAlpha), token)
                  and re.search(u'^[{}]$'.format(self.IsAlpha), tokens[i+1])): # If the next token is alpha.
                # For French and Italian, right-shift the contraction.
                detokenized_text += prepend_space + token
                prepend_space = ""

            elif (self.lang == 'cs' and i <= len(tokens)-3
                  and re.search(u'[{}][\']$'.format(self.IsAlpha), token)
                  and re.search(u'^[-–]$', tokens[i+1])
                  and re.search(u'^li$|^mail.*', tokens[i+2], re.IGNORECASE)): # In Perl, ($words[$i+2] =~ /^li$|^mail.*/i)
                # In Czech, right-shift "-li" and a few Czech dashed words (e.g. e-mail)
                detokenized_text += prepend_space + token + tokens[i+1]
                next(tokens, None) # Advance over the dash
                prepend_space = ""

            # Combine punctuation smartly.
            elif re.search(r'''^[\'\"„“`]+$''', token):
                normalized_quo = token
                if re.search(r'^[„“”]+$', token):
                    normalized_quo = '"'
                quote_counts[normalized_quo] = quote_counts.get(normalized_quo, 0)

                if self.lang == 'cs' and token == u"„":
                    quote_counts[normalized_quo] = 0
                if self.lang == 'cs' and token == u"“":
                    quote_counts[normalized_quo] = 1


                if quote_counts[normalized_quo] % 2 == 0:
                    if (self.lang == 'en' and token == u"'" and i > 0
                        and re.search(r'[s]$', tokens[i-1]) ):
                        # Left shift on single quote for possessives ending
                        # in "s", e.g. "The Jones' house"
                        detokenized_text += token
                        prepend_space = " "
                    else:
                        # Right shift.
                        detokenized_text += prepend_space + token
                        prepend_space = ""
                        quote_counts[normalized_quo] += 1
                else:
                    # Left shift.
                    detokenized_text += token
                    prepend_space = " "
                    quote_counts[normalized_quo] += 1

            elif (self.lang == 'fi' and re.search(r':$', tokens[i-1])
                  and re.search(self.FINNISH_REGEX, token)):
                # Finnish : without intervening space if followed by case suffix
                # EU:N EU:n EU:ssa EU:sta EU:hun EU:iin ...
                detokenized_text += prepend_space + token
                prepend_space = " "

            else:
                detokenized_text += prepend_space + token
                prepend_space = " "

        # Merge multiple spaces.
        regexp, substitution = self.ONE_SPACE
        detokenized_text = re.sub(regexp, substitution, detokenized_text)
        # Removes heading and trailing spaces.
        detokenized_text = detokenized_text.strip()

        return detokenized_text if return_str else detokenized_text.split()

    def detokenize(self, tokens, return_str=False):
        """ Duck-typing the abstract *tokenize()*."""
        return self.tokenize(tokens, return_str)
