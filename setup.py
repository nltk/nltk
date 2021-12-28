#!/usr/bin/env python
#
# Setup script for the Natural Language Toolkit
#
# Copyright (C) 2001-2021 NLTK Project
# Author: NLTK Team <nltk.team@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

# Work around mbcs bug in distutils.
# https://bugs.python.org/issue10945
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
from setuptools import find_packages, setup

# Specify groups of optional dependencies
extras_require = {
    "machine_learning": [
        "numpy",
        "python-crfsuite",
        "scikit-learn",
        "scipy",
    ],
    "plot": ["matplotlib"],
    "tgrep": ["pyparsing"],
    "twitter": ["twython"],
    "corenlp": ["requests"],
}

# Add a group made up of all optional dependencies
extras_require["all"] = {
    package for group in extras_require.values() for package in group
}

# Adds CLI commands
console_scripts = """
[console_scripts]
nltk=nltk.cli:cli
"""

_project_homepage = "https://www.nltk.org/"

setup(
    name="nltk",
    description="Natural Language Toolkit",
    version=nltk_version,
    url=_project_homepage,
    project_urls={
        "Documentation": _project_homepage,
        "Source Code": "https://github.com/nltk/nltk",
        "Issue Tracker": "https://github.com/nltk/nltk/issues",
    },
    long_description="""\
The Natural Language Toolkit (NLTK) is a Python package for
natural language processing.  NLTK requires Python 3.6, 3.7, 3.8, or 3.9.""",
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
    maintainer="NLTK Team",
    maintainer_email="nltk.team@gmail.com",
    author="NLTK Team",
    author_email="nltk.team@gmail.com",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
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
    package_data={"nltk": ["test/*.doctest", "VERSION"]},
    python_requires=">=3.6",
    install_requires=[
        "click",
        "joblib",
        "regex>=2021.8.3",
        "tqdm",
    ],
    extras_require=extras_require,
    packages=find_packages(),
    zip_safe=False,  # since normal files will be present too?
    entry_points=console_scripts,
)
