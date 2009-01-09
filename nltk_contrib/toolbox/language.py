#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Settings Parser
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module provides functionality for reading language settings files for 
Toolbox. 
"""

from nltk.etree.ElementTree import TreeBuilder
from nltk.toolbox import ToolboxSettings
import re

class Letter(object):
    __slots__ = ('upper', 'lower')
    
    def __init__(self):
        self.upper = self.lower = None


class Language(object):
    """Class for Toolbox Language settings.
    """
    def __init__(self, fname, encoding=None):
        """Initialise from the settings file"""
        set = ToolboxSettings()
        set.open(fname)
        settings = set.parse(unwrap=False, encoding=encoding)

        self.init_case(settings.findtext('case'))
        self.sort_order = {}
        for sort_order in settings.findall('srtset/srt'):
            so = SortOrder(sort_order)
            self.sort_order[so.name] = so
        self.default_order = self.sort_order[settings.findtext('srtset/srtDefault')]

    def init_case(self, case_pairs):
        self.case = case = {}
        for c in case_pairs.splitlines():
            val = c.split()
            if len(val) != 2:
                raise ValueError, '"%s" is not a valid case association' % c
            u, l = val
            let_u = case[u] = Letter()
            let_l = case[l] = Letter()
            let_u.upper = let_l.upper = u
            let_u.lower = let_l.lower = l

    def lower(self, let):
        """return the lower case form of the letter.
        
        @rtype: string
        """
        return self.case[let].lower

    def upper(self, let):
        """return the upper case form of the letter.
        
        @rtype: string
        """
        return self.case[let].upper


class Graph(object):
    """"""
    __slots__ = ('order', 'type')
    
    def __init__(self):
        self.order = self.type = None


class SortOrder(object):
    """Class for Shoebox sort orders
    
    """
    
    def __init__(self, srt_order):
        self.name = srt_order.text
        self.desc = srt_order.findtext('desc')
        # if they don't exist make them a empty list so we don't need to test again
        try:    
            primary = srt_order.findtext('primary').splitlines()
        except AttributeError:
            primary = []
        try:
            sec_pre = srt_order.findtext('SecPreceding').split()
        except AttributeError:
            sec_pre = []
        try:
            sec_fol = srt_order.findtext('SecFollowing').split()
        except AttributeError:
            sec_fol = []
        try:
            ignore = srt_order.findtext('ignore').split()
        except AttributeError:
            ignore = []
        self.sec_after = srt_order.find('SecAfterBase') is not None

        primaries = [p.split() for p in primary]

        self.graphs = graphs = {}
        unmarked = len(sec_pre) + 1
        primaries[0:0] = [' '] #, '\t', '\n']
        i = 1
        for p in primaries:
            j = 1
            for m in p:
                if m in graphs:
                    raise ValueError, 'primary "%s" already in sort order' % m
                graphs[m] = g = Graph()
                g.type = 'p'
                g.order = (i, j, unmarked)
                j += 1
            i += 1
        prims = graphs.keys()
        prims.remove(' ')
        self.letter_pat = self.make_pattern(prims)

        i = 1
        for s in sec_pre:
            if s in graphs:
                raise ValueError, 'secondary preceding "%s" already in sort order' % s
            graphs[s] = g = Graph()
            g.type = 's'
            g.order = i
            i += 1

        # increment for unmarked case
        i += 1
        for s in sec_fol:
            if s in graphs:
                raise ValueError, 'secondary following "%s" already in sort order' % s
            graphs[s] = g = Graph()
            g.type = 's'
            g.order = i
            i += 1

        self.graph_pat = self.make_pattern(graphs.keys())
##~         graph_list = graphs.keys()
##~         
##~         # sort the longest first
##~         tmpl = [(len(x), x) for x in graph_list]
##~         tmpl.sort()
##~         tmpl.reverse()
##~         graph_list = [x[1] for x in tmpl]
##~         self.graph_pat = re.compile('|'.join([re.escape(g) for g in graph_list]))

    def make_pattern(self, slist):
        """Return a regular expression pattern to match the strings in slist"""
        # sort the longest first
        tmpl = [(len(x), x) for x in slist]
        tmpl.sort()
        tmpl.reverse()
        sorted_list = [x[1] for x in tmpl]
        escape = re.escape
        pat = re.compile('|'.join([re.escape(g) for g in sorted_list]))
        return pat

    def first_primary(self, s):
        """return the first primary in the string s"""
        match = self.letter_pat.search(s)
        if match is not None:
            return match.group()
        else:
            raise ValueError, 'no primary found in "%s"' % s

    def transform(self, s):
        graphs = self.graphs
        prim = []
        sec = []
        tert = []
        sec_order = None
        for g in self.graph_pat.findall(s):
            graph = graphs[g]
            order = graph.order
            type = graph.type
            if type == 'p':
                prim.append(order[0])
                tert.append(order[1])
                if sec_order is None:
                    sec.append(order[2])
                else:
                    sec.append(sec_order)
                    sec_order = None
            elif type == 's':
                # this ignores the situation of multiple consecutative secondaries
                if self.sec_after:
                    sec[-1] = order
                else:
                    # secondary is before the primary so save it for later
                    sec_order = order
        return (tuple(prim), tuple(sec), tuple(tert))
