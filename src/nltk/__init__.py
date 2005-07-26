# Natural Language Toolkit
#
# Copyright (C) 2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
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
    structures, such as syntax trees and morphological trees.

  - The L{probability} module implements classes that encode
    frequency distributions and probability distributions, including a
    variety of statistical smoothing techniques.

  - The L{eval} module defines basic metrics for evaluating
    performance.

  - The L{util} module defines a variety of utility classes and
    functions that are used throughout the toolkit.

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

@version: 1.4.4

@newfield developer: Developer, Developers, short
@developer: U{Edward Loper<edloper@gradient.cis.upenn.edu>}
@developer: U{Steven Bird <sb@cs.mu.oz.au>}
@developer: U{Ewan Klein <ewan@inf.ed.ac.uk>}
@developer: U{Trevor Cohn <tacohn@cs.mu.oz.au>}

@group Core Modules: token, tree, corpus, probability, util
@group Data Modules: set, cfg, fsa, featurestruct, sense
@group Task Modules: classifier, parser, speech, stemmer, tagger,
    tokenizer
@group Visualization: draw
@group Debugging: chktype, test
"""

# Define some nltk-specific docstring fields:
#   - @inprop:  Specifies a property name that is used as input
#               by a processing class.
#   - @outprop: Specifies a property name that is used as output
#               by a processing class.
__extra_epydoc_fields__ = [
    ('inprop',  None,  'Input Properties'),
    ('outprop', None, 'Output Properties'),
    ]


##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  For each new release, the version number should be updated
# here and in the Epydoc comment (above).
__version__ = "1.4.4"

# Copyright notice
__copyright__ = """\
Copyright (C) 2005 University of Pennsylvania.

Distributed and Licensed under provisions of the GNU Public
License, which is included by reference.
"""

__license__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
The Natural Langauge Toolkit is a Python package that simplifies
the construction of programs that process natural language; and
defines standard interfaces between the different components of
an NLP system.  NLTK requires Python 2.3 or higher."""
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

##//////////////////////////////////////////////////////
##  Tasks
##//////////////////////////////////////////////////////

class TaskI:
    """
    A standard NLTK language processing task.
    
    Individual processing tasks are defined as subclasses of C{TaskI}.
    Each processing task defines an X{action method}, which takes one
    or more tokens, and performs the task's action on the tokens by
    updating their properties (or the properties of contained tokens).
    Action methods are generally named after the tasks; for example,
    the action method for the C{ParserI} task is C{parse()}.

    Property Indirection
    ~~~~~~~~~~~~~~~~~~~~
    Each processing task performs its action by reading and modifying
    a token's properties.  The properties used by a task are specified
    with generic names, such as C{SUBTOKENS} and C{TAG}; but
    individual instances of the task classes should be specialized to
    use more specific property names, such as C{WORDS} and C{SENSE}.
    In order to allow this task-specific specialization, all task
    interfaces should support X{property indirection}, which maps the
    generic property names defined by the task to specific proprety
    names supplied by the user to the constructor.

    In particular, each processing task constructor should define a
    keyword parameter that specifies the mapping from generic property
    names to specific property names; and should define the
    L{property()} method, which returns the specific property name
    corresponding to a given generic property name.

    Pipeline Action Methods
    ~~~~~~~~~~~~~~~~~~~~~~~
    Each interface also defines a number of optional X{pipleine action
    methods}, which take one or more tokens, performs the task's
    action, and return the newly generated information (I{without}
    updating the tokens' properties).  Pipeline action methods are
    especially useful in cases where the task's action can generate
    multiple possible solutions.  In this case, different pipeline
    action methods can return different collections of possible
    solutions (such as lists of solutions, or probability
    distributions over solutions).  Pipeline action methods are given
    names like C{get_I{result}}, C{get_I{result}_probs},
    C{get_I{result}_scores}, and C{get_I{result}_list}.  E.g.,
    C{get_classification_probs}.

    Raw Action Methods
    ~~~~~~~~~~~~~~~~~~
    Each processing task may optionally define a X{raw action method},
    which takes one or more arguments containing the information
    needed to perform the task (not wrapped in a token), and returns
    the newly generated information.  The raw action method should be
    named C{raw_I{act}}, where C{I{act}} is the name of the action
    method.
    """

class PropertyIndirectionI:
    """
    A mix-in base clase that provides property indirection support.
    Property indirection is required by the L{TaskI} interface; see
    L{TaskI} for more information about property indireciton.
    """
    def property(self, generic_name):
        """
        @return: The specific property name that corresponds to the
        given generic property name.  If no specific property name was
        provided for C{generic_name}, then return C{generic_name}.
        @rtype: C{string}
        """
        raise NotImplementedError

    def property_names(self):
        """
        @return: The property names dictionary.
        @rtype: C{dict}
        """
        raise NotImplementedError

class PropertyIndirectionMixIn(PropertyIndirectionI):
    def __init__(self, **property_names):
        """
        Initialize the task's property indirection mapping with
        the given dictionary.

        @type property_names: C{dict} from C{string} to C{string}
        @param property_names: A dictionary, mapping from generic
            property names (as specified by the task interfaces)
            to specific property names (as specified by the user).
        """
        self.__property_names = property_names

    def property(self, generic_name):
        return self.__property_names.get(generic_name, generic_name)

    def property_names(self):
        return self.__property_names

