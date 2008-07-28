"""
FUF is an interpreter, originally written by Michael Elhadad in Common Lisp 
for a functional unification based language specifically designed
for the development of text generation applications.
This module is a port of that interpreter that relies upon the 
C{nltk.featstruct.FeatStruct} to acheive the same task. 

Unifier
=======

C{fuf.Unifier} is the implementation of the FUF
unification algorithm that (currently) inludes
the processing of most (but not all) of the features defined
in the original Common LISP version.

Link Resolution
---------------

FUF grammars allow for addressing parts of the grammar through
absolute and relative links. The targets of the links 
can be resolved by using the C{link.LinkResolver} class.


Type Definitions
----------------

FUF grammars allow for the specification of feature
value taxonomies. The value types can by stored and used
by the C{fstypes.FeatureTypeTable} and C{fstypes.TypedFeatureValue}


Linearization
-------------

The linearization of the successful unification is perfomed by the
C{linearize} module.


Morphology
----------

The morphology module is currently B{not implemented}.

Converter
=========

C{fufconvert} defines several functions for converting
FUF grammar files from their original s-expression
syntax to C{nltk.featstruct.FeatStruct}.
"""

from fufconvert import *
from fuf import *
from linearizer import *
from fstypes import *
from link import *
from util import *

__all__ = [
    # Unifier
    'Unifier',

    #LinkResolver
    'LinkResolver',

    # Type 
    'FeatureTypeTable',
    'FeatureValueType'
    ]

