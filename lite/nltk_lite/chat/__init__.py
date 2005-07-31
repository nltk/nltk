# Natural Language Toolkit: Chatbots
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Authors: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Based on an Eliza implementation by Joe Strout <joe@strout.net>,
# Jeff Epler <jepler@inetnebr.com> and Jez Higgins <jez@jezuk.co.uk>.

"""
A class for simple chatbots.  These perform simple pattern matching on sentences
typed by users, and respond with automatically generated sentences.
"""

import string
import re
import whrandom

class Chat:
    def __init__(self, pairs, reflections={}):
        """
        Initialize the chatbot.  Pairs is a list of patterns and responses.  Each
        pattern is a regular expression matching the user's statement or question,
        e.g. r'I like (.*)'.  For each such pattern a list of possible responses
        is given, e.g. ['Why do you like %1', 'Did you ever dislike %1'].  Material
        which is matched by parenthesized sections of the patterns (e.g. .*) is mapped to
        the numbered positions in the responses, e.g. %1.

        @type pairs: C{list} of C{tuple}
        @param pairs: The patterns and responses
        @type reflections: C{dict}
        @param reflections: A mapping between first and second person expressions
        @rtype: C{None}
        """

        self._pairs = [(re.compile(x),y) for (x,y) in pairs]
        self._reflections = reflections

    # bug: only permits single word expressions to be mapped
    def _substitute(self, str):
        """
        Substitute words in the string, according to the specified reflections,
        e.g. "I'm" -> "you are"
        
        @type str: C{string}
        @param str: The string to be mapped
        @rtype: C{string}
        """

        words = ""
        for word in string.split(string.lower(str)):
            if self._reflections.has_key(word):
                word = self._reflections[word]
            words += ' ' + word
        return words

    def _wildcards(self, response, match):
        pos = string.find(response,'%')
        while pos >= 0:
            num = string.atoi(response[pos+1:pos+2])
            response = response[:pos] + \
                self._substitute(match.group(num)) + \
                response[pos+2:]
            pos = string.find(response,'%')
        return response

    def respond(self, str):
        """
        Generate a response to the user input.
        
        @type str: C{string}
        @param str: The string to be mapped
        @rtype: C{string}
        """

        # check each pattern
        for (pattern, response) in self._pairs:
            match = pattern.match(str)

            # did the pattern match?
            if match:
                resp = whrandom.choice(response)    # pick a random response
                resp = self._wildcards(resp, match) # process wildcards

                # fix munged punctuation at the end
                if resp[-2:] == '?.': resp = resp[:-2] + '.'
                if resp[-2:] == '??': resp = resp[:-2] + '?'
                return resp

