#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Settings Parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""module for reading Toolbox data files
"""

from nltk_lite.etree import ElementTree
from nltk_lite.corpora.toolbox import ToolboxFile
import os.path
from nltk_lite.corpora import get_basedir
import re

def record_parse_data(file_name, key, **kwargs):
    """
    Return an element tree resulting from parsing the toolbox datafile.
    
    A convenience function that creates a Data object, opens and parses 
    the toolbox data file. The data file is assumed to be in the toolbox 
    subdirectory of the directory where NLTK looks for corpora, 
    see L{corpora.get_basedir()}.
    @param file_name: Name of file in toolbox corpus directory
    @type file_name: string
    @param key: marker at the start of each record
    @type key: string
    @param kwargs: Keyword arguments passed to L{Data.flat_parse()}
    @type kwargs: keyword arguments dictionary
    @rtype:   ElementTree._ElementInterface
    @return:  contents of toolbox data divided into header and records
    """ 
    db = Data()
    db.open(os.path.join(get_basedir(), 'toolbox', file_name))
    return db.record_parse(key, **kwargs)

_is_value = re.compile(r"\S")

def to_sfm_string(tree):
    """Return a string with a standard format representation of the toolbox
    data in tree.
    
    @type tree: ElementTree._ElementInterface
    @param tree: flat representation of toolbox data
    @rtype:   string
    @return:  string using standard format markup
    """
    # todo encoding, unicode fields, errors?
    l = list()
    for rec in tree:
        l.append('\n')
        for field in rec:
            value = field.text
            if re.search(_is_value, value):
                l.append("\\%s %s\n" % (field.tag, value))
            else:
                l.append("\\%s%s\n" % (field.tag, value))
    return ''.join(l[1:])


class Data(ToolboxFile):
    def __init__(self):
        super(Data, self).__init__()

    def record_parse(self, key, **kwargs):
        """
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

        @param key: Name of key marker at the start of each record
        @type key: string
        @param kwargs: Keyword arguments passed to L{ToolboxFile.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   ElementTree._ElementInterface
        @return:  contents of toolbox data divided into header and records
        """
        builder = ElementTree.TreeBuilder()
        builder.start('toolbox_data', {})
        builder.start('header', {})
        in_records = False
        for mkr, value in self.fields(**kwargs):
            if mkr == key:
                if in_records:
                    builder.end('record')
                else:
                    builder.end('header')
                    in_records = True
                builder.start('record', {})
            builder.start(mkr, {})
            builder.data(value)
            builder.end(mkr)
        if in_records:
            builder.end('record')
        else:
            builder.end('header')
        builder.end('toolbox_data')
        return builder.close()

    def _make_parse_table(self, grammar):
        """
        Return parsing state information used by tree_parser.
        """

        first = dict()
        gram = dict()
        for sym, value in grammar.items():
            first[sym] = value[0]
            gram[sym] = value[0] + value[1]
        parse_table = dict()
        for state in gram.keys():
            parse_table[state] = dict()
            for to_sym in gram[state]:        
                if to_sym in grammar:
                    # is a nonterminal
                    # assume all firsts are terminals
                    for i in first[to_sym]:        
                        parse_table[state][i] = to_sym
                else:
                    parse_table[state][to_sym] = to_sym
        return (parse_table, first)

    def grammar_parse(self, startsym, grammar, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file
        parsed according to the grammar.
        
        @type startsym: string
        @param startsym: Start symbol used for the grammar
        @type grammar: dictionary of tuple of tuples
        @param grammar: Contains the set of rewrite rules used to parse the 
        database.  See the description below.
        @param kwargs: Keyword arguments passed to L{ToolboxFile.fields()}
        @type kwargs: keyword arguments dictionary
        @rtype:   ElementTree._ElementInterface
        @return:  Contents of toolbox data parsed according to rules in grammar
        
        The rewrite rules in the grammar look similar to those usually used in 
        computer languages. The difference is that the ordering constraints 
        that are usually present are relaxed in this parser. The reason is that 
        toolbox databases seldom have consistent ordering of fields. Hence the 
        right side of each rule consists of a tuple with two parts. The 
        fields in the first part mark the start of nonterminal.
        Each of them can occur only once and all those must
        occur before any of the fields in the second part of that nonterminal.
        Otherwise they are interpreted as marking the start
        of another one of the same nonterminal. If there is more than one
        in the first part of the tuple they do not need to all appear in a parse.
        The fields in the second part of the tuple can occur in any order.

        Sample grammar::
            C{grammar = {
                'toolbox':      (('_sh',), ('_DateStampHasFourDigitYear', 'entry')),
                'entry':          (('lx',), ('hm', 'sense', 'dt')),
                'sense':         (('sn', 'ps'), ('pn', 'gv', 'dv',
                                           'gn', 'gp', 'dn', 'rn',
                                           'ge', 'de', 're',
                                           'example', 'lexfunc')),
                'example':     (('rf', 'xv',), ('xn', 'xe')),
                'lexfunc':       (('lf',), ('lexvalue',)),
                'lexvalue':      (('lv',), ('ln', 'le')),
            }
        """
        parse_table, first = self._make_parse_table(grammar)
        builder = ElementTree.TreeBuilder()
        pstack = list()
        state = startsym
        first_elems = list()
        pstack.append((state, first_elems))
        builder.start(state, {})
        field_iter = self.fields(**kwargs)
        loop = True
        try:
            mkr, value = field_iter.next()
        except StopIteration:
            loop = False
        while loop:
            (state, first_elems) = pstack[-1]
            if mkr in parse_table[state]:
                next_state = parse_table[state][mkr]
                if next_state == mkr:
                    if mkr in first[state]:
                        # may be start of a new nonterminal
                        if mkr not in first_elems:
                            # not a new nonterminal
                            first_elems.append(mkr)
                            add = True
                        else:
                            # a new nonterminal, second or subsequent instance
                            add = False
                            if len(pstack) > 1:
                                builder.end(state)
                                pstack.pop()
                            else:
                                raise ValueError, \
                                      'Line %d: syntax error, unexpected marker %s.' % (self.line_num, mkr)
                    else:
                        # start of terminal marker
                        add = True
                    if add:
                        if value:
                            builder.start(mkr, dict())
                            builder.data(value)
                            builder.end(mkr)
                        try:
                            mkr, value = field_iter.next()
                        except StopIteration:
                            loop = False
                else:
                    # a non terminal, first instance
                    first_elems = list()
                    builder.start(next_state, dict())
                    pstack.append((next_state, first_elems))
            else:
                if len(pstack) > 1:
                    builder.end(state)
                    pstack.pop()
                else:
                    raise ValueError, \
                          'Line %d: syntax error, unexpected marker %s.' % (self.line_num, mkr)
        for state, first_elems in reversed(pstack):
            builder.end(state)
        return builder.close()


import sys

fn = 'demos/iu_mien_samp.db'

def demo_flat():
    
    data = Data()
    data.open(fn)
    tree = ElementTree.ElementTree(data.flat_parse('lx', encoding='utf8'))
    tree.write(sys.stdout)
    

if __name__ == '__main__':
    demo_flat()
