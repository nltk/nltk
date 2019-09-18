#!/usr/bin/env python
#
# Setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# Work around mbcs bug in distutils.
# http://bugs.python.org/issue10945
import codecs
try:
    codecs.lookup("mbcs")
except LookupError:
    ascii = codecs.lookup("ascii")
    func = lambda name, enc=ascii: {True: enc}.get(name == "mbcs")
    codecs.register(func)

import os

# Use the VERSION file to get NLTK version
version_file = os.path.join(os.path.dirname(__file__), "nltk", "VERSION")
with open(version_file) as fh:
    nltk_version = fh.read().strip()

# setuptools
from setuptools import setup, find_packages
from distutils.command.build import build as build_orig
from distutils.log import INFO

# Specify groups of optional dependencies
extras_require = {
    "machine_learning": ["gensim", "numpy", "python-crfsuite", "scikit-learn", "scipy"],
    "plot": ["matplotlib"],
    "tgrep": ["pyparsing"],
    "twitter": ["twython"],
    "corenlp": ["requests"],
    "cli": ["click", "joblib", "tqdm"],
}

# Add a group made up of all optional dependencies
extras_require["all"] = set(
    package for group in extras_require.values() for package in group
)

# Add a group made up of all optional dependencies
extras_require["cythonize"] = extras_require["all"] | set(['Cython >= 0.28.5'])

setup_reqs = []
# if CYTHONIZE_NLTK is set, require Cython in build deps
if os.getenv('CYTHONIZE_NLTK') == 'true':
    setup_reqs.append('Cython >= 0.28.5')

# Adds CLI commands
console_scripts = """
[console_scripts]
nltk=nltk.cli:cli
"""

MODULES_TO_COMPILE = [
    #'nltk.ccg.*', # Fails on https://travis-ci.org/nltk/nltk/jobs/529589821#L2077
    'nltk.chat.*',
    'nltk.chunk.*',
    #'nltk.classify.*', # Fails on https://travis-ci.org/nltk/nltk/jobs/529562500#L2080
    'nltk.cluster.*',
    'nltk.draw.*',
    'nltk.grammar',
    #'nltk.inference.*', # Fails on https://travis-ci.org/nltk/nltk/jobs/529679443#L2114
    'nltk.lm.*',
    'nltk.metrics.*',
    'nltk.misc.*',
    'nltk.parse.chart',
    'nltk.probability',
    'nltk.sem.*',
    'nltk.sentiment.*',
    'nltk.stem.*',
    'nltk.tbl.*',
    #'nltk.test.*', # Fails on https://travis-ci.org/nltk/nltk/jobs/529634204#L2169
    'nltk.tokenize.*',
    'nltk.translate.*',
    'nltk.twitter.*',
    'nltk.util',
]

MODULES_TO_EXCLUDE = [
    '**/__init__.py',
    'nltk/tbl/feature.py',
    'nltk/metrics/association.py'
]


class build_cythonized(build_orig):
    def finalize_options(self):
        if os.getenv('CYTHONIZE_NLTK') == 'true':
            # translate python sources into c code
            import Cython
            from Cython.Build import cythonize
            files = [name.replace('.', os.path.sep) + '.py' for name in MODULES_TO_COMPILE]
            self.announce("Compiling %d modules using Cython %s" % (len(files), Cython.__version__), level=INFO)
            self.distribution.ext_modules = cythonize(files, language_level=3, exclude=MODULES_TO_EXCLUDE)
        super(build_cythonized, self).finalize_options()


setup(
    name="nltk",
    description="Natural Language Toolkit",
    version=nltk_version,
    url="http://nltk.org/",
    long_description="""\
The Natural Language Toolkit (NLTK) is a Python package for
natural language processing.  NLTK requires Python 3.5, 3.6, or 3.7.""",
    license="Apache License, Version 2.0",
    keywords=[
        "NLP",
        "CL",
        "natural language processing",
        "computational linguistics",
        "parsing",
        "tagging",
        "tokenizing",
        "syntax",
        "linguistics",
        "language",
        "natural language",
        "text analytics",
    ],
    maintainer="Steven Bird",
    maintainer_email="stevenbird1@gmail.com",
    author="Steven Bird",
    author_email="stevenbird1@gmail.com",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing",
        "Topic :: Text Processing :: Filters",
        "Topic :: Text Processing :: General",
        "Topic :: Text Processing :: Indexing",
        "Topic :: Text Processing :: Linguistic",
    ],
    package_data={
        "nltk": ["VERSION"],
        "nltk.test": ["*.doctest", "*.xml"],
        "nltk.metrics": ["artstein_poesio_example.txt"],
        "nltk.test.unit": ["files/*.csv.ref", "files/*.txt"],
    },
    install_requires=[
        "six",
        'singledispatch; python_version < "3.4"',
    ],
    setup_requires=setup_reqs,
    extras_require=extras_require,
    packages=find_packages(),
    zip_safe=False,  # since normal files will be present too?
    entry_points=console_scripts,
    cmdclass={
        'build': build_cythonized,
    },
)
