#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Grammar for the Toolbox MDF Alternate Hierarchy."""

# this dictionary lists all the markers that can occur in a given section
# of a shoebox record. The order is not used in parsing but may be when
# outputting a record. 

# the fields in the first tuple mark the start of nonterminal.
# Each field can occur only once and all those must
# occur before any other field in a nonterminal
# otherwise they are interpreted as marking the start
# of another one of the same nonterminal
# Fields in the second tuple alse can occur in that nonterminal.
# They must occur after those in the first tuple in 
# a given instance of the nonterminal

grammar = {
        'toolbox':   (('_sh',), ('_DateStampHasFourDigitYear', 'entry')),
        'entry':       (('lx',), ('hm', 'id', 'lc', 'ph', 'sh', 'mr', 'variant', 'sense', 'bw', 'etym',
                               'paradigm', 'st', 'subentry', 'dt')),
        'subentry': (('se',), ('hm', 'id', 'lc', 'ph', 'mr', 'variant', 'sense', 'bw', 'etym', 
                                'paradigm', 'st')),
        'variant':   (('va',), ('vn', 've', 'vr')),
        'sense':       (('sn', 'ps', 'pn'), ('gv', 'dv',
                                'chingloss', 'dn', 'chinrev', 'wn',
                                'ge', 'de', 're', 'we',
                                'gr', 'dr', 'rr', 'wr',
                                'lt', 'sc', 'example', 'usage', 'encyc', 'only',
                                'lexfunc', 'sy', 'an', 'crossref', 'mn', 'tb', 'sd', 'is', 'th', 'notes', 'so', 'bb')),
        'chingloss': (('gn',), ('gp',)),
        'chinrev':   (('rn',), ('rp',)),
        'example':   (('rf', 'xv'), ('xn', 'xe', 'xr')),
        'usage':       (('uv', 'un', 'ue'), ('ur',)),
        'encyc':       (('ev', 'en', 'ee'), ('er',)),
        'only':         (('ov', 'on', 'oe'), ('or',)),
        'lexfunc':   (('lf',), ('lexvalue',)),
        'lexvalue': (('lv',), ('ln', 'le', 'lr')),
        'crossref': (('cf',), ('cn', 'ce', 'cr')),
        'notes':       (('nt', 'np', 'ng', 'nd', 'na', 'ns', 'nq'), ()),
        'etym':         (('et',), ('eg', 'es', 'ec')),
        'paradigm': (('pd', 'pdl', 'pdv'), ('pdn', 'pde', 'pdr',
                               'sg', 'pl', 'rd', 
                               '1s', '2s', '3s', '4s', 
                               '1d', '2d', '3d', '4d',
                               '1p', '1i', '1e', '2p', '3p', '4p'))
        }

chunk_grammar = """
      etym: {<et><eg|es|ec>*}
      notes: {<nt|np|ng|nd|na|ns|nq>+}
      crossref: {<cf><cn|ce|cr>*}
      lexvalue: {<lv><ln|le|lr>*}
      lexfunc: {<lf><lexvalue>*}
      only: {<ov|on|oe>*<or>?}
      encyc: {<ev|en|ee>*<er>?}
      usage: {<uv|un|ue>*<ur>?}
      example: {<rf|xv><xn|xe>*}
      sense:   {<sn><ps|pn>*<gv|dv|gn|gp|dn|rn|wn|ge|de|re|we|lt|sc>*<example>*<usage>?<encyc>?<only>?<lexfunc>*<crossref>*<mn|tb|sd|is|th|>*<notes>*<so>*}
      variant:  { <va><vn|ve|vr>*}
      subentry:   {<se><hm><id>?<lc>?<ph>?<mr>?<variant>*<sense>+<bw>?<etym>?<paradigm>?<st>}
      entry:   {<lx><hm>?<id>?<lc>?<ph>?<sh>?<mr>?<variant>*<sense>+<bw>?<etym>?<paradigm>?<st>*<subentr>*<dt>}
"""

field_order = {
        'toolbox':   ('_sh', '_DateStampHasFourDigitYear', 'entry'),
        'entry':       ('lx', 'hm', 'sh', 'id', 'lc', 'ph', 'mr', 'variant', 'sense', 'bw', 'etym',
                               'paradigm', 'st', 'subentry', 'dt'),
        'subentry': ('se', 'hm', 'id', 'lc', 'ph', 'mr', 'variant', 'sense', 'bw', 'etym', 
                                'paradigm', 'st'),
        'variant':   ('va', 'vn', 've', 'vr'),
        'sense':       ('sn', 'ps', 'pn', 'gv', 'dv',
                                'chingloss', 'dn', 'chinrev', 'wn',
                                'ge', 'de', 're', 'we',
                                'gr', 'dr', 'rr', 'wr',
                                'lt', 'sc', 'example', 'usage', 'encyc', 'only',
                                'lexfunc', 'sy', 'an', 'crossref', 'mn', 'tb', 'sd', 'is', 'th', 'notes', 'so'),
        'chingloss': ('gn', 'gp'),
        'chinrev':   ('rn', 'rp'),
        'example':   ('rf', 'xv', 'xn', 'xe', 'xr'),
        'usage':       ('uv', 'un', 'ue', 'ur'),
        'encyc':       ('ev', 'en', 'ee', 'er'),
        'only':         ('ov', 'on', 'oe', 'or'),
        'lexfunc':   ('lf', 'lexvalue'),
        'lexvalue': ('lv', 'ln', 'le', 'lr'),
        'crossref': ('cf', 'cn', 'ce', 'cr'),
        'notes':       ('nt', 'np', 'ng', 'nd', 'na', 'ns', 'nq' ),
        'etym':         ('et', 'eg', 'es', 'ec'),
        'paradigm': ('pd', 'pdl', 'pdv', 'pdn', 'pde', 'pdr',
                               'sg', 'pl', 'rd', 
                               '1s', '2s', '3s', '4s', 
                               '1d', '2d', '3d', '4d',
                               '1p', '1i', '1e', '2p', '3p', '4p')
        }

default_fields = {
        'toolbox':   ('_sh', '_DateStampHasFourDigitYear'),
        'entry':       ('lx', 'hm', 'variant', 'sense', 'bw', 'st'),
        'subentry': ('se', 'hm', 'variant', 'sense', 'bw', 'st'),
        'variant':   ('va', ),
        'sense':       ('sn', 'ps', 'dv',
                                'chingloss', 'dn', 
                                'ge', 'de', 
                                'example', 'lexfunc'),
        'chingloss': ('gn', 'gp'),
        'chinrev':   ('rn', 'rp'),
        'example':   ('xv', 'xn', 'xe'),
        'usage':       ('uv', 'un', 'ue'),
        'encyc':       ('ev', 'en', 'ee'),
        'only':         ('ov', 'on', 'oe'),
        'lexfunc':   ('lf', 'lexvalue'),
        'lexvalue': ('lv', ),
        'crossref': ('cf', ),
        'notes':       ('nt', 'nq' ),
        'etym':         ('et', 'eg', ),
        }

blanks_before = {
        'toolbox':   ('entry',),
        'entry':       ('variant', 'sense', 'bw', 'paradigm', 'subentry', 'bw'),
        'subentry': ('variant', 'sense', 'bw', 'paradigm', 'bw'),
        'sense':       ('example', 'usage', 'encyc', 'only', 'lexfunc', 'crossref', 'is', 'notes', 'so'),
        }

blanks_between = {
        'toolbox':   ('entry',),
        'entry':       ('sense', 'bw', 'paradigm', 'subentry', 'bw'),
        'subentry': ('sense', 'bw', 'paradigm', 'bw'),
        'sense':       ('example', 'usage', 'encyc', 'only', 'lexfunc', 'crossref', 'so'),
        }
