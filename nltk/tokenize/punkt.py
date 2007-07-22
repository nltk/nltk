# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2007 University of Pennsylvania
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
from nltk import tokenize, defaultdict
from nltk.probability import FreqDist

class PunktTokenizer:
    """
    @ivar _abbrev_types: A set of word types for known abbreviations.
    @ivar _collocations: A set of word type tuples for known common
        collocations where the first word ends in a period.  E.g.,
        ('S.', 'Bach') is a common collocation in a text that
        discusses 'Johann S. Bach'.  These count as negative evidence
        for sentence boundaries.
    @ivar _sent_starters: A set of word types for words that often
        appear at the beginning of sentences.
    @ivar _upper_contexts: A dictionary mapping word types to the
        set of contexts that word type appears in when capitalized.
        Contexts are: C{'initial'}, C{'internal'}, and C{'unknown'}.
    @ivar _lower_contexts: A dictionary mapping word types to the
        set of contexts that word type appears in when not capitalized.
        Contexts are: C{'initial'}, C{'internal'}, and C{'unknown'}.
    """
    
    def __init__(self, abbrev_types, collocations, sent_starters,
                 upper_contexts, lower_contexts):
        self._abbrev_types = abbrev_types
        self._collocations = collocations
        self._sent_starters = sent_starters
        self._upper_contexts = upper_contexts
        self._lower_contexts = lower_contexts

    def tokenize(self, text):
        sentbreak_toks = set() # words that end a sentence
        abbrev_toks = set()    # abbreviation words
        ellipsis_toks = set()  # ellipsis words
        
        # Break the text into tokens; and record which token indices
        # correspond to line starts and paragraph starts.
        tokens, linestart_toks, parastart_toks = self._tokenize_words(text)

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        self._annotate_first_pass(tokens, self._abbrev_types,
                                 sentbreak_toks, abbrev_toks, ellipsis_toks)

        # Make a second pass through the document, using token context
        # information to change our preliminary decisions about where
        # sentence breaks, abbreviations, and ellipsis occurs.
        self._annotate_second_pass(tokens, self._abbrev_types,
                                  self._collocations, self._sent_starters,
                                  self._upper_contexts, self._lower_contexts,
                                  sentbreak_toks, abbrev_toks, ellipsis_toks)

        ## [XX] TESTING
        #self.dump(tokens, abbrev_toks, ellipsis_toks, sentbreak_toks,
        #          parastart_toks, linestart_toks)

        # Splice the words & whitespace together to form a sentence.
        sentences = ['']
        pos = 0
        WS_REGEXP = re.compile(r'\s*')
        
        for i, tok in enumerate(tokens):
            # Find the whitespace before this token, and update pos.
            ws = WS_REGEXP.match(text, pos).group()
            pos += len(ws) + len(tok)

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
    INTERNAL_PUNCTUATION = tuple(',:;')

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

    @staticmethod
    def _tokenize_words(plaintext):
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
                tokens += tokenize.pword(line)
            else:
                parastart_toks.add(len(tokens))

        return tokens, linestart_toks, parastart_toks

    #////////////////////////////////////////////////////////////
    #{ Annotation Procedures
    #////////////////////////////////////////////////////////////

    @classmethod
    def _annotate_first_pass(cls, tokens, abbrev_types,
                             sentbreak_toks, abbrev_toks, ellipsis_toks):
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
                if (tok[:-1].lower() in abbrev_types or
                    tok[:-1].lower().split('-')[-1] in abbrev_types):
                    abbrev_toks.add(i)
                else:
                    sentbreak_toks.add(i)

    @classmethod
    def _annotate_second_pass(cls, tokens, abbrev_types, 
                              collocations, sent_starters,
                              upper_contexts, lower_contexts,
                              sentbreak_toks, abbrev_toks, ellipsis_toks):
        
        for i in range(len(tokens)-1):
            tok, next_tok = tokens[i], tokens[i+1]
            typ = cls.type_of_token(tok, False)
            next_typ = cls.type_of_token(next_tok, (i+1 in sentbreak_toks))
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
                ortho_heuristic = cls._is_orthographic_sentence_starter(
                    next_tok, next_typ, upper_contexts, lower_contexts)
                if ortho_heuristic == True:
                    sentbreak_toks.add(i)

                # [4.1.3. Frequent Sentence Starter Heruistic] If the
                # next word is capitalized, and is a member of the
                # frequent-sentence-starters list, then label tok as a
                # sentence break.
                if ( cls.is_upper(next_tok[:1]) and
                     next_typ in sent_starters):
                    sentbreak_toks.add(i)

            # [4.3. Token-Based Detection of Initials and Ordinals]
            # Check if any initials or ordinals tokens that are marked
            # as sentbreaks should be reclassified as abbreviations.
            if tok_is_initial or typ == '##number##':
                # [4.1.2. Collocational Heuristic] If there's a
                # collocation between the word before and after the
                # period, and the next word is *not* a frequent
                # sentence starter, then label tok as an abbreviation.
                if ( ((typ, next_typ) in collocations) and
                     not (cls.is_upper(next_tok[:1]) and
                          next_typ in sent_starters) ):
                    sentbreak_toks.discard(i)
                    abbrev_toks.add(i)

                # [4.1.1. Orthographic Heuristic] Check if there's
                # orthogrpahic evidence about whether the next word
                # starts a sentence or not.
                ortho_heuristic = cls._is_orthographic_sentence_starter(
                    next_tok, next_typ, upper_contexts, lower_contexts)
                if ortho_heuristic == False:
                    sentbreak_toks.discard(i)
                    abbrev_toks.add(i)

            # Special heuristic for initials: if orthogrpahic
            # heuristc is unknown, and next word is always
            # capitalized, then mark as abbrev (eg: J. Bach).
            if ( ortho_heuristic == 'unknown' and tok_is_initial and
                 cls.is_upper(next_tok[:1]) and
                 not lower_contexts[next_typ] ):
                sentbreak_toks.discard(i)
                abbrev_toks.add(i)

    @classmethod
    def _is_orthographic_sentence_starter(cls, tok, typ, upper_contexts,
                                         lower_contexts):
        """
        Decide whether the given token is the first token in a sentence.
        """
        # Sentences don't start with punctuation marks:
        if tok in cls.PUNCTUATION:
            return False

        # If the word is capitalized, occurs at least once with a
        # lower case first letter, and never occurs with an upper case
        # first letter sentence-internally, then it's a sentence starter.
        if ( cls.is_upper(tok[:1]) and
             lower_contexts[typ] and
             'internal' not in upper_contexts[typ] ):
            return True

        # If the word is lower case, and either (a) we've seen it used
        # with upper case, or (b) we've never seen it used
        # sentence-initially with lower case, then it's not a sentence
        # starter.
        if ( cls.is_lower(tok[:1]) and
             (upper_contexts[typ] or
              'initial' not in lower_contexts[typ]) ):
            return False

        # Otherwise, we're not sure.
        return 'unknown'

    #////////////////////////////////////////////////////////////
    #{ Training..
    #////////////////////////////////////////////////////////////


    @classmethod
    def train(cls, text, verbose=False):
        # our annotations on the training data:
        sentbreak_toks = set() # words that end a sentence
        abbrev_toks = set()    # abbreviation words
        ellipsis_toks = set()  # ellipsis words
        
        # Break the text into tokens; and record which token indices
        # correspond to line starts and paragraph starts.
        tokens, linestart_toks, parastart_toks = cls._tokenize_words(text)

        # Find the frequency of each case-normalized type.
        type_fdist = FreqDist(cls.type_of_token(t,False) for t in tokens)

        # Construct a list of abbreviations
        abbrev_types, possible_rare_abbrev_types = cls._find_abbrev_types(
            tokens, type_fdist, verbose)

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        cls._annotate_first_pass(tokens, abbrev_types, sentbreak_toks,
                                 abbrev_toks, ellipsis_toks)

        # Check what contexts each word type can appear in, given the
        # case of its first letter.
        upper_contexts, lower_contexts = cls._get_orthography_data(
            tokens, parastart_toks, linestart_toks,
            sentbreak_toks, abbrev_toks, ellipsis_toks)

        # Look for rare abbreviations, and add them to our list of abbrevs
        rare_abbrev_types = cls._get_rare_abbrev_types(
            tokens, sentbreak_toks, abbrev_toks,
            upper_contexts, lower_contexts,
            possible_rare_abbrev_types, verbose)
        abbrev_types.update(rare_abbrev_types)
        
        # Find the frequency of each case-normalized word, ignoring periods.
        baretype_fdist = FreqDist()
        for tok in tokens:
            tok = cls.type_of_token(tok, False)
            baretype_fdist.inc(tok)
            if tok.endswith('.'):
                baretype_fdist.inc(tok[:-1])

        # Find a list of bigram collocations whose first word ends in
        # a period -- these do *not* indicate sentence boundaries.
        collocations = cls._find_collocations(
            tokens, abbrev_toks, sentbreak_toks, baretype_fdist, verbose)

        # Find a list of 'sentence-starter' words, which have a high
        # likelihood of starting new sentences.
        sent_starters = cls._find_sent_starters(
            tokens, sentbreak_toks, baretype_fdist)

        # Build the tokenizer!
        return PunktTokenizer(abbrev_types, collocations, sent_starters,
                              upper_contexts, lower_contexts)

    #////////////////////////////////////////////////////////////
    #{ Orthographic data
    #////////////////////////////////////////////////////////////

    @classmethod
    def _get_orthography_data(cls, tokens, parastart_toks, linestart_toks,
                              sentbreak_toks, abbrev_toks, ellipsis_toks):
        """
        Collect information about whether each token type occurs
        with different case patterns (i) overall, (ii) at
        sentence-initial positions, and (iii) at sentence-internal
        positions.  Return this information as a pair of dictionaries,
        C{upper_contexts} and C{lower_contexts}, mapping each word
        type to a list of contexts that it has been observed in.  This
        set of contexts can include the strings C{'initial'},
        C{'internal'}, and C{'unknown'}.
        """
        # typ -> {'initial', 'internal', 'unknown'}
        upper_contexts = defaultdict(set)
        lower_contexts = defaultdict(set)
        
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
            typ = cls.type_of_token(token, (i in sentbreak_toks))
            
            # Update the case frequency distributions.
            if cls.is_upper(token[:1]):
                upper_contexts[typ].add(context)
            elif cls.is_lower(token[:1]):
                lower_contexts[typ].add(context)

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

        return upper_contexts, lower_contexts
        
    #////////////////////////////////////////////////////////////
    #{ Abbreviations
    #////////////////////////////////////////////////////////////

    @classmethod
    def _find_abbrev_types(cls, tokens, type_fdist, verbose):
        # Count up how many words end with periods.
        num_period_toks = len([t for t in tokens if t.endswith('.')])

        abbrev_types = set()
        possible_rare_abbrev_types = set()

        candidates = type_fdist
        if verbose: candidates = sorted(type_fdist)
            
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
            count_a = (type_fdist[candidate] +
                       type_fdist[candidate[:-1]])
            count_b = num_period_toks
            count_ab = type_fdist[candidate]
            ll = cls._dunning_log_likelihood(count_a, count_b,
                                             count_ab, len(tokens))

            # Apply three scaling factors to 'tweak' the basic log
            # likelihood ratio:
            #   F_length: long word -> less likely to be an abbrev
            #   F_periods: more periods -> more likely to be an abbrev
            #   F_penalty: penalize occurances w/o a period
            f_length = math.exp(-num_nonperiods)
            f_periods = num_periods
            f_penalty = math.pow(num_nonperiods, -type_fdist[candidate[:-1]])
            score = ll * f_length * f_periods * f_penalty

            if score >=cls.ABBREV:
                abbrev_types.add(candidate[:-1])
                if verbose:
                    print ('  Abbreviation: [%6.4f] %s' %
                           (score, candidate[:-1]))
            elif count_a < cls.ABBREV_BACKOFF:
                possible_rare_abbrev_types.add(candidate[:-1])

        # Return the list of abbrev_types.
        return abbrev_types, possible_rare_abbrev_types

    # This function combines the work done by the original code's
    # functions `count_orthography_context`, `get_orthography_count`,
    # and `get_rare_abbreviations`.
    @classmethod
    def _get_rare_abbrev_types(cls, tokens, sentbreak_toks, abbrev_toks,
                               upper_contexts, lower_contexts,
                               possible_rare_abbrev_types, verbose):
        """
        Construct and return a list of rare abbreviations.  A word
        type is counted as a rare abbreviation if...
          - it's not already marked as an abbreviation (already checked)
          - it occurs fewer than ABBREV_BACKOFF times (already checked)
          - either it is followed by a sentence-internal punctuation
            mark, *or* it is followed by a lower-case word that
            sometimes appears with upper case, but never occurs with
            lower case at the beginning of sentences.
        """
        # Set of tokens for whih there is orthographic evidence that
        # they are abbreviations:
        rare_abbrev_types = set()
        
        for i in range(len(tokens)-1):
            # If a token contains a sentence-final period, but has not
            # been classified as an abbrevaition...
            if i in sentbreak_toks and i not in abbrev_toks:
                # Find the case-normalized type of the token.  If it's
                # a sentence-final token, strip off the period.
                typ = cls.type_of_token(tokens[i], (i in sentbreak_toks))
                
                # If the type hasn't been categorized as an
                # abbreviation already, and is sufficiently rare...
                if typ in possible_rare_abbrev_types:
                    # Record this token as an abbreviation if the next
                    # token is a sentence-internal punctuation mark.
                    # [XX] :1 or check the whole thing??
                    if tokens[i+1][:1] in cls.INTERNAL_PUNCTUATION:
                        rare_abbrev_types.add(typ)
                        print ('  Rare abbrev: %s' % typ)

                    # Record this type as an abbreviation if the next
                    # token...  (i) starts with a lower case letter,
                    # (ii) sometimes occurs with an uppercase letter,
                    # and (iii) never occus with an uppercase letter
                    # sentence-internally.
                    # [xx] should the check for (ii) be modified??
                    elif cls.is_lower(tokens[i+1][:1]):
                        typ2 = cls.type_of_token(tokens[i+1],
                                                 (i+1 in sentbreak_toks))
                        if ('initial' in upper_contexts[typ2] and
                            'internal' not in upper_contexts[typ2]):
                            rare_abbrev_types.add(typ)
                            if verbose:
                                print ('  Rare Abbrev: %s' % typ)
                        
        return rare_abbrev_types

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

    @classmethod
    def _find_collocations(cls, tokens, abbrev_toks, sentbreak_toks,
                           baretype_fdist, verbose):
        """
        Return a dictionary mapping collocations to log-likelihoods.
        """
        collocations = set()

        # Count how often each collocation occurs.
        collocation_counts = cls._count_collocations(
            tokens, abbrev_toks, sentbreak_toks).items()
        if verbose: collocation_counts.sort()
        
        for (typ1, typ2), col_count in collocation_counts:
            typ1_count = baretype_fdist[typ1]
            typ2_count = baretype_fdist[typ2]
            if typ1_count > 1 and typ2_count > 1:
                ll = cls._col_log_likelihood(typ1_count, typ2_count,
                                              col_count, len(tokens))
                # Filter out the not-so-collocative
                if (ll >= cls.COLLOCATION and 
                    (float(len(tokens))/typ1_count >
                     float(typ2_count)/col_count)):
                    collocations.add( (typ1,typ2) )
                    if verbose:
                        print ('  Collocation: [%6.4f] %r+%r' %
                               (ll, typ1, typ2))
                    
        return collocations

    @classmethod
    def _count_collocations(cls, tokens, abbrev_toks, sentbreak_toks):
        """
        Return a dictionary mapping word type pairs to counts.
        """
        collocation_counts = defaultdict(int)

        for i in range(len(tokens)-1):
            tok1, tok2 = tokens[i], tokens[i+1]

            # If tok1 is a potential abbreviation...  (if i is already
            # in abbrev_toks, isn't this redundant??)
            if (i in abbrev_toks or (i in sentbreak_toks and
                                     re.match('(\d+|[A-Z-a-z])\.$', tok1))):
                # Get the types of both tokens.  If typ1 ends in a period,
                # then strip that off.
                typ1 = cls.type_of_token(tok1, False)
                typ2 = cls.type_of_token(tok2, (i+1 in sentbreak_toks))
                collocation_counts[typ1,typ2] += 1
                
        return collocation_counts
    
    #////////////////////////////////////////////////////////////
    #{ Sentence-Starter Finder
    #////////////////////////////////////////////////////////////

    @classmethod
    def _find_sent_starters(cls, tokens, sentbreak_toks, baretype_fdist):
        sent_starters = set()
        sentstart_counts = cls._count_sentstarts(tokens, sentbreak_toks)
        
        for (typ, typ_at_sentbreak_count) in sentstart_counts.items():
            typ_count = baretype_fdist[typ]
            sentbreak_count = len(sentbreak_toks)
            
            ll = cls._col_log_likelihood(sentbreak_count, typ_count,
                                          typ_at_sentbreak_count,
                                          len(tokens))

            if (ll >= cls.SENT_STARTER and
                float(len(tokens))/sentbreak_count >
                float(typ_count)/typ_at_sentbreak_count):
                sent_starters.add(typ)
        return sent_starters
            
    @classmethod
    def _count_sentstarts(cls, tokens, sentbreak_toks):
        # Dictionary from typ -> count.
        sentstart_counts = defaultdict(int)
        
        for i in range(1, len(tokens)):
            # If a token (i) is preceeded by a sentece break that is
            # not a potential ordinal number or initial, and (ii) is
            # alphabetic, then add it a a sentence-starter.
            if ( (i-1 in sentbreak_toks) and
                 # [xx] different def of ordinals here than in orig.
                 (not re.match(r'([A-Za-z]|\d+)\.$', tokens[i-1])) and
                 (re.match(r'[A-Za-z]+$', tokens[i])) ):
                typ = cls.type_of_token(tokens[i], i in sentbreak_toks)
                sentstart_counts[typ] += 1

        return sentstart_counts

if __name__ == '__main__':
    from nltk.corpus import treebank
    text = treebank.text()
    tokenizer = PunktTokenizer.train(text, verbose=True)
    sents = tokenizer.tokenize(text)
    for sent in sents[:5]:
        print `sent`
    
            
                    
            

               
