#
# Natural Language Toolkit for Python:
# Taggers
# Edward Loper
#
# Created [03/16/01 05:32 PM]
# (extracted from nltk.py, created [02/26/01 11:24 PM])
# $Id$
#

from chktype import chktype as _chktype
from token import TaggedTokenType, Token
import re
import probability

def shift_in(lst, elt):
    """##
    Given a list <CODE>[<I>e1</I>, <I>e2</I>, ..., <I>en</I>]</CODE>,
    and an element <I>x</I>, return the list
    <CODE>[<I>e2</I>, <I>e3</I>, ..., <I>x</I>]</CODE>.

    This is a simple helper function used by NthOrderTagger.

    @param lst The list to shift.
    @type lst list
    @param elt The element to shift into the list.
    @type elt any
    @returntype list
    @return The shifted list.
    """
    if len(lst) > 0:
        del lst[0]
        lst.append(elt)
  
class TaggerI:
    # other requirements? (e.g., in, out have same length)?
    """##
    A processing interface for assigning a tag to each token in an
    ordered list of tokens.  Taggers are required to define one
    function, <CODE>tag</CODE>, which takes a list of
    <CODE>Tokens</CODE>, and returns a list of <CODE>Token</CODE>s.
    Typically, the input tokens will be <CODE>SimpleToken</CODE>s, and
    the output tokens will be <CODE>TaggedToken</CODE>s.  However,
    taggers may also be written to map between other types of tokens,
    as long as they are still performing the same conceptual task. <P> 

    Classes implementing the <CODE>TaggerI</CODE> interface may choose
    to only support certain classes of tokens.  If a method is unable
    to return a correct result because it is given an unsupported
    class of token, then it should raise a NotImplementedError.  (??
    is this the right exception? use NotSupportedError? ValueError?
    ??)
    """
    def tag(self, tokens):
        """##
        Assign a tag to each token in an ordered list of tokens, and
        return the resulting list of tagged tokens.

        @param tokens The list of tokens to be tagged.
        @type tokens list of TokenI
        @return The tagged list of tokens.
        @returntype list of TokenI
        """
        raise AssertionError()

class NN_CD_Tagger(TaggerI):
    """##
    A \"default\" tagger, which will assign the tag <CODE>CD</CODE> to 
    numbers, and <CODE>NN</CODE> to anything else. <P>

    This tagger expects a list of <CODE>SimpleToken</CODE>s as its
    inputs, and generates a list of <CODE>TaggedToken</CODE>s as its
    output.
    """
    def tag(self, tokens):
        # Inherit docs from TaggerI
        tagged_tokens = []
        for token in tokens:
            word = token.type().name()
            if re.match('^[0-9]+(.[0-9]+)?$', word):
                token_type = TaggedTokenType(word, 'CD')
            else:
                token_type = TaggedTokenType(word, 'NN')
            tagged_tokens.append(Token(token_type, token.source()))
        return tagged_tokens

class NthOrderTagger(TaggerI):
    """##
    An <I>n</I>-th order stochastic tagger.  Before an
    <CODE>NthOrderTagger</CODE> can be used, it should be trained on a 
    list of <CODE>TaggedToken</CODE>s.  Using this list, it will
    construct a frequency distribution describing the frequencies with 
    each word is tagged in different contexts.  The context considered 
    consists of the word to be tagged and the <I>n</I> previous words' 
    tags.  Once it has constructed this frequency distribution, it
    uses it to tag words by assigning each word the tag with the
    maximum frequency given its context.  If the
    <CODE>NthOrderTagger</CODE> encounters a word in a context for
    which it has no data, it will assign it the tag \"UNK\". <P>

    This tagger expects a list of <CODE>SimpleToken</CODE>s as its
    input, and generates a list of <CODE>TaggedToken</CODE>s as its
    output.
    """
    def __init__(self, n):
        """##
        Construct a new <I>n</I>-th order stochastic tagger.  The
        new tagger should be trained, using the train() method, before
        it is used to tag data.
        
        @param n The order of the new <CODE>NthOrderTagger</CODE>.
        @type n int
        """
        self._n = n
        self._freqDist = probability.CFFreqDist()

    def train(self, tagged_tokens):
        """##
        Train this <CODE>NthOrderTagger</CODE> using the given
        training data.  If this method is called multiple times, then
        the training data from each call will be used.
        
        @param tagged_tokens The training data.
        @type tagged_tokens list of TaggedToken
        @returntype None
        """
        # prev_tags is a list of the previous n tags that we've assigned.
        prev_tags = ['UNK' for x in range(self._n)]
      
        for token in tagged_tokens:
            context = tuple(prev_tags+[token.type().name()])
            feature = token.type().tag()
            self._freqDist.inc( probability.CFSample(context, feature) )

            # Update prev_tags
            shift_in(prev_tags, token.type().tag())

    def tag(self, tokens):
        # Inherit docs from TaggerI
        tagged_tokens = []
      
        prev_tags = ['UNK' for x in range(self._n)]
        for token in tokens:
            # Predict the next tag
            context = tuple(prev_tags+[token.type().name()])
            context_event = probability.ContextEvent(context)
            sample = self._freqDist.cond_max(context_event)
            if sample: tag = sample.feature()
            else: tag = 'UNK'

            # Update words
            token_type = TaggedTokenType(token.type().name(), tag)
            tagged_tokens.append(Token(token_type, token.source()))

            # Update prev_tags
            shift_in(prev_tags, tag)

        return tagged_tokens

class BackoffTagger(TaggerI):
    """##
    A <CODE>Tagger</CODE> that tags tokens using a basic backoff
    model.  Each <CODE>BackoffTagger</CODE> is paramatrised by an
    ordered list sub-taggers.  In order to assign a tag to a token,
    each of these sub-taggers is consulted in order.  If a sub-tagger
    is unable to determine a tag for the given token, it should use a
    special \"unknown tag.\"  The first tag returned by a sub-tagger,
    other than the unknown tag, is used for each Token. <P>

    This tagger expects a list of <CODE>SimpleToken</CODE>s as its
    input, and generates a list of <CODE>TaggedToken</CODE>s as its
    output.  Each sub-tagger should accept a list a list of
    <CODE>SimpleToken</CODE>s as its input, and should generate a list
    of <CODE>TaggedToken</CODE>s as its output.
    """
    def __init__(self, subtaggers, unknown_tag='UNK'):
        """##
        Construct a new <CODE>BackoffTagger</CODE>, from the given
        list of sub-taggers.  The unknown tag specifies which tag
        should be treated as an indication that a sub-tagger cannot
        successfully tag a <CODE>Token</CODE>.
        @param subtaggers The list of sub-taggers used by this
               <CODE>BackoffTagger</CODE>.  These sub-taggers will be
               consulted in the order in which they appear in the
               list.
        @type subtaggers list of TaggerI
        @param unknown_tag The tag which indicates that a sub-tagger
               is unable to tag a <CODE>Token</CODE>.
        @type unknown_tag sting.
        """
        self._unk = unknown_tag
        self._taggers = subtaggers

    def tag(self, tokens):
        # Inherit docs from TaggerI

        # Find the output of all the taggers.
        tagger_outputs = []
        for tagger in self._taggers:
            out = tagger.tag(tokens)
            tagger_outputs.append(out)

        # Check for consistancy
        length = len(tokens)
        for tagger_output in tagger_outputs:
            if len(tagger_output) != length:
                raise ValueError('Broken tagger!')
          
        # For each word, find the first tagged output value that is
        # not unknown.
        tagged_tokens = []
        for i_token in range(len(tokens)):
            tag = self._unk
            for i_tagger in range(len(self._taggers)):
                token = tagger_outputs[i_tagger][i_token]
                if token.type().tag() != self._unk:
                    tagged_tokens.append(token)
                    break # out of for i_tagger ...
        return tagged_tokens
  
def test_tagger():
    """##
    A simple test function for the <CODE>Tagger</CODE> classes.  It
    constructs a <CODE>BackoffTagger</CODE> using a 1st order
    <CODE>NthOrderTagger</CODE>, a 0th order
    <CODE>NthOrderTagger</CODE>, and an <CODE>NN_CD_Tagger</CODE>.  It 
    trains the tagger using the contents of the file \"foo.test,\" and 
    then tags the contents of that file.
    @returntype None
    """
    from token import TaggedTokenizer
    tokens=TaggedTokenizer().tokenize(open('foo.test', 'r').read())

    t0 = NthOrderTagger(0)
    t0.train(tokens)

    t1 = NthOrderTagger(1)                
    t1.train(tokens)

    ft = BackoffTagger( (t1, t0, NN_CD_Tagger()), 'UNK')
    for t in ft.tag(tokens): print t.type(),

if __name__ == '__main__': test_tagger()
