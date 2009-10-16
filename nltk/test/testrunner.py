#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# NLTK test-suite runner
#
# Author: Bjørn Arild Mæland <bjorn.maeland@gmail.com>
#

import os, sys
import doctest_driver

# Make sure that we are in the test-directory
_dir = os.path.dirname(sys.argv[0])
if os.path.isdir(_dir):
    os.chdir(_dir)

# These tests are expected to fail.
# NOTE: Remember to remove tests from this list after they have been fixed.
FAILING_TESTS = [
    "ccg.doctest", # This test randomly fails - nondeterministic output
    "collocations.doctest",
    "corpus.doctest",
    "portuguese_en.doctest",
    "probability.doctest",
    "relextract.doctest",
    ]

# These tests require extra dependencies and should not run by default
# TODO: Run the tests if the relevant dependeices are present on the system
DEPENDENT_TESTS = [
    "classify.doctest",
    "discourse.doctest",
    "drt.doctest",
    "gluesemantics.doctest",
    "inference.doctest",
    "nonmonotonic.doctest",
    ]

TESTS = [x for x in os.listdir(os.getcwd()) if x.endswith('.doctest') and
         not x in FAILING_TESTS + DEPENDENT_TESTS]
TESTS.sort()

def main():
    optionflags, verbosity, kbinterrupt_continue = 0, 1, 0

    testrun = doctest_driver.run(TESTS, optionflags, verbosity,
                                 kbinterrupt_continue)

    if not testrun.failures == 0:
        print
        print "A test failed unexpectedly. Please report this error"
        print "to the nltk-dev mailinglist."
        exit(1)

    # TODO: create an option for the doctest driver to disable output
    # when the expected-to-fail tests run
    for ft in FAILING_TESTS:
        testrun = doctest_driver.run([ft], optionflags, verbosity,
                                     kbinterrupt_continue)
        if testrun.failures == 0:
            print
            print "A test that was expected to fail actually passed: %s" % ft
            print "Please report this to the nltk-dev mailinglist."
            exit(1)

    print
    print "All tests OK! (The ones that did fail were expected to fail)"

if __name__ == '__main__': main()
