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

Classes and interfaces used to tag each token of a document with
supplementary information, such as its part of speech or its WordNet
synset tag.  Tagged tokens are represented by C{Token} objects whose
types are C{TaggedType} objects.  C{TaggedType}s consist of a base
type (the original token's type) and a tag.  A C{TaggedType} with base
M{b} and tag M{t} is written as M{b/m}.

A token M{tok} with tag M{type} is tagged by constructing a new token
whose type is M{type/tag}, where M{tag} is the appropriate tag value.
The new token's location is equal to M{tok}'s location.  To tag a
document, a new document is constructed, whose tokens are the result
of tagging the original document's tokens.  The tagger module defines
the C{TaggerI} interface for creating classes to tag documents.  It
also defines several different implementations of this interface,
providing a variety ways to tag documents.

The tagger module also defines the function C{parseTaggedType()} and
the tokenizer C{TaggedTokenizer}, for reading tagged tokens from
strings. 
"""

from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq
import types
from nltk.token import Token, TokenizerI, Location
import re
from nltk.probability import FreqDist, ConditionalFreqDist

##//////////////////////////////////////////////////////
##  TaggedType
##//////////////////////////////////////////////////////
class TaggedType:
    """
    An element of text that consists of a base type and a tag.  A
    typical example would be a part-of-speech tagged word, such as
    C{'bank'/'NN'}.  The base type and the tag are typically strings,
    but may be any immutable hashable objects.  Note that string base
    types and tags are case sensitive.

    @see: parseTaggedType
    @type _base: (any)
    @ivar _base: The base type of the C{TaggedType}.  This represents
        the type that is tagged.
    @type _tag: (any)
    @ivar _tag: The base type's tag.  This provides information about
        the base type, such as its part-of-speech.
    """
    def __init__(self, base, tag):
        """
        Construct a new C{TaggedType}

        @param base: The new C{TaggedType}'s base type.
        @param tag: The new C{TaggedType}'s tag.
        """
        self._base = base
        self._tag = tag
        
    def base(self):
        """
        @return: this C{TaggedType}'s base type.
        @rtype: (any)
        """
        return self._base
    
    def tag(self):
        """
        @return: this C{TaggedType}'s tag.
        @rtype: (any)
        """
        return self._tag
    
    def __eq__(self, other):
        """
        @return: true if this C{TaggedType} is equal to C{other}.  In
            particular, return true iff C{self.base()==other.base()}
            and C{self.tag()==other.tag()}.
        @raise TypeError: if C{other} is not a C{TaggedType}
        """
        return (_classeq(self, other) and
                self._base == other._base and
                self._tag == other._tag)

    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash( (self._base, self._tag) )
    
    def __repr__(self):
        """
        @return: a concise representation of this C{TaggedType}.
        @rtype: string
        """
        return repr(self._base)+'/'+repr(self._tag)

##//////////////////////////////////////////////////////
##  Parsing and Tokenizing TaggedTypes
##//////////////////////////////////////////////////////
def parseTaggedType(string):
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
    assert _chktype(1, string, types.StringType)
    elts = string.split('/', 1)
    if len(elts) > 1:
        return TaggedType('/'.join(elts[:-1]), elts[-1].upper())
    else:
        return TaggedType(string, None)

class TaggedTokenizer(TokenizerI):
    """
    A tokenizer that splits a string of tagged text into words, based
    on whitespace.  Each tagged word is encoded as a C{Token} whose
    type is a C{TaggedType}.  Location indices start at zero, and have
    a unit of C{'w'}.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        words = str.split()
        tokens = []
        for i in range(len(words)):
            toktype = parseTaggedType(words[i])
            tokloc = Location(i, unit='w', source=source)
            tokens.append(Token(toktype, tokloc))
        return tokens

##//////////////////////////////////////////////////////
##  Parsing and Tokenizing TaggedTypes
##//////////////////////////////////////////////////////
class TaggerI:
    """
    A processing interface for assigning a tag to each token in an
    ordered list of tokens.  Taggers are required to define one
    function, C{tag}, which tags a list of C{Token}s.
    
    Classes implementing the C{TaggerI} interface may choose to only
    support certain classes of tokens for input.  If a method is
    unable to return a correct result because it is given an
    unsupported class of token, then it should raise a
    NotImplementedError.
    """
    def __init__(self):
        """
        Construct a new C{Tagger}.
        """
        assert 0, "TaggerI is an abstract interface"
        
    def tag(self, tokens):
        """
        Assign a tag to each token in an ordered list of tokens, and
        return the resulting list of tagged tokens.  In particular,
        return a list C{out} where:

            - C{len(tokens)} = C{len(out)}
            - C{out[i].type} = C{TaggedType(tokens[i].type, M{tag})}
                for some C{M{tag}}.
            - C{out[i].loc()} = C{tokens[i].loc()}

        @param tokens: The list of tokens to be tagged.
        @type tokens: C{list} of C{Token}
        @return: The tagged list of tokens.
        @returntype: C{list} of C{Token}
        """
        assert 0, "TaggerI is an abstract interface"

class SequentialTagger(TaggerI):
    """
    An abstract base class for taggers that assign tags to tokens in
    sequential order.  In particular, X{sequential taggers} are
    taggers that:

        - Assign tags to one token at a time, starting with the first
          token of the text, and proceeding in sequential order.
        - Decide which tag to assign a token on the basis of that
          token, the tokens that preceed it, and the predicted tags of
          the tokens that preceed it.

    Each C{SequentialTagger} subclass defines the C{next_tag} method,
    which returns the tag for a token, given the list of tagged tokens
    that preceeds it.  The C{tag} method calls C{next_tag} once for
    each token, and uses the return values to construct the tagged
    text.
    """
    def next_tag(self, tagged_tokens, next_token):
        """
        Decide which tag to assign a token, given the list of tagged
        tokens that preceeds it.

        @type tagged_tokens: C{list} of tagged C{Token}
        @param tagged_tokens: A list of the tagged tokens that preceed
            C{token}.  The tokens' base types are taken from the text
            being tagged, and their tags are prediced by previous
            calls to C{next_tag}.  In particular, the I{n}th element
            of C{tagged_tokens} is a tagged token whose base type is
            equal to the type of the I{n}th element of the text; whose
            location is equal to the location of the I{n}th element of
            the text; and whose tag is a predicted tag returned by a
            previous call to C{next_tag}.
        @type next_token: C{Token}
        @param next_token: The (untagged) token for which to assign a
            tag. 
        @rtype: tag
        @return: the most likely tag for C{token}, given that it is
            preceeded by C{tagged_tokens}.
        """
        assert 0, "next_tag not defined by SequentialTagger subclass"

    def tag(self, tokens):
        # Inherit documentation
        assert _chktype(1, tokens, [Token], (Token,))

        # Tag each token, in sequential order.
        tagged_text = []
        for token in tokens:
            # Get the tag for the next token.
            tag = self.next_tag(tagged_text, token)

            # Construct a tagged token with the given tag, and add it
            # to the end of tagged_text.
            tagged_token = Token(TaggedType(token.type(), tag), token.loc())
            tagged_text.append(tagged_token)

        return tagged_text

class NN_CD_Tagger(SequentialTagger):
    """
    A "default" tagger, which will assign the tag C{"CD"} to numbers,
    and C{"NN"} to anything else.  This tagger expects token types to
    be C{strings}s.
    """
    def __init__(self): pass

    def next_tag(self, tagged_tokens, next_token):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_token, Token)
        
        if re.match(r'^[0-9]+(.[0-9]+)?$', next_token.type()):
            return 'CD'
        else:
            return 'NN'

class UnigramTagger(SequentialTagger):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a list of C{TaggedToken}s.  Using
    this training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{NthOrderTagger} encounters a
    word in a context for which it has no data, it will assign it the
    tag C{None}.
    """
    def __init__(self):
        self._freqdist = ConditionalFreqDist()
    
    def train(self, tagged_tokens):
        """
        Train this C{UnigramTagger} using the given training data.  If
        this method is called multiple times, then the training data
        will be combined.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        for token in tagged_tokens:
            context = token.type().base()
            feature = token.type().tag()
            self._freqdist[context].inc(feature)

    def next_tag(self, tagged_tokens, next_token):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_token, Token)

        # Find the most likely tag for the token's type.
        context = next_token.type()
        return self._freqdist[context].max()
    
class NthOrderTagger(SequentialTagger):
    """
    An I{n}-th order stochastic tagger.  Before an C{NthOrderTagger}
    can be used, it should be trained on a list of C{TaggedToken}s.
    Using this list, it will construct a frequency distribution
    describing the frequencies with each word is tagged in different
    contexts.  The context considered consists of the word to be
    tagged and the I{n} previous words' tags.  Once it has constructed
    this frequency distribution, it uses it to tag words by assigning
    each word the tag with the maximum frequency given its context.
    If the C{NthOrderTagger} encounters a word in a context for which
    it has no data, it will assign it the tag C{None}.
    """
    def __init__(self, n):
        """
        Construct a new I{n}-th order stochastic tagger.  The
        new tagger should be trained, using the train() method, before
        it is used to tag data.
        
        @param n: The order of the new C{NthOrderTagger}.
        @type n: int
        """
        assert _chktype(1, n, types.IntType)
        if n < 0: raise ValueError('n must be non-negative')
        self._n = n
        self._freqdist = ConditionalFreqDist()

    def train(self, tagged_tokens):
        """
        Train this C{NthOrderTagger} using the given training data.
        If this method is called multiple times, then the training
        data will be combined.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        # prev_tags is a list of the previous n tags that we've assigned.
        prev_tags = []
        
        for token in tagged_tokens:
            context = tuple(prev_tags + [token.type().base()])
            feature = token.type().tag()
            self._freqdist[context].inc(feature)

            # Update prev_tags
            prev_tags.append(token.type().tag())
            if len(prev_tags) == (self._n+1):
                del prev_tags[0]

    def next_tag(self, tagged_tokens, next_token):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_token, Token)

        # Find the tags of the n previous tokens.
        prev_tags = []
        start = max(len(tagged_tokens) - self._n, 0)
        for token in tagged_tokens[start:]:
            prev_tags.append(token.type().tag())

        # Return the most likely tag for the token's context.
        context = tuple(prev_tags + [next_token.type()])
        return self._freqdist[context].max()

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
    def __init__(self, subtaggers):
        """
        Construct a new C{BackoffTagger}, from the given
        list of sub-taggers.
        
        @param subtaggers: The list of sub-taggers used by this
               C{BackoffTagger}.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers: list of SequentialTagger
        """
        assert _chktype(1, subtaggers, (SequentialTagger,), [SequentialTagger])
        self._subtaggers = subtaggers

    def next_tag(self, tagged_tokens, next_token):
        # Inherit docs from SequentialTagger
        assert _chktype(1, tagged_tokens, [Token], (Token,))
        assert _chktype(2, next_token, Token)

        for subtagger in self._subtaggers:
            tag = subtagger.next_tag(tagged_tokens, next_token)
            if tag is not None:
                return tag

        # Default to None if all subtaggers return None.
        return None

def untag(tagged_tokens):
    """
    Given a list of tagged tokens, return a list of tokens constructed
    from the tagged tokens' base types and locations.  In particular,
    if C{tagged_tokens} = [I{ttok_1}, ..., I{ttok_n}], return a
    list of tokens [I{tok_1}, ..., I{tok_n}], where I{tok_i}.loc() ==
    I{ttok_i}.loc() and I{tok_i}.type() == I{ttok_i}.type.base().

    @param tagged_tokens: The list of tokens to transform.
    @type tagged_tokens: C{list} of C{TaggedToken}
    @return: A list of tokens constructed from the C{tagged_tokens}'
        base types and locations.
    @rtype: C{list} of C{Token}
    """
    assert _chktype(1, tagged_tokens, [Token], (Token,))
    return [Token(t.type().base(), t.loc()) for t in tagged_tokens]

def accuracy(orig, test):
    """
    Test the accuracy of a tagged text, with respect the correct
    tagging.  This accuracy is defined as the percentage of tokens
    tagged correctly.  Note that C{orig} and C{test} should be the
    same length, and should contain tokens with corresponding base
    types and locations; otherwise, C{test} is not a valid tagging of
    C{orig}.

    @param orig: The original (correctly-tagged) text.  This is the
        "gold standard" against which C{test} is compared.
    @type orig: C{list} of C{TaggedToken}
    @param test: The tagging whose accuracy you wish to test.
    @type test: C{list} of C{TaggedToken}
    """
    assert _chktype(1, test, [Token], (Token,))
    assert _chktype(2, orig, [Token], (Token,))
    if len(orig) != len(test):
        raise ValueError('Invalid Tagging')

    correct = 0
    for i in range(len(orig)):
        if orig[i] == test[i]: correct += 1
    return float(correct)/len(orig)

def demo(tagged_text_str):
    """
    A simple test function for the C{Tagger} classes.  It constructs a
    C{BackoffTagger} using a 1st order C{NthOrderTagger}, a 0th order
    C{NthOrderTagger}, and an C{NN_CD_Tagger}.  It trains the tagger
    using the contents C{tagged_text_str}, and then tags the contents
    of that file.
    
    @returntype: None
    """
    print 'tokenizing...'
    tokens = TaggedTokenizer().tokenize(tagged_text_str)
    train_tokens = tokens[200:]
    test_tokens = tokens[:280]

    print 'training unigram tagger (%d tokens)...' % len(train_tokens)
    t0 = UnigramTagger()
    t0.train(train_tokens)

    print 'training 1st order tagger (%d tokens)...' % len(train_tokens)
    t1 = NthOrderTagger(1)                
    t1.train(train_tokens)

    print 'training 2nd order tagger (%d tokens)...' % len(train_tokens)
    t2 = NthOrderTagger(2) 
    t2.train(train_tokens)

    print 'creating combined backoff tagger...'
    ft = BackoffTagger( (t2, t1, t0, NN_CD_Tagger()) )
    
    print 'running the tagger... (%d tokens)...' % len(test_tokens)
    result = ft.tag(untag(test_tokens))

    print 'Accuracy: %.5f' % accuracy(test_tokens, result)

if __name__ == '__main__':
    demo(open('/home/edloper/tmp/foo.text', 'r').read())
