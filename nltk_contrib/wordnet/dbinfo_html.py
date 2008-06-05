# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
import copy

from nltk import defaultdict
from itertools import groupby
from urllib import quote_plus

from nltk.wordnet.synset import *

import browseutil as bu

ALL_POS = ['noun', 'verb', 'adj', 'adv']
COL_HEADS = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Total']
DISPLAY_NAMES = [('forms','Word forms'), ('simple','--- simple words'),
    ('collo','--- collocations'), ('syns','Synsets'),
    ('w_s_pairs','Word-Sense Pairs'),
    ('monos','Monosemous Words and Senses'),
    ('poly_words','Polysemous Words'),
    ('poly_senses','Polysemous Senses'),
    ('apimw','Average Polysemy Including Monosemous Words'),
    ('apemw','Average Polysemy Excluding Monosemous Words'),
    ('rels','Relations')]
WORDNET_PATH = "nltk:corpora/wordnet/"


#
# TODO: Some items in this file are tagged with TODO and XXX, to indicate work
# that should be done to improve this code,  Other general issues exist:
#
# TODO Line 34 and 175: Output SHOULD be optional, and MAY be off by default.
#      This may make it easier to use dbinfo_html in a scripting context.
#
# TODO Docstrings should be changed so that they document expected types and
#      values of parameters and return values.
#



#
# Utility procedures,
#

def get_data(type, pos):
    """
    Read an index data file for the given part of speach and return a
    list of lines from it.
    """
    data = nltk.data.load("%s%s.%s" % (WORDNET_PATH, type, pos), format='raw')
    return [ line for line in data.split('\n') if 
             not line.startswith('  ') and line != "" ] 


def make_list(data, num):
    """
    Make a list of 'data' items 'num' elements long
    """
    # Copy is required here to avoid aliasing the data, so that a
    # change to one item in the resulting lists changes all the items.
    return [copy.copy(data) for x in range(num)]


def concat_map(func, list):
    """
    Map the function over the list and then concatente the items
    in the list using the plus operator
    """
    # Note that this uses a generator expression, it will only
    # traverse the items in the list once
    return reduce(lambda a, b: a+b, (func(i) for i in list))


def first(x):
    "Return the first element from the given sequence"
    return x[0]


def group_rel_count_keys_by_first(rel_counts):
    return groupby(sorted(rel_counts.keys()),key=first)


def display_name_from_rk(rk):
    dn = bu._dbname_to_dispname(rk[0]).split('/')
    if dn[0] == '???':
        dn = rk[0] + '(???)'
    else:
        dn = dn[0]
    return dn


#
# dbinfo_html.py is split into two main procedures.
#
# 1. get_stats_from_database() --- Retrive data and build stats.
#
# 2. htmlize_stats() --- Format the statistics into a web page.
#
# get_stats_from_database() returns a 'Stats' object, which htmlize_stats()
# interprets.

class Stats:
    """
    Statistics gathered from the NLTK Wordnet database.
    """
    
    def __init__(self, counts, rel_counts, rel_words):
        self.counts = counts
        self.rel_counts = rel_counts
        self.rel_words = rel_words


def get_stats_from_database():
    '''
    Gather statistics from the database.  This returns a Stats object.
    '''
    print 'Database information is being gathered!'
    print
    print 'Producing this summary may, depending on your computer,'
    print 'take a couple of minutes. Please be patient!'
    counts = make_list(make_list(0, len(COL_HEADS)), len(DISPLAY_NAMES))
    rel_counts = defaultdict(int)
    rel_words = {}
    unique_beginners = defaultdict(list)

    for n_pos,pos in enumerate(ALL_POS): #['adv']): #all_pos):
        print '\n\nStarting the summary for POS: %s' % COL_HEADS[n_pos]
        # TODO: this dictionary could probably be replaced by a number of
        # variables.
        d = defaultdict(int)

        # Word counts.
        for ind in get_data("index", pos):
            ind_parts = ind.split()
            syn_count = int(ind_parts[2])
            d['w_s_pairs'] += syn_count
            if syn_count == 1:
                d['monos'] += 1
            else:
                d['poly_words'] += 1
                d['poly_senses'] += syn_count
            w = ind_parts[0]
            d['forms'] += 1
            if w.find('_') != -1:
                d['simple'] += 1
            else:
                d['collo'] += 1
        d['apimw'] = 1.0 * (d['monos'] + d['poly_senses']) / \
                           (d['monos'] + d['poly_words'])
        d['apemw'] = 1.0 * d['poly_senses'] / d['poly_words']

        # Synsets and relations
        for syns in get_data("data", pos):
            d['syns'] += 1
            synset = getSynset(pos,int(syns[:8]))
            syn_rel = bu.relations_2(synset)
            if (HYPERNYM not in syn_rel) and \
                    ('hypernym (instance)' not in syn_rel):
                unique_beginners[n_pos].append(synset)
            d['rels'] += len(syn_rel)
            for sr in syn_rel:
                rel_counts[(sr,n_pos)] += 1
                rel_words[(sr,n_pos)] = synset.words[0]

        # Prepare counts for displaying
        nd = {}
        for n,(x,y) in enumerate(DISPLAY_NAMES):
            nd[x] = n
            if x in d:
                counts[n][n_pos] = d[x]
                counts[n][4] += d[x]
            if x == 'apimw' or x == 'apemw':
                m_c = counts[nd['monos']][4]
                m_ps = counts[nd['poly_senses']][4]
                m_pw = counts[nd['poly_words']][4]
                if x == 'apimw':
                    counts[n][4] = 1.0 * (m_c + m_ps) / (m_c + m_pw)
                else:
                    counts[n][4] = 1.0 * m_ps /  m_pw
    return Stats(counts, rel_counts, rel_words)


def htmlize_stats(stats):
    """
    Given a stats object build a HTML page summarising them.
    """
    print '\n\nStarting the construction of result tables'

    html = (bu.html_header % '* Database Info *') + \
            bu._hlev(2, 'Word, synset and relation counts by POS')
    html += '''
<table border="1" cellpadding="1" cellspacing="1"
summary="">
<col align="left"><col align="right"><col align="right">
<col align="right"><col align="right"><col align="right">
<tr><th></th><th align="center">Noun</th><th align="center">Verb</th>
<th align="center">Adjective</th><th align="center">Adverb</th>
<th align="center">Total</th></tr>
'''
    
    for n,(x,y) in enumerate(DISPLAY_NAMES):
        num_counts = len(stats.counts[n])
        if x == 'rels':
            html += '<tr><th align="left"> </th>' + \
                ('<td align="right"></td>'*num_counts) + \
                '</tr>\n'
        html += '<tr><th align="left">%s</th>' % y
        if  x == 'apimw' or x == 'apemw':
            html += concat_map(lambda c: '<td align="right">%6.2f</td>' % c,
                               stats.counts[n])
        else:
            html += concat_map(lambda c: '<td align="right">%6d</td>' % c,
                               stats.counts[n])
        html += '</tr>\n'

    # Format the relation counts
    r_counts = make_list(0, len(COL_HEADS))
    for rk in group_rel_count_keys_by_first(stats.rel_counts):
        for i in range(len(COL_HEADS)):
            r_counts[i] = 0
        dn = display_name_from_rk(rk)
        html += '<tr><th align="left">--- %s</th>' % dn
        for y in rk[1]:
            r_counts[y[1]] = stats.rel_counts[y]
        r_counts[len(COL_HEADS) - 1] = sum(r_counts)
        html += concat_map(lambda rc: '<td align="right">%6d</td>' % rc,
                           r_counts)
        html += '</tr>\n'
    
    html += '</table>'

    # Format the example words for relations
    html += '<br><br>' + bu._hlev(2, 'Example words for relations, 1 per POS')
    html += '''
<table border="1" cellpadding="1" cellspacing="1"
summary="">
<caption></caption>
<col align="center"><col align="center"><col align="center">
<col align="center"><col align="center">
<tr><th>Relation</th><th>Noun</th><th>Verb</th><th>Adjective</th>
<th>Adverb</th></tr>
'''

    for rk in group_rel_count_keys_by_first(stats.rel_counts):
        dn = display_name_from_rk(rk)
        html += '<tr><th align="center">' + dn + '</th>'
        rel_word_examples = [''] * 4
        for y in rk[1]:
            rel_word_examples[y[1]] = stats.rel_words[y]

        def format_td(x):
            # XXX: The links generated here don't work.  I don't know what
            # they are supposed to link to.
            format_str = '<td align="center"><a href="M%s">%s</a></td>'
            quoted_href = quote_plus(x + '#' + str(bu.uniq_cntr()))
            anchor = x.replace('_', ' ')
            return format_str % (quoted_href, anchor)
        
        hlp = concat_map(format_td, rel_word_examples)
        # XXX: This line doesn't work, Since when there is no anchor above
        # there is still a quoted_href.
        hlp = hlp.replace('<a href="M"></a>','-')
        html += hlp + '</tr>\n'
    html += '</table>' + bu.html_trailer
    return html


def main():
    """
    Program entry point
    """
    stats = get_stats_from_database()
    html = htmlize_stats(stats)
    dbinfo_html_file = open('NLTK Wordnet Browser Database Info.html', 'wt')
    dbinfo_html_file.write(html)
    dbinfo_html_file.close()
    print '\n\nCreation complete: NLTK Wordnet Browser Database Info.html'


if __name__ == '__main__':
    main()
