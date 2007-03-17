#!/usr/local/bin/python
#
# Distutils setup script for the Natural Language Toolkit(Contrib) - Classifier
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from distutils.core import setup, Extension
import nltk_lite_contrib

setup(
    #############################################
    ## Distribution Metadata
    name = "Classifier",
    description = "Natural Language Toolkit(Contrib) - Classifier",
    
    version = nltk_lite_contrib.__version__,
    url = nltk_lite_contrib.__url__,
    long_description = nltk_lite_contrib.__longdescr__,
    license = nltk_lite_contrib.__license__,
    keywords = nltk_lite_contrib.__keywords__,
    maintainer = nltk_lite_contrib.__maintainer__,
    maintainer_email = nltk_lite_contrib.__maintainer_email__,
    author = nltk_lite_contrib.__author__,
    author_email = nltk_lite_contrib.__author__,
    
    #############################################
    ## Package List
    packages = ['nltk_lite_contrib', 'nltk_lite_contrib.classifier', 
                'nltk_lite_contrib.classifier_tests', 'nltk_lite_contrib.classifier.exceptions']
    )
