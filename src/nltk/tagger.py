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

from chktype import chktype as _chktype
from types import StringType as _StringType
from token import Token, TokenizerI, Location
import re
import probability

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
        if not isinstance(other, TaggedType):
            raise TypeError("TaggedType compared for equality "+
                            "with a non-TaggedType.")
        return (self._base == other._base and
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
def parseTaggedType(string, unknownTag='UNK'):
    """
    Parse a string into a C{TaggedType}.  The C{TaggedType}'s base
    type will be the substring preceeding the first '/', and the
    C{TaggedType}'s tag will be the substring following the first
    '/'.  If the input string contains no '/', then the base type will
    be the input string and the tag will be C{unknownTag}.

    @param string: The string to parse
    @type string: {string}
    @param unknownTag: A default tag to use if C{string} does not
        contain a tag.
    @type unknownTag: string
    @return: The C{TaggedType} represented by C{string}
    @rtype: C{TaggedType}
    """
    _chktype("parseTaggedType", 1, string, (_StringType,))
    _chktype("parseTaggedType", 2, unknownTag, (_StringType,))
    elts = string.split('/', 1)
    if len(elts) > 1:
        return TaggedType('/'.join(elts[:-1]), elts[-1].upper())
    else:
        return TaggedType(string, unknownTag)

class TaggedTokenizer(TokenizerI):
    """
    A tokenizer that splits a string of tagged text into words, based
    on whitespace.  Each tagged word is encoded as a C{Token} whose
    type is a C{TaggedType}.  Location indices start at zero, and have
    a unit of C{'word'}.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("TaggedTokenizer.tokenize", 1, str, (_StringType,))
        words = str.split()
        tokens = []
        for i in range(len(words)):
            ttype = parseTaggedType(words[i])
            tokens.append(Token(ttype, Location(i, unit='word',
                                                source=source)))
        return tokens

class ChunkedTaggedTokenizer(TaggedTokenizer):
    """
    A tagged tokenizer that is sensitive to [] chunks, and returns
    a list of tokens and chunks, where each chunk is a list of tokens.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        _chktype("ChunkedTaggedTokenizer.tokenize", 1, str, (_StringType,))
        # check that brackets are balanced and not nested
        brackets = re.sub(r'[^\[\]]', '', str)
        if not re.match(r'(\[\])*', brackets):
            print "ERROR: unbalanced or nested brackets"
        words = str.split()
        tokens = []
        inchunk = 0
        for i in range(len(words)):
            if words[i] == '[':
                tokens.append([])
                inchunk = 1
            elif words[i] == ']':
                inchunk = 0
            else:
                ttype = parseTaggedType(words[i])
                if inchunk:
                    tokens[-1].append(Token(ttype, Location(i, unit='word',
                                                            source=source)))
                else:
                    tokens.append(Token(ttype, Location(i, unit='word',
                                                        source=source)))
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

class NN_CD_Tagger(TaggerI):
    """
    A \"default\" tagger, which will assign the tag C{CD} to numbers,
    and C{NN} to anything else.  This tagger expects a list of
    C{strings}s as its inputs.
    """
    def __init__(self): pass
    
    def tag(self, tokens):
        # Inherit docs from TaggerI
        tagged_tokens = []
        for token in tokens:
            base_type = token.type()
            if re.match(r'^[0-9]+(.[0-9]+)?$', base_type):
                tag = TaggedType(base_type, 'CD')
            else:
                tag = TaggedType(base_type, 'NN')
            tagged_tokens.append(Token(tag, token.loc()))
        return tagged_tokens

class UnigramTagger(TaggerI):
    """
    A unigram stochastic tagger.  Before a C{UnigramTagger} can be
    used, it should be trained on a list of C{TaggedToken}s.  Using
    this training data, it will find the most likely tag for each word
    type.  It will then use this information to assign the most
    frequent tag to each word.  If the C{NthOrderTagger} encounters a
    word in a context for which it has no data, it will assign it the
    tag \"UNK\".
    
    This tagger expects a list of C{Token}s as its
    input, and generates a list of C{TaggedToken}s as its
    output.
    """
    def __init__(self):
        self._freqdist = probability.CFFreqDist()
    
    def train(self, tagged_tokens):
        """
        Train this C{UnigramTagger} using the given
        training data.  If this method is called multiple times, then
        the training data from every call will be used.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        for token in tagged_tokens:
            context = token.type().base()
            feature = token.type().tag()
            self._freqdist.inc( probability.CFSample(context, feature) )

    def tag(self, tokens):
        # Inherit docs from TaggerI
        tagged_tokens = []
      
        for token in tokens:
            # Predict the next tag
            context = token.type()
            context_event = probability.ContextEvent(context)
            sample = self._freqdist.cond_max(context_event)
            if sample: tag = sample.feature()
            else: tag = 'UNK'

            # Add the newly tagged token to tagged_tokens
            token_type = TaggedType(token.type(), tag)
            tagged_tokens.append(Token(token_type, token.loc()))

        return tagged_tokens
    
class NthOrderTagger(TaggerI):
    """
    An I{n}-th order stochastic tagger.  Before an
    C{NthOrderTagger} can be used, it should be trained on a 
    list of C{TaggedToken}s.  Using this list, it will
    construct a frequency distribution describing the frequencies with 
    each word is tagged in different contexts.  The context considered 
    consists of the word to be tagged and the I{n} previous words' 
    tags.  Once it has constructed this frequency distribution, it
    uses it to tag words by assigning each word the tag with the
    maximum frequency given its context.  If the
    C{NthOrderTagger} encounters a word in a context for
    which it has no data, it will assign it the tag \"UNK\".

    This tagger expects a list of C{Token}s as its
    input, and generates a list of C{TaggedToken}s as its
    output.
    """
    def __init__(self, n):
        """
        Construct a new I{n}-th order stochastic tagger.  The
        new tagger should be trained, using the train() method, before
        it is used to tag data.
        
        @param n: The order of the new C{NthOrderTagger}.
        @type n: int
        """
        self._n = n
        self._freqdist = probability.CFFreqDist()

    def train(self, tagged_tokens):
        """
        Train this C{NthOrderTagger} using the given
        training data.  If this method is called multiple times, then
        the training data from every call will be used.
        
        @param tagged_tokens: The training data.
        @type tagged_tokens: list of TaggedToken
        @returntype: None
        """
        # prev_tags is a list of the previous n tags that we've assigned.
        prev_tags = ['UNK'] * self._n
      
        for token in tagged_tokens:
            context = tuple(prev_tags+[token.type().base()])
            feature = token.type().tag()
            self._freqdist.inc( probability.CFSample(context, feature) )

            # Update prev_tags
            if len(prev_tags) > 0:
                del prev_tags[0]
                prev_tags.append(token.type().tag())

    def tag(self, tokens):
        # Inherit docs from TaggerI
        tagged_tokens = []
      
        prev_tags = ['UNK'] * self._n
        for token in tokens:
            # Predict the next tag
            context = tuple(prev_tags+[token.type()])
            context_event = probability.ContextEvent(context)
            sample = self._freqdist.cond_max(context_event)
            if sample: tag = sample.feature()
            else: tag = 'UNK'

            # Add the newly tagged token to tagged_tokens
            token_type = TaggedType(token.type(), tag)
            tagged_tokens.append(Token(token_type, token.loc()))

            # Update prev_tags
            if len(prev_tags) > 0:
                del prev_tags[0]
                prev_tags.append(tag)

        return tagged_tokens

class BackoffTagger(TaggerI):
    """
    A C{Tagger} that tags tokens using a basic backoff
    model.  Each C{BackoffTagger} is paramatrised by an
    ordered list sub-taggers.  In order to assign a tag to a token,
    each of these sub-taggers is consulted in order.  If a sub-tagger
    is unable to determine a tag for the given token, it should use a
    special \"unknown tag.\"  The first tag returned by a sub-tagger,
    other than the unknown tag, is used for each Token.

    This tagger expects a list of C{Token}s as its
    input, and generates a list of C{TaggedToken}s as its
    output.  Each sub-tagger should accept a list a list of
    C{Token}s as its input, and should generate a list
    of C{TaggedToken}s as its output.
    """
    def __init__(self, subtaggers, unknown_tag='UNK'):
        """
        Construct a new C{BackoffTagger}, from the given
        list of sub-taggers.  The unknown tag specifies which tag
        should be treated as an indication that a sub-tagger cannot
        successfully tag a C{Token}.
        
        @param subtaggers: The list of sub-taggers used by this
               C{BackoffTagger}.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers: list of TaggerI
        @param unknown_tag: The tag which indicates that a sub-tagger
               is unable to tag a C{Token}.
        @type unknown_tag: sting.
        """
        self._unk = unknown_tag
        self._subtaggers = subtaggers

    def tag(self, tokens):
        # Inherit docs from TaggerI

        # Find the output of all the taggers.
        tagger_outputs = []
        for tagger in self._subtaggers:
            out = tagger.tag(tokens)
            tagger_outputs.append(out)

        # Check for consistancy
        length = len(tokens)
        for tagger_output in tagger_outputs:
            if len(tagger_output) != length:
                raise ValueError('Broken tagger!')
          
        # For each word, find the first tagged output value whose
        # tag is not "unknown."
        num_tokenizers = len(self._subtaggers)
        tagged_tokens = []
        for i_token in range(len(tokens)):
            for i_tagger in range(num_tokenizers):

                # Did this tagger successfully tag this token?
                token = tagger_outputs[i_tagger][i_token]
                if token.type().tag() != self._unk:
                    tagged_tokens.append(token)
                    break # out of "for i_tagger in ..."

                # If this is the last tokenizer, use its result, even
                # if its tag is "unkonwn."
                if i_tagger == num_tokenizers-1:
                    tagged_tokens.append(token)
                    
        return tagged_tokens

def untag(tokens):
    return [Token(t.type().base(), t.loc()) for t in tokens]

def accuracy(orig, test):
    if len(orig) != len(test):
        print "OUCH! Bad lengths!!!"

    correct = 0
    for (o,t) in zip(orig, test):
        if o == t: correct += 1
    return float(correct)/len(orig)

def test_tagger():
    """
    A simple test function for the C{Tagger} classes.  It
    constructs a C{BackoffTagger} using a 1st order
    C{NthOrderTagger}, a 0th order
    C{NthOrderTagger}, and an C{NN_CD_Tagger}.  It 
    trains the tagger using the contents of the file \"foo.test,\" and 
    then tags the contents of that file.
    
    @returntype: None
    """
    tokens=TaggedTokenizer().tokenize(open('/home/edloper/tmp/foo.text', 'r').read())

    t0 = NthOrderTagger(0)
    t0.train(tokens[100:])

    t1 = NthOrderTagger(1)                
    t1.train(tokens[100:])

    ft = BackoffTagger( (t1, t0, NN_CD_Tagger()), 'UNK')
    result = ft.tag(untag(tokens)[:100])
    print 'Original:  ',
    for t in tokens[:100]: print t.type(),
    print ; print
    print 'Result:  ',
    for t in result[:100]: print t.type(),
    print ; print
    print 'Accuracy', accuracy(tokens[:100], result)
    print ; print

if __name__ == '__main__': test_tagger()
