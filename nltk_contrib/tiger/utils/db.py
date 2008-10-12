# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Utilities for SQLite3 database handling."""
try:
    from pysqlite2 import dbapi2 as sqlite3
except ImportError:
    import sqlite3

def create_inmem_db():
    """Creates a new, empty in-memory SQlite3 database."""
    return sqlite3.connect(":memory:")
