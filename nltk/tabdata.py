# Natural Language Toolkit: Encode/Decocode Data as Tab-files
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#


def rm_nl(s):
    if s[-1] == "\n":
        return s[:-1]
    return s


class TabEncoder:

    def list2txt(self, s):
        return "\n".join(s)

    def set2txt(self, s):
        return self.list2txt(list(s))

    def tup2tab(self, tup):
        return "\t".join(tup)

    def tups2tab(self, x):
        return "\n".join([self.tup2tab(tup) for tup in x])

    def dict2tab(self, d):
        return self.tups2tab(d.items())

    def ivdict2tab(self, d):
        # From integer-value dictionary
        return self.tups2tab([(a, str(b)) for a, b in d.items()])


class TabDecoder:

    def txt2list(self, f):
        return [rm_nl(x) for x in f]

    def txt2set(self, f):
        return {rm_nl(x) for x in f}

    def tab2tup(self, s):
        return tuple(s.split("\t"))

    def tab2tups(self, f):
        return [self.tab2tup(rm_nl(x)) for x in f]

    def tab2dict(self, f):
        return {a: b for a, b in self.tab2tups(f)}

    def tab2ivdict(self, f):
        # To integer-value dictionary
        return {a: int(b) for a, b in self.tab2tups(f)}


# ---------------------------------------------------------------------------
# Maxent data
# ---------------------------------------------------------------------------


class MaxentEncoder(TabEncoder):

    def tupdict2tab(self, d):
        """Encode a ``(fname, fval, label) -> fid`` mapping as tab rows.

        A str value is written as is. ``None``, a bool and an int are written
        as ``repr-None``, ``repr-True``/``repr-False`` and ``repr-<int>`` so
        the decoder gives them back as the same type; the bool test comes
        first because ``True == 1`` and ``False == 0`` would otherwise alias
        an int 1 or 0 to a bool. A ``wordlen`` value is a bare int, as in the
        shipped tagger and chunker files, which the decoder restores by name.
        """

        def rep(a, b):
            if a == "wordlen":
                return repr(b)
            if b is None or isinstance(b, bool):
                return f"repr-{b}"
            if isinstance(b, int):
                return f"repr-{b}"
            return b

        return self.tups2tab(
            [(a, rep(a, b), c, repr(d)) for ((a, b, c), d) in d.items()]
        )


class MaxentDecoder(TabDecoder):

    def tupkey2dict(self, f):
        """Decode the rows :meth:`MaxentEncoder.tupdict2tab` writes.

        ``repr-<int>`` is restored as an int: the encoder used to write an int
        0 or 1 that way by accident (it aliased them to bools) while this side
        handed the token back as the string ``"repr-1"``, so every int-valued
        feature of a saved model was silently dropped on reload.
        """

        def rep(a, b):
            if a == "wordlen":
                return int(b)
            if b == "repr-None":
                return None
            if b == "repr-True":
                return True
            if b == "repr-False":
                return False
            if b.startswith("repr-"):
                tail = b[5:]
                digits = tail[1:] if tail.startswith("-") else tail
                if digits.isascii() and digits.isdigit():
                    return int(tail)
            return b

        return {(a, rep(a, b), c): int(d) for (a, b, c, d) in self.tab2tups(f)}


# ---------------------------------------------------------------------------
# Punkt data
# ---------------------------------------------------------------------------


class PunktDecoder(TabDecoder):

    def tab2intdict(self, f):
        from collections import defaultdict

        return defaultdict(int, {a: int(b) for a, b in self.tab2tups(f)})
