#!/usr/local/bin/python
#
# Distutils setup script for the NLTK contributions package
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from distutils.core import setup, Extension
import os, os.path
import nltk_contrib

# Should we include the C/C++ extensions?
USE_EXTENSIONS = 0

#############################################
## Extension modules
EXTENSIONS = [
    Extension('nltk_contrib.misc.festival.tts',
              sources=['nltk_contrib/misc/festival/tts.cc'],
              libraries=['Festival', 'estools', 'eststring',
                         'estbase', 'nsl', 'curses'],
              include_dirs=['/usr/include/festival',
                            '/usr/include/speech_tools'],
              ),
    ]
if not USE_EXTENSIONS: EXTENSIONS = None

#############################################
## Find packages
def find_packages(path, prefix='', packages=None):
    if packages is None: packages = []
    for name in os.listdir(path):
        filepath = os.path.join(path, name)
        if not os.path.isdir(filepath): continue
        if prefix: pkg = '%s.%s' % (prefix, name)
        else: pkg = name
        if os.path.isfile(os.path.join(filepath, '__init__.py')):
            packages.append(pkg)
        # Recurse even in directories that don't include __init__.py
        # files.  This lets us use the __path__ magic for packages.
        find_packages(filepath, pkg, packages)
    return packages
packages = find_packages('.')

setup_dict = {
    #############################################
    ## Distribution Metadata
    'name': "nltk_contrib",
    'description': "Natural Language Toolkit: Contributions",
    
    'version': nltk_contrib.__version__,
    'url': nltk_contrib.__url__,
    'long_description': nltk_contrib.__longdescr__,
    'licence': nltk_contrib.__licence__,
    'keywords': nltk_contrib.__keywords__,
    'maintainer': nltk_contrib.__maintainer__,
    'maintainer_email': nltk_contrib.__maintainer_email__,
    'author': nltk_contrib.__author__,
    'author_email': nltk_contrib.__author__,
    # 'platforms': <platforms>,
    
    #############################################
    ## Package List
    'packages': packages,
    
    #############################################
    ## Extension Modules
    'ext_modules': EXTENSIONS,
    }

setup(**setup_dict)
#try: setup(**setup_dict)
#except:
#    print 'Trying again without extension modules'
#    del setup_dict['ext_modules']
#    setup(**setup_dict)
