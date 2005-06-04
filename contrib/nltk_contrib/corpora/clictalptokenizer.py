
from nltk import TaskI, PropertyIndirectionMixIn
import re, sre_parse, sre_constants, sre_compile
from nltk.chktype import chktype
from nltk.token import *
from nltk.tokenizer import *
from nltk.tokenreader import TokenReaderI
"""
Tokenizer for tagged corpora with lemma. Will include reader later to exclude lemmas.
"""

class LineTokenizerTaggedWithLemma(AbstractTokenizer):
    """
    A tokenizer for CLICTALP data that divides a string of text into subtokens with lemmas and POS, based on
    newline characters.  I.e., C{LineTokenizer} creates a tagged token with lemma for
    each newline-delimited substring in the input text.  Blank lines
    are ignored.
    
    @inprop: C{TEXT}: The input token's text content.
    @inprop: C{LOC}: The input token's location.  I{(optional)}
    @inprop: C{TAG}: The input token's POS tag.  
    @inprop: C{LEMMA}: The input token's lemma.  I{(optional)}
    @outprop: C{SUBTOKENS}: The list of tokenized subtokens.
    """
    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return [s for s in text.split('\n') if s.strip() != '']#[s for s in text.split('\n') if s.strip() != '']

    def tokenize(self, token, add_locs=False, add_contexts=False):
        # Delegate to self.raw_tokenize()
        assert chktype(1, token, Token)
        self._tokenize_from_raw(token, add_locs, add_contexts)


    def raw_xtokenize(self, text):
        assert chktype(1, text, str)
        TEXT = self.property('TEXT')
        SUBTOKENS = self.property('SUBTOKENS')
        token = Token({TEXT:text})
        self.xtokenize(token)
        for subtok in token[SUBTOKENS]:
            yield subtok[TEXT]

    def _tokenize_from_raw(self, token, add_locs, add_contexts):
        """
        Tokenize the given token by using C{self.raw_tokenize} to
        tokenize its text string.  Locations are reconstructed by
        searching for each consecutive token in the text string.  To
        ensure that locations are correctly assigned,
        C{self.raw_tokenize} must make the following guarantee:

            - For each subtoken M{t[i]}, the text separating M{t[i-1]}
              and M{t[i]} does not contain M{t[i]} as a substring.

        This method is intended to be used by subclasses that wish to
        implement the C{tokenize} method based on C{raw_tokenize}.
        """
        assert chktype(1, token, Token)
        TEXT = self.property('TEXT')
        LOC = self.property('LOC')
        TAG = self.property('TAG')
        LEMMA = self.property('LEMMA')
        SUBTOKENS = self.property('SUBTOKENS')
        CONTEXT = self.property('CONTEXT')

        # Use raw_tokenize to get a list of subtoken texts, that includes lemma and POS info.
        text = token[TEXT]
        subtok_texts = self.raw_tokenize(text)

        # Create the list of subtokens, splitting POS and lemma from TEXT string, and adding as properties.
        #subtoks = [Token({TEXT:t}) for t in subtok_texts]
        subtoks = []
        for x in subtok_texts:
            w,l,p = x.split()
            tk = Token({TEXT:w},TAG=p)
            tk[LEMMA] = l
            subtoks.append(tk)

        # Add locations (if requested)
        if add_locs:
            source, end = self._get_initial_loc(token)
            for subtok in subtoks:
                start = text.find(subtok[TEXT], end)
                assert start>=0, 'Tokenization alignment failure'
                end = start+len(subtok[TEXT])
                subtok[LOC] = CharSpanLocation(start,end,source)

        # Add subtoken context pointers (if requested)
        if add_contexts:
            for i, subtok in enumerate(subtoks):
                context = SubtokenContextPointer(token, SUBTOKENS, i)
                subtok[CONTEXT] = context
        
        # Write subtoks to the SUBTOKENS property.
        token[SUBTOKENS] = subtoks        


class LemmaTaggedTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    A token reader for the CLICTALP corpus that divides a string of tagged and lemmatized
    words into subtokens.  Words should be separated by whitespace, and each word
    should have the form C{I{text} I{lemma} I{tag}}, where C{I{text}} specifies
    the word's C{TEXT} property, C{I{tag}} specifies its C{TAG} property and C{I{lemma}}
    specifies its C{LEMMA} property.
    Words that do not contain a slash are assigned a C{tag}
    of C{None}.
    
    @outprop: C{SUBTOKENS}: The list of subtokens.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{TAG}: The subtokens' tags.
    @outprop: C{LEMMA}: The subtokens' LEMMA.
    """
    def __init__(self, **property_names):
        PropertyIndirectionMixIn.__init__(self, **property_names)

    # [XX] source and add_locs are ignored!
    def read_token(self, s, add_contexts=False, add_locs=False, source=None):
        TAG = self.property('TAG')
        TEXT = self.property('TEXT')
        LEMMA = self.property('LEMMA')
        SUBTOKENS = self.property('SUBTOKENS')
        CONTEXT = self.property('CONTEXT')
        subtoks = []
        lista = [s for s in s.split("\n") if s.strip() != '']
        for z in lista:
            w,l,p = z.split()
            if p:
                tk = Token(**{TEXT: w, TAG: p})
            else:
                tk = Token(**{TEXT: w, TAG: None})
            tk[LEMMA] = l
            subtoks.append(tk)
        tok = Token(**{SUBTOKENS: subtoks})
        if add_contexts:
            for i, subtok in enumerate(subtoks):
                subtok[CONTEXT] = SubtokenContextPointer(tok, SUBTOKENS, i)
        return tok

    def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
        return [self.read_token(s, add_contexts, add_locs, source)]
