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
def parse_tagged_type(string):
    """
    Parse a string into a C{TaggedType}.  The C{TaggedType}'s base
    type will be the substring preceeding the first '/', and the
    C{TaggedType}'s tag will be the substring following the first
    '/'.  If the input string contains no '/', then the base type will
    be the input string and the tag will be C{None}.

    @param string: The string to parse
    @type string: {string}
    @return: The C{TaggedType} represented by C{string}
    @rtype: C{TaggedType}
    """
    assert chktype(1, string, types.StringType)
    elts = string.split('/')
    if len(elts) > 1:
        return TaggedType('/'.join(elts[:-1]), elts[-1].upper())
    else:
        return TaggedType(string, None)

class TaggedTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of tagged words into subtokens.
    Words should be separated by whitespace, and each word should have
    the form C{I{text}/I{tag}}, where C{I{text}} specifies the word's
    C{text} property, and C{I{tag}} specifies its C{tag} property.
    Words that do not contain a slash are assigned a C{tag} of C{None}.
    """
    _wstokenizer = WSTokenizer()
    
    def tokenize(self, token, **propnames):
        """
        @include: TokenizerI.tokenize
        @outprop: C{tag}: The property where the subtokens' tags
                  should be stored.
        """
        assert chktype(1, token, Token)
        subtokens_prop = propnames.get('subtokens', 'subtokens')
        text_prop = propnames.get('text', 'text')
        tag_prop = propnames.get('tag', 'tag')

        # First, use WSTokenizer to divide on whitespace.
        self._wstokenizer.tokenize(token)

        # Then, split each subtoken's text into a text and a tag.
        for subtok in token[subtokens_prop]:
            split = subtok[text_prop].find('/')
            if split >= 0:
                subtok[tag_prop] = subtok[text_prop][split+1:]
                subtok[text_prop] = subtok[text_prop][:split]
            else:
                subtok[tag_prop] = None

    def xtokenize(self, token, **propnames):
        """
        @include: TokenizerI.xtokenize
        @outprop: C{tag}: The property where the subtokens' tags
                  should be stored.
        """
        AbstractTokenizer.xtokenize(self, token, **propnames)

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
    # The input and output properties that are used by most taggers.
    # Specialized taggers might add extra input properties or output
    # properties.
    _STANDARD_PROPERTIES = """
    @inprop:  C{subtokens}: The list of subtokens to tag
    @inprop:  C{subtokens.text}: The text content of the tokens to
        be tagged.
    @outprop: C{subtokens.tag}: The property where each subtoken's
        tag should be stored.
    """
    __doc__ += _STANDARD_PROPERTIES
    
    def __init__(self, propnames={}):
        """
        Construct a new tagger.
        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this tagger.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular tagger,
            see its class docstring.
        """
        if self.__class__ == TaggerI:
            raise AssertionError, "Interfaces can't be instantiated"
        
    def tag(self, token):
        """
        Assign a tag to each subtoken in C{token['subtokens']}, and
        write those tags to the subtokens' C{tag} properties.
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

    # [XX] add tag_n
    # [XX] add raw_tag_n

##//////////////////////////////////////////////////////
##  Taggers
##//////////////////////////////////////////////////////
class SequentialTagger(TaggerI):
    """
    An abstract base class for taggers that assign tags to subtokens
    one at a time, in sequential order.

    By default, sequential taggers process tags in the order that they
    are listed (i.e., from first to last).  But the C{reverse}
    parameter to the constructor can be used to reverse this order.

    Each C{SequentialTagger} subclass must define the C{tag_subtoken}
    method, which returns the tag that should be assigned to a given
    subtoken.  The C{tag} method calls C{tag_subtoken} once for each
    token, and assigns the returned values to the corresponding tags.
    """
    __doc__ += TaggerI._STANDARD_PROPERTIES
    
    def __init__(self, reverse=False, propnames={}):
        """
        Construct a new sequential tagger.
        
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from last to first).
        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this tagger.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular tagger,
            see its class docstring.
        """
        self._props = propnames
        self._reverse = reverse

    def tag_subtoken(self, subtokens, i):
        """
        @rtype: C{string}
        @return: The tag that should be assigned to the specified
            token, C{subtokens[i]}.
        @type subtokens: C{list} of L{Token}
        @param subtokens: A list of the subtokens that are being
            tagged.
        @type i: C{int}
        @param i: The index of the subtoken whose tag should be
            returned.
        """
        raise AssertionError()

    def raw_tag_word(self, words, i):
        """
        @rtype: C{string}
        @return: The tag that should be assigned to the specified
            word, C{words[i]}.
        @type words: C{list} of C{string}
        @param words: A list of the words that are being tagged.
        @type i: C{int}
        @param i: The index of the word whose tag should be returned.
        """
        raise AssertionError()

    def tag(self, token):
        assert chktype(1, token, Token)
        subtokens_prop = self._props.get('subtokens', 'subtokens')

        # Tag each token, in sequential order.
        subtokens = token[subtokens_prop]
        for i, subtoken in enumerate(subtokens):
            subtoken['tag'] = self.tag_subtoken(subtokens, i)

    def raw_tag(self, words):
        assert chktype(1, words, [str], (str,))
        return [self.raw_tag_word(words, i) for i in range(len(words))]
                                      
class NN_CD_Tagger(SequentialTagger):
    """
    A "default" tagger, which will assign the tag C{"CD"} to numbers,
    and C{"NN"} to anything else.
    """
    __doc__ += TaggerI._STANDARD_PROPERTIES

    def tag_subtoken(self, subtokens, i):
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        text = subtokens[i][subtokens_text_prop]
        if re.match(r'^[0-9]+(.[0-9]+)?$', text):
            return 'CD'
        else:
            return 'NN'

    def raw_tag_word(self, words, i):
        if re.match(r'^[0-9]+(.[0-9]+)?$', word):
            return 'CD'
        else:
            return 'NN'

    def __repr__(self):
        return '<NN_CD_Tagger>'

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
    __doc__ += TaggerI._STANDARD_PROPERTIES
    
    def __init__(self, reverse=False, propnames={}):
        """
        Construct a new unigram stochastic tagger.  The new tagger
        should be trained, using the L{train()} method, before it is
        used to tag data.
        
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from last to first).
        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this tagger.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular tagger,
            see its class docstring.
        """
        SequentialTagger.__init__(self, reverse, propnames)
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
        @rtype: None
        """
        assert chktype(1, tagged_token, Token)
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        subtokens_tag_prop = self._props.get('subtokens.tag', 'tag')

        # Record each text/tag pair in the frequency distribution.
        for subtok in tagged_token[subtokens_prop]:
            word = subtok[subtokens_text_prop]
            tag = subtok[subtokens_tag_prop]
            self._freqdist[word].inc(tag)

    def tag_subtoken(self, subtokens, i):
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        
        # Find the most likely tag, given the subtoken's text.
        context = subtokens[i][subtokens_text_prop]
        return self._freqdist[context].max()

    def raw_train(self, words, tags):
        for word, tag in zip(words, tags):
            self._freqdist[word].inc(tag)

    def raw_tag_word(self, words, i):
        # Find the most likely tag, given the word's text.
        context = words[i]
        return self._freqdist[context].max()
    
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
    __doc__ += TaggerI._STANDARD_PROPERTIES
    
    def __init__(self, n, reverse=False, propnames={}):
        """
        Construct a new I{n}-th order stochastic tagger.  The new
        tagger should be trained, using the L{train()} method, before
        it is used to tag data.
        
        @param n: The order of the new C{NthOrderTagger}.
        @type n: int
        @param reverse: If true, then assign tags to subtokens in
            reverse sequential order (i.e., from last to first).
        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this tagger.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular tagger,
            see its class docstring.
        """
        assert chktype(1, n, types.IntType)
        if n < 0: raise ValueError('n must be non-negative')
        SequentialTagger.__init__(self, reverse, propnames)
        self._freqdist = ConditionalFreqDist()
        self._n = n

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
        @rtype: None
        """
        assert chktype(1, tagged_token, Token)
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        text_prop = self._props.get('subtokens.text', 'text')
        tag_prop = self._props.get('subtokens.tag', 'tag')
        left, right = self._left, self._right
        
        # Extract the list of subtokens & list of tags.
        subtokens = tagged_token[subtokens_prop]
        tags = tuple([t[tag_prop] for t in subtokens])

        for i, subtok in enumerate(subtokens):
            if i+left<0: continue
            # Construct the context from the current subtoken's text
            # and the adjacent tokens' tags.
            context = (subtok[text_prop], tags[i+left:i+right])

            # Record the current token in the frequency distribution.
            tag = subtok[tag_prop]
            self._freqdist[context].inc(tag)

    def tag_subtoken(self, subtokens, i):
        text_prop = self._props.get('subtokens.text', 'text')
        tag_prop = self._props.get('subtokens.tag', 'tag')
        left, right = self._left, self._right
        if i+left<0: return None

        # Construct the cotext from the current subtoken's text and
        # the adjacent tokens' tags.
        context_tags = [tok[tag_prop] for tok in subtokens[i+left:i+right]]
                        
        context = (subtokens[i][text_prop], tuple(context_tags))

        # Find the most likely tag for this subtoken, given the context.
        return self._freqdist[context].max()

    def raw_train(self, words, tags):
        left,right = self._left, self._right
        for i, tag in enumerate(words):
            if i+left<0: continue
            context = (word, tuple(tags[0,i+left:i+right]))
            self._freqdist[context].inc(tag)

    def raw_tag_word(self, words, i):
        left,right = self._left, self._right
        if i+left<0: return None
        context = (words[i], tuple(tags[0,i+left:i+right]))
        return self._freqdist[context].max()

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

    This tagger expects a list of C{Token}s as its input, and
    generates a list of C{TaggedToken}s as its output.  Each
    sub-tagger should accept a list a list of C{Token}s as its input,
    and should generate a list of C{TaggedToken}s as its output.
    """
    def __init__(self, subtaggers, reverse=False, propnames={}):
        """
        Construct a new C{BackoffTagger}, from the given
        list of sub-taggers.
        
        @param subtaggers: The list of sub-taggers used by this
               C{BackoffTagger}.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers: list of SequentialTagger
        """
        assert chktype(1, subtaggers, (SequentialTagger,), [SequentialTagger])
        self._subtaggers = subtaggers
        SequentialTagger.__init__(self, reverse, propnames)

    def tag_subtoken(self, subtokens, i):
        for subtagger in self._subtaggers:
            tag = subtagger.tag_subtoken(subtokens, i)
            if tag is not None:
                return tag

        # Default to None if all subtaggers return None.
        return None

    def raw_tag_word(self, words, i):
        for subtagger in self._subtaggers:
            tag = subtagger.raw_tag_word(words, i)
            if tag is not None:
                return tag

        # Default to None if all subtaggers return None.
        return None

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

    print '    Accuracy = %4.1f%%' % (100.0*correct/total)

def demo(num_files=20):
    """
    A simple demonstration function for the C{Tagger} classes.  It
    constructs a C{BackoffTagger} using a 2nd order C{NthOrderTagger},
    a 1st order C{NthOrderTagger}, a 0th order C{NthOrderTagger}, and
    an C{NN_CD_Tagger}.  It trains and tests the tagger using the
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
    sys.stdout.write('Reading training data'); sys.stdout.flush()
    train_tokens = []
    num_words = 0
    for item in items[:num_files*2/3]:
        sys.stdout.write('.'); sys.stdout.flush()
        train_tokens.append(brown.tokenize(item))
        num_words += len(train_tokens[-1]['subtokens'])
    print '\nRead in %d words for training' % num_words

    # Create a default tagger
    default_tagger = NN_CD_Tagger()

    print 'training unigram tagger...'
    t0 = UnigramTagger()
    for tok in train_tokens: t0.train(tok)
        
    print 'training bigram tagger...'
    t1 = NthOrderTagger(1)                
    for tok in train_tokens: t1.train(tok)

    print 'training trigram tagger...'
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
    print '\nRead in %d words for testing' % num_words

    # Run the taggers.  For t0, t1, and t2, back-off to NN_CD_Tagger.
    # This is especially important for t1 and t2, which count on
    # having known tags as contexts; if they get a context containing
    # None, then they will generate an output of None, and so all
    # words will get tagged a None.
    print 'running the taggers...'
    print '-'*75
    print 'Default (NN/CD) tagger:'
    _demo_tagger(test_tokens, default_tagger)
    print 'Unigram tagger:'
    _demo_tagger(test_tokens, BackoffTagger([t0, default_tagger]))
    print 'Bigram tagger:'
    _demo_tagger(test_tokens, BackoffTagger([t1, t0, default_tagger]))
    print 'Trigram tagger:'
    _demo_tagger(test_tokens, BackoffTagger([t2, t1, t0, default_tagger]))

if __name__ == '__main__':
    # Standard boilerpate.  (See note in <http://?>)
    #from nltk.tagger import *
    demo(100)
