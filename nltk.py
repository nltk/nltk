#
# Natural Language Toolkit for Python
# Edward Loper
#
# Created [02/26/01 11:24 PM]
# $Id$
#

"""##
foo (error in pydoc)
-@exclude .*Type
@exclude _typemsg
@exclude _Old.*

@variable _type_safety_level The level of type safety to use when
checking the input parameters to methods defined by the Natural
Language Toolkit.  Currently defined values are 0 (no type checking);
1 (check types only); 2 (check types and classes); and 3 (full type
checking).  Note that using level 3 could potentially result in
signifigant loss of efficiency.
"""

from types import *
import re

##################################################
##################################################
##
## The pydoc code is divided into 6 sections:
##     1. Utility Functions
##     2. The Set Class
##     3. Tokens and Tokenizers
##     4. Syntax Trees (commented out)
##     5. Events and Frequency Distributions
##     6. Testing code: Taggers
##
##################################################
##################################################
##
## Current Status of Code:
##     1. Commented
##     2. Commented
##     3. Mainly Commented
##     4. Partially Implemented, commented out.
##     5. Partially Implemented
##     6. Flux
##
##################################################
##################################################
##
## Conventions:
##     * Class names are written LikeThis
##     * Interface names end in "I" LikeThisI
##     * private names start with "_" _like_this
##
##################################################
##################################################


#################################################################
##  UTILITY FUNCTIONS
#################################################################

def make_docs(target='/home/edloper/html/'):
    import pydoc, nltk
    reload(nltk)
    docs=pydoc.doc(nltk)
    pydoc.HTML_Doc(docs).write(target)
    
##//////////////////////////////////////////////////////
##  Type-checking
##//////////////////////////////////////////////////////

# 0 = no type checks
# 1 = just raw types
# 2 = types & classes
# 3 = full type safety
_type_safety_level=3
    
def _typemsg(types):
    """##
    Construct a string naming the given type specification.  This
    function is intended soley for use by _chktype.
    """
    typestr = ''
    for typ in types:
        if type(typ) in (TypeType, ClassType):
            typestr += typ.__name__
        elif type(typ) == ListType:
            typestr += '(list whose elements are: '+_typemsg(typ)+')'
        elif type(typ) == TupleType:
            typestr += '(tuple whose elements are: '+_typemsg(typ)+')'
        else:
            raise AssertionError('Bad arg to typemsg')
        typestr = typestr + ' or'
    return typestr[:-3]

def _chktype(name, n, arg, types):
    """##
    Automated type-checking function for parameters of functions and
    methods.  This function will check to ensure that a given argument
    (<CODE>arg</CODE> matches a type specification
    (<CODE>types</CODE>).  If it does not, it will raise a TypeError
    containing the name of the function or method, the argument
    number, and the allowable types. <P>

    Soon, support will be added for dictionaries.

    @param name The name of the function or method whose parameter's
           type is being checked.
    @type name string

    @param n The position of the parameter whose type is being
             checked.  If it's not a positional parameter, I'm not
             sure what to do yet.
    @type n int

    @param arg The value of the parameter whose type is being
           checked.
    @type arg (any)

    @param types A list of the allowable types.  Each allowable type
           should be either a type (e.g., types.IntType); a class
           (e.g., Token); a list of allowable types; or a tuple of
           allowable types.  If the argument matches any of the
           allowable types, then _chktype will return; otherwise, a
           TypeError will be raised.  Matching is defined as follows:
           <UL>
             <LI> An argument matches a type if its type is equal to
                  that type.
             <LI> An argument matches a class if it is an instance of
                  that class.
             <LI> An arguent matches a list if the argument is a list
                  and each element of the argument matches any element
                  of the allowable type list.
             <LI> An arguent matches a tuple if the argument is a tuple
                  and each element of the argument matches any element
                  of the allowable type tuple.
           </UL>
    @type types List or Tuple
    """
    if _type_safety_level <= 0: return
    if type(types) not in (ListType, TupleType):
        raise AssertionError("_chktype expected a list of types/classes")
    for t in types:
        if type(t) == TypeType:
            if type(arg) == t: return
        elif type(t) == ClassType:
            if _type_safety_level <= 1: return
            if isinstance(arg, t): return
        elif type(t) == ListType:
            if _type_safety_level <= 2: return
            if type(arg) == ListType:
                type_ok = 1
                for elt in arg:
                    try: _chktype(name, n, elt, t)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == TupleType:
            if _type_safety_level <= 2: return
            if type(arg) == TupleType:
                type_ok = 1
                for elt in arg:
                    try: _chktype(name, n, elt, t)
                    except: type_ok = 0
                if type_ok: return
        else:
            raise AssertionError("_chktype expected a valid "+\
                                 "type specification.")

    # Type mismatch -- construct a user-readable error.
    errstr = "argument " + `n` + " to " + name + "() must " +\
             "have type: " + _typemsg(types)
    raise TypeError(errstr)

#################################################################
##  Set class
#################################################################

class Set:
    """##
    An unordered container class that contains no duplicate elements.
    In particular, a set contains no elements e1 and e2 such that
    e1==e2.  Currently, the Set class is given a fairly minimal
    implementation.  However, more members (e.g., to iterate over a
    set) may be defined in the future.

    Although the Set class attempts to ensure that it contains no
    duplicate elements, it can only do so under the following
    circumstances:
    <UL>
      <LI> For all elements ei, ej added to the Set, ei==ej if and
           only if ej==ei.  This should always be the case as long as
           the elements in the Set use well-defined comparison
           functions.  An example where it would not be the case would
           be if ei defined __cmp__() to always return 0, and ej
           defined __cmp__() to always return -1.
      <LI> Mutable elements inserted in the Set are not modified after
           they are inserted.
    </UL>

    If these circumstances are not met, the Set will continue to
    function, but it will no longer guarantee that it contains no
    duplicate elements.
    """
    def __init__(self, *lst):
        """##
        Construct a new Set, containing the elements in
        <CODE>lst</CODE>.  If <CODE>lst</CODE> contains any duplicate
        elements, only one of the elements will be included.  Example
        usage:
          <PRE>
          set = Set('apple', 'orange', 'pear')
          </PRE>
        @param lst The elements that will be contained by the new Set.
        @type lst Any
        """
        self._lst = []
        for elt in lst:
            self.insert(elt)

    def insert(self, elt):
        """##
        Adds the specified element to this Set if it is not already
        present.  Formally, add <CODE>elt</CODE> to this Set if and
        only if this set contains no element <I>ei</I> such that
        <CODE>elt</CODE>==<I>e</I>.

        @param elt The element to insert into the Set.
        @type elt Any
        @returntype None
        """
        if elt not in self._lst:
            self._lst.append(elt)

    def union(self, other):
        """##
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element <I>e</I>
        if and only if either <CODE>self</CODE> or <CODE>other</CODE>
        contain <I>e</I>.
        
        @param other The Set with which this Set will be unioned.
        @type other Set
        @return The union of <CODE>self</CODE> and <CODE>other</CODE>. 
        @returntype Set
        """
        _chktype("union", 1, other, (Set,))
        newSet = apply(Set, self)
        for elt in other._lst:
            newSet.insert(elt)
        return newSet

    def intersection(self, other):
        """##
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element <I>e</I> if and only if both <CODE>self</CODE> and
        <CODE>other</CODE> contain <I>e</I>.
        
        @param other The Set with which this Set will be intersected.
        @type other Set
        @return The intersection of <CODE>self</CODE> and
                <CODE>other</CODE>. 
        @returntype Set
        """
        _chktype("intersection", 1, other, (Set,))
        newSet = apply(Set, self)
        for elt in self._lst:
            if elt not in other._lst:
                newSet._lst.remove(elt)
        return newSet

    # set1 & set2
    def __and__(self, other):
        """##
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element <I>e</I> if and only if both <CODE>self</CODE> and
        <CODE>other</CODE> contain <I>e</I>. <P>

        This method is invoked for expressions of the form
        <CODE>set1 & set2</CODE>.
        
        @param other The Set with which this Set will be intersected.
        @type other Set
        @return The intersection of <CODE>self</CODE> and
                <CODE>other</CODE>. 
        @returntype Set
        """
        return intersection(self, other)

    # set1 | set2
    def __or__(self, other):
        """##
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element <I>e</I>
        if and only if either <CODE>self</CODE> or <CODE>other</CODE>
        contain <I>e</I>. <P>
        
        This method is invoked for expressions of the form
        <CODE>set1 | set2</CODE>.
        
        @param other The Set with which this Set will be unioned.
        @type other Set
        @return The union of <CODE>self</CODE> and <CODE>other</CODE>. 
        @returntype Set
        """
        return union(self, other)

    def contains(self, elt):
        """##
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element <I>e</I> such that <CODE>elt</CODE>==e.
        
        @param elt The element whose presence in the set is to be
               tested.
        @return True if this set contains the given element.
        @returntype boolean
        """
        return elt in self._lst

    # elt in set
    def __contains__(self, elt):
        """##
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element <I>e</I> such that <CODE>elt</CODE>==e.
        
        This method is invoked for expressions of the form
        <CODE>elt in set</CODE>.
        
        @param elt The element whose presence in the set is to be
               tested.
        @return True if this set contains the given element.
        @returntype boolean
        """
        return self.contains(elt)

    def copy(self):
        """##
        Return a copy of this set.  Changes to the copy will not be
        reflected in the original, and vice versa.  However, changes
        to the copy's elements <I>will</I> be reflected in the
        original, and vice versa.  <P>

        Currently, Sets are immutable, so this method has little use.
        However, the Set class may eventually be extended to make Sets 
        mutable.
        
        @return A copy of this set.
        @returntype Set.
        """
        s=Set()
        s._lst = self._lst[:]
        return s

    def __repr__(self):
        """##
        Return the formal string representation of this Set.  Sets
        are formally represented by strings of the form:
        <CODE>Set(elt1, elt2, elt3)</CODE>

        @return The formal string representation of this Set.
        @returntype string
        """
        return 'Set'+`tuple(self._lst)`

    def __str__(self):
        """##
        Return the informal string representation of this Set.  Sets
        are informally represented by strings of the form:
        <CODE>{elt1, elt2, ..., eltn}</CODE>.
        For example, the informal string representation of
        <CODE>Set('apple', 'orange', 'pear')</CODE> is
        <CODE>{'apple', 'orange', 'pear'}</CODE>.

        @return The informal string representation of this Set.
        @returntype string
        """
        return '{'+str(self._lst)[1:-1]+'}'
    
    def __len__(self):
        """##
        Return the number of elements contained in this Set.
        @return The number of elements contained in this Set.
        @returntype int
        """
        return len(self._lst)
    
    def count(self):
        """##
        Return the number of elements contained in this Set.
        @return The number of elements contained in this Set.
        @returntype int
        """
        return len(self._lst)

    def __cmp__(self, other):
        """##
        Return 0 if the given object is equal to this Set.  In
        particular, return 0 if and only if <CODE>other</CODE> is a
        Set, every member of this set is contained in
        <CODE>other</CODE>, and every member of <CODE>other</CODE> is
        contained in this Set.  Otherwise, return a non-zero number.
        
        @param other The object to compare this Set to.
        @type other any
        @return 0 if the given object is equal to this Set.
        @returntype int
        """
        if not isinstance(other, Set): return -1000
        return cmp(self._lst, other._lst)

    def __hash__(self):
        """##
        Return the hash value for this Set.  If two Sets are equal,
        they are guaranteed to have the same hash value.  However, two 
        Sets may have the same hash value and still not be equal.

        @raise TypeError if some element of the set is not a hashable
               type. 
        @return The hash value for this Set.
        @returntype int
        """
        h = 0
        for elt in self._lst:
            h = hash(elt)/2 + h/2
        return h
            
        
    
#################################################################
##  Tokens and Tokenizers
#################################################################

##//////////////////////////////////////////////////////
##  Tokens
##//////////////////////////////////////////////////////

class Token:
    """##
    An occurance of a single unit of text, such as a word or a
    punctuation mark.  A Token consists of a token type and a source.
    The token type is the unit of text (e.g., a specific word).
    Source is the position at which this token occured in the
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
        return str(self._type)+'@'+str(self._source)

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
        raise NotImplementedError()

class IndexTextLocation(TextLocationI):
    """##
    NEEDS DOCS.
    Record the starting index.
    Possibly optionally record a source str/source name?
    Word number or char index or what??
    """
    def __init__(self, index):
        self._index = index
    def __cmp__(self, other):
        if not isinstance(other, IndexTextLocation): return -1000
        return cmp(self._index, other._index)
    def __hash__(self):
        return self.index
    def __str__(self):
        return str(self._index)
    def __repr__(self):
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
        Otherwise,  return a non-zero number.
        
        @param other The object to compare this token type to.
        @type other any
        @return 0 if the given object is equal to this token type.
        @returntype int
        """
        raise NotImplementedError()
    
    def __hash__(self):
        """##
        Compute a hash value for this token types.  All token types
        must implement this function.  A minimal implementation can
        simply return 0 for all token types.
        
        @return The hash value for this token type.
        @returntype int
        """
        raise NotImplementedError()

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
        if not isinstance(other, SimpleToken): return -1000
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
    type's tag is a string representing the name's syntactic category,
    such as \"NN\" or \"VBZ\".  Two <CODE>TaggedTokenType</CODE>s are
    equal if their names are equal and their tags are equal.
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
        if not isinstance(other, SimpleToken): return -1000
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
        raise NotImplementedError()

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
    whitespace.  Each tagged word is encodeed as a <CODE>Token</CODE>
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
  
# #################################################################
# ##  Syntax Trees?
# #################################################################

# class SyntaxNodeI:
#     def tag(self):
#         raise NotImplementedError()
#     def setTag(self, tag):
#         raise NotImplementedError()
#     # also, all list functions??  

# # Case sensitivity?
# class SyntaxNode(SyntaxNodeI):
#     def __init__(self, tag, children=[]):
#         _chktype('SyntaxNode', 1, tag, (StringType,))
#         _chktype('SyntaxNode', 2, children, ([SyntaxNodeI, TokenI],))
#         self._tag = tag
#         self._children = list(children)

#     def __repr__(self):
#         str = '['+self._tag+': '
#         for elt in self._children:
#             str = str + `elt` + ' '
#         return str + ']'

#     def tag(): return self._tag
#     def setTag(self, tag): self._tag = tag

#     def __cmp__(self, other):
#         if not isinstance(other, SyntaxNode): return -1000
#         if len(self) != len(other): return -500
#         for i in range(len(self)):
#             c = cmp(self[i], other[i])
#             if c != 0: return c
#         return 0

#     def __add__(self, lst):
#         _chktype('add', 1, lst, ([SyntaxNodeI, TokenI],))
#         return SyntaxNode(self._tag, self._children+lst)

#     # //////////////////////
#     # List-type functions
#     # These are basically just wrappers, with appropriate
#     # type-checking added.
#     # //////////////////////
#     def append(self, elt):
#         _chktype('append', 1, elt, (SyntaxNodeI, TokenI))
#         self._children.append(elt)

#     def extend(self, lst):
#         _chktype('extend', 1, lst, ([SyntaxNodeI, TokenI],))
#         self._children.extend(lst)

#     def count(self):
#         return self._children.count()

#     def index(self, elt):
#         _chktype('index', 1, elt, (SyntaxNodeI, TokenI))
#         return self._children.index(elt)

#     def insert(self, index, elt):
#         _chktype('insert', 1, index, (IntType,))
#         _chktype('insert', 2, elt, (SyntaxNodeI, TokenI))
#         self._children.insert(index, elt)

#     def pop(self):
#         return self._children.pop()

#     def remove(self, elt):
#         _chktype('remove', 1, elt, (SyntaxNodeI, TokenI))
#         self._children.remove(elt)

#     def reverse(self):
#         self._children.reverse()

#     def sort(self, func=cmp):
#         self._children.sort(func)

#     def __len__(self):
#         return len(self._children)

#     def __getitem__(self, index):
#         _chktype('__getitem__', 1, index, (IntType, SliceType))
#         if type(index) == IntType: return self._children[index]
#         else: return self._children[index.start:index.end]

#     def __setitem__(self, index, elt):
#         _chktype('__setitem__', 1, index, (IntType, SliceType))
#         _chktype('__setitem__', 2, elt, (SyntaxNodeI, TokenI))
#         if type(index) == IntType: self._children[index] = elt
#         else: self._children[index.start:index.end] = elt
      
#     def __delitem__(self, index):
#         _chktype('__delitem__', 1, index, (IntType, SliceType))
#         if type(index) == IntType: del self._children[index]
#         else: del self._children[index.start:index.end]

#################################################################
##  Events & Frequency Distributions
#################################################################

##//////////////////////////////////////////////////////
##  Sample
##//////////////////////////////////////////////////////
  
# A sample can be any Python object that is not an Event.  Typical
# examples are tokens, lists of tokens, sets of tokens.  Samples can't be 
# Functions, either.
# Every sample must define == correctly (and __hash__)
  
##//////////////////////////////////////////////////////
##  Event
##//////////////////////////////////////////////////////

# Comparison of events!?!??
class _OldEvent:
    """##
    The <CODE>Event</CODE> class represents events in a probability
    space.  An <CODE>Event</CODE> is defined with respect to a
    sample space, and can be thought of as a subset of that sample
    space.  <CODE>Event</CODE>s can be defined either by specifying
    the samples that make them up, or by means of a function.  <P/>

    For example, consider the sample space composed of all integers.
    We can define the following <CODE>Event</CODE>s in that sample
    space:
    <PRE>
    e1 = Event(1, 2, 3)
    e2 = Event(lambda x: x>0)
    </PRE>

    We can also test whether a sample is contained in an event:
    <PRE>
    if 1 in e1: print 'Event e1 contains 1'
    </PRE>

    Should we be able to test for subset?
    <PRE>
    if e1.is_subset(e2): print 'Event e1 is a subset of event e2'
    </PRE>
    """
    # check whether all members of source are not functions or Events??
    def __init__(self, *source):
        self._range = None
        if len(source) == 0:
            raise TypeError("Event expected at least 1 argument")
        if (len(source) == 1) and (type(source[0]) == FunctionType):
            self._func = source[0]
            self._set = None
        else:
            self._func = None
            self._set = apply(Set, source)

    def contains(self, sample):
        if self._func:
            return self._func(sample)
        elif self._set:
            return sample in self._set
        else: raise AssertionError('Bad Event')
          
    def __contains__(self, elt):
        return self.contains(elt)

    def toSet(self, sample_space):
        _chktype("toSet", 1, sample_space, (Set,))
        if self._set:
            return self._set.union(sample_space)
        elif self._func:
            self._set = Set()
            for elt in sample_space:
                if self._func(elt):
                    self._set.append(elt)
            return self._set
        else: raise AssertionError('Bad Event')
  
    def toFunc(self):
        if self._func:
            return self._func
        elif self._set:
            return (lambda x:x in self._set)
        else: raise AssertionError('Bad Event')

class EventI:
    """##
    An event
    """
    def __contains__(self, sample):
        raise NotImplementedError()
    def contains(self, sample):
        raise NotImplementedError()
    def __cmp__(self, other): # ok not to implement!
        raise NotImplementedError()

class SampleEvent(EventI):
    def __init__(self, sample):
        self._sample = sample
    def __contains__(self, sample):
        return sample == self._sample
    def contains(self, sample):
        return sample == self._sample
  
class SetEvent(EventI):
    def __init__(self, set):
        self._set = set
    def __contains__(self, sample):
        return sample in self._set
    def contains(self, sample):
        return sample in self._set

class FuncEvent(EventI):
    def __init__(self, func):
        self._func = func
    def __contains__(self, sample):
        return self._func(sample) != 0
    def contains(self, sample):
        return self._func(sample) != 0

##//////////////////////////////////////////////////////
##  Frequency Distribution
##//////////////////////////////////////////////////////

class FreqDistI:
    """##
    Interface definition for Frequency Distribution classes.  This
    class specifies all functions that any Frequency Distribution
    should implement.  Frequency Distribution classes should be
    inherited from <CODE>FreqDistI</CODE>. <P>

    A frequency distribution is used to represent the relative
    frequencies of a set of samples, all from the same sample space.
    For example, it could be used to record the frequency of each word 
    in a document.  Frequency distributions are generally constructed
    by incrementing the count for a sample every time it is
    encountered in some source.  For example, the following code will
    produce a frequency distribution representing the frequency of
    each word in a document:
    <PRE>
    freqDist = SomeFreqDistClass()
    for word in document:
        freqDist.inc(word)
    </PRE>

    The Frequency Distribution interface defines a number of functions
    for finding statistics about a frequency distribution:
    <UL>
      <LI> N: the total number of samples
      <LI> count(e): the total number of samples that are in event e.
      <LI> freq(e): count(e)/N
      <LI> cond_freq(e, c): count(e&c)/count(c)
    </UL>
    """
    def inc(self, sample):
        raise NotImplementedError()
    def N(self):
        raise NotImplementedError()
    def freq(self, event):
        raise NotImplementedError()
    def count(self, event):
        raise NotImplementedError()
    def cond_freq(self, event, condition): 
        raise NotImplementedError()
    def sampleSet(self):
        """## Return a set containing all samples that make up this
        FreqDist. """
        raise NotImplementedError()

class SimpleFreqDist:
    def __init__(self):
        self._dict = {}
        self._N = 0

    def inc(self, sample):
        self._N += 1
        if self._dict.has_key(sample):
            self._dict[sample] += 1
        else:
            self._dict[sample] = 1

    def N(self):
        return self._N

    def count(self, event):
        # If it's a sample, the answer is easy.
        if not isinstance(event, EventI):
            if self._dict.has_key(event):
                return self._dict[event]
            else:
                return 0

        # If it's a full-fledged event, do a search..  This is slow.
        count = 0
        for (key, c) in self._dict.items():
            if key in event:
                count += c
        return count

    def freq(self, event):
        return float(self.count(event))/self.N()

    def cond_freq(self, event, condition):
        if not isinstance(event, EventI):
            event = SampleEvent(event)
        if not isinstance(condition, EventI):
            condition = SampleEvent(condition)

        e_count = 0
        c_count = 0
        for (sample, c) in self._dict.items():
            if sample in condition:
                c_count += c
                if sample in event:
                    e_count += c
        if c_count == 0: return None
        else: return float(e_count)/c_count

    # Have a default of the universal set for event?
    def max_freq_sample(self, condition):
        """##
        Return the sample with the highest frequency, under the given
        condition. 
        """
        max_freq = -1
        max_sample = None
        for sample in self._dict.keys():
            freq = self.cond_freq(sample, condition)
            if freq > max_freq:
                max_sample = sample
                max_freq = freq
        return max_sample

    def __str__(self):
        return repr(self._dict)

  
  
##//////////////////////////////////////////////////////
##  Context-Feature Samples
##//////////////////////////////////////////////////////

class CFSample:
    """##
    A sample consisting of a context and a feature.
    <CODE>CFSample</CODE>s are intended to be used as sample points
    for <CODE>FreqDist</CODE>s.  For example:
    <PRE>
    for (context, feature) in samples:         # Train
        freqDist.inc( CFSample(context, feature) )
    for context in contexts:                   # Tag new data
        context_event = CFSample_context_event(context)
        print freqDist.max_freq_sample(context_event).feature()
    </PRE>
    @see(nltk.CFSample_context_event) CFSample_context_event()
    """
    def __init__(self, context, feature):
        self._context = context
        self._feature = feature
    def context(self): return self._context
    def feature(self): return self._feature
    def __str__(self):
        return '('+str(self._context)+', '+str(self._feature)+')'
    def __repr__(self):
        return 'CFSample('+repr(self._context)+', '+\
               repr(self._feature)+')'
    def __cmp__(self, other):
        c = cmp(self._context, other._context)
        if c != 0: return c
        else: return cmp(self._feature, other._feature)
    def __hash__(self):
        return hash(self._context)/2+hash(self._feature)/2
  
class ContextEvent(EventI):
    def __init__(self, context):
        self._context = context
    def __contains__(self, sample):
        return sample.context() == self._context
    def contains(self, sample):
        return sample.context() == self._context
    def context(self):
        return self._context
  
class CFFreqDist(FreqDistI):
    def __init__(self):
        self._dict = {}
        self._N = 0
        self._cond_N = {}

    def inc(self, sample):
        _chktype("CFFreqDist.inc", 1, sample, (CFSample,))
        self._N += 1
        if self._dict.has_key(sample.context()):
            self._cond_N[sample.context()] += 1
            if self._dict[sample.context()].has_key(sample.feature()):
                self._dict[sample.context()][sample.feature()] += 1
            else:
                self._dict[sample.context()][sample.feature()] = 1
        else:
            self._cond_N[sample.context()] = 1
            self._dict[sample.context()] = {sample.feature():1}

    def N(self):
        return self._N

    def count(self, event):
        _chktype("CFFreqDist.count", 1, event, (CFSample, ContextEvent))
        if type(event) == CFSample:
            if self._dict.has_key(event.context()) and \
               self._dict[event.context()].has_key(event.feature()):
                return self._dict[event.context()][event.feature()]
            else:
                return 0
        else:
            if self._cond_N.has_key(event.context()):
                return self._cond_N[event.context()]
            else:
                return 0

    def cond_freq(self, event, condition):
        """##
        Condition must be a ContextEvent
        """
        _chktype("CFFreqDist.cond_freq", 1, event, (CFSample,))
        _chktype("CFFreqDist.cond_freq", 2, condition, (ContextEvent,))
        feature = event.feature()
        context = condition.context()
        if not self._dict.has_key(context) or \
           not self._dict[context].has_key(feature):
            return 0.0
        return float(self._dict[context][feature]) / self._cond_N[context]

    def max_freq_sample(self, condition):
        _chktype("CFFreqDist.max_freq_sample", 1, condition, (ContextEvent,))
        context = condition.context()
        if not self._dict.has_key(context): return None
        max_freq = -1
        max_feature = None
        for (feature, freq) in self._dict[context].items():
            if freq > max_freq:
                max_feature = feature
                max_freq = freq
        if max_feature == None: return None
        else: return CFSample(context, max_feature)

    def __str__(self):
        return repr(self._dict)
        
#################################################################
##  Trial -- stuff needed for pset 2
#################################################################

def shift_in(lst, elt):
    if len(lst) > 0:
        del lst[0]
        lst.append(elt)
  
class TaggerI:
    """##
    Interface for taggers, which map [Word] -> [TaggedWord]
    """
    def tag(self, words): 
        raise NotImplementedError()

class NN_CD_Tagger(TaggerI):
    def __init__(self): pass
    def tag(self, tokens):
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
    def __init__(self, n):
        self._n = n
        self._freqDist = CFFreqDist()

    def train(self, tagged_tokens):
        # prev_tags is a list of the previous n tags that we've assigned.
        prev_tags = ['UNK' for x in range(self._n)]
      
        for token in tagged_tokens:
            context = tuple(prev_tags+[token.type().name()])
            feature = token.type().tag()
            self._freqDist.inc( CFSample(context, feature) )

            # Update prev_tags
            shift_in(prev_tags, token.type().tag())

    def tag(self, tokens):
        tagged_tokens = []
      
        prev_tags = ['UNK' for x in range(self._n)]
        for token in tokens:
            # Predict the next tag
            context = tuple(prev_tags+[token.type().name()])
            context_event = ContextEvent(context)
            sample = self._freqDist.max_freq_sample(context_event)
            if sample: tag = sample.feature()
            else: tag = 'UNK'

            # Update words
            token_type = TaggedTokenType(token.type().name(), tag)
            tagged_tokens.append(Token(token_type, token.source()))

            # Update prev_tags
            shift_in(prev_tags, tag)

        return tagged_tokens

class FallbackTagger(TaggerI):
    def __init__(self, taggers, unknown_tag):
        self._unk = unknown_tag
        self._taggers = taggers

    def tag(self, tokens):

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
    tokens=TaggedTokenizer().tokenize(open('foo.test', 'r').read())

    t0 = NthOrderTagger(0)
    t0.train(tokens)

    t1 = NthOrderTagger(1)                
    t1.train(tokens)

    ft = FallbackTagger( (t1, t0, NN_CD_Tagger()), 'UNK')
    s = ''
    for t in ft.tag(tokens): s += str(t.type())
    return s
    
