# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Algorithm: Kiss & Strunk (2006)
# Author: Willy <willy@csse.unimelb.edu.au> (original Python port)
#         Steven Bird <sb@csse.unimelb.edu.au> (additions)
#         Edward Loper <edloper@gradient.cis.upenn.edu> (rewrite)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id: probability.py 4865 2007-07-11 22:16:07Z edloper $

"""
The Punkt sentence tokenizer.  The algorithm for this tokenizer is
described in Kiss & Strunk (2006)::

  Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
    Boundary Detection.  Computational Linguistics 32: 485-525.

Implementation Notes
====================
Notes I'm keeping as I rework the original code...

Differenes
~~~~~~~~~~
In general, I tried to ensure that my code would generate the same
basic values as the original code, even if it used different methods
or data structures to do so (e.g., stand-off annotation for word
types).  But there were a few places where I chose to differ
substanitively from the original code.  This was usually done either
because the original code appeared to have a bug, or because it
allowed me to simplify the code without (hopefully) affecting the
overall result.  Here's a list of substanitive differences:

- in count_orthography_context(), '.?!' are included in a list of
  'word-internal punctuation'.
  
- the original has a bunch of places where it will try to scan the
  next token, but gives up if there's too many intervening newlines.
  The new code doesn't preserve that behavior.
  
- the original code only looked for collocations if the first word
  was (a) tagged as an abbreviation, or (b) a digit or initial.
  In case (a), the collocation heuristic will be redundant -- the
  given word will never be tagged as a sentence boundary by the first
  pass.  I saw no mention of these conditions in the original paper,
  so I replaced them with the simple condition that the first word
  end with a period.

- for rare abbrevs caused by words followed by lowercase letters, the
  code & the comment diagreed in the original file.  I chose to follow
  the code, since I believe that the comment describes a condition
  that will never be true.

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
# UNK=unknown, UC=uppercase, LC=lowercase.

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

#} (end orthographic context constants)
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
    #(re.compile(r'([A-Za-z]\.)(\d+)'), r'\1 \2'),
    
    # Separate words from ellipses
    (re.compile(r'([^\.]|^)(\.{2,})(.?)'), r'\1 \2 \3'),

    (re.compile(r'(^|\s)(\.{2,})([^\.\s])'), r'\1\2 \3'),
    (re.compile(r'([^\.\s])(\.{2,})($|\s)'), r'\1 \2\3'),
    ]

######################################################################
#{ Punkt Sentence Tokenizer
######################################################################

class PunktSentenceTokenizer(TokenizerI):
    """
    A sentence tokenizer which uses an unsupervised algorithm to build
    a model for abbreviation words, collocations, and words that start
    sentences; and then uses that model to find sentence boundaries.
    This approach has been shown to work well for many European
    languages.
    """
    def __init__(self, train_text=None, verbose=False):
        # These are needed for tokenization:
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
        frequency distribution, and stored in L{_collocations}."""
        
        self._sent_starter_fdist = FreqDist()
        """A frequency distribution giving the frequency of all words
        that occur at the training data at the beginning of a sentence
        (after the first pass of annotation).  Especially common
        sentence starters are extracted from this frequency
        distribution, and stored in L{sent_starters}.
        """
        
        if train_text:
            self.train(train_text, verbose)
        
    #////////////////////////////////////////////////////////////
    #{ Tokenization
    #////////////////////////////////////////////////////////////

    def tokenize(self, text):
        sentbreak_toks = set() # words that end a sentence
        abbrev_toks = set()    # abbreviation words
        ellipsis_toks = set()  # ellipsis words
        
        # Break the text into tokens; and record which token indices
        # correspond to line starts and paragraph starts.
        tokens, linestart_toks, parastart_toks = self._tokenize_words(text)

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        self._annotate_first_pass(tokens, sentbreak_toks,
                                  abbrev_toks, ellipsis_toks)

        # Make a second pass through the document, using token context
        # information to change our preliminary decisions about where
        # sentence breaks, abbreviations, and ellipsis occurs.
        self._annotate_second_pass(tokens, sentbreak_toks,
                                   abbrev_toks, ellipsis_toks)

        ## [XX] TESTING
        #self.dump(tokens, abbrev_toks, ellipsis_toks, sentbreak_toks,
        #          parastart_toks, linestart_toks)

        return self._build_sentence_list(text, tokens, sentbreak_toks)

    def _build_sentence_list(self, text, tokens, sentbreak_toks):
        """
        Given the original text, the list of word tokens, and the set
        of indices at which sentence breaks occur, construct and
        return a tokenized list of sentence strings.
        """
        # Most of the work here is making sure that we put the right
        # pieces of whitespace back in all the right places.
        sentences = ['']

        # Our position in the source text, used to keep track of which
        # whitespace to add:
        pos = 0

        # A regular expression that finds pieces of whitespace:
        WS_REGEXP = re.compile(r'\s*')
        
        for i, tok in enumerate(tokens):
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
            if sentences[-1]:
                sentences[-1] += ws + tok
            else:
                sentences[-1] += tok

            # If we're at a sentence break, then start a new sentence.
            if i in sentbreak_toks:
                sentences.append('')

        # If the last sentence is emtpy, discard it.
        if sentences[-1] == '': sentences.pop()
        return sentences

    # [XX] TESTING
    def dump(self, tokens, abbrev_toks, ellipsis_toks, sentbreak_toks,
             parastart_toks, linestart_toks):
        print 'writing to /tmp/punkt.new...'
        out = open('/tmp/punkt.new', 'w')
        for i, tok in enumerate(tokens):
            out.write(tok)
            if i in abbrev_toks: out.write('<A>')
            if i in ellipsis_toks: out.write('<E>')
            if i in sentbreak_toks: out.write('<S>')
            if i+1 in parastart_toks:
                out.write('\n\n')
            elif i+1 in linestart_toks:
                out.write('\n')
            elif i<(len(tokens)-1):
                out.write(' ')
        out.close()

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

    PUNCTUATION = tuple(';:,.!?')
    INTERNAL_PUNCTUATION = tuple(',:;') # might want to extend this..

    INCLUDE_ABBREV_COLLOCS = False
    """Determines whether the tokenizer will keep track of
    collocations whose first token is already a known (non-initial)
    abbreviation.  It should be safe to set this to False, because the
    decision algorithm currently only uses collocations when looking
    at initial tokens (e.g., 'B.').  But the original code did find
    collocations for abbreviations.. who knows why."""

    #////////////////////////////////////////////////////////////
    #{ Helper Functions
    #////////////////////////////////////////////////////////////

    @staticmethod
    def type_of_token(tok, strip_final_period):
        tok = re.sub(r'^\d+\.?$', '##number##', tok.lower())
        if strip_final_period and len(tok)>1 and tok[-1]=='.':
            return tok[:-1]
        else:
            return tok

    @staticmethod
    def is_upper(c):
        assert len(c)==1
        return 'A' <= c <= 'Z'

    @staticmethod
    def is_lower(c):
        assert len(c)==1
        return 'a' <= c <= 'z'

        
    #////////////////////////////////////////////////////////////
    #{ Word tokenization
    #////////////////////////////////////////////////////////////

    def _tokenize_words(self, plaintext):
        """
        Divide the given text into tokens, using the punkt word
        segmentation regular expression, and return the resulting list
        of tokens.  Also return two sets, C{linestart_toks} and
        C{parastart_toks}, specifying the indices of tokens that occur at
        the start of lines and paragraphs, respectively.
        """
        parastart_toks = set()
        linestart_toks = set()
        tokens = []
        for line in plaintext.split('\n'):
            linestart_toks.add(len(tokens))
            if line.strip():
                tokens += punkt_word_tokenize(line)
            else:
                parastart_toks.add(len(tokens))

        return tokens, linestart_toks, parastart_toks

    #////////////////////////////////////////////////////////////
    #{ Annotation Procedures
    #////////////////////////////////////////////////////////////

    def _annotate_first_pass(self, tokens, sentbreak_toks,
                             abbrev_toks, ellipsis_toks):
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
        for i, tok in enumerate(tokens):
            if tok in ('?','!','.'):
                sentbreak_toks.add(i)
            elif re.match('\.\.+$', tok):
                ellipsis_toks.add(i)
            elif tok.endswith('.') and not tok.endswith('..'):
                if (tok[:-1].lower() in self._abbrev_types or
                    tok[:-1].lower().split('-')[-1] in self._abbrev_types):
                    abbrev_toks.add(i)
                else:
                    sentbreak_toks.add(i)

    def _annotate_second_pass(self, tokens, sentbreak_toks,
                              abbrev_toks, ellipsis_toks):
        
        for i in range(len(tokens)-1):
            tok, next_tok = tokens[i], tokens[i+1]
            typ = self.type_of_token(tok, False)
            next_typ = self.type_of_token(next_tok, (i+1 in sentbreak_toks))
            tok_is_initial = re.match(r'[A-Za-z]\.$', tokens[i])

            if not tok.endswith('.'):
                continue # we only care about words ending in periods.

            # [4.2. Token-Based Reclassification of Abbreviations] If
            # the token is an abbreviation or an ellipsis, then decide
            # whether we should *also* classify it as a sentbreak.
            if ( (i in abbrev_toks or i in ellipsis_toks) and
                 (not tok_is_initial) ):
                # [4.1.1. Orthographic Heuristic] Check if there's
                # orthogrpahic evidence about whether the next word
                # starts a sentence or not.
                is_sent_starter = self._ortho_heuristic(next_tok, next_typ)
                if is_sent_starter == True:
                    sentbreak_toks.add(i)

                # [4.1.3. Frequent Sentence Starter Heruistic] If the
                # next word is capitalized, and is a member of the
                # frequent-sentence-starters list, then label tok as a
                # sentence break.
                if ( self.is_upper(next_tok[:1]) and
                     next_typ in self._sent_starters):
                    sentbreak_toks.add(i)

            # [4.3. Token-Based Detection of Initials and Ordinals]
            # Check if any initials or ordinals tokens that are marked
            # as sentbreaks should be reclassified as abbreviations.
            if tok_is_initial or typ == '##number##':
                # [4.1.2. Collocational Heuristic] If there's a
                # collocation between the word before and after the
                # period, and the next word is *not* a frequent
                # sentence starter, then label tok as an abbreviation.
                if ( ((typ, next_typ) in self._collocations) and
                     not (self.is_upper(next_tok[:1]) and
                          next_typ in self._sent_starters) ):
                    sentbreak_toks.discard(i)
                    abbrev_toks.add(i)

                # [4.1.1. Orthographic Heuristic] Check if there's
                # orthogrpahic evidence about whether the next word
                # starts a sentence or not.
                is_sent_starter = self._ortho_heuristic(next_tok, next_typ)
                if is_sent_starter == False:
                    sentbreak_toks.discard(i)
                    abbrev_toks.add(i)

                # Special heuristic for initials: if orthogrpahic
                # heuristc is unknown, and next word is always
                # capitalized, then mark as abbrev (eg: J. Bach).
                if ( is_sent_starter == 'unknown' and tok_is_initial and
                     self.is_upper(next_tok[:1]) and
                     not (self._ortho_context[next_typ] & _ORTHO_UC) ):
                    sentbreak_toks.discard(i)
                    abbrev_toks.add(i)

    def _ortho_heuristic(self, tok, typ):
        """
        Decide whether the given token is the first token in a sentence.
        """
        # Sentences don't start with punctuation marks:
        if tok in self.PUNCTUATION:
            return False

        ortho_context = self._ortho_context[typ]

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

    #////////////////////////////////////////////////////////////
    #{ Training..
    #////////////////////////////////////////////////////////////

    def freeze(self):
        """
        Reduce the memory requirements of this tokenizer by discarding
        all data structures that are only needed for incremental
        training.  After a tokenizer has been frozen, it can not be
        incrementally trained on new data.
        """
        self._type_fdist = None
        self._num_period_toks = None
        self._collocation_fdist = None
        self._sent_starter_fdist = None

    def train(self, text, verbose=False):
        if self._type_fdist is None:
            raise ValueError("This Punkt tokenizer has been 'frozen', which "
                             "prevents any further training.")
        
        # our annotations on the training data:
        sentbreak_toks = set() # words that end a sentence
        abbrev_toks = set()    # abbreviation words
        ellipsis_toks = set()  # ellipsis words
        
        # Break the text into tokens; and record which token indices
        # correspond to line starts and paragraph starts.
        tokens, linestart_toks, parastart_toks = self._tokenize_words(text)

        # Find the frequency of each case-normalized type.  (Don't
        # strip off final periods.)  Also keep track of the number of
        # tokens that end in periods.
        for tok in tokens:
            self._type_fdist.inc(self.type_of_token(tok,False))
            if tok.endswith('.'):
                self._num_period_toks += 1
        
        # Construct a list of abbreviations
        self._find_abbrev_types(verbose)

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        self._annotate_first_pass(tokens, sentbreak_toks,
                                 abbrev_toks, ellipsis_toks)

        # Check what contexts each word type can appear in, given the
        # case of its first letter.
        self._get_orthography_data(tokens, parastart_toks, linestart_toks,
                                   sentbreak_toks, abbrev_toks, ellipsis_toks)

        # Look for rare abbreviations, and add them to our list of abbrevs
        self._find_rare_abbrev_types(tokens, sentbreak_toks,
                                     abbrev_toks, verbose)
        
        # Find a list of bigram collocations whose first word ends in
        # a period -- these do *not* indicate sentence boundaries.
        self._count_collocations(tokens, abbrev_toks, sentbreak_toks)
        self._find_collocations(tokens, abbrev_toks, sentbreak_toks, verbose)

        # Find a list of 'sentence-starter' words, which have a high
        # likelihood of starting new sentences.
        self._count_sent_starters(tokens, sentbreak_toks)
        self._find_sent_starters(tokens, sentbreak_toks, verbose)

    #////////////////////////////////////////////////////////////
    #{ Orthographic data
    #////////////////////////////////////////////////////////////

    def _get_orthography_data(self, tokens, parastart_toks, linestart_toks,
                              sentbreak_toks, abbrev_toks, ellipsis_toks):
        """
        Collect information about whether each token type occurs
        with different case patterns (i) overall, (ii) at
        sentence-initial positions, and (iii) at sentence-internal
        positions.
        """
        # 'initial' or 'internal' or 'unknown'
        context = 'internal'
        
        for i, token in enumerate(tokens):
            # If we encounter a paragraph break, then it's a good sign
            # that it's a sentence break.  But err on the side of
            # caution (by not positing a sentence break) if we just
            # saw an abbreviation.
            if i in parastart_toks and context != 'unknown':
                context = 'initial'

            # If we're at the beginning of a line, then err on the
            # side of calling our context 'initial'.
            if i in linestart_toks and context == 'internal':
                context = 'unknown'

            # Find the case-normalized type of the token.  If it's a
            # sentence-final token, strip off the period.
            typ = self.type_of_token(token, (i in sentbreak_toks))
            
            # Update the orthographic context table.
            if self.is_upper(token[:1]) and context=='initial':
                self._ortho_context[typ] |= _ORTHO_BEG_UC
            elif self.is_upper(token[:1]) and context=='internal':
                self._ortho_context[typ] |= _ORTHO_MID_UC
            elif self.is_upper(token[:1]) and context=='unknown':
                self._ortho_context[typ] |= _ORTHO_UNK_UC
            elif self.is_lower(token[:1]) and context=='initial':
                self._ortho_context[typ] |= _ORTHO_BEG_LC
            elif self.is_lower(token[:1]) and context=='internal':
                self._ortho_context[typ] |= _ORTHO_MID_LC
            elif self.is_lower(token[:1]) and context=='unknown':
                self._ortho_context[typ] |= _ORTHO_UNK_LC

            # Decide whether the next word is at a sentence boundary.
            if i in sentbreak_toks:
                if not re.match(r'([0-9,\.-]+|[A-Za-z])\.$', token):
                    context = 'initial'
                else:
                    context = 'unknown'
            elif i in ellipsis_toks or i in abbrev_toks:
                context = 'unknown'
            else:
                context = 'internal'
        
    #////////////////////////////////////////////////////////////
    #{ Abbreviations
    #////////////////////////////////////////////////////////////

    def _find_abbrev_types(self, verbose):
        # Reset the list of abbreviations.
        self._abbrev_types = set()

        candidates = self._type_fdist
        if verbose: candidates = sorted(candidates)
            
        for candidate in candidates:
            # Check some basic conditions, to rule out words that are
            # clearly not abbrev_types.
            if not ( re.search(r'[A-Za-z]', candidate) and  # rule 1
                     candidate.endswith('.') and            # rule 2
                     not re.match(r'\d+\.$', candidate) and # rule 3
                     not re.match(r'\.+$', candidate) ):    # rule 4
                continue

            # Count how many periods & nonperiods are in the
            # candidate.
            num_periods = candidate.count('.')
            num_nonperiods = len(candidate) - num_periods
            
            # Let <a> be the candidate without the period, and <b>
            # be the period.  Find a log likelihood ration that
            # indicates whether <ab> occurs as a single unit (high
            # value of ll), or as two independent units <a> and
            # <b> (low value of ll).
            count_with_period = self._type_fdist[candidate]
            count_without_period = self._type_fdist[candidate[:-1]]
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

            if score >= self.ABBREV:
                self._abbrev_types.add(candidate[:-1])
                if verbose:
                    print ('  Abbreviation: [%6.4f] %s' %
                           (score, candidate[:-1]))

    # This function combines the work done by the original code's
    # functions `count_orthography_context`, `get_orthography_count`,
    # and `get_rare_abbreviations`.
    def _find_rare_abbrev_types(self, tokens, sentbreak_toks,
                                abbrev_toks, verbose):
        """
        Add any rare abbreviations to C{self._abbrev_types}.  A word
        type is counted as a rare abbreviation if...
          - it's not already marked as an abbreviation
          - it occurs fewer than ABBREV_BACKOFF times
          - either it is followed by a sentence-internal punctuation
            mark, *or* it is followed by a lower-case word that
            sometimes appears with upper case, but never occurs with
            lower case at the beginning of sentences.
        """
        for i in range(len(tokens)-1):
            # If a token contains a sentence-final period, but has not
            # been classified as an abbrevaition...
            if i in sentbreak_toks and i not in abbrev_toks:
                # Find the case-normalized type of the token.  If it's
                # a sentence-final token, strip off the period.
                typ = self.type_of_token(tokens[i], (i in sentbreak_toks))
                
                # If the type hasn't been categorized as an
                # abbreviation already, and is sufficiently rare...
                count = self._type_fdist[typ] + self._type_fdist[typ[:-1]]
                if (typ not in self._abbrev_types and
                    count < self.ABBREV_BACKOFF):
                    # Record this token as an abbreviation if the next
                    # token is a sentence-internal punctuation mark.
                    # [XX] :1 or check the whole thing??
                    if tokens[i+1][:1] in self.INTERNAL_PUNCTUATION:
                        self._abbrev_types.add(typ)
                        print ('  Rare abbrev: %s' % typ)

                    # Record this type as an abbreviation if the next
                    # token...  (i) starts with a lower case letter,
                    # (ii) sometimes occurs with an uppercase letter,
                    # and (iii) never occus with an uppercase letter
                    # sentence-internally.
                    # [xx] should the check for (ii) be modified??
                    elif self.is_lower(tokens[i+1][:1]):
                        typ2 = self.type_of_token(tokens[i+1],
                                                 (i+1 in sentbreak_toks))
                        typ2_ortho_context = self._ortho_context[typ2]
                        if ( (typ2_ortho_context & _ORTHO_BEG_UC) and
                             not (typ2_ortho_context & _ORTHO_MID_UC) ):
                            self._abbrev_types.add(typ)
                            if verbose:
                                print ('  Rare Abbrev: %s' % typ)

    #////////////////////////////////////////////////////////////
    #{ Log Likelihoods
    #////////////////////////////////////////////////////////////

    # helper for _find_abbrev_types:
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

    def _count_collocations(self, tokens, abbrev_toks, sentbreak_toks):
        """
        Update C{self._collocation_fdist} by counting up any
        collocations that occur in the given token list.
        """
        for i in range(len(tokens)-1):
            tok1, tok2 = tokens[i], tokens[i+1]

            # If tok1 is a potential abbreviation...  (if i is already
            # in abbrev_toks, isn't this redundant??)
            if ((self.INCLUDE_ABBREV_COLLOCS and i in abbrev_toks) or
                (i in sentbreak_toks and
                 re.match('(\d+|[A-Z-a-z])\.$', tok1))):
                # Get the types of both tokens.  If typ1 ends in a period,
                # then strip that off.
                typ1 = self.type_of_token(tok1, False)
                typ2 = self.type_of_token(tok2, (i+1 in sentbreak_toks))
                self._collocation_fdist.inc( (typ1,typ2) )
    
    def _find_collocations(self, tokens, abbrev_toks,
                           sentbreak_toks, verbose):
        """
        Return a dictionary mapping collocations to log-likelihoods.
        """
        # Reset the list of collocations:
        self._collocations = set()
        
        for (typ1, typ2), col_count in self._collocation_fdist.items():
            typ1_count = self._type_fdist[typ1]+self._type_fdist[typ1+'.']
            typ2_count = self._type_fdist[typ2]+self._type_fdist[typ2+'.']
            if typ1_count > 1 and typ2_count > 1:
                ll = self._col_log_likelihood(typ1_count, typ2_count,
                                              col_count, self._type_fdist.N())
                # Filter out the not-so-collocative
                if (ll >= self.COLLOCATION and 
                    (float(self._type_fdist.N())/typ1_count >
                     float(typ2_count)/col_count)):
                    self._collocations.add( (typ1,typ2) )
                    if verbose:
                        print ('  Collocation: [%6.4f] %r+%r' %
                               (ll, typ1, typ2))

    #////////////////////////////////////////////////////////////
    #{ Sentence-Starter Finder
    #////////////////////////////////////////////////////////////

    def _count_sent_starters(self, tokens, sentbreak_toks):
        for i in range(1, len(tokens)):
            # If a token (i) is preceeded by a sentece break that is
            # not a potential ordinal number or initial, and (ii) is
            # alphabetic, then add it a a sentence-starter.
            if ( (i-1 in sentbreak_toks) and
                 # [xx] different def of ordinals here than in orig.
                 (not re.match(r'([A-Za-z]|\d+)\.$', tokens[i-1])) and
                 (re.match(r'[A-Za-z]+$', tokens[i])) ):
                typ = self.type_of_token(tokens[i], i in sentbreak_toks)
                self._sent_starter_fdist.inc(typ)

    def _find_sent_starters(self, tokens, sentbreak_toks, verbose):
        # Reset the list of sentence starters:
        self._sent_starters = set()
        
        for (typ, typ_at_sentbreak_count) in self._sent_starter_fdist.items():
            typ_count = self._type_fdist[typ]+self._type_fdist[typ+'.']
            sentbreak_count = len(sentbreak_toks)
            
            ll = self._col_log_likelihood(sentbreak_count, typ_count,
                                         typ_at_sentbreak_count,
                                          self._type_fdist.N())

            if (ll >= self.SENT_STARTER and
                float(self._type_fdist.N())/sentbreak_count >
                float(typ_count)/typ_at_sentbreak_count):
                self._sent_starters.add(typ)
                if verbose:
                    print ('  Sent Starter: [%6.4f] %r' % (ll, typ))

            

               
