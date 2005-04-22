# Natural Language Toolkit: Prefix and Suffix Taggers
#
# Module written by Tiago Tresoldi <tresoldi@users.sf.net>,
# based on NLTK's UnigramTagger and tutorials.
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes for stochastic taggers for tagging based on leading or trailing
substrings of tokens' text.

@group Tagger: PrefixTagger, SuffixTagger
"""

from nltk.token import Token
from nltk.tagger import SequentialTagger
from nltk.chktype import chktype
from nltk.probability import ConditionalFreqDist

class AffixTagger (SequentialTagger):
    """
    An abstract class for stochastic taggers that assign tags to subtokens
    based on leading or trailing substrings (it is important to note that
    the substrings are not necessarily "true" morphological affixes).
    """
    def __init__ (self, length, minlength, reverse=False, **property_names):
        """
        Construct a new affix stochastic tagger. The new tagger should be
        trained, using the L{train()} method, before it is used to tag
        data.
        
        @type length: C{number}
        @param length: The length of the suffix to be considered during 
            training and tagging.
        @type minlength: C{number}
        @param minlength: The minimum length for a word to be considered
            during training and tagging. It must be longer that C{length}.
        @param reverse: If true, then assign tags to subtokens in reverse
            sequential order (i.e., from the last to the first).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names. Each entry maps from a default
            property name to a new property name.        
        """
        SequentialTagger.__init__(self, reverse, **property_names)
        self._freqdist = ConditionalFreqDist()
        
        assert length >= 1
        assert minlength >= 2
        assert minlength > length
        
        self._length = length
        self._minlength = minlength
        
    def train (self, tagged_token):
        raise NotImplementedError()
    
    def raw_train (self, words, tags):
        raise NotImplementedError()

class PrefixTagger (AffixTagger):
    """
    A stochastic tagger which works based on the first letters of tokens. 
    Before a C{PrefixTagger} can be used, it should be trained on a tagged
    corpus. Using this training data, it will find the most likely tag for 
    each word type. It will then use this information to assign the most
    frequent tag to each word. If the C{PrefixTagger} encounters a prefix in
    a word for which it has no data, it will assign the tag C{None}.
    """
    def __init__ (self, length, minlength, reverse=False, **property_names):
        """
        Construct a new prefix stochastic tagger. The new tagger should be
        trained, using the L{train()} method(), before it is used to tag
        data.
        
        @type length: C{number}
        @param length: The length of the suffix to be considered during 
            training and tagging.
        @type minlength: C{number}
        @param minlength: The minimum length for a word to be considered
            during training and tagging. It must be longer that C{length}.
        @param reverse: If true, then assign tags to subtokens in reverse
            sequential order (i.e., from the last to the first).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names. Each entry maps from a default
            property name to a new property name.        
        """
        AffixTagger.__init__(self, length, minlength, reverse, **property_names)
        
    def train (self, tagged_token):
        """
        Train this C{PrefixTagger} using the given training data. If this
        method is called multiple times, then the training data will be
        combined.
        
        @param tagged_token: A tagged corpus. Each subtoken in
            C{tagged_token} should define the C{text} and C{tag} properties.
        @type tagged_token: L{Token}
        """
        assert chktype(1, tagged_token, Token)
        SUBTOKENS = self.property('SUBTOKENS')
        TEXT = self.property('TEXT')
        TAG = self.property('TAG')
        
        # If 'TEXT' has the minimum length, record each prefix/tag pair in the
        # frequency distribution
        for subtok in tagged_token[SUBTOKENS]:
            word = subtok[TEXT]
            tag = subtok[TAG]
            if len(word) >= self._minlength:
                self._freqdist[ word[:self._length] ].inc(tag)
                
    def tag_subtoken (self, subtokens, i):
        TEXT = self.property('TEXT')
        
        # Find the most likely tag, given the subtokens's prefix, if subtoken's
        # text has the minimum length
        context = subtokens[i][TEXT][:self._length]
        if len( subtokens[i][TEXT] ) >= self._minlength:
            return self._freqdist[context].max()

    def raw_train (self, words, tags):
        for word, tag in zip(words, tags):
            if len(word) >= self._minlength:
                self._freqdist[ word[:self._length] ].inc(tag)
                
    def raw_tag (self, words):
        tags = []
        for word in words:
            if len(word) >= self._minlength:
                tags.append( self._freqdist.__getitem__( word[:self._length] ).max() )
            else:
                tags.append(None)
        
    def __repr__ (self):
        return '<PrefixTagger>'

class SuffixTagger (AffixTagger):
    """
    A stochastic tagger which works based on the last letters of tokens. 
    Before a C{SuffixTagger} can be used, it should be trained on a tagged
    corpus. Using this training data, it will find the most likely tag for 
    each word type. It will then use this information to assign the most
    frequent tag to each word. If the C{SuffixTagger} encounters a suffix in
    a word for which it has no data, it will assign the tag C{None}.
    """
    def __init__ (self, length, minlength, reverse=False, **property_names):
        """
        Construct a new suffix stochastic tagger. The new tagger should be
        trained, using the L{train()} method(), before it is used to tag
        data.
        
        @type length: C{number}
        @param length: The length of the suffix to be considered during 
            training and tagging.
        @type minlength: C{number}
        @param minlength: The minimum length for a word to be considered
            during training and tagging. It must be longer that C{length}.
        @param reverse: If true, then assign tags to subtokens in reverse
            sequential order (i.e., from the last to the first).
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names. Each entry maps from a default
            property name to a new property name.        
        """
        AffixTagger.__init__(self, length, minlength, reverse, **property_names)
        
    def train (self, tagged_token):
        """
        Train this C{SuffixTagger} using the given training data. If this
        method is called multiple times, then the training data will be
        combined.
        
        @param tagged_token: A tagged corpus. Each subtoken in
            C{tagged_token} should define the C{text} and C{tag} properties.
        @type tagged_token: L{Token}
        """
        assert chktype(1, tagged_token, Token)
        SUBTOKENS = self.property('SUBTOKENS')
        TEXT = self.property('TEXT')
        TAG = self.property('TAG')
        
        # If 'TEXT' has the minimum length, record each suffix/tag pair in the
        # frequency distribution
        for subtok in tagged_token[SUBTOKENS]:
            word = subtok[TEXT]
            tag = subtok[TAG]
            if len(word) >= self._minlength:
                self._freqdist[ word[-self._length:] ].inc(tag)
                
    def tag_subtoken (self, subtokens, i):
        TEXT = self.property('TEXT')
        
        # Find the most likely tag, given the subtokens's suffix, if subtoken's
        # text has the minimum length
        context = subtokens[i][TEXT][-self._length:]
        if len( subtokens[i][TEXT] ) >= self._minlength:
            return self._freqdist[context].max()

    def raw_train (self, words, tags):
        for word, tag in zip(words, tags):
            if len(word) >= self._minlength:
                self._freqdist[ word[-self._length:] ].inc(tag)
                
    def raw_tag (self, words):
        tags = []
        for word in words:
            if len(word) >= self._minlength:
                tags.append( self._freqdist.__getitem__( word[-self._length:] ).max() )
            else:
                tags.append(None)
        
    def __repr__ (self):
        return '<SuffixTagger>'
