# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest
from nltk.corpus import (sinica_treebank, conll2007, indian, cess_cat, cess_esp,
                         floresta, ptb, udhr)
from nltk.tree import Tree
from nltk.test.unit.utils import skipIf


class TestUdhr(unittest.TestCase):

    def test_words(self):
        for name in udhr.fileids():
            try:
                words = list(udhr.words(name))
            except AssertionError:
                print(name)
                raise
            self.assertTrue(words)

    def test_raw_unicode(self):
        for name in udhr.fileids():
            txt = udhr.raw(name)
            assert not isinstance(txt, bytes), name


class TestIndian(unittest.TestCase):

    def test_words(self):
        words = indian.words()[:3]
        self.assertEqual(words, ['মহিষের', 'সন্তান', ':'])

    def test_tagged_words(self):
        tagged_words = indian.tagged_words()[:3]
        self.assertEqual(tagged_words, [('মহিষের', 'NN'), ('সন্তান', 'NN'), (':', 'SYM')])


class TestCess(unittest.TestCase):
    def test_catalan(self):
        words = cess_cat.words()[:15]
        txt = "El Tribunal_Suprem -Fpa- TS -Fpt- ha confirmat la condemna a quatre anys d' inhabilitació especial"
        self.assertEqual(words, txt.split())

    def test_esp(self):
        words = cess_esp.words()[:15]
        txt = "El grupo estatal Electricité_de_France -Fpa- EDF -Fpt- anunció hoy , jueves , la compra del"
        self.assertEqual(words, txt.split())


class TestFloresta(unittest.TestCase):
    def test_words(self):
        words = floresta.words()[:10]
        txt = "Um revivalismo refrescante O 7_e_Meio é um ex-libris de a"
        self.assertEqual(words, txt.split())

class TestSinicaTreebank(unittest.TestCase):

    def test_sents(self):
        first_3_sents = sinica_treebank.sents()[:3]
        self.assertEqual(
            first_3_sents,
            [['一'], ['友情'], ['嘉珍', '和', '我', '住在', '同一條', '巷子']]
        )

    def test_parsed_sents(self):
        parsed_sents = sinica_treebank.parsed_sents()[25]
        self.assertEqual(parsed_sents,
            Tree('S', [
                Tree('NP', [
                    Tree('Nba', ['嘉珍'])
                ]),
                Tree('V‧地', [
                    Tree('VA11', ['不停']),
                    Tree('DE', ['的'])
                ]),
                Tree('VA4', ['哭泣'])
            ]))


class TestCoNLL2007(unittest.TestCase):
    # Reading the CoNLL 2007 Dependency Treebanks

    def test_sents(self):
        sents = conll2007.sents('esp.train')[0]
        self.assertEqual(
            sents[:6],
            ['El', 'aumento', 'del', 'índice', 'de', 'desempleo']
        )

    def test_parsed_sents(self):

        parsed_sents = conll2007.parsed_sents('esp.train')[0]

        self.assertEqual(parsed_sents.tree(),
            Tree('fortaleció', [
                Tree('aumento', [
                    'El',
                    Tree('del', [
                        Tree('índice', [
                            Tree('de', [
                                Tree('desempleo', ['estadounidense'])
                            ])
                        ])
                    ])
                ]),
                'hoy',
                'considerablemente',
                Tree('al', [
                    Tree('euro', [
                        Tree('cotizaba', [
                            ',',
                            'que',
                            Tree('a', [
                                Tree('15.35', ['las', 'GMT'])
                            ]),
                            'se',
                            Tree('en', [
                                Tree('mercado', [
                                    'el',
                                    Tree('de', ['divisas']),
                                    Tree('de', ['Fráncfort'])
                                ])
                            ]),
                            Tree('a', ['0,9452_dólares']),
                            Tree('frente_a', [
                                ',',
                                Tree('0,9349_dólares', [
                                    'los',
                                    Tree('de', [
                                        Tree('mañana', ['esta'])
                                    ])
                                ])
                            ])
                        ])
                    ])
                ]),
                '.'
            ])
        )


@skipIf(not ptb.fileids(), "A full installation of the Penn Treebank is not available")
class TestPTB(unittest.TestCase):
    def test_fileids(self):
        self.assertEqual(
            ptb.fileids()[:4],
            ['BROWN/CF/CF01.MRG', 'BROWN/CF/CF02.MRG', 'BROWN/CF/CF03.MRG', 'BROWN/CF/CF04.MRG']
        )

    def test_words(self):
        self.assertEqual(
            ptb.words('WSJ/00/WSJ_0003.MRG')[:7],
            ['A', 'form', 'of', 'asbestos', 'once', 'used', '*']
        )

    def test_tagged_words(self):
        self.assertEqual(
            ptb.tagged_words('WSJ/00/WSJ_0003.MRG')[:3],
            [('A', 'DT'), ('form', 'NN'), ('of', 'IN')]
        )

    def test_categories(self):
        self.assertEqual(
            ptb.categories(),
            ['adventure', 'belles_lettres', 'fiction', 'humor', 'lore', 'mystery', 'news', 'romance', 'science_fiction']
        )

    def test_news_fileids(self):
        self.assertEqual(
            ptb.fileids('news')[:3],
            ['WSJ/00/WSJ_0001.MRG', 'WSJ/00/WSJ_0002.MRG', 'WSJ/00/WSJ_0003.MRG']
        )

    def test_category_words(self):
        self.assertEqual(
            ptb.words(categories=['humor','fiction'])[:6],
            ['Thirty-three', 'Scotty', 'did', 'not', 'go', 'back']
        )

# unload corpora
from nltk.corpus import teardown_module
