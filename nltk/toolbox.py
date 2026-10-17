# Natural Language Toolkit: Toolbox Reader
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Module for reading, writing and manipulating
Toolbox databases and settings files.
"""

import codecs
from io import StringIO
from xml.etree.ElementTree import Element, ElementTree, SubElement, TreeBuilder

from nltk import redos
from nltk.data import PathPointer, _refuse_file_not_ours, find
from nltk.data import text_encoding as _text_encoding
from nltk.pathsec import open as pathsec_open
from nltk.termsec import safe_print
from nltk.xmlsec import safe_element_name

#: Maximum depth the recursive Toolbox settings helpers will descend to.
#: Beyond this they raise ValueError instead of letting Python raise an
#: uncaught RecursionError (CWE-674).  Configurable.
MAX_TOOLBOX_DEPTH = 500

#: Most fields ``ToolboxData.parse(grammar=...)`` chunks in one record: the chunk
#: rules rescan the rest of a record for every match, so a wider record is
#: refused before matching (the widest shipped record has 423). Configurable.
MAX_CHUNK_RECORD_FIELDS = 10_000


class StandardFormat:
    """
    Class for reading and processing standard format marker files and strings.
    """

    #: A file's lines end at LF, CRLF or CR, as open() reads them; a string's
    #: at LF only, as StringIO always split them (``toolbox.doctest``).
    _cr_ends_line = True

    def __init__(self, filename=None, encoding=None):
        self._encoding = encoding
        if filename is not None:
            self.open(filename)

    def open(self, sfm_file):
        """
        Open a standard format marker file for sequential reading.

        :param sfm_file: name of the standard format marker input file
        :type sfm_file: str
        """
        encoding = _text_encoding(self._encoding)
        if isinstance(sfm_file, PathPointer):
            # Spelled with underscores the codec misses the reader's BOM table
            # and applies its own BOM rule, as open() does on the other route
            # (the table drops a utf-8 or utf-16-le BOM that open() keeps).
            self._file = sfm_file.open(encoding.replace("-", "_").replace(" ", "_"))
        else:
            # pathsec containment with O_NOFOLLOW and hardlink guards (CWE-59,
            # GHSA-cr8c), and the refusal a PathPointer open gives a file another
            # account owns or can write.
            self._file = _refuse_file_not_ours(
                pathsec_open(
                    sfm_file,
                    "r",
                    context="toolbox.StandardFormat",
                    encoding=self._encoding,
                ),
                sfm_file,
            )
        self._cr_ends_line = True

    def open_string(self, s):
        """
        Open a standard format marker string for sequential reading.

        :param s: string to parse as a standard format marker input file
        :type s: str
        """
        self._file = StringIO(s)
        self._cr_ends_line = False

    def _lines(self):
        """The lines of the open file or string, without their line breaks.

        The text is split here rather than by the stream: a Standard Format
        line ends at LF, CRLF or CR, as open() reads it, so U+2028, U+2029,
        NEL, VT, FF, FS, GS and RS end no line on any route, where the
        stream's own readline would end one at each.
        """
        text = self._file.read()
        if self._cr_ends_line:
            text = text.replace("\r\n", "\n").replace("\r", "\n")
        start, end = 0, len(text)
        while start < end:
            stop = text.find("\n", start)
            if stop < 0:
                stop = end
            yield text[start:stop]
            start = stop + 1

    def raw_fields(self):
        """
        Return an iterator that returns the next field in a (marker, value)
        tuple. Linebreaks and trailing white space are preserved except
        for the final newline in each field.

        :rtype: iter(tuple(str, str))
        """
        join_string = "\n"
        line_regexp = r"^%s(?:\\(\S+)\s*)?(.*)$"
        # discard a BOM in the first line: UTF-8 bytes read as Latin-1, or U+FEFF
        first_line_pat = redos.compile(line_regexp % "(?:\xef\xbb\xbf|\ufeff)?")
        line_pat = redos.compile(line_regexp % "")
        # need to get first line outside the loop for correct handling
        # of the first marker if it spans multiple lines
        file_iter = self._lines()
        # PEP 479, prevent RuntimeError when StopIteration is raised inside generator
        try:
            line = next(file_iter)
        except StopIteration:
            # no more data is available, terminate the generator
            return
        mobj = redos.match(first_line_pat, line)
        mkr, line_value = mobj.groups()
        value_lines = [line_value]
        self.line_num = 0
        for line in file_iter:
            self.line_num += 1
            mobj = redos.match(line_pat, line)
            line_mkr, line_value = mobj.groups()
            if line_mkr:
                yield (mkr, join_string.join(value_lines))
                mkr = line_mkr
                value_lines = [line_value]
            else:
                value_lines.append(line_value)
        self.line_num += 1
        yield (mkr, join_string.join(value_lines))

    def fields(
        self,
        strip=True,
        unwrap=True,
        encoding=None,
        errors="strict",
        unicode_fields=None,
    ):
        """
        Return an iterator that returns the next field in a ``(marker, value)``
        tuple, where ``marker`` and ``value`` are unicode strings if an ``encoding``
        was specified in the ``fields()`` method. Otherwise they are non-unicode strings.

        :param strip: strip trailing whitespace from the last line of each field
        :type strip: bool
        :param unwrap: Convert newlines in a field to spaces.
        :type unwrap: bool
        :param encoding: Name of an encoding to use. If it is specified then
            the ``fields()`` method returns unicode strings rather than non
            unicode strings.
        :type encoding: str or None
        :param errors: Error handling scheme for codec. Same as the ``decode()``
            builtin string method.
        :type errors: str
        :param unicode_fields: Set of marker names whose values are UTF-8 encoded.
            Ignored if encoding is None. If the whole file is UTF-8 encoded set
            ``encoding='utf8'`` and leave ``unicode_fields`` with its default
            value of None.
        :type unicode_fields: sequence
        :rtype: iter(tuple(str, str))
        """
        if encoding is None and unicode_fields is not None:
            raise ValueError("unicode_fields is set but not encoding.")
        unwrap_pat = redos.compile(r"\n+")
        for mkr, val in self.raw_fields():
            if unwrap:
                val = unwrap_pat.sub(" ", val)
            if strip:
                val = val.rstrip()
            yield (mkr, val)

    def close(self):
        """Close a previously opened standard format marker file or string."""
        self._file.close()
        try:
            del self.line_num
        except AttributeError:
            pass


def _sanitize_marker(mkr):
    """A marker as the XML element name it is written as: see
    :func:`nltk.xmlsec.safe_element_name`."""
    return safe_element_name(mkr, prefix="tb_")


class ToolboxData(StandardFormat):
    def parse(self, grammar=None, **kwargs):
        if grammar:
            return self._chunk_parse(grammar=grammar, **kwargs)
        else:
            return self._record_parse(**kwargs)

    def _record_parse(self, key=None, **kwargs):
        r"""
        Returns an element tree structure corresponding to a toolbox data file with
        all markers at the same level.

        Thus the following Toolbox database::
            \_sh v3.0  400  Rotokas Dictionary
            \_DateStampHasFourDigitYear

            \lx kaa
            \ps V.A
            \ge gag
            \gp nek i pas

            \lx kaa
            \ps V.B
            \ge strangle
            \gp pasim nek

        after parsing will end up with the same structure (ignoring the extra
        whitespace) as the following XML fragment after being parsed by
        ElementTree::
            <toolbox_data>
                <header>
                    <_sh>v3.0  400  Rotokas Dictionary</_sh>
                    <_DateStampHasFourDigitYear/>
                </header>

                <record>
                    <lx>kaa</lx>
                    <ps>V.A</ps>
                    <ge>gag</ge>
                    <gp>nek i pas</gp>
                </record>

                <record>
                    <lx>kaa</lx>
                    <ps>V.B</ps>
                    <ge>strangle</ge>
                    <gp>pasim nek</gp>
                </record>
            </toolbox_data>

        :param key: Name of key marker at the start of each record. If set to
            None (the default value) the first marker that doesn't begin with
            an underscore is assumed to be the key.
        :type key: str
        :param kwargs: Keyword arguments passed to ``StandardFormat.fields()``
        :type kwargs: dict
        :rtype: ElementTree._ElementInterface
        :return: contents of toolbox data divided into header and records
        """
        builder = TreeBuilder()
        builder.start("toolbox_data", {})
        builder.start("header", {})
        in_records = False
        for mkr, value in self.fields(**kwargs):
            # 1. Structural Logic: Use the ORIGINAL `mkr` and `key`
            if key is None and not in_records and mkr and mkr[0] != "_":
                key = mkr
            if mkr == key:
                if in_records:
                    builder.end("record")
                else:
                    builder.end("header")
                    in_records = True
                builder.start("record", {})

            # 2. Emission Logic: Use `safe_mkr` STRICTLY for XML tags
            safe_mkr = _sanitize_marker(mkr)
            builder.start(safe_mkr, {})
            builder.data(value)
            builder.end(safe_mkr)

        if in_records:
            builder.end("record")
        else:
            builder.end("header")
        builder.end("toolbox_data")
        return builder.close()

    def _tree2etree(self, parent):
        from nltk.tree import Tree

        # a chunk label is written as an element name like a marker is
        root = Element(safe_element_name(parent.label(), prefix="tb_"))
        for child in parent:
            if isinstance(child, Tree):
                root.append(self._tree2etree(child))
            else:
                text, tag = child
                e = SubElement(root, tag)
                e.text = text
        return root

    def _chunk_parse(self, grammar=None, root_label="record", trace=0, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file
        parsed according to the chunk grammar.

        :type grammar: str
        :param grammar: Contains the chunking rules used to parse the
            database.  See ``chunk.RegExp`` for documentation.
        :type root_label: str
        :param root_label: The node value that should be used for the
            top node of the chunk structure.
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            ``1`` will generate normal tracing output; and ``2`` or
            higher will generate verbose tracing output.
        :type kwargs: dict
        :param kwargs: Keyword arguments passed to ``toolbox.StandardFormat.fields()``
        :rtype: ElementTree._ElementInterface
        :raises ValueError: if a record has more than ``MAX_CHUNK_RECORD_FIELDS``
            fields
        """
        from nltk import chunk
        from nltk.tree import Tree

        cp = chunk.RegexpParser(grammar, root_label=root_label, trace=trace)
        db = self.parse(**kwargs)
        records = db.findall("record")
        widest = max((len(record) for record in records), default=0)
        if widest > MAX_CHUNK_RECORD_FIELDS:
            raise ValueError(
                f"Toolbox record has {widest} fields, more than "
                f"MAX_CHUNK_RECORD_FIELDS ({MAX_CHUNK_RECORD_FIELDS}); chunking is "
                "quadratic in a record's width. Raise "
                "nltk.toolbox.MAX_CHUNK_RECORD_FIELDS to allow it."
            )
        tb_etree = Element("toolbox_data")
        header = db.find("header")
        tb_etree.append(header)
        for record in records:
            parsed = cp.parse([(elem.text, elem.tag) for elem in record])
            tb_etree.append(self._tree2etree(parsed))
        return tb_etree


_is_value = redos.compile(r"\S")
#: What the reader takes for one marker: a run of non white space.
_one_marker = redos.compile(r"\S+")
#: A value line the reader would take for a new field: a backslash and a
#: non white space character just after a line break.
_marker_line = redos.compile(r"[\r\n]\\\S")


def _reads_as_one_marker(mkr):
    # Every white space character but U+0020 is unprintable, so a printable
    # marker without a space has none; anything else goes to the regex.
    if mkr.isprintable():
        return bool(mkr) and " " not in mkr
    return redos.fullmatch(_one_marker, mkr) is not None


def _check_writable(mkr, value, blocks=False):
    """Refuse a field that would not read back as itself.

    Standard Format has no escape, so a marker that is empty or holds white
    space, in a settings file a marker starting with ``+`` or ``-``, and a
    value with a line that starts with a marker all read back as other fields.

    :raises ValueError: if the field cannot be written faithfully
    """
    if (
        not isinstance(mkr, str)
        or not _reads_as_one_marker(mkr)
        or (blocks and mkr[0] in "+-")
    ):
        raise ValueError(f"cannot write marker {mkr!r}: it would not read back as one")
    if "\\" in value and redos.search(_marker_line, value):
        raise ValueError(
            f"cannot write the value of marker {mkr!r}: a line in it starts with "
            "a marker, so it would read back as a separate field"
        )


def _sfm_line(mkr, value):
    if redos.search(_is_value, value):
        return f"\\{mkr} {value}\n"
    return f"\\{mkr}{value}\n"


def _encode_sfm(lines, encoding, errors, unicode_fields):
    """Encode the ``(marker, line)`` pairs ``to_sfm_string`` writes, ``None``
    marking a record break, and refuse output the reader would read as other
    fields.

    One incremental encoder writes a BOM once and keeps a shift state across
    fields. An error handler (``ignore``, ``backslashreplace``, the byte a
    ``surrogateescape`` gives) or a ``unicode_fields`` field can change what is
    written, so the bytes are decoded as the reader decodes a file, in one
    call, and when that is not the text written they are read back.

    :raises ValueError: if the output would not read back with the markers
        written
    """
    encoder = codecs.getincrementalencoder(_text_encoding(encoding))(errors)
    chunks = []
    for mkr, line in lines:
        if mkr is not None and unicode_fields is not None and mkr in unicode_fields:
            chunks.append(line.encode("utf8", errors))
        else:
            chunks.append(encoder.encode(line))
    chunks.append(encoder.encode("", final=True))
    data = b"".join(chunks)
    seen = codecs.decode(data, encoding, "replace")
    if seen != "".join(line for _, line in lines):
        reader = StandardFormat()
        reader._file = StringIO(seen)
        read = [mkr for mkr, _ in reader.raw_fields()]
        written = [mkr for mkr, _ in lines if mkr is not None]
        if read != written:
            at = next(
                (i for i, (got, want) in enumerate(zip(read, written)) if got != want),
                min(len(read), len(written)),
            )
            raise ValueError(
                f"cannot write marker {written[at] if at < len(written) else None!r}"
                f" with encoding {encoding!r} and errors {errors!r}: the output "
                f"reads back as marker {read[at] if at < len(read) else None!r}"
            )
    return data


def to_sfm_string(tree, encoding=None, errors="strict", unicode_fields=None):
    """
    Return a string with a standard format representation of the toolbox
    data in tree (tree can be a toolbox database or a single record).

    :param tree: flat representation of toolbox data (whole database or single record)
    :type tree: ElementTree._ElementInterface
    :param encoding: Name of an encoding to use.
    :type encoding: str
    :param errors: Error handling scheme for codec. Same as the ``encode()``
        builtin string method.
    :type errors: str
    :param unicode_fields:
    :type unicode_fields: dict(str) or set(str)
    :rtype: str, or bytes when ``encoding`` is given
    :raises ValueError: if a field would read back as other fields
    """
    if tree.tag == "record":
        root = Element("toolbox_data")
        root.append(tree)
        tree = root

    if tree.tag != "toolbox_data":
        raise ValueError("not a toolbox_data element structure")
    if encoding is None and unicode_fields is not None:
        raise ValueError(
            "if encoding is not specified then neither should unicode_fields"
        )
    lines = []
    for rec in tree:
        # A blank line between records, none before the first field written.
        if lines:
            lines.append((None, "\n"))
        for field in rec:
            mkr = field.tag
            value = field.text or ""
            _check_writable(mkr, value)
            lines.append((mkr, _sfm_line(mkr, value)))
    if encoding is None:
        return "".join(line for _, line in lines)
    return _encode_sfm(lines, encoding, errors, unicode_fields)


class ToolboxSettings(StandardFormat):
    """This class is the base class for settings files."""

    def __init__(self, filename=None, encoding=None):
        """Open ``filename``, if given, decoding it with ``encoding``."""
        super().__init__(filename, encoding)

    def parse(self, encoding=None, errors="strict", **kwargs):
        """
        Return the contents of toolbox settings file with a nested structure.

        :param encoding: encoding used by settings file
        :type encoding: str
        :param errors: Error handling scheme for codec. Same as ``decode()``
            builtin method.
        :type errors: str
        :param kwargs: Keyword arguments passed to ``StandardFormat.fields()``
        :type kwargs: dict
        :rtype: ElementTree._ElementInterface
        """
        builder = TreeBuilder()
        depth = 0
        for mkr, value in self.fields(encoding=encoding, errors=errors, **kwargs):
            block = mkr[0] if mkr else None
            if block in ("+", "-"):
                mkr = mkr[1:]
            else:
                block = None
            safe_mkr = _sanitize_marker(mkr)
            if block == "+":
                depth += 1
                if depth > MAX_TOOLBOX_DEPTH:
                    raise ValueError(
                        f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
                        f"({MAX_TOOLBOX_DEPTH}); the input may be "
                        "adversarially deep. Raise "
                        "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
                    )
                builder.start(safe_mkr, {})
                builder.data(value)
            elif block == "-":
                builder.end(safe_mkr)
                depth -= 1
            else:
                builder.start(safe_mkr, {})
                builder.data(value)
                builder.end(safe_mkr)
        return builder.close()


def to_settings_string(tree, encoding=None, errors="strict", unicode_fields=None):
    # write XML to file
    l = list()
    _to_settings_string(
        tree.getroot(),
        l,
        encoding=encoding,
        errors=errors,
        unicode_fields=unicode_fields,
    )
    return "".join(l)


def _to_settings_string(node, l, _depth=0, max_depth=None, **kwargs):
    # write XML to file
    if max_depth is None:
        max_depth = MAX_TOOLBOX_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
            f"({MAX_TOOLBOX_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
        )
    tag = node.tag
    text = node.text
    _check_writable(tag, text or "", blocks=True)
    if len(node) == 0:
        if text:
            l.append(f"\\{tag} {text}\n")
        else:
            l.append("\\%s\n" % tag)
    else:
        if text:
            l.append(f"\\+{tag} {text}\n")
        else:
            l.append("\\+%s\n" % tag)
        for n in node:
            _to_settings_string(n, l, _depth + 1, max_depth, **kwargs)
        l.append("\\-%s\n" % tag)
    return


def remove_blanks(elem, _depth=0, max_depth=None):
    """
    Remove all elements and subelements with no text and no child elements.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    """
    if max_depth is None:
        max_depth = MAX_TOOLBOX_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
            f"({MAX_TOOLBOX_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
        )
    out = list()
    for child in elem:
        remove_blanks(child, _depth + 1, max_depth)
        if child.text or len(child) > 0:
            out.append(child)
    elem[:] = out


def add_default_fields(elem, default_fields, _depth=0, max_depth=None):
    """
    Add blank elements and subelements specified in default_fields.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param default_fields: fields to add to each type of element and subelement
    :type default_fields: dict(tuple)
    """
    if max_depth is None:
        max_depth = MAX_TOOLBOX_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
            f"({MAX_TOOLBOX_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
        )
    for field in default_fields.get(elem.tag, []):
        if elem.find(field) is None:
            SubElement(elem, field)
    for child in elem:
        add_default_fields(child, default_fields, _depth + 1, max_depth)


def sort_fields(elem, field_orders):
    """
    Sort the elements and subelements in order specified in field_orders.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param field_orders: order of fields for each type of element and subelement
    :type field_orders: dict(tuple)
    """
    order_dicts = dict()
    for field, order in field_orders.items():
        order_dicts[field] = order_key = dict()
        for i, subfield in enumerate(order):
            order_key[subfield] = i
    _sort_fields(elem, order_dicts)


def _sort_fields(elem, orders_dicts, _depth=0, max_depth=None):
    """sort the children of elem"""
    if max_depth is None:
        max_depth = MAX_TOOLBOX_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
            f"({MAX_TOOLBOX_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
        )
    try:
        order = orders_dicts[elem.tag]
    except KeyError:
        pass
    else:
        tmp = sorted(
            ((order.get(child.tag, 1e9), i), child) for i, child in enumerate(elem)
        )
        elem[:] = [child for key, child in tmp]
    for child in elem:
        if len(child):
            _sort_fields(child, orders_dicts, _depth + 1, max_depth)


def _last_descendant(elem):
    """The last element of ``elem``'s subtree in document order.

    Follows last children, so the cost is the length of that path; listing
    the subtree instead made add_blank_lines quadratic in depth and width.
    """
    while len(elem):
        elem = elem[-1]
    return elem


def add_blank_lines(tree, blanks_before, blanks_between, _depth=0, max_depth=None):
    """
    Add blank lines before all elements and subelements specified in blank_before.

    :param elem: toolbox data in an elementtree structure
    :type elem: ElementTree._ElementInterface
    :param blank_before: elements and subelements to add blank lines before
    :type blank_before: dict(tuple)
    """
    if max_depth is None:
        max_depth = MAX_TOOLBOX_DEPTH
    if _depth > max_depth:
        raise ValueError(
            f"Toolbox nesting depth exceeds MAX_TOOLBOX_DEPTH "
            f"({MAX_TOOLBOX_DEPTH}); the input may be "
            "adversarially deep. Raise "
            "nltk.toolbox.MAX_TOOLBOX_DEPTH to allow it."
        )
    try:
        before = blanks_before[tree.tag]
        between = blanks_between[tree.tag]
    except KeyError:
        for elem in tree:
            if len(elem):
                add_blank_lines(
                    elem, blanks_before, blanks_between, _depth + 1, max_depth
                )
    else:
        last_elem = None
        for elem in tree:
            tag = elem.tag
            if last_elem is not None and last_elem.tag != tag:
                if tag in before and last_elem is not None:
                    e = _last_descendant(last_elem)
                    e.text = (e.text or "") + "\n"
            else:
                if tag in between and last_elem is not None:
                    e = _last_descendant(last_elem)
                    e.text = (e.text or "") + "\n"
            if len(elem):
                add_blank_lines(
                    elem, blanks_before, blanks_between, _depth + 1, max_depth
                )
            last_elem = elem


def demo():
    from itertools import islice

    #    zip_path = find('corpora/toolbox.zip')
    #    lexicon = ToolboxData(ZipFilePathPointer(zip_path, 'toolbox/rotokas.dic')).parse()
    file_path = find("corpora/toolbox/rotokas.dic")
    lexicon = ToolboxData(file_path).parse()
    safe_print("first field in fourth record:")
    safe_print(lexicon[3][0].tag)
    safe_print(lexicon[3][0].text)

    safe_print("\nfields in sequential order:")
    for field in islice(lexicon.find("record"), 10):
        safe_print(field.tag, field.text)

    safe_print("\nlx fields:")
    for field in islice(lexicon.findall("record/lx"), 10):
        safe_print(field.text)

    file_path = find("corpora/toolbox/MDF/MDF_AltH.typ")
    settings = ToolboxSettings(file_path, encoding="cp1252")
    #    settings.open(ZipFilePathPointer(zip_path, entry='toolbox/MDF/MDF_AltH.typ'))
    tree = settings.parse(unwrap=False)
    safe_print(tree.find("expset/expMDF/rtfPageSetup/paperSize").text)
    settings_tree = ElementTree(tree)
    safe_print(to_settings_string(settings_tree).encode("utf8"))


if __name__ == "__main__":
    demo()
