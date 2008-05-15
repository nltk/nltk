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

all_pos = ['noun', 'verb', 'adj', 'adv']
col_heads = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Total']
display_names = [('forms','Word forms'), ('simple','--- simple words'),
    ('collo','--- collocations'), ('syns','Synsets'),
    ('w_s_pairs','Word-Sense Pairs'),
    ('monos','Monosemous Words and Senses'),
    ('poly_words','Polysemous Words'),
    ('poly_senses','Polysemous Senses'),
    ('apimw','Average Polysemy Including Monosemous Words'),
    ('apemw','Average Polysemy Excluding Monosemous Words'),
    ('rels','Relations')]
WORDNET_PATH = "nltk:corpora/wordnet/"


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


def create_db_info():
    '''
    Create the file: NLTK Wordnet Browser Database Info.html
    '''
    print 'Database information is being gathered!'
    print
    print 'Producing this summary may, depending on your computer,'
    print 'take a couple of minutes. Please be patient!'
    counts = make_list(make_list(0, len(col_heads)), len(display_names))
    rel_counts = defaultdict(int)
    rel_words = {}
    unique_beginners = defaultdict(list)

    for n_pos,pos in enumerate(all_pos): #['adv']): #all_pos):
        print '\n\nStarting the summary for POS: %s' % col_heads[n_pos]
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
            if HYPERNYM not in syn_rel and 'hypernym (instance)' not in syn_rel:
                unique_beginners[n_pos].append(synset)
            d['rels'] += len(syn_rel)
            for sr in syn_rel:
                rel_counts[(sr,n_pos)] += 1
                rel_words[(sr,n_pos)] = synset.words[0]

        # Prepare counts for displaying
        nd = {}
        for n,(x,y) in enumerate(display_names):
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

    # Format the counts
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
    
    for n,(x,y) in enumerate(display_names):
        num_counts = len(counts[n])
        if x == 'rels':
            html += '<tr><th align="left"> </th>' + \
                ('<td align="right"></td>'*num_counts) + \
                '</tr>\n'
        html += '<tr><th align="left">%s</th>' % y
        if  x == 'apimw' or x == 'apemw':
            html += concat_map(lambda c: '<td align="right">%6.2f</td>' % c,
                               counts[n])
        else:
            html += concat_map(lambda c: '<td align="right">%6d</td>' % c,
                               counts[n])
        html += '</tr>\n'

    # Format the relation counts
    r_counts = make_list(0, len(col_heads))
    for rk in groupby(sorted(rel_counts.keys()),key=first):
        for i in range(len(col_heads)):
            r_counts[i] = 0
        dn = bu._dbname_to_dispname(rk[0]).split('/')
        if dn[0] == '???':
            dn = rk[0] + '(???)'
        else:
            dn = dn[0]
        html += '<tr><th align="left">--- %s</th>' % dn
        for y in rk[1]:
            r_counts[y[1]] = rel_counts[y]
        r_counts[len(col_heads) - 1] = sum(r_counts)
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
<tr><th>Relation</th><th>Noun</th><th>Verb</th><th>Adjective</th><th>Adverb</th></tr>
'''

    for rk in groupby(sorted(rel_counts.keys()),key=first):
        dn = bu._dbname_to_dispname(rk[0]).split('/')
        if dn[0] == '???':
            dn = rk[0] + '(???)'
        else:
            dn = dn[0]
        html += '<tr><th align="center">' + dn + '</th>'
        rel_word_examples = [''] * 4
        for y in rk[1]:
            rel_word_examples[y[1]] = rel_words[y]
        hlp = ''.join('<td align="center"><a href="M' + \
                quote_plus(x + '#' + str(bu.uniq_cntr())) + '">' + \
                            x.replace('_', ' ') + '</a></td>' \
                                    for x in rel_word_examples)
        hlp = hlp.replace('<a href="M"></a>','-')
        html += hlp + '</tr>\n'
    html += '</table>' + bu.html_trailer
    dbinfo_html_file = open('NLTK Wordnet Browser Database Info.html', 'wt')
    dbinfo_html_file.write(html)
    dbinfo_html_file.close()
    print '\n\nCreation complete: NLTK Wordnet Browser Database Info.html'
    return


def main():
    """
    Program entry point"
    """
    create_db_info()


if __name__ == '__main__':
    main()
