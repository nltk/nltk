# Natural Language Toolkit
#
# Copyright (C) 2003 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
NLTK, the Natural Language Toolkit, is a collection of modules that
simplify the task of creating natural language systems.  NLTK covers
symbolic and statistical natural language processing, and is
interfaced to annotated corpora.

NLTK is primarily intended for use as a teaching tool.  Along with the
tutorials and problem sets available from U{the NLTK
webpage<http://nltk.sourceforge.net>}, NLTK provides ready-to-use
computational linguistics courseware.  Students can augment and
replace existing components, learning structured programming by
example, and manipulating sophisticated models from the outset.

NLTK can also be used to implement small research systems, and to
quickly prototype larger research or production systems.  

Modules
=======
NLTK is implemented as a collection of independent modules, each of
which defines a specific data structure or task. A set of core modules
defines basic data types and processing systems that are used
throughout the toolkit.

  - The L{token} module provides basic classes for processing
  individual elements of text, such as words or sentences.

  - The L{tree} module defines data structures for representing tree
  structures over text, such as syntax trees and morphological trees.

  - TThe L{probability} module implements classes that encode
  frequency distributions and probability distributions, including a
  variety of statistical smoothing techniques.

The remaining modules define data structures and interfaces for
performing specific natural language processing tasks.  This list of
modules will grow over time, as we add new tasks and algorithms to the
toolkit.

Interfaces
----------
Natural language processing tasks (such as parsing or classifying
texts) are defined by interfaces.  An X{interface} is a special type
of base class that specifies a set of methods that must be supported.
For example, the L{ParserI<nltk.parser.ParserI>} interface specifies
that parsers must support the L{parse()<nltk.parser.ParserI.parse>}
method.

Each subclass of an interface provides an implementation for the
natural language processing task defined by the interface.  For
example, L{ShiftReduceParser<nltk.parser.ShiftReduceParser>},
L{RecursiveDescentParser<nltk.parser.RecursiveDescentParser>}, and
L{ChartParser<nltk.parser.chart.ChartParser>} are all implementations
of the C{ParserI} interface.

@version: 1.1a

@newfield developer: Developer, Developers, short
@developer: L{Edward Loper<edloper@gradient.cis.upenn.edu>}
@developer: L{Steven Bird <sb@cs.mu.oz.au>}
@developer: L{Ewan Klein <ewan@inf.ed.ac.uk>}
@developer: L{Trevor Cohn <tacohn@cs.mu.oz.au>}

@group Core Modules: token, tree, corpus, probability
@group Data Modules: set, cfg, fsa
@group Task Modules: classifier, parser, speech, stemmer, tagger
@group Visualization: draw
@group Debugging: chktype, test
@sort: token, tree, corpora, probability
@sort: set, cfg, fsa
@sort: classifier, parser, speech, stemmer, tagger
"""

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "1.1a"

# Copyright notice
__copyright__ = """\
Copyright (C) 2003 University of Pennsylvania.

Distributed and Licensed under provisions of the GNU Public
License, which is included by reference.
"""

__licence__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Langauge Toolkit is a Python package that simplifies
the construction of programs that process natural language; and
defines standard interfaces between the different components of
an NLP system.  NLTK requires Python 2.1 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language']
__url__ = "http://nltk.sf.net/"

# Maintainer, contributors, etc.
__maintainer__ = "Edward Loper"
__maintainer_email__ = "edloper@gradient.cis.upenn.edu"
__author__ = __maintainer__
__author_email__ = __maintainer_email__
