# Natural Language Toolkit
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
The Natural Language Toolkit is a package intended to simplify the
task of programming natural language systems.  It is intended to be
used as a teaching tool, not as a basis for building production
systems.

The natural language toolkit is under active development.

Interfaces
==========

The Natural Language Toolkit is implemented as a set of interfaces and
classes.  Interfaces are a concept loosely borrowed from Java.  They
are essentially a specification of a set of methods.  Any class that
implements all of an interface's methods according to the interface's
specification are said to \"implement\" that interface.

In the context of this toolkit, an interface is implemented as a
class, all of whose methods simply raise AssertionError.  The
__doc__ strings of these methods, together with the methods'
declarations,  provide specifications for the methods.

Interface classes are named with a trailing \"I\", such as
C{TokenizerI} or C{EventI}.

Interface and Class Hierarchy
=============================

The classes defined by the Natural Language Toolkit can be divided
into two basic categories: Data classes; and Processing (or
Task-Oriented) Classes. 

Data Classes
------------

Data classes are used to store several different types of information
that are relavant to natural language processing.  Data classes can
generally be grouped into small clusters, with minimal interaction
between the clusters.  The clusters that are currently defined by the
Natural Language Toolkit are listed below.  Under each cluster, the
top-level classes and interfaces contained in that cluster are given.

  - B{Sets}: Encodes the mathmatical notion of a \"finite set\".
    - Set: A finite set.
    
  - B{Tokens}: Encodes units of text such as words.
      - Location: A span over indices in a text
      - Type: A unit of text.  This is actually not implemented as a
        class or an interface -- (almost) anything can be a Type.
      - Token: An occurance of a unit of text.
         
  - B{Syntax Trees}: Encodes syntax trees.
      - Tree: A hierarchical structure spanning a text.
      - TreeToken: An occurance of a Tree.
        
  - B{Probability}: Encodes data structures associated with
    the mathmatical notion of probability, such as events and
    frequency distributions.
      - Sample: Encodes the mathmatical notion of a
        \"sample\".  This is actually not implemented as a class or
        an interface -- (almost) anything can be a Sample.
      - EventI: A (possibly infinite) set of samples.
      - FreqDistI: The frequency distribution of a collection of
        samples. 
      - ProbDistI: A probability distribution, typically derived from
        a frequency distribution (e.g., using ELE).
          
Processing Classes
------------------

Processing classes are used to perform a variety of tasks that are
relavant to natural language processing.  Processing classes can
generally be grouped into small clusters, with minimial interaction
between the clusters.  Each cluster typically makes use of several
data-class clusters.  The processing clusters that are currently
defined by the Natural Language Toolkit are listed below.  Under each
cluster, the interfaces contained in that cluster are given.

  - B{Tokenizers}: Separate a string of text into a list of
    Tokens. 
       - TokenizerI
  - B{Taggers}: Assign tags to each Token in a list of Tokens.
       - TaggerI
  - B{Parser}: Produce Trees that represent the internal structure of
    a text.

@author: Edward Loper
@version: 0.3
"""

"""
Open Questions
==============

The following is a list of currently unresolved questions, pertaining
to currently implemented interfaces and classes.
  - Terminology/Naming Questions
    - Is \"Token Type\" too easily confusable with the notion of
         type in python?  E.g., names like SimpleTokenType suggest
         that they are similar to StringType, IntType, etc. when they
         are very different.  I could use \"TokenTyp\" to distinguish, 
         but this also seems somewhat confusing to the uninitiated.
  - Is the token/token type/text location system too complex?
       Often, one only cares about the token type.  E.g., a tokenizer
       could be defined as mapping string to list of TokenType, and a
       tagger as mapping list of SimpleTokenType to TaggedTokenType.
       But sometimes we really need to be able to distinguish tokens,
       not just token types.. e.g., to test the chunk parser from the
       chunk parsing problem set.
  - Should FreqDist.max() and FreqDist.cond_max() be merged, with
       the condition as an optional argument?  Same for
       FreqDist.freq() and FreqDist.cond_freq().
  - Should I implement cross-toolkit policies on how to use __str__ 
       and __repr__?  If so, what should they be?

"""

# Define some useful meta-data.
__author__ = "Edward Loper <edloper@gradient.cis.upenn.edu>"
__copyright__ = """\
Copyright (C) 2001 University of Pennsylvania.

Distributed and Licensed under provisions of the IBM Common Public
License (Version 0.5), which is included by reference.  The IBM Common 
Public License can be found in the file LICENSE.TXT in the
distribution."""
__version__ = "0.3"
__url__ = "http://nltk.sf.net/"


