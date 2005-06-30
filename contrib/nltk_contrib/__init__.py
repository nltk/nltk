# Natural Language Toolkit: Third-Party Contributions
#
# Copyright (C) 2003-2005 The original contributors
# URL: <http://nltk.sf.net>
#
# $Id$

"""
Third-Party Contributions to the Natural Language Toolkit (NLTK).
These Python programs are designed to work with NLTK, and perform a
wide variety of natural language processing tasks.  While they are not
integrated into NLTK (yet), these programs may be of interest to NLTK
developers and to people teaching NLP using Python.

B{Tip:} To avoid using long fully qualified names, C{nltk_contrib}
modules are typically imported with C{from I{pkg} import I{module}}
statements:

    >>> from nltk_contrib.upenn.cis530.fall2001 import tag
    >>> tag.demo()

@version: 1.4.4
@newfield contributor: Contributor, Contributors, short
@contributor: Robert Berwick
@contributor: Seh Ying Boo
@contributor: Alice Boxhall
@contributor: Steve Cassidy
@contributor: Chen-Fu Chiang
@contributor: Jinyoung Choi
@contributor: Trevor Cohn
@contributor: Nikhil Dinesh
@contributor: Rebecca Dridan
@contributor: Brent Gray
@contributor: Yurie Hara
@contributor: Peter Hawkins
@contributor: Edward Ivanovic
@contributor: Haejoong Lee
@contributor: Christopher Maloof
@contributor: Carl de Marcken
@contributor: Rob Speer
@contributor: Oliver Steele
@contributor: Jason Yang
@contributor: Beracah Yankama
@contributor: David Zhang
"""

##//////////////////////////////////////////////////////
##  Package path manipulation
##//////////////////////////////////////////////////////

def _add_subdirectories_to_package(package_path_list):
    """
    Given the path list of a package (C{__path__}), add the paths of
    all (direct) subdirectories to that path.  Subdirectories that
    contain C{__init__.py} files are assumed to contain subpackages,
    and are I{not} added to the path list.  Typically, this function
    is used by adding the following line to a packages' C{__init__.py}
    file:

        >>> _add_subdirectories_to_package(__path__)

    @param package_path_list: The C{__path__} attribute of a package.
    @type package_path_list: C{list}
    @rtype: C{None}
    """
    import os, os.path
    pkgpath = package_path_list[0]
    for file in os.listdir(pkgpath):
        path = os.path.join(pkgpath, file)
        if os.path.isdir(path) and file != 'CVS':
            if not os.path.isfile(os.path.join(path, '__init__.py')):
                package_path_list.append(path)

##//////////////////////////////////////////////////////
##  Metadata
##//////////////////////////////////////////////////////

# Version.  This version number is independent of nltk's version
# number, but parallels it.  (I.e., we release nltk version x.y and
# nltk_contrib version x.y at the same time.)
__version__ = "1.4.4"

# Copyright notice
__copyright__ = """\
Copyright (C) 2003-2005 The individual authors.

Unless otherwise stated, these programs are Distributed and Licensed
under provisions of the GNU Public License, which is included by
reference."""

__licence__ = "GNU Public License"
# Description of the toolkit, keywords, and the project's primary URL.
__longdescr__ = """\
Contributed files for the Natural Language Toolkit.  The Natural
Langauge Toolkit is a Python package that simplifies the construction
of programs that process natural language; and defines standard
interfaces between the different components of an NLP system.  NLTK
requires Python 2.4 or higher."""
__keywords__ = ['NLP', 'CL', 'natural language processing',
                'computational linguistics', 'parsing', 'tagging',
                'tokenizing', 'syntax', 'linguistics', 'language',
                'natural language']
__url__ = "http://nltk.sourceforge.net/"

# Maintainer, contributors, etc.
__maintainer__ = "Edward Loper"
__maintainer_email__ = "edloper@gradient.cis.upenn.edu"
__author__ = __maintainer__
__author_email__ = __maintainer_email__
