#
# Natural Language Toolkit for Python:
# Edward Loper
#
# Created [03/16/01 05:27 PM]
# (extracted from nltk.py, created [02/26/01 11:24 PM])
# $Id$
#

"""##
The Natural Language Toolkit is a package intended to simplify the
task of programming natural language systems.  It is intended to be
used as a teaching tool, not as a basis for building production
systems. <P>

This is a prototype implementation for the natural language toolkit.
The natural language toolkit is still under development.

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
Task-Oriented) Classes.  The Natural Language Toolkit is still under
development, and any definitions are subject to change.

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
    <LI> Better name than \"SimpleTagger\"?
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
  <LI> Should FreqDist.max() and FreqDist.cond_max() be merged, with
       the condition as an optional argument?  Same for
       FreqDist.freq() and FreqDist.cond_freq().
  <LI> Should I implement cross-toolkit policies on how to use __str__ 
       and __repr__?  If so, what should they be?
  <LI> How should I split the toolkit into modules?  Should I use a
       multi-layer structure (e.g., <CODE>nltk.probability</CODE>)?
</UL>

@exclude .*(?!Token).....Type
@exclude ....Type
@exclude ...Type
@exclude _typemsg
@exclude _Old.*

@author Edward Loper
@version 0.1
"""
