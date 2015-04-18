# -*- coding: utf-8 -*-
"""
The following test performs a random series of reads, seeks, and
tells, and checks that the results are consistent.
"""
from __future__ import absolute_import, unicode_literals
import random
import functools
from io import BytesIO
from nltk.corpus.reader import SeekableUnicodeStreamReader

def check_reader(unicode_string, encoding, n=1000):
    bytestr = unicode_string.encode(encoding)
    strlen = len(unicode_string)
    stream = BytesIO(bytestr)
    reader = SeekableUnicodeStreamReader(stream, encoding)
    # Find all character positions
    chars = []
    while True:
        pos = reader.tell()
        chars.append( (pos, reader.read(1)) )
        if chars[-1][1] == '': break
    # Find all strings
    strings = dict( (pos,'') for (pos,c) in chars )
    for pos1, char in chars:
        for pos2, _ in chars:
            if pos2 <= pos1:
                strings[pos2] += char
    while True:
        op = random.choice('tsrr')
        # Check our position?
        if op == 't': # tell
            reader.tell()
        # Perform a seek?
        if op == 's': # seek
            new_pos = random.choice([p for (p,c) in chars])
            reader.seek(new_pos)
        # Perform a read?
        if op == 'r': # read
            if random.random() < .3: pos = reader.tell()
            else: pos = None
            if random.random() < .2: size = None
            elif random.random() < .8:
                size = random.randint(0, int(strlen/6))
            else: size = random.randint(0, strlen+20)
            if random.random() < .8:
                s = reader.read(size)
            else:
                s = reader.readline(size)
            # check that everything's consistent
            if pos is not None:
                assert pos in strings
                assert strings[pos].startswith(s)
                n -= 1
                if n == 0:
                    return 'passed'


#Call the randomized test function `check_reader` with a variety of
#input strings and encodings.

ENCODINGS = ['ascii', 'latin1', 'greek', 'hebrew', 'utf-16', 'utf-8']

STRINGS = [
    """
    This is a test file.
    It is fairly short.
    """,

    "This file can be encoded with latin1. \x83",

    """\
    This is a test file.
    Here's a blank line:

    And here's some unicode: \xee \u0123 \uffe3
    """,

    """\
    This is a test file.
    Unicode characters: \xf3 \u2222 \u3333\u4444 \u5555
    """,

]

def test_reader():
    for string in STRINGS:
        for encoding in ENCODINGS:
            try:
                # skip strings that can't be encoded with the current encoding
                string.encode(encoding)
                yield check_reader, string, encoding
            except UnicodeEncodeError:
                pass



# nose shows the whole string arguments in a verbose mode; this is annoying,
# so large string test is separated.

LARGE_STRING = """\
This is a larger file.  It has some lines that are longer \
than 72 characters.  It's got lots of repetition.  Here's \
some unicode chars: \xee \u0123 \uffe3 \ueeee \u2345

How fun!  Let's repeat it twenty times.
"""*10

def test_reader_on_large_string():
    for encoding in ENCODINGS:
        try:
            # skip strings that can't be encoded with the current encoding
            LARGE_STRING.encode(encoding)
            def _check(encoding, n=1000):
                check_reader(LARGE_STRING, encoding, n)

            yield _check, encoding

        except UnicodeEncodeError:
            pass

def teardown_module(module=None):
    import gc
    gc.collect()
