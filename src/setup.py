#!/usr/local/bin/python
#
# Distutils setup script for the Natural Language
# Processing Toolkit
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from distutils.core import setup, Extension
import nltk

# Should we include the C/C++ extensions?
USE_EXTENSIONS = 0

#############################################
## Extension modules
EXTENSIONS = [
    Extension('nltk._ctoken',
              sources=['extensions/ctoken.c',
                       'extensions/location_object.c']),
    ]
if not USE_EXTENSIONS: EXTENSIONS = None

setup(
    #############################################
    ## Distribution Metadata
    name = "nltk",
    description = "Natural Language Toolkit",
    
    version = nltk.__version__,
    url = nltk.__url__,
    long_description = nltk.__longdescr__,
    licence = nltk.__licence__,
    keywords = nltk.__keywords__,
    maintainer = nltk.__maintainer__,
    maintainer_email = nltk.__maintainer_email__,
    author = nltk.__author__,
    author_email = nltk.__author__,
    # platforms = <platforms>,
    
    #############################################
    ## Package List
    packages = ['nltk', 'nltk.test', 'nltk.draw', 'nltk.classifier',
                'nltk.parser', 'nltk.stemmer'],
    
    #############################################
    ## Extension Modules
    ext_modules = EXTENSIONS,
    
    )
