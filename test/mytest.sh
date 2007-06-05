#! /bin/bash
#
# PYTHONPATH needs to be set since module imports have been made local,
# in order to reduce dependencies with existing NLTK-Lite code.

PYTHONPATH=/Users/ewan/svn/new_syn_sem:/\
Users/ewan/svn/new_syn_sem/parse:\
Users/ewan/svn/new_syn_sem/semantics:

export PYTHONPATH

python doctest_driver.py --normalize_whitespace --ellipsis featgram.doctest

#python germangrammar.unittest.py

