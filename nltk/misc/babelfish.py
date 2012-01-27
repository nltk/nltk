# coding: utf8
# babelizer.py - API for simple access to babelfish.altavista.com.
#                Requires python 2.0 or better.
# From: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/64937
# Author: Jonathan Feinberg <jdf@pobox.com>
# Modified by Steven Bird to work with current babelfish
#
# See it in use at http://babel.MrFeinberg.com/

r"""API for simple access to babelfish.altavista.com.

Summary:

    >>> from nltk.misc import babelfish as babelizer
    >>> babelizer.available_languages
    ['Chinese', 'English', 'French', 'German', 'Greek', 'Italian', 'Japanese', 'Korean', 'Portuguese', 'Russian', 'Spanish']
    >>> babelizer.translate('How much is that doggie in the window?',
    ...                     'english', 'french')
    'Combien co\xfbte ce chienchien dans la fen\xeatre ?'
"""

import re
import string
import urllib
import sys

"""
Various patterns I have encountered in looking for the babelfish result.
We try each of them in turn, based on the relative number of times I've
seen each of these patterns.  $1.00 to anyone who can provide a heuristic
for knowing which one to use.   This includes AltaVista employees.
"""
__where = [ re.compile(r'<div id="result"><div style="padding:0.6em;">([^<]*)'),
            re.compile(r'name=\"q\">([^<]*)'),
            re.compile(r'td bgcolor=white>([^<]*)'),
            re.compile(r'<\/strong><br>([^<]*)'),
            re.compile(r'padding:10px[^>]+>([^<]*)')
          ]

__languages = { 'english'   : 'en',
                'french'    : 'fr',
                'spanish'   : 'es',
                'german'    : 'de',
                'greek'     : 'el',
                'italian'   : 'it',
                'portuguese': 'pt',
                'chinese'   : 'zh',
                'japanese'  : 'ja',
                'korean'    : 'ko',
                'russian'   : 'ru'
              }

"""
  All of the available language names.
"""
available_languages = sorted([x.title() for x in __languages])

class BabelizerError(Exception):
    """
    Calling translate() or babelize() can raise a BabelizerError
    """
class BabelfishChangedError(BabelizerError):
    """
    Thrown when babelfish.yahoo.com changes some detail of their HTML layout,
    and babelizer no longer submits data in the correct form, or can no
    longer parse the results.
    """
class BabelizerIOError(BabelizerError):
    """
    Thrown for various networking and IO errors.
    """

def clean(text):
    return re.sub(r'\s+', ' ', text.strip())

def translate(phrase, source, target):
    """
    Use babelfish to translate phrase from source language to target language.
    It's only guaranteed to work if 'english' is one of the two languages.

    :raise BabelizeError: If an error is encountered.
    """

    phrase = clean(phrase)
    try:
        source_code = __languages[source]
        target_code = __languages[target]
    except KeyError, lang:
        raise ValueError, "Language %s not available" % lang


    params = urllib.urlencode({'doit': 'done',
                               'tt': 'urltext',
                               'urltext': phrase,
                               'lp': source_code + '_' + target_code})
    try:
        response = urllib.urlopen('http://babelfish.yahoo.com/translate_txt', params)

    except IOError, what:
        raise BabelizerIOError("Couldn't talk to server: %s" % what)

    html = response.read()
    for regex in __where:
        match = regex.search(html)
        if match: break
    if not match: raise BabelfishChangedError("Can't recognize translated string.")
    return clean(match.group(1))

def babelize(phrase, source, target, limit = 12):
    """
    Use babelfish to translate back and forth between source and
    target until either no more changes occur in translation or
    limit iterations have been reached, whichever comes first.
    It's only guaranteed to work if 'english' is one of the two
    languages.

    :raise BabelizeError: If an error is encountered.
    """
    phrase = clean(phrase)
    seen = set([phrase])
    yield phrase

    flip = {source: target, target: source}
    next = source
    for i in range(limit):
        phrase = translate(phrase, next, flip[next])
        if phrase in seen:
            break
        seen.add(phrase)
        yield phrase
        next = flip[next]

HELP = """NLTK Babelizer Commands:
All single-word inputs are commands:
help: this help message
languages: print the list of languages
language: the name of a language to use"""

def babelize_shell():
    """
    An interactive shell that uses babelfish to
    translate back and forth between source and
    target until either no more changes occur in translation or
    limit iterations have been reached, whichever comes first.
    It's only guaranteed to work if 'english' is one of the two
    languages.

    :raise BabelizeError: If an error is encountered.
    """

    print "NLTK Babelizer: type 'help' for a list of commands."

    language = ''
    phrase = ''
    try:
        while True:
            command = raw_input('Babel> ')
            command = clean(command)
            if ' ' not in command:
                command = command.lower()
                if command == 'help':
                   print HELP
                elif command == 'languages':
                    print ' '.join(sorted(__languages))
                elif command in __languages:
                    language = command
                elif command in ['quit', 'bye', 'end']:
                    break
                elif command == 'run':
                    if not language:
                        print "Please specify a language first (type 'languages' for a list)."
                    elif not phrase:
                        print "Please enter a phrase first (just type it in at the prompt)."
                    else:
                        for count, new_phrase in enumerate(babelize(phrase, 'english', language)):
                            print "%s>" % count, new_phrase
                            sys.stdout.flush()
                else:
                    print "Command not recognized (type 'help' for help)."
            # if the command contains a space, it must have multiple words, and be a new phrase
            else:
                phrase = command
    except EOFError:
        print
        pass

# I won't take that from you, or from your doggie (Korean)
# the pig I found looked happy (chinese)
# absence makes the heart grow fonder (italian)
# more idioms: http://www.idiomsite.com/

if __name__ == '__main__':
    babelize_shell()
