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

# to do: add more fields! copyright, license, etc.

setup(name="nltk",
      description="Natural Language Processing Toolkit",
      author_email="ed@loper.org",
      version=nltk.__version__,
      author=nltk.__author__,
      url=nltk.__url__,
      packages=['nltk', 'nltk.test', 'nltk.draw'])
