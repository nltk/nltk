# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Algorithm: Kiss & Strunk (2006)
# Author: Willy <willy@csse.unimelb.edu.au> (original Python port)
#         Steven Bird <sb@csse.unimelb.edu.au> (additions)
#         Edward Loper <edloper@gradient.cis.upenn.edu> (rewrite)
#         Joel Nothman <jnothman@student.usyd.edu.au> (almost rewrite)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: probability.py 4865 2007-07-11 22:16:07Z edloper $

"""
The Punkt sentence tokenizer.  The algorithm for this tokenizer is
described in Kiss & Strunk (2006)::

  Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
    Boundary Detection.  Computational Linguistics 32: 485-525.
"""

import re, math
from nltk import defaultdict
from api import TokenizerI
from nltk.probability import FreqDist

######################################################################
#{ Orthographic Context Constants
######################################################################
# The following constants are used to describe the orthographic
# contexts in which a word can occur.  BEG=beginning, MID=middle,
# UNK=unknown, UC=uppercase, LC=lowercase, NC=no case.

_ORTHO_BEG_UC    = 1 << 1
"""Orthogaphic context: beginning of a sentence with upper case."""

_ORTHO_MID_UC    = 1 << 2
"""Orthogaphic context: middle of a sentence with upper case."""

_ORTHO_UNK_UC    = 1 << 3
"""Orthogaphic context: unknown position in a sentence with upper case."""

_ORTHO_BEG_LC    = 1 << 4
"""Orthogaphic context: beginning of a sentence with lower case."""

_ORTHO_MID_LC    = 1 << 5
"""Orthogaphic context: middle of a sentence with lower case."""

_ORTHO_UNK_LC    = 1 << 6
"""Orthogaphic context: unknown position in a sentence with lower case."""

_ORTHO_UC = _ORTHO_BEG_UC + _ORTHO_MID_UC + _ORTHO_UNK_UC
"""Orthogaphic context: occurs with upper case."""

_ORTHO_LC = _ORTHO_BEG_LC + _ORTHO_MID_LC + _ORTHO_UNK_LC
"""Orthogaphic context: occurs with lower case."""

_C_BEG = 0
_C_MID = 1
_C_UNK = 2

_C_NC = 0
_C_UC = 1
_C_LC = 2

_ORTHO_MAP = (
        (0, 0, 0),
        (_ORTHO_BEG_UC, _ORTHO_MID_UC, _ORTHO_UNK_UC),
        (_ORTHO_BEG_LC, _ORTHO_MID_LC, _ORTHO_UNK_LC),
)
"""Maps case and sentence position features to the appropriate flag."""

#} (end orthographic context constants)
######################################################################

######################################################################
#{ Augmented token indicies
######################################################################
# Since annotations on each token are stored as elements in a tuple,
# the following are the respective indices for each element stored to
# augment the token.

_I_TOKEN = 0
_I_PARASTART = 1
_I_LINESTART = 2
_I_TYPE = 3
_I_SENTBREAK = 4
_I_ABBR = 5
_I_ELLIPSIS = 6

#} (end augmented token indicies)
######################################################################

######################################################################
#{ Regular expressions for annotation
######################################################################

# Note: [A-Za-z] is approximated by [^\W\d] in the general case.
_ORD_RE = r'-?[\.,]?\d[\d,\.-]*'
_RE_ELLIPSIS = re.compile(r'\.\.+$')
_RE_NUMERIC = re.compile(r'^'+_ORD_RE+'\.?$')
_RE_PERIODS = re.compile(r'\.+$')
_RE_INITIAL = re.compile(r'[^\W\d]\.$', re.UNICODE)
_RE_INITIAL_OR_ORD = re.compile(r'('+_ORD_RE+'|[^\W\d])\.$')
_RE_ALPHA_CHAR = re.compile(r'[^\W\d]', re.UNICODE)
_RE_ALPHA = re.compile(r'[^\W\d]+$', re.UNICODE)

#} (end regular expressions for annotation)
######################################################################

######################################################################
#{ Punkt Word Tokenizer
######################################################################

class PunktWordTokenizer(TokenizerI):
    def tokenize(self, text):
        return punkt_word_tokenize(text)

def punkt_word_tokenize(s):
    """
    Tokenize a string using the rules from the Punkt word tokenizer.
    """
    for (regexp, repl) in _punkt_word_tokenize_regexps:
        s = regexp.sub(repl, s)
    return s.split()

#: A list of (regexp, repl) pairs applied in sequence by
#: L{punkt_word_tokenize}.  The resulting string is split on
#: whitespace.
_punkt_word_tokenize_regexps = [
    # Separate punctuation (except period) from words:
    (re.compile(r'(?=[\(\"\`{\[:;&\#\*@])(.)'), r'\1 '),
    
    (re.compile(r'(.)(?=[?!)\";}\]\*:@\'])'), r'\1 '),
    (re.compile(r'(?=[\)}\]])(.)'), r'\1 '),
    (re.compile(r'(.)(?=[({\[])'), r'\1 '),
    (re.compile(r'((^|\s)\-)(?=[^\-])'), r'\1 '),

    # Treat double-hyphen as one token:
    (re.compile(r'([^-])(\-\-+)([^-])'), r'\1 \2 \3'),
    (re.compile(r'(\s|^)(,)(?=(\S))'), r'\1\2 '),

    # Only separate comma if space follows:
    (re.compile(r'(.)(,)(\s|$)'), r'\1 \2\3'),

    # Combine dots separated by whitespace to be a single token:
    (re.compile(r'\.\s\.\s\.'), r'...'),

    # [xx] why is this one commented out?
    ## Separate "No.6"
    #(re.compile(r'([^\W\d]\.)(\d+)', re.UNICODE), r'\1 \2'),
    
    # Separate words from ellipses
    (re.compile(r'([^\.]|^)(\.{2,})(.?)'), r'\1 \2 \3'),

    (re.compile(r'(^|\s)(\.{2,})([^\.\s])'), r'\1\2 \3'),
    (re.compile(r'([^\.\s])(\.{2,})($|\s)'), r'\1 \2\3'),
    ]

#: Regular expression to find only contexts that include a possible
#: sentence boundary within a given text.
_punkt_period_context_regexp = re.compile(r"""
    \S*                          # some word material
    ([.?!])                      # a potential sentence ending
    (?:
        ([?!)\";}\]\*:@\'({\[])  # either other punctuation
        |
        \s+(\S+)                 # or whitespace and some other token
    )""", re.UNICODE | re.VERBOSE)

######################################################################
#{ Punkt Parameters
######################################################################

class PunktParameters(object):
    """Stores data used to perform sentence boundary detection with punkt."""

    def __init__(self):
        self._abbrev_types = set()
        """A set of word types for known abbreviations."""
        
        self._collocations = set()
        """A set of word type tuples for known common collocations
        where the first word ends in a period.  E.g., ('S.', 'Bach')
        is a common collocation in a text that discusses 'Johann
        S. Bach'.  These count as negative evidence for sentence
        boundaries."""
        
        self._sent_starters = set()
        """A set of word types for words that often appear at the
        beginning of sentences."""
        
        self._ortho_context = defaultdict(int)
        """A dictionary mapping word types to the set of orthographic
        contexts that word type appears in.  Contexts are represented
        by adding orthographic context flags: ..."""

    def clear_abbrevs(self):
        self._abbrev_types = set()

    def remove_abbrev(self, abbr):
        self._abbrev_types.remove(abbr)

    def add_abbrev(self, abbr):
        self._abbrev_types.add(abbr)

    def clear_collocations(self):
        self._collocations = set()

    def add_collocation(self, colloc):
        self._collocations.add(colloc)

    def clear_sent_starters(self):
        self._sent_starters = set()

    def add_sent_starter(self, word):
        self._sent_starters.add(word)

    def add_ortho_context(self, typ, flag):
        self._ortho_context[typ] |= flag


######################################################################
#{ Punkt base class
######################################################################

class _PunktBaseClass(object):
    """
    Includes common components of PunktTrainer and PunktSentenceTokenizer.
    """
    
    def __init__(self):
        self._params = PunktParameters()
        """The collection of parameters that determines the behavior
        of the punkt tokenizer."""

    #////////////////////////////////////////////////////////////
    #{ Helper Functions
    #////////////////////////////////////////////////////////////

    @staticmethod
    def type_of_token(tok):
        """
        Case-normalizes the given token and replaces numbers by
        '##number##'.
        """
        return _RE_NUMERIC.sub('##number##', tok.lower())

    @staticmethod
    def stripped_type(aug_tok, always_strip=False):
        """
        Given an augmented token, strip a final period if the token is
        marked as a sentence break, or if always_strip=True.
        """
        if ((always_strip or aug_tok[_I_SENTBREAK])
            and len(aug_tok[_I_TYPE]) > 1
            and aug_tok[_I_TYPE][-1] == '.'):
            return aug_tok[_I_TYPE][:-1]
        return aug_tok[_I_TYPE]

    @staticmethod
    def is_upper(c):
        assert len(c)==1
        return 'A' <= c <= 'Z'

    @staticmethod
    def is_lower(c):
        assert len(c)==1
        return 'a' <= c <= 'z'

    @staticmethod
    def char_case(c):
        # Not Unicode-compliant!
        assert len(c)==1
        if 'a' <= c <= 'z':
            return _C_LC
        elif 'A' <= c <= 'Z':
            return _C_UC
        return _C_NC

    @staticmethod
    def pair_iter(it):
        """
        Yields pairs of tokens from the given iterator such that each input
        token will appear as the first element in a yielded tuple. The last
        pair will have None as its second element.
        """
        it = iter(it)
        prev = it.next()
        for el in it:
            yield (prev, el)
            prev = el
        yield (prev, None)

    #////////////////////////////////////////////////////////////
    #{ Word tokenization
    #////////////////////////////////////////////////////////////

    def _tokenize_words(self, plaintext):
        """
        Divide the given text into tokens, using the punkt word
        segmentation regular expression, and generate the resulting list
        of tokens augmented as three-tuples with two boolean values for whether
        the given token occurs at the start of a paragraph or a new line,
        respectively.
        """
        parastart = False
        for line in plaintext.split('\n'):
            if line.strip():
                line_toks = iter(punkt_word_tokenize(line))

                yield (line_toks.next(), parastart, True)
                parastart = False

                for t in line_toks:
                    yield (t, False, False)
            else:
                parastart = True

    def _augment_tokens(self, tokens):
        """
        Augments each given token to a format compatible with the output of
        _tokenize_words().
        """
        tokens = iter(tokens)
        first_tok = tokens.next()
        fn = self._get_token_augmenter(first_tok)
        yield fn(first_tok)
        for tok in tokens:
            yield fn(tok)

    def _get_token_augmenter(self, sample_tok):
        if type(sample_tok) != type(()):
            # Assume tokens are plain text
            # No paragraph or line starts can be determined
            return lambda t: (t, False, False)
        elif len(sample_tok) == 3:
            # Assume tokens are (text, parastart, linestart)
            return lambda t: t
        elif len(sample_tok) == 2:
            # Assume tokens are (text, parastart)
            return lambda t: t + (False,)
        else:
            raise ValueError(
                "Tokens should be plain text, or tuples of size 2-3")

    #////////////////////////////////////////////////////////////
    #{ Annotation Procedures
    #////////////////////////////////////////////////////////////

    def _mark_types(self, tokens):
        """
        Augments a token with its type, as determined by type_of_token().
        """
        for t in tokens:
            yield t + (self.type_of_token(t[_I_TOKEN]),)

    def _annotate_first_pass(self, tokens):
        """
        Perform the first pass of annotation, which makes decisions
        based purely based on the word type of each word:
        
          - '?', '!', and '.' are marked as sentence breaks.
          - sequences of two or more periods are marked as ellipsis.
          - any word ending in '.' that's a known abbreviation is
            marked as an abbreviation.
          - any other word ending in '.' is marked as a sentence break.

        Return these annotations as a tuple of three sets:
        
          - sentbreak_toks: The indices of all sentence breaks.
          - abbrev_toks: The indices of all abbreviations.
          - ellipsis_toks: The indices of all ellipsis marks.
        """
        for aug_tok in tokens:
            yield self._first_pass_annotation(aug_tok)

    def _first_pass_annotation(self, aug_tok):
        """
        Performs type-based annotation on a single token.
        """

        tok = aug_tok[_I_TOKEN]

        if tok in ('?','!','.'):
            return aug_tok + (True, False, False) # sentence break
        elif _RE_ELLIPSIS.match(tok):
            return aug_tok + (False, False, True) # ellipsis
        elif tok.endswith('.') and not tok.endswith('..'):
            if (tok[:-1].lower() in self._params._abbrev_types or
                tok[:-1].lower().split('-')[-1] in self._params._abbrev_types):
                return aug_tok + (False, True, False) # abbreviation
            else:
                return aug_tok + (True, False, False) # sentence break

        return aug_tok + (False, False, False)

######################################################################
#{ Punkt Trainer
######################################################################


class PunktTrainer(_PunktBaseClass):
    """Learns parameters used in Punkt sentence boundary detection."""

    def __init__(self, train_text=None, verbose=False):
        _PunktBaseClass.__init__(self)

        self._type_fdist = FreqDist()
        """A frequency distribution giving the frequency of each
        case-normalized token type in the training data."""
        
        self._num_period_toks = 0
        """The number of words ending in period in the training data."""
        
        self._collocation_fdist = FreqDist()
        """A frequency distribution giving the frequency of all
        bigrams in the training data where the first word ends in a
        period.  Bigrams are encoded as tuples of word types.
        Especially common collocations are extracted from this
        frequency distribution, and stored in
        L{_params}.L{collocations <PunktParameters._collocations>}."""
        
        self._sent_starter_fdist = FreqDist()
        """A frequency distribution giving the frequency of all words
        that occur at the training data at the beginning of a sentence
        (after the first pass of annotation).  Especially common
        sentence starters are extracted from this frequency
        distribution, and stored in L{_params}.L{_sent_starters
        <PunktParameters._sent_starters>}.
        """

        self._sentbreak_count = 0
        """The total number of sentence breaks identified in training, used for
        calculating the frequent sentence starter heuristic."""

        self._finalized = True
        """A flag as to whether the training has been finalized by finding
        collocations and sentence starters, or whether finalize_training()
        still needs to be called."""

        if train_text:
            self.train(train_text, verbose, finalize=True)

    def get_params(self):
        """
        Calculates and returns parameters for sentence boundary detection as
        derived from training."""
        if not self._finalized:
            self.finalize_training()
        return self._params

    #////////////////////////////////////////////////////////////
    #{ Customization Variables
    #////////////////////////////////////////////////////////////

    ABBREV = 0.3
    """cut-off value whether a 'token' is an abbreviation"""

    ABBREV_BACKOFF = 5
    """upper cut-off for Mikheev's(2002) abbreviation detection algorithm"""

    COLLOCATION = 7.88
    """minimal log-likelihood value that two tokens need to be considered
    as a collocation"""

    SENT_STARTER = 30
    """minimal log-likelihood value that a token requires to be considered
    as a frequent sentence starter"""

    INTERNAL_PUNCTUATION = ',:;' # might want to extend this..
    """sentence internal punctuation, which indicates an abbreviation if
    preceded by a period-final token."""

    INCLUDE_ALL_COLLOCS = False
    """this includes as potential collocations all word pairs where the first
    word ends in a period. It may be useful in corpora where there is a lot
    of variation that makes abbreviations like Mr difficult to identify."""
    
    INCLUDE_ABBREV_COLLOCS = False
    """this includes as potential collocations all word pairs where the first
    word is an abbreviation. Such collocations override the orthographic
    heuristic, but not the sentence starter heuristic. This is overridden by
    INCLUDE_ALL_COLLOCS, and if both are false, only collocations with initials
    and ordinals are considered."""
    """"""

    MIN_COLLOC_FREQ = 1
    """this sets a minimum bound on the number of times a bigram needs to
    appear before it can be considered a collocation, in addition to log
    likelihood statistics. This is useful when INCLUDE_ALL_COLLOCS is True."""

    #////////////////////////////////////////////////////////////
    #{ Training..
    #////////////////////////////////////////////////////////////

    def train(self, text, verbose=False, finalize=True):
        """
        Collects training data from a given text. If finalize is True, it
        will determine all the parameters for sentence boundary detection. If
        not, this will be delayed until get_params() or finalize_training() is
        called. If verbose is True, abbreviations found will be listed.
        """
        # Break the text into tokens; record which token indices correspond to
        # line starts and paragraph starts; and determine their types.
        self._train_tokens(self._tokenize_words(text), verbose)
        if finalize:
            self.finalize_training(verbose)

    def train_tokens(self, tokens, verbose=False, finalize=True):
        """
        Collects training data from a given list of tokens.
        """
        self._train_tokens(self._augment_tokens(tokens), verbose)
        if finalize:
            self.finalize_training(verbose)

    def _train_tokens(self, tokens, verbose):
        self._finalized = False

        # Ensure tokens are a list
        tokens = list(self._mark_types(tokens))

        # Find the frequency of each case-normalized type.  (Don't
        # strip off final periods.)  Also keep track of the number of
        # tokens that end in periods.
        for aug_tok in tokens:
            self._type_fdist.inc(aug_tok[_I_TYPE])
            if aug_tok[_I_TOKEN].endswith('.'):
                self._num_period_toks += 1

        # Look for new abbreviations, and for types that no longer are
        unique_types = self._unique_types(tokens)
        for abbr, score, is_add in self._reclassify_abbrev_types(unique_types):
            if score >= self.ABBREV:
                if is_add:
                    self._params.add_abbrev(abbr)
                    if verbose:
                        print ('  Abbreviation: [%6.4f] %s' %
                               (score, abbr))
            else:
                if not is_add:
                    self._params.remove_abbrev(abbr)
                    if verbose:
                        print ('  Removed abbreviation: [%6.4f] %s' %
                               (score, abbr))

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        tokens = list(self._annotate_first_pass(tokens))

        # Check what contexts each word type can appear in, given the
        # case of its first letter.
        self._get_orthography_data(tokens)

        # We need total number of sentence breaks to find sentence starters
        self._sentbreak_count += self._get_sentbreak_count(tokens)

        # The remaining heuristics relate to pairs of tokens where the first
        # ends in a period.
        for aug_tok1, aug_tok2 in self.pair_iter(tokens):
            if not aug_tok1[_I_TOKEN].endswith('.') or not aug_tok2:
                continue

            # Is the first token a rare abbreviation?
            if self._is_rare_abbrev_type(aug_tok1, aug_tok2):
                self._params._abbrev_types.add(
                    self.stripped_type(aug_tok1, True))
                if verbose:
                    print ('  Rare Abbrev: %s' % aug_tok1[_I_TYPE])

            # Does second token have a high likelihood of starting a sentence?
            if self._is_potential_sent_starter(aug_tok2, aug_tok1):
                self._sent_starter_fdist.inc(aug_tok2[_I_TYPE])

            # Is this bigram a potential collocation?
            if self._is_potential_collocation(aug_tok1, aug_tok2):
                self._collocation_fdist.inc(
                    (self.stripped_type(aug_tok1, True),
                     self.stripped_type(aug_tok2)))

    def _unique_types(self, tokens):
        return set(aug_tok[_I_TYPE] for aug_tok in tokens)
        
    def finalize_training(self, verbose=False):
        """
        Uses data that has been gathered in training to determine likely
        collocations and sentence starters.
        """
        self._params.clear_sent_starters()
        for typ, ll in self._find_sent_starters():
            self._params.add_sent_starter(typ)
            if verbose:
                print ('  Sent Starter: [%6.4f] %r' % (ll, typ))

        self._params.clear_collocations()
        for (typ1, typ2), ll in self._find_collocations():
            self._params.add_collocation( (typ1,typ2) )
            if verbose:
                print ('  Collocation: [%6.4f] %r+%r' %
                       (ll, typ1, typ2))

        self._finalized = True

    #////////////////////////////////////////////////////////////
    #{ Overhead reduction
    #////////////////////////////////////////////////////////////

    def freq_threshold(self, ortho_thresh=2, type_thresh=2, colloc_thres=2,
            sentstart_thresh=2):
        """
        Allows memory use to be reduced after much training by removing data
        about rare tokens that are unlikely to have a statistical effect with
        further training. Entries occurring above the given thresholds will be
        retained.
        """
        if ortho_thresh > 1:
            for tok, count in self._type_fdist.iteritems():
                if count < ortho_thresh:
                    try:
                        del self._params._ortho_context[tok]
                    except KeyError:
                        pass

        self._type_fdist = self._freq_threshold(self._type_fdist, type_thresh)
        self._collocation_fdist = self._freq_threshold(
                self._collocation_fdist, colloc_thres)
        self._sent_starter_fdist = self._freq_threshold(
                self._sent_starter_fdist, sentstart_thresh)

    def _freq_threshold(self, fdist, threshold):
        """
        Returns a FreqDist containing only data with counts below a given
        threshold, as well as a mapping (None -> count_removed).
        """
        # We assume that there is more data below the threshold than above it
        # and so create a new FreqDist rather than working in place.
        res = FreqDist()
        num_removed = 0
        for tok, count in fdist.iteritems():
            if count < threshold:
                num_removed += 1
            else:
                res.inc(tok, count)
        res.inc(None, num_removed)
        return res

    #////////////////////////////////////////////////////////////
    #{ Orthographic data
    #////////////////////////////////////////////////////////////

    def _get_orthography_data(self, tokens):
        """
        Collect information about whether each token type occurs
        with different case patterns (i) overall, (ii) at
        sentence-initial positions, and (iii) at sentence-internal
        positions.
        """
        # 'initial' or 'internal' or 'unknown'
        context = _C_MID
        tokens = list(tokens)
        
        for aug_tok in tokens:
            # If we encounter a paragraph break, then it's a good sign
            # that it's a sentence break.  But err on the side of
            # caution (by not positing a sentence break) if we just
            # saw an abbreviation.
            if aug_tok[_I_PARASTART] and context != _C_UNK:
                context = _C_BEG

            # If we're at the beginning of a line, then err on the
            # side of calling our context 'initial'.
            if aug_tok[_I_LINESTART] and context == _C_MID:
                context = _C_UNK

            # Find the case-normalized type of the token.  If it's a
            # sentence-final token, strip off the period.
            typ = self.stripped_type(aug_tok)
            token = aug_tok[_I_TOKEN]
            
            # Update the orthographic context table.
            flag = _ORTHO_MAP[self.char_case(token[:1])][context]
            if flag:
                self._params.add_ortho_context(typ, flag)

            # Decide whether the next word is at a sentence boundary.
            if aug_tok[_I_SENTBREAK]:
                if not _RE_INITIAL_OR_ORD.match(token):
                    context = _C_BEG
                else:
                    context = _C_UNK
            elif aug_tok[_I_ELLIPSIS] or aug_tok[_I_ABBR]:
                context = _C_UNK
            else:
                context = _C_MID
        
    #////////////////////////////////////////////////////////////
    #{ Abbreviations
    #////////////////////////////////////////////////////////////

    def _reclassify_abbrev_types(self, types):
        """
        (Re)classifies each given token if
          - it is period-final and not a known abbreviation; or
          - it is not period-final and is otherwise a known abbreviation
        by checking whether its previous classification still holds according
        to the heuristics of section 3.
        Yields triples (abbr, score, is_add) where abbr is the type in question,
        score is its log-likelihood with penalties applied, and is_add specifies
        whether the present type is a candidate for inclusion or exclusion as an
        abbreviation, such that:
          - (is_add and score >= 0.3)    suggests a new abbreviation; and
          - (not is_add and score < 0.3) suggests excluding an abbreviation.
        """
        # (While one could recalculate abbreviations from all .-final tokens at
        # every iteration, in cases requiring efficiency, the number of tokens
        # in the present training document will be much less.)

        for typ in types:
            # Check some basic conditions, to rule out words that are
            # clearly not abbrev_types.
            if not _RE_ALPHA_CHAR.search(typ) or typ == '##number##':
                continue
            
            if typ.endswith('.'):
                if typ in self._params._abbrev_types:
                    continue
                typ = typ[:-1]
                is_add = True
            else:
                if typ not in self._params._abbrev_types:
                    continue
                is_add = False

            # Count how many periods & nonperiods are in the
            # candidate.
            num_periods = typ.count('.') + 1
            num_nonperiods = len(typ) - num_periods + 1
            
            # Let <a> be the candidate without the period, and <b>
            # be the period.  Find a log likelihood ratio that
            # indicates whether <ab> occurs as a single unit (high
            # value of ll), or as two independent units <a> and
            # <b> (low value of ll).
            count_with_period = self._type_fdist[typ + '.']
            count_without_period = self._type_fdist[typ]
            ll = self._dunning_log_likelihood(
                count_with_period + count_without_period,
                self._num_period_toks, count_with_period,
                self._type_fdist.N())

            # Apply three scaling factors to 'tweak' the basic log
            # likelihood ratio:
            #   F_length: long word -> less likely to be an abbrev
            #   F_periods: more periods -> more likely to be an abbrev
            #   F_penalty: penalize occurances w/o a period
            f_length = math.exp(-num_nonperiods)
            f_periods = num_periods
            f_penalty = math.pow(num_nonperiods, -count_without_period)
            score = ll * f_length * f_periods * f_penalty

            yield typ, score, is_add

    def find_abbrev_types(self):
        """
        Recalculates abbreviations given type frequencies, despite no prior
        determination of abbreviations.
        This fails to include abbreviations otherwise found as "rare".
        """
        self._params.clear_abbrevs()
        tokens = (typ for typ in self._type_fdist if typ and typ.endswith('.'))
        for abbr, score, is_add in self._reclassify_abbrev_types(tokens):
            if score >= self.ABBREV:
                self._params.add_abbrev(abbr)

    # This function combines the work done by the original code's
    # functions `count_orthography_context`, `get_orthography_count`,
    # and `get_rare_abbreviations`.
    def _is_rare_abbrev_type(self, cur_tok, next_tok):
        """
        A word type is counted as a rare abbreviation if...
          - it's not already marked as an abbreviation
          - it occurs fewer than ABBREV_BACKOFF times
          - either it is followed by a sentence-internal punctuation
            mark, *or* it is followed by a lower-case word that
            sometimes appears with upper case, but never occurs with
            lower case at the beginning of sentences.
        """
        if cur_tok[_I_ABBR] or not cur_tok[_I_SENTBREAK]:
            return False

        # Find the case-normalized type of the token.  If it's
        # a sentence-final token, strip off the period.
        typ = self.stripped_type(cur_tok)
        
        # Proceed only if the type hasn't been categorized as an
        # abbreviation already, and is sufficiently rare...
        count = self._type_fdist[typ] + self._type_fdist[typ[:-1]]
        if (typ in self._params._abbrev_types or count >= self.ABBREV_BACKOFF):
            return False

        # Record this token as an abbreviation if the next
        # token is a sentence-internal punctuation mark.
        # [XX] :1 or check the whole thing??
        if next_tok[_I_TOKEN][:1] in self.INTERNAL_PUNCTUATION:
            return True

        # Record this type as an abbreviation if the next
        # token...  (i) starts with a lower case letter,
        # (ii) sometimes occurs with an uppercase letter,
        # and (iii) never occus with an uppercase letter
        # sentence-internally.
        # [xx] should the check for (ii) be modified??
        elif self.is_lower(next_tok[_I_TOKEN][:1]):
            typ2 = self.stripped_type(next_tok)
            typ2_ortho_context = self._params._ortho_context[typ2]
            if ( (typ2_ortho_context & _ORTHO_BEG_UC) and
                 not (typ2_ortho_context & _ORTHO_MID_UC) ):
                return True

    #////////////////////////////////////////////////////////////
    #{ Log Likelihoods
    #////////////////////////////////////////////////////////////

    # helper for _reclassify_abbrev_types:
    @staticmethod
    def _dunning_log_likelihood(count_a, count_b, count_ab, N):
        """
        A function that calculates the modified Dunning log-likelihood
        ratio scores for abbreviation candidates.  The details of how
        this works is available in the paper.
        """
        p1 = float(count_b) / N
        p2 = 0.99
        
        null_hypo = (float(count_ab) * math.log(p1) +
                     (count_a - count_ab) * math.log(1.0 - p1))
        alt_hypo  = (float(count_ab) * math.log(p2) +
                     (count_a - count_ab) * math.log(1.0 - p2))
        
        likelihood = null_hypo - alt_hypo
        
        return (-2.0 * likelihood)

    @staticmethod
    def _col_log_likelihood(count_a, count_b, count_ab, N):
        """
        A function that will just compute log-likelihood estimate, in
        the original paper it's decribed in algorithm 6 and 7.

        This *should* be the original Dunning log-likelihood values,
        unlike the previous log_l function where it used modified
        Dunning log-likelihood values
        """
        import math
        
        p = 1.0 * count_b / N
        p1 = 1.0 * count_ab / count_a
        p2 = 1.0 * (count_b - count_ab) / (N - count_a)

        summand1 = (count_ab * math.log(p) +
                    (count_a - count_ab) * math.log(1.0 - p))

        summand2 = ((count_b - count_ab) * math.log(p) +
                    (N - count_a - count_b + count_ab) * math.log(1.0 - p))
    
        if count_a == count_ab:
            summand3 = 0
        else:
            summand3 = (count_ab * math.log(p1) +
                        (count_a - count_ab) * math.log(1.0 - p1))
    
        if count_b == count_ab:
            summand4 = 0
        else:
            summand4 = ((count_b - count_ab) * math.log(p2) +
                        (N - count_a - count_b + count_ab) * math.log(1.0 - p2))
    
        likelihood = summand1 + summand2 - summand3 - summand4
    
        return (-2.0 * likelihood)
    
    #////////////////////////////////////////////////////////////
    #{ Collocation Finder
    #////////////////////////////////////////////////////////////

    def _is_potential_collocation(self, aug_tok1, aug_tok2):
        """
        Returns True if the pair of tokens may form a collocation given
        log-likelihood statistics.
        """
        return ((self.INCLUDE_ALL_COLLOCS or
                (self.INCLUDE_ABBREV_COLLOCS and aug_tok1[_I_ABBR]) or
                (aug_tok1[_I_SENTBREAK] and
                    _RE_INITIAL_OR_ORD.match(aug_tok1[_I_TOKEN])))
                and _RE_ALPHA_CHAR.search(aug_tok2[_I_TYPE]))

    def _find_collocations(self):
        """
        Generates likely collocations and their log-likelihood.
        """
        for types, col_count in self._collocation_fdist.iteritems():
            try:
                typ1, typ2 = types
            except TypeError:
                # types may be None after calling freq_threshold()
                continue
            if typ2 in self._params._sent_starters:
                continue

            typ1_count = self._type_fdist[typ1]+self._type_fdist[typ1+'.']
            typ2_count = self._type_fdist[typ2]+self._type_fdist[typ2+'.']
            if (typ1_count > 1 and typ2_count > 1
                    and self.MIN_COLLOC_FREQ <
                        col_count <= min(typ1_count, typ2_count)):

                ll = self._col_log_likelihood(typ1_count, typ2_count,
                                              col_count, self._type_fdist.N())
                # Filter out the not-so-collocative
                if (ll >= self.COLLOCATION and 
                    (float(self._type_fdist.N())/typ1_count >
                     float(typ2_count)/col_count)):
                    yield (typ1, typ2), ll

    #////////////////////////////////////////////////////////////
    #{ Sentence-Starter Finder
    #////////////////////////////////////////////////////////////

    def _is_potential_sent_starter(self, cur_tok, prev_tok):
        """
        Returns True given a token and the token that preceds it if it
        seems clear that the token is beginning a sentence.
        """
        # If a token (i) is preceeded by a sentece break that is
        # not a potential ordinal number or initial, and (ii) is
        # alphabetic, then it is a a sentence-starter.
        return ( prev_tok[_I_SENTBREAK] and 
             # [xx] different def of ordinals here than in orig.
             (not _RE_INITIAL_OR_ORD.match(prev_tok[_I_TOKEN])) and
             (_RE_ALPHA.match(cur_tok[_I_TOKEN])) )

    def _find_sent_starters(self):
        """
        Uses collocation heuristics for each candidate token to
        determine if it frequently starts sentences.
        """
        for (typ, typ_at_break_count) in self._sent_starter_fdist.iteritems():
            if not typ:
                continue

            typ_count = self._type_fdist[typ]+self._type_fdist[typ+'.']
            if typ_count < typ_at_break_count:
                # needed after freq_threshold
                continue

            ll = self._col_log_likelihood(self._sentbreak_count, typ_count,
                                         typ_at_break_count,
                                          self._type_fdist.N())

            if (ll >= self.SENT_STARTER and
                float(self._type_fdist.N())/self._sentbreak_count >
                float(typ_count)/typ_at_break_count):

                yield typ, ll

    def _get_sentbreak_count(self, tokens):
        """
        Returns the number of sentence breaks marked in a given set of
        augmented tokens.
        """
        return sum(1 for aug_tok in tokens if aug_tok[_I_SENTBREAK])


######################################################################
#{ Punkt Sentence Tokenizer
######################################################################


class PunktSentenceTokenizer(_PunktBaseClass,TokenizerI):
    """
    A sentence tokenizer which uses an unsupervised algorithm to build
    a model for abbreviation words, collocations, and words that start
    sentences; and then uses that model to find sentence boundaries.
    This approach has been shown to work well for many European
    languages.
    """
    def __init__(self, train_text=None, verbose=False):
        """
        train_text can either be the sole training text for this sentence
        boundary detector, or can be a PunktParameters object.
        """
        _PunktBaseClass.__init__(self)
        
        if train_text:
            self._params = self.train(train_text, verbose)

    def train(self, train_text, verbose=False):
        """
        Derives parameters from a given training text, or uses the parameters
        given. Repeated calls to this method destroy previous parameters. For
        incremental training, instantiate a separate PunktTrainer instance.
        """
        if isinstance(train_text, PunktParameters):
            return train_text
        return PunktTrainer(train_text).get_params()        
    
    #////////////////////////////////////////////////////////////
    #{ Tokenization
    #////////////////////////////////////////////////////////////

    def tokenize(self, text):
        """
        Given a text, returns a list of the sentences in that text.
        """
        return list(self.sentences_from_text(text))

    def sentences_from_text(self, text):
        """
        Given a text, generates the sentences in that text by only
        testing candidate sentence breaks.
        """
        last_break = 0
        for match in _punkt_period_context_regexp.finditer(text):
            if self.text_contains_sentbreak(match.group(0)):
                yield text[last_break:match.end(1)]
                if match.group(3):
                    # next sentence starts after whitespace
                    last_break = match.start(3)
                else:
                    # next sentence starts at following punctuation
                    last_break = match.start(2)
        yield text[last_break:]

    def text_contains_sentbreak(self, text):
        """
        Returns True if the given text includes a sentence break.
        """
        for t in self._annotate_tokens(self._tokenize_words(text)):
            if t[_I_SENTBREAK]:
                return True
        return False
   
    def sentences_from_text_legacy(self, text):
        """
        Given a text, generates the sentences in that text.
        """
        tokens = self._annotate_tokens(self._tokenize_words(text))
        return self._build_sentence_list(text, tokens)

    def sentences_from_tokens(self, tokens):
        """
        Given a set of tokens, generates lists of tokens, each list
        corresponding to a sentence.
        """
        tokens = iter(self._annotate_tokens(self._augment_tokens(tokens)))
        sentence = []
        for aug_tok in tokens:
            sentence.append(aug_tok[_I_TOKEN])
            if aug_tok[_I_SENTBREAK]:
                yield sentence
                sentence = []
        if sentence:
            yield sentence
            
    def _annotate_tokens(self, tokens):
        """
        Given a set of tokens augmented with markers for line-start and
        paragraph-start, returns an iterator through those tokens with full
        annotation including predicted sentence breaks.
        """
        # Break the text into tokens; and record which token indices
        # correspond to line starts and paragraph starts.
        tokens = self._mark_types(tokens)

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        tokens = self._annotate_first_pass(tokens)

        # Make a second pass through the document, using token context
        # information to change our preliminary decisions about where
        # sentence breaks, abbreviations, and ellipsis occurs.
        tokens = self._annotate_second_pass(tokens)

        ## [XX] TESTING
        #tokens = list(tokens)
        #self.dump(tokens)

        return tokens

    def _build_sentence_list(self, text, tokens):
        """
        Given the original text and the list of augmented word tokens,
        construct and return a tokenized list of sentence strings.
        """
        # Most of the work here is making sure that we put the right
        # pieces of whitespace back in all the right places.

        # Our position in the source text, used to keep track of which
        # whitespace to add:
        pos = 0

        # A regular expression that finds pieces of whitespace:
        WS_REGEXP = re.compile(r'\s*')
        
        sentence = ''
        for aug_tok in tokens:
            tok = aug_tok[_I_TOKEN]

            # Find the whitespace before this token, and update pos.
            ws = WS_REGEXP.match(text, pos).group()
            pos += len(ws)

            # Some of the rules used by the punkt word tokenizer
            # strip whitespace out of the text, resulting in tokens
            # that contain whitespace in the source text.  If our
            # token doesn't match, see if adding whitespace helps.
            # If so, then use the version with whitespace.
            if text[pos:pos+len(tok)] != tok:
                pat = '\s*'.join(re.escape(c) for c in tok)
                m = re.compile(pat).match(text,pos)
                if m: tok = m.group()

            # Move our position pointer to the end of the token.
            assert text[pos:pos+len(tok)] == tok
            pos += len(tok)

            # Add this token.  If it's not at the beginning of the
            # sentence, then include any whitespace that separated it
            # from the previous token.
            if sentence:
                sentence += ws + tok
            else:
                sentence += tok

            # If we're at a sentence break, then start a new sentence.
            if aug_tok[_I_SENTBREAK]:
                yield sentence
                sentence = ''

        # If the last sentence is emtpy, discard it.
        if sentence:
            yield sentence

    # [XX] TESTING
    def dump(self, tokens):
        print 'writing to /tmp/punkt.new...'
        out = open('/tmp/punkt.new', 'w')
        for aug_tok in tokens:
            if aug_tok[_I_PARASTART]:
                out.write('\n\n')
            elif aug_tok[_I_LINESTART]:
                out.write('\n')
            else:
                out.write(' ')

            out.write(aug_tok[_I_TOKEN])
            if aug_tok[_I_ABBR]: out.write('<A>')
            if aug_tok[_I_ELLIPSIS]: out.write('<E>')
            if aug_tok[_I_SENTBREAK]: out.write('<S>')
        out.close()

    #////////////////////////////////////////////////////////////
    #{ Customization Variables
    #////////////////////////////////////////////////////////////

    PUNCTUATION = tuple(';:,.!?')

    #////////////////////////////////////////////////////////////
    #{ Annotation Procedures
    #////////////////////////////////////////////////////////////

    def _annotate_second_pass(self, tokens):
        """
        Performs a token-based classification (section 4) over the given
        tokens, making use of the orthographic heuristic (4.1.1), collocation
        heuristic (4.1.2) and frequent sentence starter heuristic (4.1.3).
        """
        for t1, t2 in self.pair_iter(tokens):
            yield self._second_pass_annotation(t1, t2)

    def _second_pass_annotation(self, aug_tok1, aug_tok2):
        """
        Performs token-based classification over a pair of contiguous tokens
        returning an updated augmented token for the first of them.
        """
        # Is it the last token? We can't do anything then.
        if not aug_tok2:
            return aug_tok1

        tok = aug_tok1[_I_TOKEN]
        if not tok.endswith('.'):
            # We only care about words ending in periods.
            return aug_tok1

        typ = aug_tok1[_I_TYPE]
        next_tok = aug_tok2[_I_TOKEN]
        next_typ = self.stripped_type(aug_tok2)
        tok_is_initial = _RE_INITIAL.match(tok)

        # [4.1.2. Collocational Heuristic] If there's a
        # collocation between the word before and after the
        # period, then label tok as an abbreviation and NOT
        # a sentence break. Note that collocations with
        # frequent sentence starters as their second word are
        # excluded in training.
        if (typ, next_typ) in self._params._collocations:
            return aug_tok1[:_I_SENTBREAK] + (False, True) + aug_tok1[_I_ABBR+1:]

        # [4.2. Token-Based Reclassification of Abbreviations] If
        # the token is an abbreviation or an ellipsis, then decide
        # whether we should *also* classify it as a sentbreak.
        if ( (aug_tok1[_I_ABBR] or aug_tok1[_I_ELLIPSIS]) and
             (not tok_is_initial) ):
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(next_tok, next_typ)
            if is_sent_starter == True:
                return aug_tok1[:_I_SENTBREAK] + (True,) + aug_tok1[_I_SENTBREAK+1:]

            # [4.1.3. Frequent Sentence Starter Heruistic] If the
            # next word is capitalized, and is a member of the
            # frequent-sentence-starters list, then label tok as a
            # sentence break.
            if ( self.is_upper(next_tok[:1]) and
                 next_typ in self._params._sent_starters):
                return aug_tok1[:_I_SENTBREAK] + (True,) + aug_tok1[_I_SENTBREAK+1:]

        # [4.3. Token-Based Detection of Initials and Ordinals]
        # Check if any initials or ordinals tokens that are marked
        # as sentbreaks should be reclassified as abbreviations.
        if tok_is_initial or typ == '##number##':
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(next_tok, next_typ)
            if is_sent_starter == False:
                return aug_tok1[:_I_SENTBREAK] + (False, True) + aug_tok1[_I_ABBR+1:]

            # Special heuristic for initials: if orthogrpahic
            # heuristc is unknown, and next word is always
            # capitalized, then mark as abbrev (eg: J. Bach).
            if ( is_sent_starter == 'unknown' and tok_is_initial and
                 self.is_upper(next_tok[:1]) and
                 not (self._params._ortho_context[next_typ] & _ORTHO_UC) ):
                return aug_tok1[:_I_SENTBREAK] + (False, True) + aug_tok1[_I_ABBR+1:]

        return aug_tok1

    def _ortho_heuristic(self, tok, typ):
        """
        Decide whether the given token is the first token in a sentence.
        """
        # Sentences don't start with punctuation marks:
        if tok in self.PUNCTUATION:
            return False

        ortho_context = self._params._ortho_context[typ]

        # If the word is capitalized, occurs at least once with a
        # lower case first letter, and never occurs with an upper case
        # first letter sentence-internally, then it's a sentence starter.
        if ( self.is_upper(tok[:1]) and
             (ortho_context & _ORTHO_LC) and
             not (ortho_context & _ORTHO_MID_UC) ):
            return True

        # If the word is lower case, and either (a) we've seen it used
        # with upper case, or (b) we've never seen it used
        # sentence-initially with lower case, then it's not a sentence
        # starter.
        if ( self.is_lower(tok[:1]) and
             ((ortho_context & _ORTHO_UC) or
              not (ortho_context & _ORTHO_BEG_LC)) ):
            return False

        # Otherwise, we're not sure.
        return 'unknown'

