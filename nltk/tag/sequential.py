# Natural Language Toolkit: Sequential Backoff Taggers
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
#         Tiago Tresoldi <tresoldi@users.sf.net> (original affix tagger)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes for tagging sentences sequentially, left to right.  The
abastract base class L{SequentialBackoffTagger} serves as the base
class for all the taggers in this module.  Tagging of individual words
is performed by the method L{choose_tag()}, which is defined by
subclasses of L{SequentialBackoffTagger}.  If a tagger is unable to
determine a tag for the specified token, then its I{backoff tagger} is
consulted instead.  Any C{SequentialBackoffTagger} may serve as a
backoff tagger for any other C{SequentialBackoffTagger}.
"""

import re, yaml
from nltk import FreqDist, ConditionalFreqDist
from nltk.tag.api import *
from nltk.tag.util import *
from nltk.internals import deprecated, Deprecated

######################################################################
#{ Abstract Base Classes
######################################################################
class SequentialBackoffTagger(TaggerI):
    """
    An abstract base class for taggers that tags words sequentially,
    left to right.  Tagging of individual words is performed by the
    method L{choose_tag()}, which should be defined by subclasses.  If
    a tagger is unable to determine a tag for the specified token,
    then its backoff tagger is consulted.

    @ivar _taggers: A list of all the taggers that should be tried to
        tag a token (i.e., C{self} and its backoff taggers).
    """
    def __init__(self, backoff=None):
        if backoff is None:
            self._taggers = [self]
        else:
            self._taggers = [self] + backoff._taggers

    def _get_backoff(self):
        if len(self._taggers) < 2: return None
        else: return self._taggers[1]
    backoff = property(_get_backoff, doc='''
        The backoff tagger for this tagger.''')
    
    def tag(self, tokens):
        # docs inherited from TaggerI
        tags = []
        for i in range(len(tokens)):
            tags.append(self.tag_one(tokens, i, tags))
        return zip(tokens, tags)
            
    def tag_one(self, tokens, index, history):
        """
        Determine an appropriate tag for the specified token, and
        return that tag.  If this tagger is unable to determine a tag
        for the specified token, then its backoff tagger is consulted.
        
        @rtype: C{str}
        @type tokens: C{list}
        @param tokens: The list of words that are being tagged.
        @type index: C{int}
        @param index: The index of the word whose tag should be
            returned.
        @type history: C{list} of C{str}
        @param history: A list of the tags for all words before
            C{index}.
        """
        tag = None
        for tagger in self._taggers:
            tag = tagger.choose_tag(tokens, index, history)
            if tag is not None:  break
        return tag
    
    def choose_tag(self, tokens, index, history):
        """
        Decide which tag should be used for the specified token, and
        return that tag.  If this tagger is unable to determine a tag
        for the specified token, return C{None} -- do I{not} consult
        the backoff tagger.  This method should be overridden by
        subclasses of C{SequentialBackoffTagger}.

        @rtype: C{str}
        @type tokens: C{list}
        @param tokens: The list of words that are being tagged.
        @type index: C{int}
        @param index: The index of the word whose tag should be
            returned.
        @type history: C{list} of C{str}
        @param history: A list of the tags for all words before
            C{index}.
        """
        raise AssertionError('SequentialBackoffTagger is an abstract class')

    #////////////////////////////////////////////////////////////
    #{ Deprecated
    
    @deprecated('Use batch_tag instead.')
    def tag_sents(self, sents, verbose=False):
        self.tag_batch(sents, verbose)

class ContextTagger(SequentialBackoffTagger):
    """
    An abstract base class for sequential backoff taggers that choose
    a tag for a token based on the value of its "context".  Different
    subclasses are used to define different contexts.

    A C{ContextTagger} chooses the tag for a token by calculating the
    token's context, and looking up the corresponding tag in a table.
    This table can be constructed manually; or it can be automatically
    constructed based on a training corpus, using the L{train()}
    factory method.
    """
    def __init__(self, context_to_tag, backoff=None):
        """
        @param context_to_tag: A dictionary mapping contexts to tags.
        @param backoff: The backoff tagger that should be used for this tagger.
        """
        SequentialBackoffTagger.__init__(self, backoff)
        if context_to_tag:
            self._context_to_tag = context_to_tag
        else:
            self._context_to_tag = {}

    def context(self, tokens, index, history):
        """
        @return: the context that should be used to look up the tag
            for the specified token; or C{None} if the specified token
            should not be handled by this tagger.
        @rtype: (hashable)
        """
        raise AssertionError('Abstract base class')

    def choose_tag(self, tokens, index, history):
        context = self.context(tokens, index, history)
        return self._context_to_tag.get(context)

    def size(self):
        """
        @return: The number of entries in the table used by this
        tagger to map from contexts to tags.
        """
        return len(self._context_to_tag)

    def __repr__(self):
        return '<%s: size=%d>' % (self.__class__.__name__, self.size())

    def _train(self, tagged_corpus, cutoff=1, verbose=False):
        """
        Initialize this C{ContextTagger}'s L{_context_to_tag} table
        based on the given training data.  In particular, for each
        context C{I{c}} in the training data, set
        C{_context_to_tag[I{c}]} to the most frequent tag for that
        context.  However, exclude any contexts that are already
        tagged perfectly by the backoff tagger(s).

        The old value of C{self._context_to_tag} (if any) is discarded.

        @param tagged_corpus: A tagged corpus.  Each item should be
            a C{list} of C{(word, tag)} tuples.
        @param cutoff: If the most likely tag for a context occurs
            fewer than C{cutoff} times, then exclude it from the
            context-to-tag table for the new tagger.
        """
        token_count = hit_count = 0

        # A context is considered 'useful' if it's not already tagged
        # perfectly by the backoff tagger.
        useful_contexts = set()
        
        # Count how many times each tag occurs in each context.
        fd = ConditionalFreqDist()
        for sentence in tagged_corpus:
            tokens, tags = zip(*sentence)
            for index, (token, tag) in enumerate(sentence):
                # Record the event.
                token_count += 1
                context = self.context(tokens, index, tags[:index])
                if context is None: continue
                fd[context].inc(tag)
                # If the backoff got it wrong, this context is useful:
                if (self.backoff is None or
                    tag != self.backoff.tag_one(tokens, index, tags[:index])):
                    useful_contexts.add(context)

        # Build the context_to_tag table -- for each context, figure
        # out what the most likely tag is.  Only include contexts that
        # we've seen at least `cutoff` times.
        for context in useful_contexts:
            best_tag = fd[context].max()
            hits = fd[context][best_tag]
            if hits > cutoff:
                self._context_to_tag[context] = best_tag
                hit_count += hits

        # Display some stats, if requested.
        if verbose:
            size = len(self._context_to_tag)
            backoff = 100 - (hit_count * 100.0)/ token_count
            pruning = 100 - (size * 100.0) / len(fd.conditions())
            print "[Trained Unigram tagger:",
            print "size=%d, backoff=%.2f%%, pruning=%.2f%%]" % (
                size, backoff, pruning)

######################################################################
#{ Tagger Classes
######################################################################

class DefaultTagger(SequentialBackoffTagger, yaml.YAMLObject):
    """
    A tagger that assigns the same tag to every token.
    """
    yaml_tag = '!nltk.DefaultTagger'
    
    def __init__(self, tag):
        """
        Construct a new tagger that assigns C{tag} to all tokens.
        """
        self._tag = tag
        SequentialBackoffTagger.__init__(self, None)
        
    def choose_tag(self, tokens, index, history):
        return self._tag  # ignore token and history

    def __repr__(self):
        return '<DefaultTagger: tag=%s>' % self._tag
    

class NgramTagger(ContextTagger, yaml.YAMLObject):
    """
    A tagger that chooses a token's tag based on its word string and
    on the preceeding I{n} word's tags.  In particular, a tuple
    C{(tags[i-n:i-1], words[i])} is looked up in a table, and the
    corresponding tag is returned.  N-gram taggers are typically
    trained them on a tagged corpus.
    """
    yaml_tag = '!nltk.NgramTagger'
    
    def __init__(self, n, train=None, model=None, backoff=None,
                 cutoff=1, verbose=False):
        """
        Train a new C{NgramTagger} using the given training data or
        the supplied model.  In particular, construct a new tagger
        whose table maps from each context C{(tag[i-n:i-1], word[i])}
        to the most frequent tag for that context.  But exclude any
        contexts that are already tagged perfectly by the backoff
        tagger.
        
        @param train: A tagged corpus.  Each item should be
            a C{list} of C{(word, tag)} tuples.
        @param backoff: A backoff tagger, to be used by the new
            tagger if it encounters an unknown context.
        @param cutoff: If the most likely tag for a context occurs
            fewer than C{cutoff} times, then exclude it from the
            context-to-tag table for the new tagger.
        """
        self._n = n
        
        if (train and model) or (not train and not model):
            raise ValueError('Must specify either training data or trained model.')
        ContextTagger.__init__(self, model, backoff)
        if train:
            self._train(train, cutoff, verbose)
            
    def context(self, tokens, index, history):
        tag_context = tuple(history[max(0,index-self._n+1):index])
        return (tag_context, tokens[index])


class UnigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string.
    Unigram taggers are typically trained on a tagged corpus.
    """
    yaml_tag = '!nltk.UnigramTagger'

    def __init__(self, train=None, model=None, backoff=None,
                 cutoff=1, verbose=False):
        NgramTagger.__init__(self, 1, train, model, backoff, cutoff, verbose)

    def context(self, tokens, index, history):
        return tokens[index]


class BigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string and on
    the preceeding words' tag.  In particular, a tuple consisting
    of the previous tag and the word is looked up in a table, and
    the corresponding tag is returned.  Bigram taggers are typically
    trained on a tagged corpus.
    """
    yaml_tag = '!nltk.BigramTagger'

    def __init__(self, train=None, model=None, backoff=None,
                 cutoff=1, verbose=False):
        NgramTagger.__init__(self, 2, train, model, backoff, cutoff, verbose)


class TrigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string and on
    the preceeding two words' tags.  In particular, a tuple consisting
    of the previous two tags and the word is looked up in a table, and
    the corresponding tag is returned.  Trigram taggers are typically
    trained them on a tagged corpus.
    """
    yaml_tag = '!nltk.TrigramTagger'

    def __init__(self, train=None, model=None, backoff=None,
                 cutoff=1, verbose=False):
        NgramTagger.__init__(self, 3, train, model, backoff, cutoff, verbose)


class AffixTagger(ContextTagger, yaml.YAMLObject):
    """
    A tagger that chooses a token's tag based on a leading or trailing
    substring of its word string.  (It is important to note that these
    substrings are not necessarily "true" morphological affixes).  In
    particular, a fixed-length substring of the word is looked up in a
    table, and the corresponding tag is returned.  Affix taggers are
    typically constructed by training them on a tagged corpys; see
    L{train()}.
    """
    yaml_tag = '!nltk.AffixTagger'

    def __init__(self, train=None, model=None, affix_length=-3,
                 min_stem_length=2, backoff=None, cutoff=1, verbose=False):
        """
        Construct a new affix tagger.
        
        @param affix_length: The length of the affixes that should be
            considered during training and tagging.  Use negative
            numbers for suffixes.
        @param min_stem_length: Any words whose length is less than
            C{min_stem_length+abs(affix_length)} will be assigned a
            tag of C{None} by this tagger.
            
        """
        if (train and model) or (not train and not model):
            raise ValueError('Must specify either training data or '
                             'trained model')
        ContextTagger.__init__(self, model, backoff)

        self._affix_length = affix_length
        self._min_word_length = min_stem_length + abs(affix_length)

        if train:
            self._train(train, cutoff, verbose)

    def context(self, tokens, index, history):
        token = tokens[index]
        if len(token) < self._min_word_length:
            return None
        elif self._affix_length > 0:
            return token[:self._affix_length]
        else:
            return token[self._affix_length:]


class RegexpTagger(SequentialBackoffTagger, yaml.YAMLObject):
    """
    A tagger that assigns tags to words based on regular expressions
    over word strings.
    """
    yaml_tag = '!nltk.RegexpTagger'
    def __init__(self, regexps, backoff=None):
        """
        Construct a new regexp tagger.

        @type regexps: C{list} of C{(str, str)}
        @param regexps: A list of C{(regexp, tag)} pairs, each of
            which indicates that a word matching C{regexp} should
            be tagged with C{tag}.  The pairs will be evalutated in
            order.  If none of the regexps match a word, then the
            optional backoff tagger is invoked, else it is
            assigned the tag C{None}.
        """
        self._regexps = regexps
        SequentialBackoffTagger.__init__(self, backoff)

    def choose_tag(self, tokens, index, history):
        for regexp, tag in self._regexps:
            if re.match(regexp, tokens[index]): # ignore history
                return tag
        return None

    def __repr__(self):
        return '<Regexp Tagger: size=%d>' % len(self._regexps)

