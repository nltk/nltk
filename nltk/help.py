# Natural Language Toolkit (NLTK) Help
#
# Copyright (C) 2001-2026 NLTK Project
# Authors: Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Provide structured access to documentation.
"""

from textwrap import wrap

from nltk import redos
from nltk.data import find, open_datafile
from nltk.jsontags import safe_json_load


def brown_tagset(tagpattern=None):
    _format_tagset("brown_tagset", tagpattern)


def claws5_tagset(tagpattern=None):
    _format_tagset("claws5_tagset", tagpattern)


def upenn_tagset(tagpattern=None):
    _format_tagset("upenn_tagset", tagpattern)


#####################################################################
# UTILITIES
#####################################################################


def _print_entries(tags, tagdict):
    for tag in tags:
        entry = tagdict[tag]
        defn = [tag + ": " + entry[0]]
        examples = wrap(
            entry[1], width=75, initial_indent="    ", subsequent_indent="    "
        )
        print("\n".join(defn + examples))


def _format_tagset(tagset, tagpattern=None):
    # Load tagset from json file.
    with open_datafile(find("help/tagsets_json/PY3_json/"), f"{tagset}.json") as fin:
        # Bounded parse (size + nesting depth) so a tampered tagset file cannot
        # crash the interpreter through the recursive C decoder.
        tagdict = safe_json_load(fin, context="nltk.help._format_tagset")

    if not tagpattern:
        _print_entries(sorted(tagdict), tagdict)
    elif tagpattern in tagdict:
        _print_entries([tagpattern], tagdict)
    else:
        tagpattern = redos.compile(tagpattern)
        tags = [tag for tag in sorted(tagdict) if tagpattern.match(tag)]
        if tags:
            _print_entries(tags, tagdict)
        else:
            print("No matching tags found.")


if __name__ == "__main__":
    brown_tagset(r"NN.*")
    upenn_tagset(r".*\$")
    claws5_tagset("UNDEFINED")
    brown_tagset(r"NN")
