#!/usr/bin/env python
#
# Distribute setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import distribute_setup
distribute_setup.use_setuptools()

from setuptools import setup, find_packages
import nltk

#
# Prevent setuptools from trying to add extra files to the source code
# manifest by scanning the version control system for its contents.
#
from setuptools.command import sdist
del sdist.finders[:]

setup(
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
    classifiers = nltk.__classifiers__,
    package_data = {'nltk': ['nltk.jar', 'test/*.doctest']},
    packages = find_packages(),
    zip_safe=False, # since normal files will be present too?
    install_requires=['PyYAML==3.09'],
    test_suite = 'nltk.test.simple',
    )
