# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
import os

from nltk_contrib.tiger.corpus import Corpus
from nltk_contrib.tiger.indexer import graph_serializer
from nltk_contrib.tiger.indexer.tiger_corpus_indexer import TigerCorpusIndexer, INDEX_VERSION
from nltk_contrib.tiger.tigerxml import parse_tiger_corpus

from nltk_contrib.tiger.utils.db import sqlite3

__all__ = ("open_corpus_volatile", "open_corpus")

GRAPH_INDEX_EXTENSION = ".tci"

def _connect(db_path):
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA temp_store = MEMORY")
    return db


class DbProvider(object):
    def __init__(self, path):
        self._path = path

    def connect(self):
        return _connect(self._path)

    def can_reconnect(self):
        return True


class EmptyDbProvider(object):
    def connect(self):
        raise RuntimeError, "cannot reopen memory-only db"
    
    def can_reconnect(self):
        return False

    
def open_corpus_volatile(treebank_id, tigerxml_corpus_path, veeroot=True):
    """Indexes a TIGER-XML corpus using a volatile in-memory index."""
    db = sqlite3.connect(":memory:")
    _index_treebank(tigerxml_corpus_path, db, veeroot)
    return Corpus(treebank_id, db, EmptyDbProvider())


def open_corpus(treebank_id, tigerxml_corpus_path, index_always = False, veeroot=True):
    db_path = os.path.splitext(tigerxml_corpus_path)[0] + GRAPH_INDEX_EXTENSION
    
    if not os.path.exists(db_path):
        db = _connect(db_path)
        _index_treebank(tigerxml_corpus_path, db, veeroot)
    else:
        db = _connect(db_path)
        if index_always or not _check_db(db):
            db.close()
            os.remove(db_path)
            db = _connect(db_path)
            _index_treebank(tigerxml_corpus_path, db, veeroot)
            
    return Corpus(treebank_id, db, DbProvider(db_path))
    
    
def _check_db(db):
    try: 
        index_meta = dict(db.execute("SELECT key, value FROM index_metadata"))
        return index_meta.get("finished", False) and \
               index_meta.get("index_version", -1) == INDEX_VERSION
    except sqlite3.OperationalError:
        return False

    
def _index_treebank(corpus_path, db, veeroot=True):
    indexer = TigerCorpusIndexer(db, graph_serializer.GraphSerializer(), always_veeroot=veeroot)
    parse_tiger_corpus(corpus_path, indexer) 
    indexer.finalize()
    
