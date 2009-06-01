#!/usr/bin/env python
#
# Distutils setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from distutils.core import setup
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
    ## Package Data
    package_data = {'nltk': ['nltk.jar', 'test/*.doctest']},
    
    #############################################
    ## Package List
    packages = ['nltk',
                'nltk.app',
                'nltk.chat',
                'nltk.chunk',
                'nltk.ccg',
                'nltk.classify',
                'nltk.corpus',
                'nltk.corpus.reader',
                'nltk.cluster',
                'nltk.draw',
                'nltk.inference',
                'nltk.metrics',
                'nltk.misc',
                'nltk.model',
                'nltk.parse',
                'nltk.sem',
                'nltk.stem',
                'nltk.tag',
                'nltk.test',
                'nltk.tokenize',
                'nltk.toolbox',
                'nltk.etree',
                'nltk_contrib',
                'nltk_contrib.bioreader',
                'nltk_contrib.classifier',
                'nltk_contrib.classifier.exceptions',
                'nltk_contrib.classifier_tests',
                'nltk_contrib.coref',
                'nltk_contrib.dependency',
                'nltk_contrib.fst',
                'nltk_contrib.fuf',
                'nltk_contrib.hadoop',
                'nltk_contrib.hadoop.hadooplib',
                'nltk_contrib.lambek',
                'nltk_contrib.lpath',
                'nltk_contrib.lpath.lpath',
                'nltk_contrib.lpath.at_lite',
                'nltk_contrib.misc',
                'nltk_contrib.mit',
                'nltk_contrib.mit.six863',
                'nltk_contrib.mit.six863.kimmo',
                'nltk_contrib.mit.six863.parse',
                'nltk_contrib.mit.six863.semantics',
                'nltk_contrib.mit.six863.tagging',
                'nltk_contrib.readability',
                'nltk_contrib.rte',
                'nltk_contrib.tag',
                'nltk_contrib.tiger',
                'nltk_contrib.tiger.indexer',
                'nltk_contrib.tiger.query',
                'nltk_contrib.tiger.utils',
                'nltk_contrib.toolbox',
                'yaml'
                ],
    )
