#!/usr/local/bin/python
#
# Distutils setup script for the Natural Language
# Processing Toolkit
#
# Created [05/27/01 09:04 PM]
# Edward Loper
#

from distutils.core import setup
import nltk

setup(name="nltk",
      description="Natural Language Processing Toolkit",
      author_email="ed@loper.org",
      version=nltk.__version__,
      author=nltk.__author__,
      url=nltk.__url__,
      packages=['nltk'])

