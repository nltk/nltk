#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""module for reading Toolbox data files
"""

from nltk_lite.etree import ElementTree
from nltk_lite.corpora import toolbox

class ToolboxData(toolbox.ToolboxData):
    def __init__(self):
        super(toolbox.ToolboxData, self).__init__()

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
        @param kwargs: Keyword arguments passed to L{toolbox.StandardFormat.fields()}
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
        
            grammar = {
                'toolbox':  (('_sh',),      ('_DateStampHasFourDigitYear', 'entry')),
                'entry':    (('lx',),       ('hm', 'sense', 'dt')),
                'sense':    (('sn', 'ps'),  ('pn', 'gv', 'dv',
                                             'gn', 'gp', 'dn', 'rn',
                                             'ge', 'de', 're',
                                             'example', 'lexfunc')),
                'example':  (('rf', 'xv',), ('xn', 'xe')),
                'lexfunc':  (('lf',),       ('lexvalue',)),
                'lexvalue': (('lv',),       ('ln', 'le')),
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

def demo_flat():
    
    tree = ElementTree.ElementTree(toolbox.parse_corpus('iu_mien_samp.db', key='lx', encoding='utf8'))
    tree.write(sys.stdout)
    

if __name__ == '__main__':
    demo_flat()
