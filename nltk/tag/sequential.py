# Natural Language Toolkit: Sequential Backoff Taggers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
#         Tiago Tresoldi <tresoldi@users.sf.net> (original affix tagger)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Classes for tagging sentences sequentially, left to right.  The
abstract base class L{SequentialBackoffTagger} serves as the base
class for all the taggers in this module.  Tagging of individual words
is performed by the method L{choose_tag()
<SequentialBackoffTagger.choose_tag>}, which is defined by
subclasses of L{SequentialBackoffTagger}.  If a tagger is unable to
determine a tag for the specified token, then its I{backoff tagger} is
consulted instead.  Any C{SequentialBackoffTagger} may serve as a
backoff tagger for any other C{SequentialBackoffTagger}.
"""

import re, yaml

from nltk.probability import FreqDist, ConditionalFreqDist
from nltk.classify.naivebayes import NaiveBayesClassifier

from api import *
from util import *

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


class ContextTagger(SequentialBackoffTagger):
    """
    An abstract base class for sequential backoff taggers that choose
    a tag for a token based on the value of its "context".  Different
    subclasses are used to define different contexts.

    A C{ContextTagger} chooses the tag for a token by calculating the
    token's context, and looking up the corresponding tag in a table.
    This table can be constructed manually; or it can be automatically
    constructed based on a training corpus, using the L{_train()}
    factory method.

    @ivar _context_to_tag: Dictionary mapping contexts to tags.
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

    def _train(self, tagged_corpus, cutoff=0, verbose=False):
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
    trained on a tagged corpus.
    """
    yaml_tag = '!nltk.NgramTagger'
    
    def __init__(self, n, train=None, model=None,
                 backoff=None, cutoff=0, verbose=False):
        """
        Train a new C{NgramTagger} using the given training data or
        the supplied model.  In particular, construct a new tagger
        whose table maps from each context C{(tag[i-n:i-1], word[i])}
        to the most frequent tag for that context.  But exclude any
        contexts that are already tagged perfectly by the backoff
        tagger.
        
        @param train: A tagged corpus consisting of a C{list} of tagged
            sentences, where each sentence is a C{list} of C{(word, tag)} tuples.
        @param backoff: A backoff tagger, to be used by the new
            tagger if it encounters an unknown context.
        @param cutoff: If the most likely tag for a context occurs
            fewer than C{cutoff} times, then exclude it from the
            context-to-tag table for the new tagger.
        """
        self._n = n
        self._check_params(train, model)
        
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

    def __init__(self, train=None, model=None,
                 backoff=None, cutoff=0, verbose=False):
        NgramTagger.__init__(self, 1, train, model,
                             backoff, cutoff, verbose)

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

    def __init__(self, train, model=None,
                 backoff=None, cutoff=0, verbose=False):
        NgramTagger.__init__(self, 2, train, model,
                             backoff, cutoff, verbose)


class TrigramTagger(NgramTagger):
    """
    A tagger that chooses a token's tag based its word string and on
    the preceeding two words' tags.  In particular, a tuple consisting
    of the previous two tags and the word is looked up in a table, and
    the corresponding tag is returned.  Trigram taggers are typically
    trained them on a tagged corpus.
    """
    yaml_tag = '!nltk.TrigramTagger'

    def __init__(self, train=None, model=None,
                 backoff=None, cutoff=0, verbose=False):
        NgramTagger.__init__(self, 3, train, model,
                             backoff, cutoff, verbose)


class AffixTagger(ContextTagger, yaml.YAMLObject):
    """
    A tagger that chooses a token's tag based on a leading or trailing
    substring of its word string.  (It is important to note that these
    substrings are not necessarily "true" morphological affixes).  In
    particular, a fixed-length substring of the word is looked up in a
    table, and the corresponding tag is returned.  Affix taggers are
    typically constructed by training them on a tagged corpus; see
    L{the constructor <__init__>}.
    """
    yaml_tag = '!nltk.AffixTagger'

    def __init__(self, train=None, model=None, affix_length=-3,
                 min_stem_length=2, backoff=None, cutoff=0, verbose=False):
        """
        Construct a new affix tagger.
        
        @param affix_length: The length of the affixes that should be
            considered during training and tagging.  Use negative
            numbers for suffixes.
        @param min_stem_length: Any words whose length is less than
            C{min_stem_length+abs(affix_length)} will be assigned a
            tag of C{None} by this tagger.
        """
        self._check_params(train, model)
        
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

class ClassifierBasedTagger(SequentialBackoffTagger, FeaturesetTaggerI):
    """
    A sequential tagger that uses a classifier to choose the tag for
    each token in a sentence.  The featureset input for the classifier
    is generated by a feature detector function::

        feature_detector(tokens, index, history) -> featureset

    Where C{tokens} is the list of unlabeled tokens in the sentence;
    C{index} is the index of the token for which feature detection
    should be performed; and C{history} is list of the tags for all
    tokens before C{index}.
    """
    def __init__(self, feature_detector=None, train=None,
                 classifier_builder=NaiveBayesClassifier.train,
                 classifier=None, backoff=None,
                 cutoff_prob=None, verbose=False):
        """
        Construct a new classifier-based sequential tagger.

        @param feature_detector: A function used to generate the
            featureset input for the classifier::
                feature_detector(tokens, index, history) -> featureset

        @param train: A tagged corpus consisting of a C{list} of tagged
            sentences, where each sentence is a C{list} of C{(word, tag)} tuples.
            
        @param backoff: A backoff tagger, to be used by the new tagger
            if it encounters an unknown context.
            
        @param classifier_builder: A function used to train a new
            classifier based on the data in C{train}.  It should take
            one argument, a list of labeled featuresets (i.e.,
            C{(featureset, label)} tuples).
            
        @param classifier: The classifier that should be used by the
            tagger.  This is only useful if you want to manually
            construct the classifier; normally, you would use C{train}
            instead.
            
        @param backoff: A backoff tagger, used if this tagger is
            unable to determine a tag for a given token.
            
        @param cutoff_prob: If specified, then this tagger will fall
            back on its backoff tagger if the probability of the most
            likely tag is less than C{cutoff_prob}.
        """
        self._check_params(train, classifier)

        SequentialBackoffTagger.__init__(self, backoff)
        
        if (train and classifier) or (not train and not classifier):
            raise ValueError('Must specify either training data or '
                             'trained classifier.')

        if feature_detector is not None:
            self._feature_detector = feature_detector
            # The feature detector function, used to generate a featureset
            # or each token: feature_detector(tokens, index, history) -> featureset

        self._cutoff_prob = cutoff_prob
        """Cutoff probability for tagging -- if the probability of the
           most likely tag is less than this, then use backoff."""
        
        self._classifier = classifier
        """The classifier used to choose a tag for each token."""

        if train:
            self._train(train, classifier_builder, verbose)

    def choose_tag(self, tokens, index, history):
        # Use our feature detector to get the featureset.
        featureset = self.feature_detector(tokens, index, history)
        
        # Use the classifier to pick a tag.  If a cutoff probability
        # was specified, then check that the tag's probability is
        # higher than that cutoff first; otherwise, return None.
        if self._cutoff_prob is None:
            return self._classifier.classify(featureset)
        else:
            pdist = self._classifier.prob_classify(featureset)
            tag = pdist.max()
            if pdist.prob(tag) >= self._cutoff_prob:
                return tag
            else:
                return None

    def _train(self, tagged_corpus, classifier_builder, verbose):
        """
        Build a new classifier, based on the given training data
        (C{tagged_corpus}).
        """

        classifier_corpus = []
        if verbose:
            print 'Constructing training corpus for classifier.'
        
        for sentence in tagged_corpus:
            history = []
            untagged_sentence, tags = zip(*sentence)
            for index in range(len(sentence)):
                featureset = self.feature_detector(untagged_sentence,
                                                    index, history)
                classifier_corpus.append( (featureset, tags[index]) )
                history.append(tags[index])

        if verbose:
            print 'Training classifier (%d instances)' % len(classifier_corpus)
        self._classifier = classifier_builder(classifier_corpus)

    def __repr__(self):
        return '<ClassifierBasedTagger: %r>' % self._classifier

    def feature_detector(self, tokens, index, history):
        """
        Return the feature detector that this tagger uses to generate
        featuresets for its classifier.  The feature detector is a
        function with the signature::

          feature_detector(tokens, index, history) -> featureset

        @see: L{classifier()}
        """
        return self._feature_detector(tokens, index, history)

    def classifier(self):
        """
        Return the classifier that this tagger uses to choose a tag
        for each word in a sentence.  The input for this classifier is
        generated using this tagger's feature detector.

        @see: L{feature_detector()}
        """
        return self._classifier

class ClassifierBasedPOSTagger(ClassifierBasedTagger):
    """
    A classifier based part of speech tagger.
    """
    def feature_detector(self, tokens, index, history):
        word = tokens[index]
        if index == 0:
            prevword = prevprevword = None
            prevtag = prevprevtag = None
        elif index == 1:
            prevword = tokens[index-1].lower()
            prevprevword = None
            prevtag = history[index-1]
            prevprevtag = None
        else:
            prevword = tokens[index-1].lower()
            prevprevword = tokens[index-2].lower()
            prevtag = history[index-1]
            prevprevtag = history[index-2]

        if re.match('[0-9]+(\.[0-9]*)?|[0-9]*\.[0-9]+$', word):
            shape = 'number'
        elif re.match('\W+$', word):
            shape = 'punct'
        elif re.match('[A-Z][a-z]+$', word):
            shape = 'upcase'
        elif re.match('[a-z]+$', word):
            shape = 'downcase'
        elif re.match('\w+$', word):
            shape = 'mixedcase'
        else:
            shape = 'other'
            
        features = {
            'prevtag': prevtag,
            'prevprevtag': prevprevtag,
            'word': word,
            'word.lower': word.lower(),
            'suffix3': word.lower()[-3:],
            'suffix2': word.lower()[-2:],
            'suffix1': word.lower()[-1:],
            'prevprevword': prevprevword,
            'prevword': prevword,
            'prevtag+word': '%s+%s' % (prevtag, word.lower()),
            'prevprevtag+word': '%s+%s' % (prevprevtag, word.lower()),
            'prevword+word': '%s+%s' % (prevword, word.lower()),
            'shape': shape,
            }
        return features

    
