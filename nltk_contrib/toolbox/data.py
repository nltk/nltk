#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""module for reading Toolbox data files
"""

from nltk.etree.ElementTree import Element, SubElement, TreeBuilder
from nltk import toolbox
import re
from datetime import date

class ToolboxData(toolbox.ToolboxData):
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

    def grammar_parse(self, startsym, grammar, no_blanks=True, **kwargs):
        """
        Returns an element tree structure corresponding to a toolbox data file
        parsed according to the grammar.
        
        @type startsym: string
        @param startsym: Start symbol used for the grammar
        @type grammar: dictionary of tuple of tuples
        @param grammar: Contains the set of rewrite rules used to parse the 
        database.  See the description below.
        @type no_blanks: boolean
        @param no_blanks: blank fields that are not important to the structure are deleted
        @type kwargs: keyword arguments dictionary
        @param kwargs: Keyword arguments passed to L{toolbox.StandardFormat.fields()}
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
        builder = TreeBuilder()
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
                        if not no_blanks or value:
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

def indent(elem, level=0):
    """
    Recursive function to indent an ElementTree._ElementInterface
    used for pretty printing. Code from 
    U{http://www.effbot.org/zone/element-lib.htm}. To use run indent
    on elem and then output in the normal way. 
    
    @param elem: element to be indented. will be modified. 
    @type elem: ElementTree._ElementInterface
    @param level: level of indentation for this element
    @type level: nonnegative integer
    @rtype:   ElementTree._ElementInterface
    @return:  Contents of elem indented to reflect its structure
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def to_sfm_string(tree, encoding=None, errors='strict', unicode_fields=None):
    """Return a string with a standard format representation of the toolbox
    data in tree (tree can be a toolbox database or a single record). Should work for trees
    parsed by grammar_parse too.
    
    @param tree: flat representation of toolbox data (whole database or single record)
    @type tree: ElementTree._ElementInterface
    @param encoding: Name of an encoding to use.
    @type encoding: string
    @param errors: Error handling scheme for codec. Same as the C{encode} 
        inbuilt string method.
    @type errors: string
    @param unicode_fields:
    @type unicode_fields: string
    @rtype:   string
    @return:  string using standard format markup
    """
    # write SFM to file
    # unicode_fields parameter does nothing as yet
    l = list()
    _to_sfm_string(tree, l, encoding=encoding, errors=errors, unicode_fields=unicode_fields)
    s = ''.join(l)
    if encoding is not None:
        s = s.encode(encoding, errors)
    return s
    
_is_value = re.compile(r"\S")

def _to_sfm_string(node, l, **kwargs):
    # write SFM to file
    if len(node) == 0:
        tag = node.tag
        text = node.text
        if text is None:
            l.append('\\%s\n' % tag)
        elif re.search(_is_value, text):
            l.append('\\%s %s\n' % (tag, text))
        else:
            l.append('\\%s%s\n' % (tag, text))
    else:
        #l.append('\n')
        for n in node:
            _to_sfm_string(n, l, **kwargs)
    return

_months = None
_month_abbr = (
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

def _init_months():
    months = dict()
    for i, m in enumerate(_month_abbr):
        months[m] = i + 1
    return months

def to_date(s, four_digit_year=True):
    """return a date object corresponding to the Toolbox date in s.
    
    @param s: Toolbox date
    @type s: string
    @param four_digit_year: Do Toolbox dates use four digits for the year? 
        Defaults to True.
    @type four_digit_year: boolean
    @return: date
    @rtype: datetime.date
    """
    global _months
    if _months is None:
        _months = _init_months()
    fields = s.split('/')
    if len(fields) != 3:
        raise ValueError, 'Invalid Toolbox date "%s"' % s
    day = int(fields[0])
    try:
        month = _months[fields[1]]
    except KeyError:
        raise ValueError, 'Invalid Toolbox date "%s"' % s
    year = int(fields[2])
    return date(year, month, day)

def from_date(d, four_digit_year=True):
    """return a Toolbox date string corresponding to the date in d.
    
    @param d: date
    @type d: datetime.date
    @param four_digit_year: Do Toolbox dates use four digits for the year? 
        Defaults to True.
    @type four_digit_year: boolean
    @return: Toolbox date
    @rtype: string
    """
    return '%04d/%s/%02d' % (date.day, _month_abbr[date.month-1], date.year)

def demo_flat():
    from nltk.etree.ElementTree import ElementTree    
    import sys

    tree = ElementTree(toolbox.xml('iu_mien_samp.db', key='lx', encoding='utf8'))
    tree.write(sys.stdout)
    

if __name__ == '__main__':
    demo_flat()
