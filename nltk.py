#
# Natural Language Toolkit for Python
# Edward Loper
#
# Created [02/26/01 11:24 PM]
# $Id$
#

"""##
The Natural Language Toolkit is a package intended to simplify the
task of programming natural language systems.  It is intended to be
used as a teaching tool, not as a basis for building production
systems. <P>

<H1> Interfaces </H1>

The Natural Language Toolkit is implemented as a set of interfaces and
classes.  Interfaces are a concept loosely borrowed from Java.  They
are essentially a specification of a set of methods.  Any class that
implements all of an interface's methods according to the interface's
specification are said to \"implement\" that interface. <P>

In the context of this toolkit, an interface is implemented as a
class, all of whose methods simply raise AssertionError.  The
__doc__ strings of these methods, together with the methods'
declarations,  provide specifications for the methods. <P>

Interface classes are named with a trailing \"I\", such as
<CODE>TokenizerI</CODE> or <CODE>EventI</CODE>.

<H1> Interface and Class Hierarchy </H1>

The classes defined by the Natural Language Toolkit can be divided
into two basic categories: Data classes; and Processing (or
Task-Oriented) Classes.

<H2> Data Classes </H2>

Data classes are used to store several different types of information
that are relavant to natural language processing.  Data classes can
generally be grouped into small clusters, with minimal interaction
between the clusters.  The clusters that are currently defined by the
Natural Language Toolkit are listed below.  Under each cluster, the
top-level classes and interfaces contained in that cluster are given.

<UL>
  <LI> <B>Sets</B>: Encodes the mathmatical notion of a \"finite set\".
  <UL>
    <LI> <A coderef='nltk.Set'>Set</A>: A finite set.
  </UL>
  <LI> <B>Tokens</B>: Encodes units of text such as words.
  <UL>
    <LI> <A coderef='nltk.TokenTypeI'>TokenTypeI</A>:
         A unit of text.
    <LI> <A coderef='nltk.TextLocationI'>TextLocationI</A>:
         A location within a text.
    <LI> <A coderef='nltk.Token'>Token</A>:
         An occurance of a unit of text.
         Consists of a TokenType and a TextLocation.
  </UL>
  <LI> <B>Syntax Trees</B>: Encodes syntax trees.  Not fully designed 
        yet.
  <LI> <B>Probability</B>: Encodes data structures associated with
        the mathmatical notion of probability, such as events and
        frequency distributions.
  <UL>
    <LI> Sample: Encodes the mathmatical notion of a
          \"sample\".  This is actually not implemented as a class or
          an interface -- (almost) anything can be a Sample.
    <LI> <A coderef='nltk.EventI'>EventI</A>:
         A (possibly infinite) set of samples.
    <LI> <A coderef='nltk.FreqDistI'>FreqDistI</A>:
          The frequency distribution of a collection of samples.
    <LI> <A coderef='nltk.ProbDistI'>ProbDistI</A>:
          A probability distribution, typically derived from a
          frequency distribution (e.g., using ELE).
  </UL>
</UL>

<H2> Processing Classes </H2>

Processing classes are used to perform a variety of tasks that are
relavant to natural language processing.  Processing classes can
generally be grouped into small clusters, with minimial interaction
between the clusters.  Each cluster typically makes use of several
data-class clusters.  The processing clusters that are currently
defined by the Natural Language Toolkit are listed below.  Under each
cluster, the interfaces contained in that cluster are given.

<UL>
  <LI> <B>Tokenizers</B>: Separate a string of text into a list of
       Tokens. 
  <UL>
     <LI> <A coderef='nltk.TokenizerI'>TokenizerI</A>
  </UL>
  <LI> <B>Taggers</B>: Assign tags to each Token in a list of Tokens.
  <UL>
     <LI> <A coderef='nltk.TaggerI'>TaggerI</A>
  </UL>
  <LI> <B>Language Model</B>: (not yet designed/implemented)
  <LI> <B>Parser</B>: (not yet designed/implemented)
</UL>

<H1> Open Questions </H1>

The following is a list of currently unresolved questions, pertaining
to currently implemented interfaces and classes.
<UL>
  <LI> Terminology/Naming Questions
  <UL>
    <LI> Is \"Token Type\" too easily confusable with the notion of
         type in python?  E.g., names like SimpleTokenType suggest
         that they are similar to StringType, IntType, etc. when they
         are very different.  I could use \"TokenTyp\" to distinguish, 
         but this also seems somewhat confusing to the uninitiated.
    <LI> What name can be used for the \"word content\" of a token
         type?  Currently, <CODE>name</CODE> is used, but that's not a 
         very intuitive name.  <CODE>word</CODE> might be used,
         although often times the string is not a word (e.g., \".\").
  </UL>
  <LI> Is the token/token type/text location system too complex?
       Often, one only cares about the token type.  E.g., a tokenizer
       could be defined as mapping string to list of TokenType, and a
       tagger as mapping list of SimpleTokenType to TaggedTokenType.
       But sometimes we really need to be able to distinguish tokens,
       not just token types.. e.g., to test the chunk parser from the
       chunk parsing problem set.
  <LI> How should text locations be represented?  character index?
       token index?  To some extent, it dosen't matter, as long as
       __cmp__ is properly defined.  Should text locations have ranges 
       or just starting points?  etc.
</UL>

@exclude .*(?!Token).....Type
@exclude ....Type
@exclude ...Type
@exclude _typemsg
@exclude _Old.*

@variable _type_safety_level The level of type safety to use when
checking the input parameters to methods defined by the Natural
Language Toolkit.  Currently defined values are:
<UL>
  <LI> 0: no type checking
  <LI> 1: check types only
  <LI> 2: check types and classes
  <LI> 3: check types, classes, list contents, and tuple contents
  <LI> 4: check types, classes, list contents, tuple contents, and
       dictionary contents.
</UL>
Higher levels of type safety (3-4) can result in signifigant loss of
efficiency. 
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
# 3 = types, classes, lists, & tuples
# 4 = full type safety (types, classes, lists, tuples, dictionaries)
_type_safety_level=4
    
def _typemsg(types):
    """##
    Construct a string naming the given type specification.  This
    function is intended soley for use by _chktype.  However, it can
    also be useful in making sure that you got your type
    specification correct.
    """
    typestr = ''
    for typ in types:
        if type(typ) in (TypeType, ClassType):
            typestr = typestr + typ.__name__ + ' or'
        elif type(typ) == ListType:
            typestr = typestr + '(list whose elements are: '+ \
                      _typemsg(typ)+') or'
        elif type(typ) == TupleType:
            typestr = typestr + '(tuple whose elements are: '+ \
                      _typemsg(typ)+') or'
        elif type(typ) == DictType:
            for (key, val) in typ.items():
                typestr = typestr + '(dictionary from ' + \
                          _typemsg((key,)) + ' to ' + _typemsg(val) + \
                          ') or'
        else:
            raise AssertionError('Bad arg to typemsg')
    return typestr[:-3]

def _chktype(name, n, arg, types, d=0):
    """##
    Automated type-checking function for parameters of functions and
    methods.  This function will check to ensure that a given argument
    (<CODE>arg</CODE> matches a type specification
    (<CODE>types</CODE>).  If it does not, it will raise a TypeError
    containing the name of the function or method, the argument
    number, and the allowable types. <P>

    This function has a well-defined interface, and is designed for
    efficient use; however, it should not necessarily be used by users 
    of the toolkit, since it is somewhat advanced. <P>

    This method does NOT handle recursive structures well; in
    particular, recursive arguments may cause it to enter an infinite
    loop. 

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
           (e.g., Token); a list of allowable types; a tuple of
           allowable types; or a dictionary from allowable types to
           lists of allowable types.  If the argument matches any of
           the allowable types, then _chktype will return; otherwise,
           a TypeError will be raised.  Matching is defined as
           follows:
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
             <LI> An argument matches a dictionary if the argument is
                  a dictionary and for each (key, value) pair of the
                  argument, there is some (key_t, value_t) pair in the
                  allowable type dictionary such that key matches
                  key_t and value matches some element of value_t.
           </UL>
    @type types List or Tuple
    @see _type_safety_level
    """
    # Unfortunately, this code is not really commented right now.
    # It's by far the most complex/advanced code in this module, and
    # isn't really intended to be played with.  It should be possible,
    # if not easy, to figure out how it works, given its definition in 
    # the __doc__ string.  I'll comment it one day, though.
    if _type_safety_level <= 0: return
    _DEBUG=0
    if _DEBUG: print ' '*d, 'Check', name, n, arg, types
    if type(types) not in (ListType, TupleType):
        raise AssertionError("_chktype expected a list of types/classes")
    for t in types:
        if type(t) == TypeType:
            if type(arg) == t: return
        elif _type_safety_level <= 1:
            return
        elif type(t) == ClassType:
            if isinstance(arg, t): return
        elif type(t) == ListType:
            if type(arg) == ListType:
                if _type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: _chktype(name, n, elt, t, d+4)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == TupleType:
            if type(arg) == TupleType:
                if _type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: _chktype(name, n, elt, t, d+4)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == DictType:
            if type(arg) == DictType:
                if _type_safety_level <= 3: return
                type_ok = 1
                for key in arg.keys():
                    if t.has_key(type(key)):
                        try: _chktype(name, n, arg[key], t[type(key)], 
                                      d+4)
                        except: type_ok = 0
                    elif type(key) in (ListType, TupleType, DictType):
                        subtype_ok = 0
                        for t_key in t.keys():
                            if type(key) == type(t_key):
                                try:
                                    _chktype(name, n, key, (t_key,), d+4)
                                    _chktype(name, n, arg[key],
                                             t[t_key], d+4)
                                    subtype_ok = 1
                                except: pass
                        if not subtype_ok: type_ok = 0
                    else:
                        type_ok = 0
                if type_ok: return
        else:
            raise AssertionError("_chktype expected a valid "+\
                                 "type specification.")

    if _DEBUG: print ' '*d, 'raising on', arg
    # Type mismatch -- construct a user-readable error.
    errstr = "\n  Argument " + `n` + " to " + name + "() must " +\
             "have type: "
    typestr = _typemsg(types)
    if len(typestr) + len(errstr) <= 75:
        raise TypeError(errstr+typestr)
    else:
        raise TypeError(errstr+'\n      '+typestr)

#################################################################
##  Set class
#################################################################

class Set:
    """##

    An unordered container class that contains no duplicate elements.
    In particular, a set contains no elements e1 and e2 such that
    e1==e2.  Currently, the <CODE>Set</CODE> class is given a fairly
    minimal implementation.  However, more members (e.g., to iterate
    over a set) may be defined in the future.

    Although the <CODE>Set</CODE> class attempts to ensure that it
    contains no duplicate elements, it can only do so under the
    following circumstances:
    
    <UL>
      <LI> For all elements ei, ej added to the <CODE>Set</CODE>,
           ei==ej if and only if ej==ei.  This should always be the
           case as long as the elements in the <CODE>Set</CODE> use
           well-defined comparison functions.  An example where it
           would not be the case would be if ei defined
           <CODE>__cmp__</CODE>() to always return 0, and ej defined
           <CODE>__cmp__</CODE>() to always return -1.
           
      <LI> Mutable elements inserted in the <CODE>Set</CODE> are not
           modified after they are inserted.
    </UL>

    If these circumstances are not met, the <CODE>Set</CODE> will
    continue to function, but it will no longer guarantee that it
    contains no duplicate elements.
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

        This method is invoked for expressions of the form:
        <PRE>
          set1 & set2
        </PRE>.
        
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
        
        This method is invoked for expressions of the form:
        <PRE>
          set1 | set2
        </PRE>.
        
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
        element <I>e</I> such that <CODE>elt</CODE>==<I>e</I>.
        
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
        element <I>e</I> such that <CODE>elt</CODE>==<I>e</I>.
        
        This method is invoked for expressions of the form:
        <PRE>
          elt in set
        </PRE>
        
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
        <PRE>
          {elt1, elt2, ..., eltn}
        </PRE>. 
        For example, the informal string representation of
        <CODE>Set('apple', 'orange', 'pear')</CODE> is:
        <PRE>
          {'apple', 'orange', 'pear'}
        </PRE>

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

    def elements(self):
        """##
        Return a <CODE>list</CODE> of the elements in this
        <CODE>Set</CODE>.  Changes to this <CODE>list</CODE> will not
        be reflected in the <CODE>Set</CODE>, and changes in the
        <CODE>Set</CODE> will not be reflected in this
        <CODE>list</CODE>.  This function is intended to allow
        iteration over a Set.
        """
        # We have to make a copy of the list.
        return self._lst[:]

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
        raise AssertionError()

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
        Otherwise, return a non-zero number.
        
        @param other The object to compare this token type to.
        @type other any
        @return 0 if the given object is equal to this token type.
        @returntype int
        """
        raise AssertionError()
    
    def __hash__(self):
        """##
        Compute a hash value for this token types.  All token types
        must implement this function.  A minimal implementation can
        simply return 0 for all token types.
        
        @return The hash value for this token type.
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
#         raise AssertionError()
#     def setTag(self, tag):
#         raise AssertionError()
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

class EventI:
    """##
    A subset of the samples that compose some sample space.  Note that 
    this subset need not be finite.  Events are typically written as
    the set of samples they contain, or as a function in first order
    logic.  Examples are:
    <PRE>
      {1,2,3}
      {x:x>0}
    </PRE>

    The only method that events are required to implement is
    <CODE>__contains__()</CODE>, which tests whether a sample is a
    contained by the event.  However, when possible, events should
    also define the following methods:
    <UL>
      <LI> <CODE>__cmp__()</CODE>, which tests whether this event is
           equal to another event.
      <LI> <CODE>subset()</CODE>, which tests whether this event is a
           subset of another event.
      <LI> <CODE>superset()</CODE>, which tests whether this event is
           a superset of another event.
      <LI> <CODE>union()</CODE>, which returns an event containing the
           union of this event's samples and another event's samples.
      <LI> <CODE>intersection()</CODE>, which returns an event
           containing the intersection of this event's samples and
           another event's samples.
      <LI> <CODE>samples()</CODE>, which returns a <CODE>Set</CODE>
           containing all of the samples that are contained by this
           event. 
      <LI> <CODE>__len__()</CODE>, which returns the number of samples 
           contained by this event.
    </UL>
    
    Classes implementing the <CODE>EventI</CODE> interface may choose
    to only support certain classes of samples, or may choose to only
    support certain types of events as arguments to the optional
    methods (<CODE>__cmp__</CODE>, <CODE>subset</CODE>, etc.).  If a
    method is unable to return a correct result because it is given an 
    unsupported type of sample or event, it should raise a
    NotImplementedError.  (?? is this the right exception? use
    NotSupportedError? ValueError? ??)
    """
    def __contains__(self, sample):
        """##
        Return true if and only if the given sample is contained in
        this event.  Return false if <CODE>sample</CODE> is not a
        supported type of sample for this <CODE>Event</CODE> class.
        
        @return A true value if and only if the given sample is
        contained in this event.
        @returntype boolean
        """
        raise AssertionError()
    
    def contains(self, sample):
        """##
        Return true if and only if the given sample is contained in
        this event.  Return false if <CODE>sample</CODE> is not a
        supported type of sample for this <CODE>Event</CODE> class.
        
        @return A true value if and only if the given sample is
        contained in this event.
        @returntype boolean
        """
        return self.__contains__(sample) # Is this ok?????
    
    def __cmp__(self, other):
        # ok not to implement!
        """##
        Return 0 if the given object is equal to the event.  Formally, 
        return 0 if and only if every sample contained by this event
        is also contained by <CODE>other</CODE>, and every sample
        contained by <CODE>other</CODE> is contained by this event.
        Otherwise, return some nonzero number.
        
        @param other The object to compare this event to.
        @type other Event
        @return 0 if the given object is equal to this event.
        @returntype int
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        @raise NotImplementedError If <CODE>other</CODE> is not an
               Event, or is not a supported Event type.
        """
        raise NotImplementedError()
    
    def subset(self, other):
        """##
        Return true if this event is a subset of the given 
        event.  Formally, return true if and only if every sample
        contained by this event is contained by <CODE>other</CODE>.
        
        @param other The object to compare this event to.
        @type other Event
        @return true if this event is a subset of the given event.
        @returntype boolean
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        @raise NotImplementedError If <CODE>other</CODE> is not a
               supported Event type.
        """
        # ok not to implement!
        raise NotImplementedError()
    
    def superset(self, other):
        """##
        Return true if this event is a superset of the given 
        event.  Formally, return true if and only if every sample
        contained by <CODE>other</CODE> is contained by this event.
        
        @param other The object to compare this event to.
        @type other Event
        @return true if this event is a superset of the given event.
        @returntype boolean
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        @raise NotImplementedError If <CODE>other</CODE> is not a
               supported Event type.
        """
        # ok not to implement!
        raise NotImplementedError()
    
    def samples(self):
        """##
        Return a <CODE>Set</CODE> containing all of the samples
        contained by this event.  The effects of changes to this
        <CODE>Set</CODE> on the <CODE>Event</CODE> are undefined.  The 
        effects of changes to the <CODE>Event</CODE> on this
        <CODE>Set</CODE> are also undefined.
        
        @return The set of samples contained in this event.
        @returntype Set
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        """
        # ok not to implement!
        raise NotImplementedError()

    def __len__(self):
        """##
        Return the number of samples contained by this event.  If this 
        event contains an infinite number of samples, return None.  If 
        this event is unable to determine how many samples are
        contained, raise NotImplementedError.

        @return The number of samples contained by this event.
        @returntype int
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        """
    def union(self, other):
        """##
        Return an event containing the union of this event's samples
        and another event's samples.  Formally, return an event that
        contains a sample if and only if either self or other contains 
        that sample.

        @param other The <CODE>Event</CODE> with which to union this
               <CODE>Event</CODE>.
        @type other Event
        @return An event containing the union of this event's samples
                and another event's samples.
        @returntype Event
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        @raise NotImplementedError If <CODE>other</CODE> is not a
               supported Event type.
        """
        raise NotImplementedError()
    
    def intersection(self, other):
        """##
        Return an event containing the intersection of this event's
        samples and another event's samples.  Formally, return an
        event that contains a sample if and only if both self and
        other contains that sample.

        @param other The <CODE>Event</CODE> with which to intersection
               this <CODE>Event</CODE>.               
        @type other Event
        @return An event containing the intersection of this event's
                samples and another event's samples.
        @returntype Event
        @raise NotImplementedError If this method is not implemented
               by this Event class.
        @raise NotImplementedError If <CODE>other</CODE> is not a
               supported Event type.
        """
        raise NotImplementedError()
    

class SampleEvent(EventI):
    """##
    An <CODE>Event</CODE> containing a single sample.
    """
    def __init__(self, sample):
        """##
        Construct a new <CODE>SampleEvent</CODE>, containing only the
        given sample.
        @param sample The sample that the new event should contain.
        @type sample any
        """
        self._sample = sample
    def __contains__(self, sample):
        # Inherit docs from EventI
        return sample == self._sample
    def contains(self, sample):
        # Inherit docs from EventI
        return sample == self._sample
    def __cmp__(self, other):
        # Inherit docs from EventI
        return self.samples() == other.samples()
    def subset(self, other):
        # Inherit docs from EventI
        return self._sample in other
    def superset(self, other):
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return self._sample == other._sample
        elif isinstance(other, SetEvent):
            return (len(other) == 0) or \
                   (len(other) == 1 and self._sample in other)
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def samples(self):
        # Inherit docs from EventI
        return Set(self._sample)
    def __len__(self):
        # Inherit docs from EventI
        return 1
    def sample(self):
        """##
        Return the single sample contained by this
        <CODE>SampleEvent</CODE>.
        @return The single sample contained by this
        <CODE>SampleEvent</CODE>.
        @returntype any
        """
        return self._sample
  
class SetEvent(EventI):
    """##
    An <CODE>Event</CODE> whose samples are defined by a Set.
    """
    def __init__(self, set):
        """##
        Construct a new <CODE>SetEvent</CODE>, whose samples are the
        elements of the given set.
        @param set The set of samples that the new event should
               contain.
        @type set Set
        """
        self._set = set
    def __contains__(self, sample):
        # Inherit docs from EventI
        return sample in self._set
    def contains(self, sample):
        # Inherit docs from EventI
        return sample in self._set
    def __cmp__(self, other):
        # Inherit docs from EventI
        return self.samples() == other.samples()
    def subset(self, other):
        # Inherit docs from EventI
        for elt in self._set.elements():
            if elt not in other: return 0
        return 1
    def superset(self, other):
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return other.sample() in self
        elif isinstance(other, SetEvent):
            return other.subset(self)
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def samples(self):
        # Inherit docs from EventI
        # Make a copy -- it's safer.
        return self._set.copy()
    def __len__(self):
        # Inherit docs from EventI
        return len(self._set)

class FuncEvent(EventI):
    """##
    An <CODE>Event</CODE> whose samples are defined by a function.
    This function should return 1 for any samples contained in the
    <CODE>Event</CODE>, and 0 for any samples not contained in the
    <CODE>Event</CODE>.  <CODE>FuncEvent</CODE>s are often created
    using <CODE>lambda</CODE> expressions.  Examples, with their
    corresponding sets, are:
    <PRE>
    e1 = FuncEvent(lambda x:x>3)            <I>{x:x>3}</I>
    e2 = FuncEvent(lambda x:x[0:2]=='hi')   <I>{x:x[0:2]=='hi'}</I>
    </PRE>
    """
    def __init__(self, func):
        """##
        Construct a new <CODE>FuncEvent</CODE> from the given
        function.  The function should return 1 for any samples
        contained in the <CODE>Event</CODE>, and 0 for any samples not 
        contained in the <CODE>Event</CODE>.
        @param func A function specifying what samples are in this
               <CODE>Event</CODE>.
        @type func Function or BuiltinFunction
        """
        self._func = func
    def __contains__(self, sample):
        return self._func(sample) != 0
    def contains(self, sample):
        return self._func(sample) != 0
    def __cmp__(self, other):
        "## Not implemented by this Event class."
        raise NotImplementedError()
    def subset(self, other): 
        "## Not implemented by this Event class."
        raise NotImplementedError()
    def superset(self, other):
        # Inherit docs from EventI
        if isinstance(other, SampleEvent):
            return other.sample() in self
        elif isinstance(other, SetEvent):
            for elt in other.samples().elements():
                if elt not in self: return 0
            return 1
        else:
            raise NotImplementedError()
    def union(self, other): 
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a and x in b))
        return FuncEvent(f)
    def intersection(self, other):
        # Inherit docs from EventI
        f = (lambda x, a=self, b=other:(x in a or x in b))
        return FuncEvent(f)
    def samples(self):
        "## Not implemented by this Event class."
        raise NotImplementedError()
    def __len__(self): 
        "## Not implemented by this Event class."
        raise NotImplementedError()

class NullEvent(EventI):
    """##
    An event that contains no samples.
    """
    def __contains__(self, sample): return 0
    def contains(self, sample): return 0
    def __cmp__(self, other): return len(other)==0
    def subset(self, other): return 1
    def superset(self, other): return len(other)==0
    def union(self, other): return other
    def intersection(self, other): return self
    def samples(self): return Set()
    def __len__(self): return 0

class UniversalEvent(EventI):
    """##
    An event that contains every sample.
    """
    def __contains__(self, sample): return 1
    def contains(self, sample): return 1
    def __cmp__(self, other):
        if isinstance(other, UniversalEvent): return 1
        else: raise NotImplementedError()
    def subset(self, other): return self==other
    def superset(self, other): return 1
    def union(self, other): return self
    def intersection(self, other): return other
    def samples(self): 
        "## Not implemented by this Event class."
        raise NotImplementedError()
    def __len__(self): return None
        
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
        raise AssertionError()
    def N(self):
        raise AssertionError()
    def freq(self, event):
        raise AssertionError()
    def count(self, event):
        raise AssertionError()
    def cond_freq(self, event, condition): 
        raise AssertionError()
    def sampleSet(self):
        """## Return a set containing all samples that make up this
        FreqDist. """
        raise AssertionError()

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
    def tag(self, tokens): 
        raise AssertionError()

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
