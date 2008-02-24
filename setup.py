#!/usr/local/bin/python
#
# Distutils setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from distutils.core import setup, Extension
import nltk

setup(
    #############################################
    ## Distribution Metadata
    name = "nltk",
    description = "Natural Language Toolkit",
    
    version = nltk.__version__,
    url = nltk.__url__,
    long_description = nltk.__longdescr__,
    license = nltk.__license__,
    keywords = nltk.__keywords__,
    maintainer = nltk.__maintainer__,
    maintainer_email = nltk.__maintainer_email__,
    author = nltk.__author__,
    author_email = nltk.__author__,
    # platforms = <platforms>,
    
    #############################################
    ## Package List
    packages = ['nltk',
                'nltk.chat',
                'nltk.chunk',
                'nltk.classify',
                'nltk.corpus',
                'nltk.corpus.reader',
                'nltk.cluster',
                'nltk.draw',
                'nltk.inference',
                'nltk.misc',
                'nltk.model',
                'nltk.parse',
                'nltk.sem',
                'nltk.stem',
                'nltk.tag',
                'nltk.test',
                'nltk.tokenize',
                'nltk.wordnet',
                'nltk.etree',
                'nltk_contrib',
                'nltk_contrib.bioreader',
                'nltk_contrib.classifier',
                'nltk_contrib.classifier.exceptions',
                'nltk_contrib.classifier_tests',
                'nltk_contrib.dependency',
                'nltk_contrib.drt',
                'nltk_contrib.fst',
                'nltk_contrib.gluesemantics',
                'nltk_contrib.lpath',
                'nltk_contrib.readability',
                'nltk_contrib.rte',
                'nltk_contrib.toolbox',
                'nltk_contrib.wordnet',
                'yaml'
                ],
    )
