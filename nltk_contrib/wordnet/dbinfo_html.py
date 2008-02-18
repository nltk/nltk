# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
from collections import defaultdict
from itertools import groupby
from urllib import quote_plus

from nltk.wordnet.synset import *

import browseutil as bu

all_pos = ['noun', 'verb', 'adj', 'adv']
col_heads = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Total']
data_path = os.environ['NLTK_DATA'] + '\\corpora\\wordnet\\'
display_names = [('forms','Word forms'), ('simple','--- simple words'),
    ('collo','--- collocations'), ('syns','Synsets'),
    ('w_s_pairs','Word-Sense Pairs'),
    ('monos','Monosemous Words and Senses'),
    ('poly_words','Polysemous Words'),
    ('poly_senses','Polysemous Senses'),
    ('apimw','Average Polysemy Including Monosemous Words'),
    ('apemw','Average Polysemy Excluding Monosemous Words'),
    ('rels','Relations')]

def create_db_info():
    '''
    Create the file: NLTK Wordnet Browser Database Info.html
    '''
    print 'Database information is being gathered!'
    print
    print 'Producing this summary may, depending on your computer,'
    print 'take a couple of minutes. Please be patient!'
    counts = [[0 for i in range(len(col_heads))]
                    for j in range(len(display_names))]
    rel_counts = defaultdict(int)
    rel_words = {}
    unique_beginners = defaultdict(list)

    for n_pos,pos in enumerate(all_pos): #['adv']): #all_pos):
        print '\n\nStarting the summary for POS: %s' % col_heads[n_pos]
        d = defaultdict(int)
        # Word counts
        for ind in open(data_path + 'index.' + pos):
            if ind.startswith('  '):
                continue
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
        for syns in open(data_path + 'data.' + pos):
            if syns.startswith('  '):
                continue
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
        if x == 'rels':
            html += '<tr><th align="left"> </th>'
            html += ''.join('<td align="right"> </td>' for c in counts[n]) \
                    + '</tr>\n'
        html += '<tr><th align="left">' + '%s' % y + '</th>'
        if  x == 'apimw' or x == 'apemw':
            html += ''.join('<td align="right">' + '%6.2f ' % c + '</td>' \
                                            for c in counts[n]) + '</tr>\n'
        else:
            html += ''.join('<td align="right">' + '%6d ' % c + '</td>' \
                                            for c in counts[n]) + '</tr>\n'

    # Format the relation counts
    r_counts = [0 for i in range(len(col_heads))]
    for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
        for i in range(len(col_heads)):
            r_counts[i] = 0
        dn = bu._dbname_to_dispname(rk[0]).split('/')
        if dn[0] == '???':
            dn = rk[0] + '(???)'
        else:
            dn = dn[0]
        html += '<tr><th align="left">' + '%s' % ('--- ' + dn) + '</th>'
        for y in rk[1]:
            r_counts[y[1]] = rel_counts[y]
        r_counts[len(col_heads) - 1] = sum(r_counts)
        html += ''.join('<td align="right">' + '%6d ' % rc + '</td>'
                         for rc in r_counts) + '</tr>\n'
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

    for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
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


if __name__ == '__main__':
    create_db_info()

