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

from distutils.core import setup
import nltk

setup(

    #############################################
    ## Distribution Metadata
    name = "nltk",
    description = "Natural Language Toolkit",
    
    version = nltk.__version__,
    url = nltk.__url__,
    license = nltk.__copyright__,
    long_description = nltk.__longdescr__,
    keywords = nltk.__keywords__,
    maintainer = nltk.__maintainer__,
    maintainer_email = nltk.__maintainer_email__,
    author = nltk.__author__,
    author_email = nltk.__author__,
    # platforms = <platforms>,
      
    
    #############################################
    ## Package List
    packages = ['nltk', 'nltk.test', 'nltk.draw']
    
    )
