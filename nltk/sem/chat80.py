# Natural Language Toolkit: Chat-80 KB Reader
# See https://www.w3.org/TR/swbp-skos-core-guide/
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>,
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
Overview
========

Chat-80 was a natural language system which allowed the user to
interrogate a Prolog knowledge base in the domain of world
geography. It was developed in the early '80s by Warren and Pereira; see
``https://www.aclweb.org/anthology/J82-3002.pdf`` for a description and
``http://www.cis.upenn.edu/~pereira/oldies.html`` for the source
files.

This module contains functions to extract data from the Chat-80
relation files ('the world database'), and convert then into a format
that can be incorporated in the FOL models of
``nltk.sem.evaluate``. The code assumes that the Prolog
input files are available in the NLTK corpora directory.

The Chat-80 World Database consists of the following files::

    world0.pl
    rivers.pl
    cities.pl
    countries.pl
    contain.pl
    borders.pl

This module uses a slightly modified version of ``world0.pl``, in which
a set of Prolog rules have been omitted. The modified file is named
``world1.pl``. Currently, the file ``rivers.pl`` is not read in, since
it uses a list rather than a string in the second field.

Reading Chat-80 Files
=====================

Chat-80 relations are like tables in a relational database. The
relation acts as the name of the table; the first argument acts as the
'primary key'; and subsequent arguments are further fields in the
table. In general, the name of the table provides a label for a unary
predicate whose extension is all the primary keys. For example,
relations in ``cities.pl`` are of the following form::

   'city(athens,greece,1368).'

Here, ``'athens'`` is the key, and will be mapped to a member of the
unary predicate *city*.

The fields in the table are mapped to binary predicates. The first
argument of the predicate is the primary key, while the second
argument is the data in the relevant field. Thus, in the above
example, the third field is mapped to the binary predicate
*population_of*, whose extension is a set of pairs such as
``'(athens, 1368)'``.

An exception to this general framework is required by the relations in
the files ``borders.pl`` and ``contains.pl``. These contain facts of the
following form::

    'borders(albania,greece).'

    'contains0(africa,central_africa).'

We do not want to form a unary concept out the element in
the first field of these records, and we want the label of the binary
relation just to be ``'border'``/``'contain'`` respectively.

In order to drive the extraction process, we use 'relation metadata bundles'
which are Python dictionaries such as the following::

  city = {'label': 'city',
          'closures': [],
          'schema': ['city', 'country', 'population'],
          'filename': 'cities.pl'}

According to this, the file ``city['filename']`` contains a list of
relational tuples (or more accurately, the corresponding strings in
Prolog form) whose predicate symbol is ``city['label']`` and whose
relational schema is ``city['schema']``. The notion of a ``closure`` is
discussed in the next section.

Concepts
========
In order to encapsulate the results of the extraction, a class of
``Concept`` objects is introduced.  A ``Concept`` object has a number of
attributes, in particular a ``prefLabel`` and ``extension``, which make
it easier to inspect the output of the extraction. In addition, the
``extension`` can be further processed: in the case of the ``'border'``
relation, we check that the relation is symmetric, and in the case
of the ``'contain'`` relation, we carry out the transitive
closure. The closure properties associated with a concept is
indicated in the relation metadata, as indicated earlier.

The ``extension`` of a ``Concept`` object is then incorporated into a
``Valuation`` object.

Persistence
===========
The functions ``val_dump`` and ``val_load`` are provided to allow a
valuation to be stored in a persistent database and re-loaded, rather
than having to be re-computed each time.

Individuals and Lexical Items
=============================
As well as deriving relations from the Chat-80 data, we also create a
set of individual constants, one for each entity in the domain. The
individual constants are string-identical to the entities. For
example, given a data item such as ``'zloty'``, we add to the valuation
a pair ``('zloty', 'zloty')``. In order to parse English sentences that
refer to these entities, we also create a lexical item such as the
following for each individual constant::

   PropN[num=sg, sem=<\P.(P zloty)>] -> 'Zloty'

The set of rules is written to the file ``chat_pnames.cfg`` in the
current directory.

"""

import dbm
import io
import itertools
import os
import re
import shelve
import stat
import sys

import nltk.data
from nltk import pathsec, redos
from nltk.pathsec import open as pathsec_open
from nltk.pathsec import validate_path
from nltk.picklesec import RestrictedUnpickler
from nltk.termsec import safe_print, sanitize_terminal

# shelve picks a dbm backend at runtime (gnu/ndbm/dumb/sqlite3) and sqlite writes
# rollback/WAL sidecars, so a store path spawns several derived backing files;
# every candidate name is checked, not just the base the caller passed.

#: The entry val_dump writes naming every key it stored. val_load reads each
#: key by lookup and never trusts iteration, which some dbm builds cut short
#: (a measured ndbm build drops a key once one value reaches 4096 bytes).
_STORE_MANIFEST_KEY = "__nltk_keys__"

#: The dbm backends' sidecars, then sqlite's from pathsec.
_STORE_SIDECAR_SUFFIXES = ("", ".db", ".dir", ".pag", ".dat", ".bak") + (
    pathsec.SQLITE_SIDECARS
)


def _store_names(base):
    """Every backing name a store at *base* may have across the dbm and sqlite
    backends; the checks cover all of them whichever backend is in use."""
    return [base + suffix for suffix in _STORE_SIDECAR_SUFFIXES]


def _check_store_dir(base, context):
    """Refuse a store whose directory another account could write or rename.

    Every backend reopens a store's backing names by path after the checks
    here, so the directory must be private and each ancestor private or sticky
    (CWE-367); :func:`nltk.pathsec.validate_private_dir` is the judge.
    """
    pathsec.validate_private_dir(
        os.path.dirname(os.path.abspath(base)) or os.curdir, context=context
    )


def _pin_store_files(base, context):
    """Hold every existing backing name of a store open (``O_NOFOLLOW``, no
    hardlink) across the backend's own open by name, through
    :func:`nltk.pathsec.pin_files`. Nothing is created."""
    return pathsec.pin_files(_store_names(base), context=context)


def _verify_store_files(pins, base, context):
    """After the backend opened the store by name, prove it saw the pinned
    inodes (:func:`nltk.pathsec.verify_pinned`); the pins are released."""
    pathsec.verify_pinned(pins, _store_names(base), context=context)


#: The header dbm's detection reads to pick its sqlite backend (Python 3.13+).
_SQLITE_HEADER = b"SQLite format 3\0"
#: The sibling names that detection consults before the file itself.
_DBM_SIBLING_SUFFIXES = (".pag", ".dir", ".db", ".dat")


class _SqliteStore:
    """A store in the ``dbm.sqlite3`` layout, one table ``Dict`` of key and
    value BLOBs, read on an armed connection instead of the backend's own.

    ``dbm`` picks that backend by file header and runs whatever schema the
    file holds on the first lookup, so a view, trigger or virtual table named
    ``Dict`` in a planted store was executed (an endless view hung
    ``val_load``). :func:`nltk.pathsec.connect_sqlite_read_only` binds the
    connection to the file, refuses such a schema and budgets every
    statement; the queries are the backend's own. The mapping is what
    :class:`shelve.Shelf` wraps: bytes keys, raw pickled values.
    """

    def __init__(self, connection):
        self._cx = connection

    def __getitem__(self, key):
        row = self._cx.execute(
            "SELECT value FROM Dict WHERE key = CAST(? AS BLOB)", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(key)
        return row[0]

    def __contains__(self, key):
        row = self._cx.execute(
            "SELECT 1 FROM Dict WHERE key = CAST(? AS BLOB)", (key,)
        ).fetchone()
        return row is not None

    def __len__(self):
        return self._cx.execute("SELECT COUNT(key) FROM Dict").fetchone()[0]

    def keys(self):
        return [row[0] for row in self._cx.execute("SELECT key FROM Dict")]

    def close(self):
        self._cx.close()


def _is_sqlite_store(db, pins):
    """Whether the PINNED file at *db* is a sqlite database that ``dbm``
    would hand to its sqlite backend: the header matches and no sibling name
    detection prefers exists. Decided on the pinned handle, never by name."""
    handle = pins.get(db)
    if handle is None or any(db + suffix in pins for suffix in _DBM_SIBLING_SUFFIXES):
        return False
    handle.seek(0)
    header = handle.read(len(_SQLITE_HEADER))
    handle.seek(0)
    return header == _SQLITE_HEADER


def _open_sqlite_store(db, pins, context):
    """A :class:`shelve.Shelf` over :class:`_SqliteStore` for the store at
    *db*: the armed connector pins and opens the file itself, the caller's
    pins are verified against the names after, and a file without the
    backend's ``Dict`` table is reported like any unreadable store."""
    connection = pathsec.connect_sqlite_read_only(
        db, names=_store_names(db), context=context
    )
    try:
        _verify_store_files(pins, db, context=context)
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'Dict'"
        ).fetchone()
        if row is None:
            raise OSError("sqlite store without the Dict table of dbm.sqlite3")
    except BaseException:
        connection.close()
        raise
    return shelve.Shelf(_SqliteStore(connection))


def _restricted_shelve_open(db, flag="r"):
    """Open a shelf whose values are read with a RESTRICTED unpickler.

    ``shelve`` unpickles each stored value with the default, unrestricted
    ``pickle.Unpickler``, so a ``.db`` file whose value bytes are a crafted
    pickle gadget runs arbitrary code when read back, even though the file
    PATH was validated (validate_path checks where the file is, not what is in
    it). Chat-80 valuations are only sets and tuples of strings, which need no
    globals, so :class:`nltk.picklesec.RestrictedUnpickler` (which blocks every
    global while allowing plain containers) loads legitimate data and refuses
    the gadget.

    A store that is a sqlite database (what ``dbm`` writes on Python 3.13+)
    is read through :class:`_SqliteStore` on the armed pathsec connection
    rather than the backend's own open, so the file's schema is screened and
    its statements budgeted; every other backend opens as before.
    """
    # Reject a symlink/hardlink at any derived backing name before shelve reopens
    # it by path, so O_NOFOLLOW guards the open validate_path alone cannot.
    context = "chat80._restricted_shelve_open"
    pins = _pin_store_files(db, context=context)
    try:
        if flag == "r" and _is_sqlite_store(db, pins):
            inner = _open_sqlite_store(db, pins, context=context)
        else:
            inner = shelve.open(db, flag)
            try:
                _verify_store_files(pins, db, context=context)
            except BaseException:
                inner.close()
                raise
    except BaseException:
        pathsec.release(pins)
        raise

    class _RestrictedShelf:
        """Delegates to a real shelf but reads values with RestrictedUnpickler.

        Valuation() iterates the shelf as (key, value) pairs, which resolves
        __getitem__ on the TYPE, so overriding it on an instance of shelve.Shelf
        would not take effect. A wrapper whose own __getitem__ does the
        restricted load is used instead.
        """

        def __iter__(self):
            return iter(inner)

        def keys(self):
            return inner.keys()

        def __len__(self):
            return len(inner)

        def __contains__(self, key):
            return key in inner

        def __getitem__(self, key):
            raw = inner.dict[key.encode(inner.keyencoding)]
            return RestrictedUnpickler(io.BytesIO(raw)).load()

        def items(self):
            for key in inner:
                yield key, self[key]

        def close(self):
            inner.close()

    return _RestrictedShelf()


###########################################################################
# Chat-80 relation metadata bundles needed to build the valuation
###########################################################################

borders = {
    "rel_name": "borders",
    "closures": ["symmetric"],
    "schema": ["region", "border"],
    "filename": "borders.pl",
}

contains = {
    "rel_name": "contains0",
    "closures": ["transitive"],
    "schema": ["region", "contain"],
    "filename": "contain.pl",
}

city = {
    "rel_name": "city",
    "closures": [],
    "schema": ["city", "country", "population"],
    "filename": "cities.pl",
}

country = {
    "rel_name": "country",
    "closures": [],
    "schema": [
        "country",
        "region",
        "latitude",
        "longitude",
        "area",
        "population",
        "capital",
        "currency",
    ],
    "filename": "countries.pl",
}

circle_of_lat = {
    "rel_name": "circle_of_latitude",
    "closures": [],
    "schema": ["circle_of_latitude", "degrees"],
    "filename": "world1.pl",
}

circle_of_long = {
    "rel_name": "circle_of_longitude",
    "closures": [],
    "schema": ["circle_of_longitude", "degrees"],
    "filename": "world1.pl",
}

continent = {
    "rel_name": "continent",
    "closures": [],
    "schema": ["continent"],
    "filename": "world1.pl",
}

region = {
    "rel_name": "in_continent",
    "closures": [],
    "schema": ["region", "continent"],
    "filename": "world1.pl",
}

ocean = {
    "rel_name": "ocean",
    "closures": [],
    "schema": ["ocean"],
    "filename": "world1.pl",
}

sea = {"rel_name": "sea", "closures": [], "schema": ["sea"], "filename": "world1.pl"}


items = [
    "borders",
    "contains",
    "city",
    "country",
    "circle_of_lat",
    "circle_of_long",
    "continent",
    "region",
    "ocean",
    "sea",
]
items = tuple(sorted(items))

item_metadata = {
    "borders": borders,
    "contains": contains,
    "city": city,
    "country": country,
    "circle_of_lat": circle_of_lat,
    "circle_of_long": circle_of_long,
    "continent": continent,
    "region": region,
    "ocean": ocean,
    "sea": sea,
}

rels = item_metadata.values()

not_unary = ["borders.pl", "contain.pl"]

###########################################################################


class Concept:
    """
    A Concept class, loosely based on SKOS
    (https://www.w3.org/TR/swbp-skos-core-guide/).
    """

    def __init__(self, prefLabel, arity, altLabels=None, closures=None, extension=None):
        """
        :param prefLabel: the preferred label for the concept
        :type prefLabel: str
        :param arity: the arity of the concept
        :type arity: int
        :param altLabels: other (related) labels, defaults to an empty list
        :type altLabels: list or None
        :param closures: closure properties of the extension
            (list items can be ``symmetric``, ``reflexive``, ``transitive``),
            defaults to an empty list
        :type closures: list or None
        :param extension: the extensional value of the concept, defaults to an empty set
        :type extension: set or None
        """
        self.prefLabel = prefLabel
        self.arity = arity
        self.altLabels = [] if altLabels is None else altLabels
        self.closures = [] if closures is None else closures
        # keep _extension internally as a set
        self._extension = set() if extension is None else extension
        # public access is via a list (for slicing)
        self.extension = sorted(list(self._extension))

    def __str__(self):
        # _extension = ''
        # for element in sorted(self.extension):
        # if isinstance(element, tuple):
        # element = '(%s, %s)' % (element)
        # _extension += element + ', '
        # _extension = _extension[:-1]

        return "Label = '{}'\nArity = {}\nExtension = {}".format(
            self.prefLabel,
            self.arity,
            self.extension,
        )

    def __repr__(self):
        return "Concept('%s')" % self.prefLabel

    def augment(self, data):
        """
        Add more data to the ``Concept``'s extension set.

        :param data: a new semantic value
        :type data: string or pair of strings
        :rtype: set

        """
        self._extension.add(data)
        self.extension = sorted(list(self._extension))
        return self._extension

    def _make_graph(self, s):
        """
        Convert a set of pairs into an adjacency linked list encoding of a graph.
        """
        g = {}
        for x, y in s:
            if x in g:
                g[x].append(y)
            else:
                g[x] = [y]
        return g

    def _transclose(self, g):
        """
        Compute the transitive closure of a graph represented as a linked list.
        """
        for x in g:
            for adjacent in g[x]:
                # check that adjacent is a key
                if adjacent in g:
                    for y in g[adjacent]:
                        if y not in g[x]:
                            g[x].append(y)
        return g

    def _make_pairs(self, g):
        """
        Convert an adjacency linked list back into a set of pairs.
        """
        pairs = []
        for node in g:
            for adjacent in g[node]:
                pairs.append((node, adjacent))
        return set(pairs)

    def close(self):
        """
        Close a binary relation in the ``Concept``'s extension set.

        :return: a new extension for the ``Concept`` in which the
                 relation is closed under a given property
        """
        from nltk.sem import is_rel

        assert is_rel(self._extension)
        if "symmetric" in self.closures:
            pairs = []
            for x, y in self._extension:
                pairs.append((y, x))
            sym = set(pairs)
            self._extension = self._extension.union(sym)
        if "transitive" in self.closures:
            all = self._make_graph(self._extension)
            closed = self._transclose(all)
            trans = self._make_pairs(closed)
            self._extension = self._extension.union(trans)
        self.extension = sorted(list(self._extension))


def clause2concepts(filename, rel_name, schema, closures=[]):
    """
    Convert a file of Prolog clauses into a list of ``Concept`` objects.

    :param filename: filename containing the relations
    :type filename: str
    :param rel_name: name of the relation
    :type rel_name: str
    :param schema: the schema used in a set of relational tuples
    :type schema: list
    :param closures: closure properties for the extension of the concept
    :type closures: list
    :return: a list of ``Concept`` objects
    :rtype: list
    """
    concepts = []
    # position of the subject of a binary relation
    subj = 0
    # label of the 'primary key'
    pkey = schema[0]
    # fields other than the primary key
    fields = schema[1:]

    # convert a file into a list of lists
    records = _str2records(filename, rel_name)

    # add a unary concept corresponding to the set of entities
    # in the primary key position
    # relations in 'not_unary' are more like ordinary binary relations
    if filename not in not_unary:
        concepts.append(unary_concept(pkey, subj, records))

    # add a binary concept for each non-key field
    for field in fields:
        obj = schema.index(field)
        concepts.append(binary_concept(field, closures, subj, obj, records))

    return concepts


def cities2table(filename, rel_name, dbname, verbose=False, setup=False):
    """
    Convert a file of Prolog clauses into a database table.

    This is not generic, since it doesn't allow arbitrary
    schemas to be set as a parameter.

    Intended usage::

        cities2table('cities.pl', 'city', 'city.db', verbose=True, setup=True)

    :param filename: filename containing the relations
    :type filename: str
    :param rel_name: name of the relation
    :type rel_name: str
    :param dbname: filename of persistent store
    :type schema: str
    """
    # dbname is a caller-supplied path that sqlite creates or opens by name.
    # Validate it before any file is created so an out-of-sandbox target is
    # refused up front (GHSA-8mgp-746c-j5xp), and judge its directory.
    validate_path(dbname, context="chat80.cities2table")
    _check_store_dir(dbname, context="chat80.cities2table")
    records = _str2records(filename, rel_name)
    # The connector pins the store and its sidecars across sqlite's own open
    # (no link, GHSA-7j4p) and arms the connection: an existing file at dbname
    # is data, so a trigger or view in it is refused and every statement bounded.
    connection = pathsec.connect_sqlite_writable(
        dbname, names=_store_names(dbname), context="chat80.cities2table"
    )
    cur = connection.cursor()
    if setup:
        cur.execute(
            """CREATE TABLE city_table
        (City text, Country text, Population int)"""
        )

    table_name = "city_table"
    for t in records:
        cur.execute("insert into %s values (?,?,?)" % table_name, t)
        if verbose:
            safe_print("inserting values into %s: " % table_name, t)
    connection.commit()
    if verbose:
        safe_print("Committing update to %s" % dbname)
    cur.close()


# PRAGMAs that move sqlite's temporary files to a caller-named directory.
_DIRECTORY_PRAGMAS = frozenset({"temp_store_directory", "data_store_directory"})


def _sql_query_authorizer(action, arg1, arg2, db_name, trigger):
    """sqlite authorizer for :func:`sql_query`: refuse statements naming a file.

    ``ATTACH`` (which ``VACUUM INTO`` is also routed through) opens or creates
    whatever path the SQL text names, and the directory pragmas redirect
    sqlite's temporary files, so a query text could reach a file outside the
    one store that was validated (CWE-73). Every other statement is left to
    sqlite, so the query surface is otherwise unchanged.
    """
    import sqlite3

    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA and str(arg1).lower() in _DIRECTORY_PRAGMAS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def sql_query(dbname, query):
    """
    Execute an SQL query over a database.
    :param dbname: filename of persistent store
    :type schema: str
    :param query: SQL query
    :type rel_name: str
    """
    import os
    import sqlite3

    try:
        path = nltk.data.find(dbname)
        # find() bounds the resource NAME to a data root; only a plain file on
        # disk can be handed to sqlite, never a zip entry or dataset pointer
        # whose string form sqlite would create or open as a fresh path.
        if not isinstance(path, nltk.data.FileSystemPathPointer) or os.path.isdir(
            path.path
        ):
            raise ValueError(
                "%s is not an uncompressed database file on disk"
                % sanitize_terminal(str(path))
            )
        db_path = path.path
        # The file BEHIND the name is validated here: the resolved target must
        # sit in a data root, and neither the store nor a sqlite sidecar may be
        # a link or special file that the by-path open would follow (GHSA-xv54).
        validate_path(db_path, context="chat80.sql_query")
        _check_store_dir(db_path, context="chat80.sql_query")
        connection = pathsec.connect_sqlite_read_only(
            db_path, names=_store_names(db_path), context="chat80.sql_query"
        )
        connection.set_authorizer(_sql_query_authorizer)
        cur = connection.cursor()
        return cur.execute(query)
    except (ValueError, sqlite3.OperationalError):
        import warnings

        warnings.warn(
            "Make sure the database file %s is installed and uncompressed."
            % sanitize_terminal(dbname)
        )
        raise


def _str2records(filename, rel):
    """
    Read a file into memory and convert each relation clause into a list.
    """
    recs = []
    # ``rel`` (caller relation name) is spliced into a regex run over each line;
    # redos.compile bounds compile + match time.
    rel_rx = redos.compile(re.escape(rel) + r"\(")  # rel is a literal relation name
    contents = nltk.data.load("corpora/chat80/%s" % filename, format="text")
    for line in contents.splitlines():
        if line.startswith(rel):
            line = rel_rx.sub("", line)
            line = redos.sub(r"\)\.$", "", line)
            record = line.split(",")
            recs.append(record)
    return recs


def unary_concept(label, subj, records):
    """
    Make a unary concept out of the primary key in a record.

    A record is a list of entities in some relation, such as
    ``['france', 'paris']``, where ``'france'`` is acting as the primary
    key.

    :param label: the preferred label for the concept
    :type label: string
    :param subj: position in the record of the subject of the predicate
    :type subj: int
    :param records: a list of records
    :type records: list of lists
    :return: ``Concept`` of arity 1
    :rtype: Concept
    """
    c = Concept(label, arity=1, extension=set())
    for record in records:
        c.augment(record[subj])
    return c


def binary_concept(label, closures, subj, obj, records):
    """
    Make a binary concept out of the primary key and another field in a record.

    A record is a list of entities in some relation, such as
    ``['france', 'paris']``, where ``'france'`` is acting as the primary
    key, and ``'paris'`` stands in the ``'capital_of'`` relation to
    ``'france'``.

    More generally, given a record such as ``['a', 'b', 'c']``, where
    label is bound to ``'B'``, and ``obj`` bound to 1, the derived
    binary concept will have label ``'B_of'``, and its extension will
    be a set of pairs such as ``('a', 'b')``.


    :param label: the base part of the preferred label for the concept
    :type label: str
    :param closures: closure properties for the extension of the concept
    :type closures: list
    :param subj: position in the record of the subject of the predicate
    :type subj: int
    :param obj: position in the record of the object of the predicate
    :type obj: int
    :param records: a list of records
    :type records: list of lists
    :return: ``Concept`` of arity 2
    :rtype: Concept
    """
    if not label == "border" and not label == "contain":
        label = label + "_of"
    c = Concept(label, arity=2, closures=closures, extension=set())
    for record in records:
        c.augment((record[subj], record[obj]))
    # close the concept's extension according to the properties in closures
    c.close()
    return c


def process_bundle(rels):
    """
    Given a list of relation metadata bundles, make a corresponding
    dictionary of concepts, indexed by the relation name.

    :param rels: bundle of metadata needed for constructing a concept
    :type rels: list(dict)
    :return: a dictionary of concepts, indexed by the relation name.
    :rtype: dict(str): Concept
    """
    concepts = {}
    for rel in rels:
        rel_name = rel["rel_name"]
        closures = rel["closures"]
        schema = rel["schema"]
        filename = rel["filename"]

        concept_list = clause2concepts(filename, rel_name, schema, closures)
        for c in concept_list:
            label = c.prefLabel
            if label in concepts:
                for data in c.extension:
                    concepts[label].augment(data)
                concepts[label].close()
            else:
                concepts[label] = c
    return concepts


def make_valuation(concepts, read=False, lexicon=False):
    """
    Convert a list of ``Concept`` objects into a list of (label, extension) pairs;
    optionally create a ``Valuation`` object.

    :param concepts: concepts
    :type concepts: list(Concept)
    :param read: if ``True``, ``(symbol, set)`` pairs are read into a ``Valuation``
    :type read: bool
    :rtype: list or Valuation
    """
    vals = []

    for c in concepts:
        vals.append((c.prefLabel, c.extension))
    if lexicon:
        read = True
    if read:
        from nltk.sem import Valuation

        val = Valuation({})
        val.update(vals)
        # add labels for individuals
        val = label_indivs(val, lexicon=lexicon)
        return val
    else:
        return vals


def val_dump(rels, db):
    """
    Make a ``Valuation`` from a list of relation metadata bundles and dump to
    persistent database.

    :param rels: bundle of metadata needed for constructing a concept
    :type rels: list of dict
    :param db: name of file to which data is written.
               The suffix '.db' will be automatically appended.
    :type db: str
    """
    # db is a caller-supplied path handed to shelve.open(), which creates the
    # backing files. Validate before any work so an out-of-sandbox target is
    # refused up front (GHSA-8mgp-746c-j5xp).
    validate_path(db, context="chat80.val_dump")
    # Reject a symlink/hardlink at any derived backing name before shelve creates
    # the store by path (O_NOFOLLOW, GHSA-7j4p).
    _check_store_dir(db, context="chat80.val_dump")
    # a link planted at any backing name is refused up front (the install
    # below never follows one either)
    pathsec.release(_pin_store_files(db, context="chat80.val_dump"))
    concepts = process_bundle(rels).values()
    valuation = make_valuation(concepts, read=True)
    # the backend writes only inside a fresh private directory beside the
    # store, then each file is renamed into place, so no name at the
    # destination is ever opened
    parent, stem = os.path.split(os.path.abspath(db))
    staging = nltk.data.make_staging_dir(prefix=".nltk_chat80_", dir=parent)
    try:
        db_out = shelve.open(os.path.join(staging, stem), "n")
        try:
            db_out.update(valuation)
            db_out[_STORE_MANIFEST_KEY] = sorted(valuation)
        finally:
            db_out.close()
        _install_store(staging, stem, db, context="chat80.val_dump")
    finally:
        try:
            pathsec.remove_tree(staging, context="chat80.val_dump")
        except OSError:
            pass


def _install_store(staging, stem, db, context):
    """Move the store files written under *staging* to the backing names of *db*.

    The old backing names are checked as every open checks them, then removed
    with :func:`nltk.pathsec.unlink` (a name is never followed), and each new
    file is renamed onto its name with :func:`nltk.pathsec.replace`, which
    replaces whatever is there without following it either and checks the
    inode after. So a name planted at the destination at any point is never
    written through (CWE-59, CWE-367); one found at the check is refused, and
    the whole set is checked again once every rename is done.
    """
    built = {}
    for entry in sorted(os.listdir(staging)):
        suffix = entry[len(stem) :]
        if not entry.startswith(stem) or suffix not in _STORE_SIDECAR_SUFFIXES:
            raise OSError(
                "chat80 store backend wrote %r, which is not a backing name the "
                "store checks know" % sanitize_terminal(entry)
            )
        st = os.lstat(os.path.join(staging, entry))
        built[db + suffix] = (os.path.join(staging, entry), (st.st_dev, st.st_ino))
    old = _pin_store_files(db, context)
    pathsec.release(old)
    for name in old:
        pathsec.unlink(name, context=context)
    for name, (path, _identity) in built.items():
        pathsec.replace(path, name, context=context)
    for name, (_path, identity) in built.items():
        st = os.lstat(name)
        if not stat.S_ISREG(st.st_mode) or (st.st_dev, st.st_ino) != identity:
            raise PermissionError(
                f"Security Violation [{context}]: store file "
                f"{sanitize_terminal(name)!r} was swapped while the store was installed."
            )


def val_load(db):
    """
    Load a ``Valuation`` from a persistent database.

    :param db: name of file from which data is read.
               The suffix '.db' should be omitted from the name.
    :type db: str
    """
    # db is a caller-supplied path handed to shelve.open(), which opens the
    # backing files. Validate before touching the filesystem so an
    # out-of-sandbox target is refused up front (GHSA-8mgp-746c-j5xp).
    validate_path(db, context="chat80.val_load")
    _check_store_dir(db, context="chat80.val_load")
    # No os.access() gate: it follows a symlink at the derived .db name and its
    # suffix assumes one dbm backend. _restricted_shelve_open opens each backing
    # name with O_NOFOLLOW (GHSA-7j4p); a store it cannot open is reported the
    # way the gate used to, with the caller's name neutralised for the terminal.
    try:
        db_in = _restricted_shelve_open(db)
    except PermissionError:
        # a security refusal stays loud and distinct from an unreadable store
        raise
    except (OSError, *dbm.error) as e:
        # the whole line is neutralised: the backend's message can quote the
        # caller's name too, and both reach the terminal
        sys.exit(sanitize_terminal("Cannot read file: {} ({})".format(db + ".db", e)))
    from nltk.sem import Valuation

    try:
        stored = _stored_items(db_in, db)
    finally:
        db_in.close()
    # val_dump stores make_valuation's Valuation, whose relations are the sorted
    # Concept.extension lists; the Valuation constructor checks every other value
    # and refuses lists, so the relations are added the way make_valuation does.
    val = Valuation(item for item in stored if not _is_extension_list(item[1]))
    val.update(item for item in stored if _is_extension_list(item[1]))
    return val


def _stored_items(db_in, db):
    """The (key, value) pairs of a store, read by the manifest val_dump wrote.

    Each manifest key is looked up directly; a manifest that is not a sorted
    list of distinct names, or that disagrees with the store, is refused. A
    store without a manifest is refused on every backend: its keys could only
    come from iteration, which is never trusted.
    """
    if _STORE_MANIFEST_KEY in db_in:
        keys = db_in[_STORE_MANIFEST_KEY]
        if (
            not isinstance(keys, list)
            or not all(type(key) is str for key in keys)
            or keys != sorted(set(keys))
            or _STORE_MANIFEST_KEY in keys
        ):
            raise ValueError(
                "chat80 store %s: its key manifest is not the sorted list of "
                "names val_dump writes" % sanitize_terminal(db)
            )
        missing = [key for key in keys if key not in db_in]
        if missing:
            raise ValueError(
                "chat80 store %s: manifest names %d key(s) the store lacks"
                % (sanitize_terminal(db), len(missing))
            )
        if len(db_in) > len(keys) + 1:
            raise ValueError(
                "chat80 store %s: holds keys its manifest does not name"
                % sanitize_terminal(db)
            )
        return [(key, db_in[key]) for key in keys]
    raise ValueError(
        "chat80 store %s has no key manifest, so its keys could only be read by "
        "iteration, which some dbm builds cut short; re-create it with val_dump"
        % sanitize_terminal(db)
    )


def _is_extension_list(value):
    """Whether ``value`` is a list ``val_dump`` writes: a ``Concept.extension``,
    the sorted distinct strings of a unary relation or string pairs of a binary one.
    """
    if type(value) is not list:
        return False
    if not (
        all(type(item) is str for item in value)
        or all(
            type(item) is tuple
            and len(item) == 2
            and all(type(part) is str for part in item)
            for item in value
        )
    ):
        return False
    return all(a < b for a, b in itertools.pairwise(value))


# def alpha(str):
# """
# Utility to filter out non-alphabetic constants.

#:param str: candidate constant
#:type str: string
#:rtype: bool
# """
# try:
# int(str)
# return False
# except ValueError:
## some unknown values in records are labeled '?'
# if not str == '?':
# return True


def label_indivs(valuation, lexicon=False):
    """
    Assign individual constants to the individuals in the domain of a ``Valuation``.

    Given a valuation with an entry of the form ``{'rel': {'a': True}}``,
    add a new entry ``{'a': 'a'}``.

    :type valuation: Valuation
    :rtype: Valuation
    """
    # collect all the individuals into a domain
    domain = valuation.domain
    # convert the domain into a sorted list of alphabetic terms
    # use the same string as a label
    pairs = [(e, e) for e in domain]
    if lexicon:
        lex = make_lex(domain)
        with pathsec_open(
            "chat_pnames.cfg", "w", context="chat80.label_indivs"
        ) as outfile:
            outfile.writelines(lex)
    # read the pairs into the valuation
    valuation.update(pairs)
    return valuation


def make_lex(symbols):
    """
    Create lexical CFG rules for each individual symbol.

    Given a valuation with an entry of the form ``{'zloty': 'zloty'}``,
    create a lexical rule for the proper name 'Zloty'.

    :param symbols: a list of individual constants in the semantic representation
    :type symbols: sequence -- set(str)
    :rtype: list(str)
    """
    lex = []
    header = """
##################################################################
# Lexical rules automatically generated by running 'chat80.py -x'.
##################################################################

"""
    lex.append(header)
    template = r"PropN[num=sg, sem=<\P.(P %s)>] -> '%s'\n"

    for s in symbols:
        parts = s.split("_")
        caps = [p.capitalize() for p in parts]
        pname = "_".join(caps)
        rule = template % (s, pname)
        lex.append(rule)
    return lex


###########################################################################
# Interface function to emulate other corpus readers
###########################################################################


def concepts(items=items):
    """
    Build a list of concepts corresponding to the relation names in ``items``.

    :param items: names of the Chat-80 relations to extract
    :type items: list(str)
    :return: the ``Concept`` objects which are extracted from the relations
    :rtype: list(Concept)
    """
    if isinstance(items, str):
        items = (items,)

    rels = [item_metadata[r] for r in items]

    concept_map = process_bundle(rels)
    return concept_map.values()


###########################################################################


def main():
    import sys
    from optparse import OptionParser

    description = """
Extract data from the Chat-80 Prolog files and convert them into a
Valuation object for use in the NLTK semantics package.
    """

    opts = OptionParser(description=description)
    opts.set_defaults(verbose=True, lex=False, vocab=False)
    opts.add_option(
        "-s", "--store", dest="outdb", help="store a valuation in DB", metavar="DB"
    )
    opts.add_option(
        "-l",
        "--load",
        dest="indb",
        help="load a stored valuation from DB",
        metavar="DB",
    )
    opts.add_option(
        "-c",
        "--concepts",
        action="store_true",
        help="print concepts instead of a valuation",
    )
    opts.add_option(
        "-r",
        "--relation",
        dest="label",
        help="print concept with label REL (check possible labels with '-v' option)",
        metavar="REL",
    )
    opts.add_option(
        "-q",
        "--quiet",
        action="store_false",
        dest="verbose",
        help="don't print out progress info",
    )
    opts.add_option(
        "-x",
        "--lex",
        action="store_true",
        dest="lex",
        help="write a file of lexical entries for country names, then exit",
    )
    opts.add_option(
        "-v",
        "--vocab",
        action="store_true",
        dest="vocab",
        help="print out the vocabulary of concept labels and their arity, then exit",
    )

    options, args = opts.parse_args()
    if options.outdb and options.indb:
        opts.error("Options --store and --load are mutually exclusive")

    if options.outdb:
        # write the valuation to a persistent database
        if options.verbose:
            outdb = options.outdb + ".db"
            safe_print("Dumping a valuation to %s" % outdb)
        val_dump(rels, options.outdb)
        sys.exit(0)
    else:
        # try to read in a valuation from a database
        if options.indb is not None:
            # No os.access() gate: it follows a symlink at the derived .db name.
            # val_load validates the path and opens each backing name O_NOFOLLOW.
            valuation = val_load(options.indb)
        # we need to create the valuation from scratch
        else:
            # build some concepts
            concept_map = process_bundle(rels)
            concepts = concept_map.values()
            # just print out the vocabulary
            if options.vocab:
                items = sorted((c.arity, c.prefLabel) for c in concepts)
                for arity, label in items:
                    safe_print(label, arity)
                sys.exit(0)
            # show all the concepts
            if options.concepts:
                for c in concepts:
                    safe_print(c)
                    safe_print()
            if options.label:
                safe_print(concept_map[options.label])
                sys.exit(0)
            else:
                # turn the concepts into a Valuation
                if options.lex:
                    if options.verbose:
                        safe_print("Writing out lexical rules")
                    make_valuation(concepts, lexicon=True)
                else:
                    valuation = make_valuation(concepts, read=True)
                    safe_print(valuation)


def sql_demo():
    """
    Print out every row from the 'city.db' database.
    """
    safe_print()
    safe_print("Using SQL to extract rows from 'city.db' RDB.")
    for row in sql_query("corpora/city_database/city.db", "SELECT * FROM city_table"):
        safe_print(row)


if __name__ == "__main__":
    main()
    sql_demo()
