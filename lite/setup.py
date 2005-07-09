#!/usr/local/bin/python
#
# Distutils setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from distutils.core import setup, Extension
import nltk_lite

setup(
    #############################################
    ## Distribution Metadata
    name = "nltk_lite",
    description = "Natural Language Toolkit",
    
    version = nltk_lite.__version__,
    url = nltk_lite.__url__,
    long_description = nltk_lite.__longdescr__,
    license = nltk_lite.__license__,
    keywords = nltk_lite.__keywords__,
    maintainer = nltk_lite.__maintainer__,
    maintainer_email = nltk_lite.__maintainer_email__,
    author = nltk_lite.__author__,
    author_email = nltk_lite.__author__,
    # platforms = <platforms>,
    
    #############################################
    ## Package List
    packages = ['nltk_lite', 'nltk_lite.corpora',
                'nltk_lite.tokenize', 'nltk_lite.tag',
                'nltk_lite.parse', 'nltk_lite.chat', 'nltk_lite.draw',
                'nltk_lite.misc'],

    )
