#
# Natural Language Toolkit for Python:
# Tokens and Tokenizers
# Edward Loper
#
# Created [03/16/01 05:30 PM]
# (extracted from nltk.py, created [02/26/01 11:24 PM])
# $Id$
#

from chktype import chktype as _chktype
from types import IntType, StringType

##//////////////////////////////////////////////////////
##  Tokens
##//////////////////////////////////////////////////////

class Token:
    """##
    An occurance of a single unit of text, such as a word or a
    punctuation mark.  A Token consists of a token type and a source.
    The token type is the unit of text (e.g., a specific word).
    The source is the position at which this token occured in the
    text. <P>

    The precise defintion of what counts as a token type, or unit of
    text, will vary for different analyses.  For example, \"bank\" and 
    \"run\" might be tokens for one analysis, while \"bank/N\" and
    \"bank/V\" might be tokens for another analysis.
    @see(nltk.TokenTypeI)
    @see(nltk.TextLocationI)
    @see(-) (insert textbook ref here?)
    """
    def __init__(self, type, source):
        """##
        Construct a new Token, with the given token type and source.
        @param type The token type for the new Token.
        @type type TokenTypeI
        @param source The source for the new Token.
        @type source TextLocationI
        """
        self._type = type
        self._source = source
    def type(self):
        """##
        Return the token type of this token.
        @return The token type of this token.
        @returntype TokenTypeI
        """
        return self._type
    def source(self):
        """##
        Return the source of this token.
        @return The source of this token.
        @returntype TextLocationI
        """
        return self._source
    def __cmp__(self, other):
        """##
        Return 0 if the given object is equal to this Token.  In
        particular, return 0 if and only if <CODE>other</CODE> is a
        Token, and its type and source are equal to this Token's type
        and source.  Otherwise, return a non-zero number.
        @param other The object to compare this Token to.
        @type other any
        @return 0 if the given object is equal to this Token.
        @returntype int
        """
        if not isinstance(other, Token): return -1000
        if cmp(self.source(), other.source()) != 0:
            return cmp(self.source(), other.source())
        return cmp(self.type(), other.type())

    def __str__(self):
        """##
        Return the informal string representation of this
        <CODE>Token</CODE>.  The informal representation
        of a <CODE>Token</CODE> has the form
        <I>type</I>@<I>source</I>. 
        
        @return The informal string representation of this
                <CODE>Token</CODE>.
        @returntype string
        """
        return str(self._type)+'@'+str(self._source)

    def __hash__(self):
        """##
        Return the hash value for this Token.  If two Tokens are equal,
        they are guaranteed to have the same hash value.  However, two 
        Tokens may have the same hash value and still not be equal.

        @raise TypeError if the <CODE>Token</CODE>'s type or source is 
               not hashable.
        @return The hash value for this Token.
        @returntype int
        """
        return hash(self._type)/2 + hash(self._source)/2
    
class TextLocationI:
    """##
    A location of an entity within a text.  Text locations can be
    compared for equality, and should be equal if and only if they
    refer to the same location.
    """
    def __cmp__(self, other):
        """##
        Return 0 if the given object is equal to this text location.
        Otherwise,  return a non-zero number.
        @param other The object to compare this text location to.
        @type other any
        @return 0 if the given object is equal to this text location.
        @returntype int
        """
        raise AssertionError()

    def __hash__(self):
        """##
        Return the hash value for this TextLocationI.  If two
        TextLocationIs are equal, they are guaranteed to have the same
        hash value.  However, two TextLocationIs may have the same
        hash value and still not be equal.

        @return The hash value for this TextLocationI.
        @returntype int
        """
        raise AssertionError()
    
class IndexTextLocation(TextLocationI):
    """##
    A <CODE>TextLocation</CODE> based on an integer index.  Typically, 
    this index will be either a token index or a character index into
    the source text.  
    """
    def __init__(self, index):
        """##
        Construct a new <CODE>IndexTextLocation</CODE>, with the given 
        index.

        @param index The index of the new
               <CODE>IndexTextLocation</CODE>.
        @type index int
        """
        _chktype("IndexTextLocation", 1, index, (IntType,))
        self._index = index
        
    def __cmp__(self, other):
        # Inherit docs from TextLocationI.
        if not isinstance(other, IndexTextLocation): return -1000
        return cmp(self._index, other._index)
    
    def __hash__(self):
        # Inherit docs from TextLocationI.
        return self.index
    
    def __str__(self):
        """##
        Return the informal string representation of this
        <CODE>IndexTextLocation</CODE>.  The informal representation
        of a <CODE>IndexTextLocation</CODE> is simply its index.
        
        @return The informal string representation of this
                <CODE>IndexTextLocation</CODE>.
        @returntype string
        """
        return str(self._index)

    def __repr__(self):
        """##
        Return the formal string representation of this
        <CODE>IndexTextLocation</CODE>.  The formal representation
        of a <CODE>IndexTextLocation</CODE> has the form
        <CODE>IndexTextLocation(<I>index</I>)</CODE>.
        
        @return The formal string representation of this
                <CODE>IndexTextLocation</CODE>.
        @returntype string
        """
        return 'IndexTextLocation('+repr(self._index)+')'

# RangeTextLocation?
    
class TokenTypeI:
    """##
    A single unit of text, such as a word or a punctuation mark.  The
    precise defintion of what counts as a token type will vary for
    different analyses.  For example, \"bank\" and \"run\" might be
    tokens for one analysis, while \"bank/N\" and \"bank/V\" might be
    tokens for another analysis. <P>

    Token types can be compared for equality, and should be equal if
    and only if they refer to the same token type. <P>
    
    Tokens should generally be immutable, unless I change my mind
    later.
    """
    def __cmp__(self, other):
        """##
        Return 0 if the given object is equal to this token type.
        Otherwise, return a non-zero number.
        
        @param other The object to compare this token type to.
        @type other any
        @return 0 if the given object is equal to this token type.
        @returntype int
        """
        raise AssertionError()
    
    def __hash__(self):
        """##
        Return the hash value for this TokenType.  If two
        TokenTypes are equal, they are guaranteed to have the same
        hash value.  However, two TokenTypes may have the same
        hash value and still not be equal.

        @return The hash value for this TokenType.
        @returntype int
        """
        raise AssertionError()

class SimpleTokenType(TokenTypeI):
    """##
    A token type represented by a single string.  This string is
    referred to as the token type's name (NOTE: need better term).  Two
    <CODE>SimpleTokenType</CODE>s are equal if their names are equal.
    Note that this implies that <CODE>SimpleTokenType</CODE>s are case 
    sensitive.
    """
    def __init__(self, name):
        """##
        Construct a new <CODE>SimpleTokenType</CODE>.
        
        @param name The new <CODE>SimpleTokenType</CODE>'s name.
        @type name string
        """
        _chktype("SimpleTokenType", 1, name, (StringType,))
        self._name = name
    def __cmp__(self, other):
        # Inherit documentation from TokenTypeI
        if not isinstance(other, SimpleTokenType): return -1000
        else: return cmp(self._name, other._name)
    def __hash__(self):
        # Inherit documentation from TokenTypeI
        return hash(self._name)
    def __str__(self):
        """##
        Return the informal string representation of this
        <CODE>SimpleTokenType</CODE>.  The informal representation of
        a <CODE>SimpleTokenType</CODE> is simply its name.
        
        @return The informal string representation of this
        <CODE>SimpleTokenType</CODE>.
        @returntype string
        """
        return self._name
    def name(self):
        """##
        Return this <CODE>SimpleTokenType</CODE>'s name.
        
        @return This <CODE>SimpleTokenType</CODE>'s name.
        @returntype string
        """
        return self._name

class TaggedTokenType(TokenTypeI):
    """##
    A token type represented by a name (NOTE: need better term) and a
    tag.  The token type's name is the word or punctuation which the
    token type represents (e.g., \"bird\" or \"running\").  The token
    type's tag is a string representing the name's category.
    Typically, tags are used to represent syntactic categories such as
    \"NN\" or \"VBZ\".  Two <CODE>TaggedTokenType</CODE>s are equal if
    their names are equal and their tags are equal.
    <CODE>TaggedTokenType</CODE>s are case sensitive in their name and
    in their tag.  <P>

    <CODE>TaggedTokenType</CODE> values are written using the form
    <CODE><I>name</I>/<I>tag</I></CODE>.  For example,
    <CODE>bird/NN</CODE> and <CODE>running/VBG</CODE> are
    representations of <CODE>TaggedTokenType</CODE>.  To convert a
    string of this representation to a <CODE>TaggedTokenType</CODE>,
    use the function parseTaggedTokenType.

    @see nltk.parseTaggedTokenType parseTaggedTokenType()
    """
    def __init__(self, name, tag):
        """##
        Construct a new <CODE>TaggedTokenType</CODE>.
        
        @param name The new <CODE>TaggedTokenType</CODE>'s name
        @type name string
        @param tag The new <CODE>TaggedTokenType</CODE>'s tag
        @type tag string
        """
        _chktype("TaggedTokenType", 1, name, (StringType,))
        _chktype("TaggedTokenType", 2, tag, (StringType,))
        self._name = name
        self._tag = tag
    def __cmp__(self, other):
        # Inherit documentation from TokenTypeI
        if not isinstance(other, TaggedTokenType): return -1000
        elif self._tag != other.tag:
            return cmp(self._tag, other._tag)
        else:
            return cmp(self._name, other._name)
    def __hash__(self):
        # Inherit documentation from TokenTypeI
        return hash(self._name)/2 + hash(self._tag)/2
    def __str__(self):
        """##
        Return the informal string representation of this
        <CODE>TaggedTokenType</CODE>.  The informal representation of
        a <CODE>TaggedTokenType</CODE> has the form
        <CODE><I>name</I>/<I>tag</I></CODE>.
        
        @return The informal string representation of this
        <CODE>TaggedTokenType</CODE>.
        @returntype string
        """
        return self._name + '/' + self._tag
    def name(self):
        """##
        Return this <CODE>SimpleTokenType</CODE>'s name.
        
        @return This <CODE>SimpleTokenType</CODE>'s name.
        @returntype string
        """
        return self._name
    def tag(self):
        """##
        Return this <CODE>SimpleTokenType</CODE>'s tag.
        
        @return This <CODE>SimpleTokenType</CODE>'s tag.
        @returntype string
        """
        return self._tag

# Issues of case sensitivity?
def parseTaggedTokenType(string, unknownTag='UNK'):
    """##
    Given the informal string representation of a
    <CODE>TaggedTokenType</CODE>, return the corresponding
    <CODE>TaggedTokenType</CODE>.  The informal representation of a
    <CODE>TaggedTokenType</CODE> has the form
    <CODE><I>name</I>/<I>tag</I></CODE>.  If the string simply has the 
    form <I>name</I>, then <CODE>unknownTag</CODE> is used as its
    tag. <P>

    Note that both names and tags are case sensitive.
    
    @param string The informal string representation of the
           <CODE>TaggedTokenType</CODE> that should be returned.
    @type string string
    @param unknownTag A default tag, used as the tag of the returned
           value if string is simply of the form <I>name</I>.
    @type unknownTag string
    @return The <CODE>TaggedTokenType</CODE> whose informal string
            representation is <CODE>string</CODE>.
    @returntype TaggedTokenType
    """
    _chktype("parseTaggedTokenType", 1, string, (StringType,))
    elts = string.split('/')
    if len(elts) > 1:
        return TaggedTokenType('/'.join(elts[:-1]), elts[-1])
    else:
        return TaggedTokenType(string, unknownTag)
  
##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
  
class TokenizerI:
    """##
    Processing class responsible for separating a string of text into
    a list of <CODE>Token</CODE>s.  This process is also known as
    <I>tokenizing</I> the string of text.  Particular
    <CODE>Tokenizer</CODE>s may split the text at different points, or 
    may produce Tokens with different types of <CODE>TokenType</CODE>.
    """
    def tokenize(self, str):
        """##
        Separate the given string of text into a list of
        <CODE>Token</CODE>s.
        @param str The string of text to tokenize.
        @type str string
        @return A list containing the <CODE>Token</CODE>s
                that are contained in <CODE>str</CODE>.
        @returntype list of Token
        """
        raise AssertionError()

class SimpleTokenizer(TokenizerI):
    """##
    A tokenizer that separates a string of text into Tokens using
    whitespace.  Each word is encoded as a <CODE>Token</CODE> whose
    type is a <CODE>SimpleTokenType</CODE>.
    <CODE>IndexTextLocation</CODE>s are used to encode the
    <CODE>Token</CODE>s' sources.

    <P>More formal definition?
    """
    def tokenize(self, str):
        # Inherit docs from TokenizerI
        words = str.split()
        tokens = []
        for i in range(len(words)):
            source = IndexTextLocation(i)
            token_type = SimpleTokenType(words[i])
            tokens.append(Token(token_type, source))
        return tokens

class TaggedTokenizer(TokenizerI):
    """##
    A tokenizer that splits a string of tagged text into Tokens using
    whitespace.  Each tagged word is encoded as a <CODE>Token</CODE>
    whose type is a <CODE>TaggedTokenType</CODE>.
    <CODE>IndexTextLocation</CODE>s are used to encode the
    <CODE>Token</CODE>s' sources.

    <P>More formal definition?
    """
    def tokenize(self, str):
        # Inherit docs from TokenizerI
        words = str.split()
        tokens = []
        for i in range(len(words)):
            source = IndexTextLocation(i)
            token_type = parseTaggedTokenType(words[i])
            tokens.append(Token(token_type, source))
        return tokens
  
