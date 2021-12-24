# Natural Language Toolkit: Extended Open Multilingual WordNet Reader
#
# Copyright (C) 2001-2021 NLTK Project
# Author: Freda Shi <freda@ttic.edu>

# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
An NLTK interface for Extended Open Multilingual WordNet

Extended Open Multilingual WordNet automatically maps WordNet synsets
to multiple languages with data extracted from Wikitionary and CLDR.

Currently ignoring all languages marked with "*" in the released corpus.
All synsets, whether manually annotated or automatically extracted, are
treated equally.

For details about WordNet, see:
https://wordnet.princeton.edu/

For details about Open Multilingual WordNet, see:
http://compling.hss.ntu.edu.sg/omw/

For details about Extended Open Multilingual WordNet, see:
http://compling.hss.ntu.edu.sg/omw/summx.html
"""

import os
from collections import defaultdict

from nltk.corpus.reader.wordnet import WordNetCorpusReader


class ExtendedOpenMultilingualWordNetCorpusReader(WordNetCorpusReader):
    def __init__(self, root, omw_reader, exomw_reader):
        super().__init__(root, omw_reader)
        self._exomw_reader = exomw_reader
        self.exomw_provenances = self.exomw_prov()

    def omw_prov(self):
        """Return a provenance dictionary of the languages in OMW"""
        provdict = defaultdict(list)
        provdict["eng"] = list()
        fileids = self._omw_reader.fileids()
        for fileid in fileids:
            prov, langfile = os.path.split(fileid)
            file_name, file_extension = os.path.splitext(langfile)
            if file_extension == ".tab":
                lang = file_name.split("-")[-1]
                provdict[lang].append(prov)
        return provdict

    def exomw_prov(self):
        """Return a provenance dictionary of the languages in Extended OMW"""
        provdict = defaultdict(list)
        provdict["eng"] = ""
        fileids = self._exomw_reader.fileids()
        for fileid in fileids:
            prov, langfile = os.path.split(fileid)
            file_name, file_extension = os.path.splitext(langfile)
            if file_extension == ".tab":
                lang = file_name.split("-")[-1]
                # only use wordnet English data -- should be examined.
                if lang == "eng":
                    continue
                provdict[lang].append(prov)
        return provdict

    def _load_lang_data(self, lang):
        """Load the wordnet data to self._lang_data"""
        if lang in self._lang_data.keys():
            return
        # load open multilingual wordnet
        for prov in self.provenances[lang]:
            with self._omw_reader.open(f"{prov}/wn-data-{lang}.tab") as fp:
                self.custom_lemmas(fp, lang)
        # load extended open multilingual wordnet
        for prov in self.exomw_provenances[lang]:
            with self._exomw_reader.open(f"{prov}/wn-{prov}-{lang}.tab") as fp:
                self.custom_lemmas(fp, lang)
        for index in range(len(self.lg_attrs)):
            for key in self._lang_data[lang][index]:
                data_item = self._lang_data[lang][index][key]
                self._lang_data[lang][index][key] = list(data_item)
        self.disable_custom_lemmas(lang)

    def langs(self):
        omw_langs = set(self.provenances.keys())
        exomw_langs = set(self.exomw_provenances.keys())
        return sorted(omw_langs.union(exomw_langs))

    def custom_lemmas(self, tab_file, lang):
        """
        Adapted from Open Multilingual WordNet Loader.

        :param tab_file: Tab file as a file or file-like object
        :type lang: str
        :param lang: ISO 639-3 code of the language of the tab file
        """
        if len(lang) != 3:
            raise ValueError("lang should be a (3 character) ISO 639-3 code")
        if lang not in self._lang_data:
            self._lang_data[lang] = [
                defaultdict(set),
                defaultdict(set),
                defaultdict(set),
                defaultdict(set),
            ]
        for line in tab_file.readlines():
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            if not line.startswith("#"):
                triple = line.strip().split("\t")
                if len(triple) < 3:
                    continue
                offset_pos, label = triple[:2]
                val = triple[-1]
                if self.map30:
                    if offset_pos in self.map30.keys():
                        offset_pos = self.map30[offset_pos]
                    else:
                        pass
                pair = label.split(":")
                attr = pair[-1]
                if len(pair) == 1 or pair[0] == lang:
                    if attr == "lemma":
                        val = val.strip().replace(" ", "_").lower()
                        self._lang_data[lang][1][val].add(offset_pos)
                    if attr in self.lg_attrs:
                        index = self.lg_attrs.index(attr)
                        self._lang_data[lang][index][offset_pos].add(val)

    def disable_custom_lemmas(self, lang):
        """prevent synsets from being mistakenly added"""
        for n in range(len(self.lg_attrs)):
            self._lang_data[lang][n].default_factory = None
