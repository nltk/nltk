# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import unittest

from nltk.corpus import (sinica_treebank, conll2007, indian, cess_cat, cess_esp,
                         floresta)
from nltk.tree import Tree

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

