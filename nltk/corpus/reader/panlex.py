# Natural Language Toolkit: PanLex Corpus Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: David Kamholz <kamholz@panlex.org>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Module docstring from readme
"""

import sqlite3

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *

class PanLexCorpusReader(CorpusReader):
    LOOKUP_Q = """
        SELECT dnx2.mn, dnx2.uq, dnx2.ap, ex2.tt, ex2.lv
        FROM dnx
        JOIN ex ON (ex.ex = dnx.ex)
        JOIN dnx dnx2 ON (dnx2.mn = dnx.mn)
        JOIN ex ex2 ON (ex2.ex = dnx2.ex)
        WHERE dnx.ex != dnx2.ex AND ex.tt = ? AND ex.lv = ?
        ORDER BY dnx2.uq DESC
    """

    def __init__(self):
        _conn = sqlite3.connect('db.sqlite')
        _c = _conn.cursor()

        _uid_lv = {}
        _lv_uid = {}

        for row in _c.execute('SELECT uid, lv, lc FROM lv'):
            _uid_lv[row[0]] = row[1]
            _lv_uid[row[1]] = row[0]

    def language_varieties(self, optional arg for 3-letter language code prefix):
        """given "eng" returns ["eng-001", ...]
        """

    def meanings(self, expr_tt, expr_uid):
        """
        >>> panlex.meanings("book", "eng-001")

        """

        d = {"quality": 3, "expressions": { ... }}
        Meaning(**d)

    lv = uid_lv[lc_to_uid(uid)]
    concepts = {}

    for i in c.execute(lookup_q, (tt,lv)):
        mn = i[0]
        uid = lv_uid[i[4]]

        if not mn in concepts:
            concepts[mn] = { 'quality': i[1], 'ap': i[2] }

        if not uid in concepts[mn]:
            concepts[mn][uid] = []

        concepts[mn][uid].append(i[3])

    for i in concepts.keys():
        print i
        print repr(concepts[i])
        print



class Meaning(object):
    def __init__(self, **kwargs):
        self = dict.__init__(**kwargs)

    def quality(self):
        return self["quality"]

