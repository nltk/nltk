# Natural Language Toolkit: Taggers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""

Classes and interfaces for tagging each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  This task, which is known as X{tagging}, is defined by
the L{TaggerI} interface.

@group Data Types: TaggedType
@group Interfaces: TaggerI
@group Taggers: SequentialTagger, NN_CD_Tagger, UnigramTagger,
    NthOrderTagger, BackoffTagger
@group Tokenizers: TaggedTokenizer
@group Parsing: parseTaggedType
@group Evaluation: untag, accuracy
@sort: TaggedType, TaggedTokenizer, parseTaggedType, TaggerI, 
    SequentialTagger, NN_CD_Tagger, UnigramTagger, NthOrderTagger, 
    BackoffTagger, untag, accuracy

@todo 2.0: Add a Viterbi Tagger.
@todo 2.0: Rename
    C{SequentialTagger} to C{GreedySequentialTagger};
    C{UnigramTagger} to C{GreedyUnigramTagger}; 
    C{NthOrderTagger} to C{GreedyNthOrderTagger}; and 
    C{BackoffTagger} to C{GreedyBackoffTagger}.
"""

import types, re
from nltk.chktype import chktype
from nltk.tokenizer import Token, AbstractTokenizer, WSTokenizer, TokenizerI
from nltk.probability import FreqDist, ConditionalFreqDist

##//////////////////////////////////////////////////////
##  Parsing and Tokenizing TaggedTypes
##//////////////////////////////////////////////////////
class TaggedTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of tagged words into subtokens.
    Words should be separated by whitespace, and each word should have
    the form C{I{text}/I{tag}}, where C{I{text}} specifies the word's
    C{text} property, and C{I{tag}} specifies its C{tag} property.
    Words that do not contain a slash are assigned a C{tag} of C{None}.
    
    @inprop: C{text}: The input token's text content.
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{text}: The subtokens' text contents.
    @outprop: C{tag}: The subtokens' tags.
    @outprop: C{loc}: The subtokens' locations.
    """
    def __init__(self, addlocs=True, **property_names):
        self._wstokenizer = WSTokenizer(addlocs=addlocs, **property_names)
        AbstractTokenizer.__init__(self, addlocs, **property_names)
    
    def tokenize(self, token):
        assert chktype(1, token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')

        # First, use WSTokenizer to divide on whitespace.
        self._wstokenizer.tokenize(token)

        # Then, split each subtoken's text into a text and a tag.
        for subtok in token[SUBTOKENS]:
            split = subtok[TEXT].find('/')
            if split >= 0:
                subtok[TAG] = subtok[TEXT][split+1:]
                subtok[TEXT] = subtok[TEXT][:split]
            else:
                subtok[TAG] = None

    def xtokenize(self, token):
        AbstractTokenizer.xtokenize(self, token)

##//////////////////////////////////////////////////////
##  Tagger Interface
##//////////////////////////////////////////////////////
class TaggerI:
    """
    A processing interface for assigning a tag to each subtoken in an
    ordered list of subtokens.  Tags are case sensitive strings that
    identify some aspect each subtoken, such as its part of speech or
    its word sense.
    """
    def tag(self, token):
        """
        Assign a tag to each subtoken in C{token['subtokens']}, and
        write those tags to the subtokens' C{tag} properties.
        @inprop: C{subtokens}: The list of subtokens to tag.
        @inprop: C{text}: The text content of the subtokens.
        @outprop: C{tag}: The property where each subtoken's
            tag should be stored.
        """
        raise NotImplementedError()

    def raw_tag(self, words):
        """
        Given a list of words, return a correpsonding list of tags for
        those words.  I.e., return a list of tags, where the M{i}th tag
        is the tag assigned to C{words[M{i}]}.
        
        @type words: C{list} of C{string}
        @param words: The list of words to tag.
        @rtype: C{list} of C{string}
        """
        raise NotImplementedError()

    # [XX] add tag_n -- but encoded how??
    # [XX] add raw_tag_n

##//////////////////////////////////////////////////////
##  Taggers
##//////////////////////////////////////////////////////

class AbstractTagger(TaggerI):
    """
    An abstract base class for taggers.  C{AbstractTagger} provides a
    default implementation for L{raw_tag} (based on C{tag}).

    It also provides L{_tag_from_raw}, which can be used to implement
    C{tag} based on C{raw_tag}.
    """
    def __init__(self, **property_names):
        """
        Construct a new tagger.
        
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractTagger:
            raise AssertionError, "Abstract classes can't be instantiated"
        self._property_names = property_names

    def raw_tag(self, words):
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')
        
        subtoks = [Token({TEXT:w}) for w in words]
        token = Token({SUBTOKENS:subtoks})
        self.tag(token)
        return [token[TAG] for token in token[SUBTOKENS]]

    def _tag_from_raw(self, token):
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')
        
        words = [subtok[TEXT] for sutbok in token[SUBTOKENS]]
        tags = self.raw_tag(words)
        for subtok, tag in zip(tokens, tags):
            subtok[TAG] = tag

    
class SequentialTagger(TaggerI):
    """
    An abstract base class for taggers that assign tags to subtokens
    one at a time, in sequential order.

    By default, sequential taggers process subtokens in left-to-right
    order.  But the C{reverse} parameter to the constructor can be
    used to reverse this order.

    Each C{SequentialTagger} subclass must define the C{tag_subtoken}
    method, which returns the tag that should be assigned to a given
    subtoken.  The C{tag} method calls C{tag_subtoken} once for each
    token, and assigns the returned value to the token's C{tag}
    property.
    """
    def __init__(self, reverse=False, **property_names):
        """
        Construct a new sequential tagger.
        
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from right to left).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        self._reverse = reverse
        self._property_names = property_names

    def tag_subtoken(self, subtokens, i):
        """
        @rtype: C{string}
        @return: The tag that should be assigned to token
            C{subtokens[i]}.
        @type subtokens: C{list} of L{Token}
        @param subtokens: A list of the subtokens that are being
            tagged.
        @type i: C{int}
        @param i: The index of the subtoken whose tag should be
            returned.
        """
        raise AssertionError()

    def tag(self, token):
        assert chktype(1, token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TAG = self._property_names.get('tag', 'tag')

        # Tag each token, in sequential order.
        subtokens = token[SUBTOKENS]
        for i, subtoken in enumerate(subtokens):
            tag = self.tag_subtoken(subtokens, i)
            subtoken[TAG] = tag

class DefaultTagger(SequentialTagger):
    """
    A tagger that assigns the same tag to every token.
    """
    def __init__(self, tag, reverse=False, **property_names):
        """
        Construct a new default tagger.

        @type tag: C{string}
        @param tag: The tag that should be assigned to every token.
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from right to left).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        SequentialTagger.__init__(self, reverse, **property_names)
        self._tag = tag
        
    def tag_subtoken(self, subtokens, i):
        return self._tag
    
    def __repr__(self):
        return '<DefaultTagger: %s>' % self._tag

class RegexpTagger(SequentialTagger):
    """
    A tagger that assigns tags to words based on regular expressions.
    """
    def __init__(self, regexps, reverse=False, **property_names):
        """
        Construct a new regexp tagger.

        @type regexp: C{list} of C{(string,string)}
        @param regexps: A list of C{(regexp,tag)} pairs, each of
            which indicates that a word matching C{regexp} should
            be tagged with C{tag}.  The pairs will be evalutated in
            order.  If none of the regexps match a word, then it is
            assigned the tag C{None}.
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from right to left).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        SequentialTagger.__init__(self, reverse, **property_names)
        self._regexps = regexps

    def tag_subtoken(self, subtokens, i):
        TEXT = self._property_names.get('text', 'text')
        text = subtokens[i][TEXT]
        for regexp, tag in self._regexps:
            if re.match(regexp, text):
                return tag
        return None
                                      
    def __repr__(self):
        return '<RegexprTagger: %d regexps>' % len(self._regexps)

class UnigramTagger(SequentialTagger):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a tagged corpus.  Using this
    training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{UnigramTagger} encounters a
    word which it has no data, it will assign it the
    tag C{None}.
    """
    def __init__(self, reverse=False, **property_names):
        """
        Construct a new unigram stochastic tagger.  The new tagger
        should be trained, using the L{train()} method, before it is
        used to tag data.
        
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from last to first).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        SequentialTagger.__init__(self, reverse, **property_names)
        self._freqdist = ConditionalFreqDist()

    def train(self, tagged_token):
        """
        Train this C{UnigramTagger} using the given training data.  If
        this method is called multiple times, then the training data
        will be combined.
        
        @param tagged_token: A tagged corpus.  Each subtoken in
            C{tagged_token} should define the C{text} and C{tag}
            properties.
        @type tagged_token: L{Token}
        @type self._property_names: C{dict}
        """
        assert chktype(1, tagged_token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')

        # Record each text/tag pair in the frequency distribution.
        for subtok in tagged_token[SUBTOKENS]:
            word = subtok[TEXT]
            tag = subtok[TAG]
            self._freqdist[word].inc(tag)

    def tag_subtoken(self, subtokens, i):
        TEXT = self._property_names.get('text', 'text')
        
        # Find the most likely tag, given the subtoken's text.
        context = subtokens[i][TEXT]
        return self._freqdist[context].max()

    def raw_train(self, words, tags):
        for word, tag in zip(words, tags):
            self._freqdist[word].inc(tag)

    def __repr__(self):
        return '<Unigram Tagger>'

class NthOrderTagger(SequentialTagger):
    """
    An I{n}-th order stochastic tagger.  Before an C{NthOrderTagger}
    can be used, it should be trained on a tagged corpus.  Using this
    training data, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n} previous words' tags (or the I{n} following
    words' tags if C{reverse=True}).  Once the tagger has been
    trained, it uses this frequency distribution to tag words by
    assigning each word the tag with the maximum frequency given its
    context.  If the C{NthOrderTagger} encounters a word in a context
    for which it has no data, it will assign it the tag C{None}.

    @param _left: The start index of the context window for tags,
        expressed as an offset from the current subtoken's index.
    @param _right: The end index of the context window for tags,
        expressed as an offset from the current subtoken's index.
    """
    def __init__(self, n, reverse=False, cutoff=0, **property_names):
        """
        Construct a new I{n}-th order stochastic tagger.  The new
        tagger should be trained, using the L{train()} method, before
        it is used to tag data.
        
        @param n: The order of the new C{NthOrderTagger}.
        @type n: int
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from last to first).
        @type cutoff: C{int}
        @param cutoff: A count-cutoff for the tagger's frequency
            distribution.  If the tagger saw fewer than
            C{cutoff} examples of a given context in training,
            then it will return a tag of C{None} for that context.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        assert chktype(1, n, types.IntType)
        if n < 0: raise ValueError('n must be non-negative')
        SequentialTagger.__init__(self, reverse, **property_names)
        self._freqdist = ConditionalFreqDist()
        self._n = n
        self._cutoff = cutoff

        # Record the start & end indices of the context window for
        # tags.
        if self._reverse:
            self._left = 1
            self._right = 1+n
        else:
            self._left = -n
            self._right = 0
        
    def train(self, tagged_token):
        """
        Train this C{NthOrderTagger} using the given training data.
        If this method is called multiple times, then the training
        data will be combined.
        
        @param tagged_token: A tagged corpus.  Each subtoken in
            C{tagged_token} should define the C{text} and C{tag}
            properties.
        @type tagged_token: L{Token}
        @type self._property_names: C{dict}
        """
        assert chktype(1, tagged_token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')
        left, right = self._left, self._right
        
        # Extract the list of subtokens & list of tags.
        subtokens = tagged_token[SUBTOKENS]
        tags = tuple([t[TAG] for t in subtokens])

        for i, subtok in enumerate(subtokens):
            if i+left<0: continue
            # Construct the context from the current subtoken's text
            # and the adjacent tokens' tags.
            context = (tags[i+left:i+right], subtok[TEXT])

            # Record the current token in the frequency distribution.
            tag = subtok[TAG]
            self._freqdist[context].inc(tag)

    def tag_subtoken(self, subtokens, i):
        TEXT = self._property_names.get('text', 'text')
        TAG = self._property_names.get('tag', 'tag')
        left, right = self._left, self._right
        if i+left<0: return None

        # Construct the cotext from the current subtoken's text and
        # the adjacent tokens' tags.
        context_tags = [tok[TAG] for tok in subtokens[i+left:i+right]]
                        
        context = (tuple(context_tags), subtokens[i][TEXT])

        # Find the most likely tag for this subtoken, given the context.
        tag = self._freqdist[context].max()

        # If we're sufficiently confident in this tag, then return it.
        # Otherwise, return None.
        if self._freqdist[context].count(tag) >= self._cutoff:
            return tag
        else:
            return None

    def raw_train(self, words, tags):
        left,right = self._left, self._right
        for i, tag in enumerate(words):
            if i+left<0: continue
            context = (tuple(tags[0,i+left:i+right]), word)
            self._freqdist[context].inc(tag)

    def __repr__(self):
        n = repr(self._n)
        if n[-1] == '1': order='%sst' % n
        elif n[-1] == '2': order='%snd' % n
        elif n[-1] == '3': order='%srd' % n
        else: order='%sth' % n
        return '<%s Order Tagger>' % order

class BackoffTagger(SequentialTagger):
    """
    A C{Tagger} that tags tokens using a basic backoff model.  Each
    C{BackoffTagger} is paramatrised by an ordered list sub-taggers.
    In order to assign a tag to a token, each of these sub-taggers is
    consulted in order.  If a sub-tagger is unable to determine a tag
    for the given token, it should use assign the special tag C{None}.
    Each token is assigned the first non-C{None} tag returned by a
    sub-tagger.
    """
    def __init__(self, subtaggers, reverse=False, **property_names):
        """
        Construct a new C{BackoffTagger}, from the given
        list of sub-taggers.
        
        @param subtaggers: The list of sub-taggers used by this
               C{BackoffTagger}.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers: list of SequentialTagger
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        assert chktype(1, subtaggers, (SequentialTagger,), [SequentialTagger])
        self._subtaggers = subtaggers
        SequentialTagger.__init__(self, reverse, **property_names)

        # Maintain a record of how often each subtagger was used
        self._subtagger_count = {}
        for subtagger in subtaggers:
            self._subtagger_count[subtagger] = 0
        self._total_count = 0

    def tag_subtoken(self, subtokens, i):
        self._total_count += 1
        for subtagger in self._subtaggers:
            tag = subtagger.tag_subtoken(subtokens, i)
            if tag is not None:
                self._subtagger_count[subtagger] += 1
                return tag

        # Default to None if all subtaggers return None.
        return None

    def print_usage_stats(self):
        total = self._total_count
        print '  %20s | %s' % ('Subtagger', 'Words Tagged')
        print '  '+'-'*21+'|'+'-'*17
        for subtagger in self._subtaggers:
            count = self._subtagger_count[subtagger]
            print '  %20s |    %4.1f%%' % (subtagger, 100.0*count/total)

    def __repr__(self):
        return '<BackoffTagger: %s>' % self._subtaggers
    
##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _demo_tagger(gold_documents, tagger):
    correct = total = 0

    # Create a set of test documents (without tags)
    test_documents = [doc.exclude('tag') for doc in gold_documents]
    
    # Run the tagger on the test documents.
    for test_doc in test_documents: tagger.tag(test_doc)

    # Evaluate performance vs the gold documents.
    for (test_doc, gold_doc) in zip(test_documents, gold_documents):
        for (t,g) in zip(test_doc['subtokens'], gold_doc['subtokens']):
            #print t==g, t,g
            total += 1
            if t==g: correct += 1

    print 'Accuracy = %4.1f%%' % (100.0*correct/total)

def demo(num_files=20):
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a C{BackoffTagger} using a 2nd order C{NthOrderTagger},
    a 1st order C{NthOrderTagger}, a 0th order C{NthOrderTagger}, and
    an C{DefaultTagger}.  It trains and tests the tagger using the
    brown corpus.

    @type num_files: C{int}
    @param num_files: The number of files that should be used for
        training and for testing.  Two thirds of these files will be
        used for training.  All files are randomly selected
        (I{without} replacement) from the brown corpus.  If
        C{num_files>=500}, then all 500 files will be used.
    @rtype: None
    """
    from nltk.corpus import brown
    import sys, random
    num_files = max(min(num_files, 500), 3)

    # Get a randomly sorted list of files in the brown corpus.
    items = list(brown.items())
    random.shuffle(items)

    # Tokenize the training files.
    print '='*75
    sys.stdout.write('Reading training data'); sys.stdout.flush()
    train_tokens = []
    num_words = 0
    for item in items[:num_files*2/3]:
        sys.stdout.write('.'); sys.stdout.flush()
        train_tokens.append(brown.tokenize(item))
        num_words += len(train_tokens[-1]['subtokens'])
    print '\n  Read in %d words for training' % num_words

    print 'Training taggers.'

    # Create a default tagger
    default_tagger = DefaultTagger('nn')

    print '  Training unigram tagger...'
    t0 = UnigramTagger()
    for tok in train_tokens: t0.train(tok)
        
    print '  Training bigram tagger...'
    t1 = NthOrderTagger(1)
    for tok in train_tokens: t1.train(tok)

    print '  Training trigram tagger...'
    t2 = NthOrderTagger(2)
    for tok in train_tokens: t2.train(tok)

    # Delete train_tokens, because it takes up lots of memory.
    del train_tokens
    
    # Tokenize the testing files
    test_tokens = []
    num_words = 0
    sys.stdout.write('Reading testing data'); sys.stdout.flush()
    for item in items[num_files*2/3:num_files]:
        sys.stdout.write('.'); sys.stdout.flush()
        test_tok = brown.tokenize(item)
        num_words += len(test_tok['subtokens'])
        test_tokens.append(test_tok)
    print '\n  Read in %d words for testing' % num_words

    # Run the taggers.  For t0, t1, and t2, back-off to DefaultTagger.
    # This is especially important for t1 and t2, which count on
    # having known tags as contexts; if they get a context containing
    # None, then they will generate an output of None, and so all
    # words will get tagged a None.
    print '='*75
    print 'Running the taggers on test data...'
    print '  Default (nn) tagger: ',
    sys.stdout.flush()
    _demo_tagger(test_tokens, default_tagger)
    print '  Unigram tagger:      ',
    sys.stdout.flush()
    _demo_tagger(test_tokens, BackoffTagger([t0, default_tagger]))
    print '  Bigram tagger:       ',
    sys.stdout.flush()
    _demo_tagger(test_tokens, BackoffTagger([t1, t0, default_tagger]))
    print '  Trigram tagger:      ',
    sys.stdout.flush()
    trigram = BackoffTagger([t2, t1, t0, default_tagger])
    _demo_tagger(test_tokens, trigram)

    print '\nUsage statistics for the trigram tagger:\n'
    trigram.print_usage_stats()
    print '='*75

if __name__ == '__main__':
    # Standard boilerpate.  (See note in <http://?>)
    #from nltk.tagger import *
    demo(1)
