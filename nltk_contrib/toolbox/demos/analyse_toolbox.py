#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Analyser
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org>
# For license information, see LICENSE.TXT

"""A tool for developing a chunking grammar to parse toolbox lexical databases

to run it:
    python analyse_toolbox.py -g mdfsamp_grammar -x lexicon.xml path_to_MDFSamp.db
you need to give the full path to MDFSamp.db that comes with NLTK in
nltk_data/corpora/toolbox/MDF/MDFSampl.db

It assumes there is a chunking grammar in file called mdfsamp_grammar. The top level
nonterminal in this chunking grammar must be "entry".
A nicely indented XML version of the lexicon structured according to the grammar is 
output to a file and the analysis report is sent to the standard output.

It outputs the number of occurences of each nonterminal in the grammar plus 
the number of occurences of each structure that parses as that nonterminal. 
The structures are listed in descending order of frequency with frequency counts. For 
nonterminals that do not occur more than thirty times it lists the entries (including 
homonym number) where that structure occurs. It also outputs a frequency count of 
markers in the databases. Toolbox records that do not fully parse are listed under 
"record" rather than under the "entry" nonterminal.
"""

import sys,  getopt
import logging
from nltk import toolbox
from nltk.probability import FreqDist
from nltk_contrib.toolbox import parse_corpus,  indent
import nltk.etree.ElementTree as ET

logging.basicConfig(level=logging.WARNING)

def string_from_entry(entry):
    lexeme = entry.findtext('lc')
    if not lexeme:
        lexeme = entry.findtext('lx')
    homonym_num = entry.findtext('hm')
    s = lexeme
    if homonym_num:
        s += '_%s' % homonym_num
    return s

def analyse_dict(structure):
    results = dict()
    for elem in structure.findall('record'):
        if elem[0].tag == 'entry' and len(elem) == 1:
            elem = elem[0]
        position = string_from_entry(elem)
        if len(elem) > 0:
            _analyse(elem,  results,  position)
    return results
    
def _analyse(structure,  results,  position):
    pattern = tuple([e.tag for e in structure])
    results.setdefault(structure.tag,  dict()).setdefault(pattern,  list()).append(position)
    for elem in structure:
        if len(elem) > 0:
            _analyse(elem,  results,  position)

def pattern_count(patt_dict):
    n = 0
    for value in patt_dict.values():
        n += len(value)
    return n
    
def count_mkrs(lexicon):
    mkr_count = FreqDist()
    nonblank_mkr_count = FreqDist()
    for record in lexicon.findall('record'):
        for e in record.getiterator():
            if len(e) == 0:
                tag = e.tag
                mkr_count.inc(tag)
                if e.text.strip():
                    nonblank_mkr_count.inc(tag)
    return (mkr_count,  nonblank_mkr_count)

def process(dict_names,  gram_fname,  xml,  encoding):
    """"""
    gram_file = open(gram_fname,  'r')
    gram = gram_file.read()
    gram_file.close()
    lexicon = parse_corpus(dict_names,  grammar=gram,  encoding=encoding, errors='replace')
    mkr_counts,  nonblank_mkr_counts = count_mkrs(lexicon)
    analysis = analyse_dict(lexicon)
    if xml:
        indent(lexicon)
        out_file = open(xml,  "w")
        out_file.write(ET.tostring(lexicon,  encoding='UTF-8'))
        out_file.close()
    
    print 'analysing files\n%s\n' % '\n'.join(dict_names)
    if xml:
        print 'XML lexicon output in file "%s"\n' % xml
    print '====chunk grammar===='
    print gram
    print '\n'
    max_positions = 30
    for structure,  patt_dict in analysis.items():
        print '\n\n===%s===: total= %d' %(structure,  pattern_count(patt_dict))
        for pattern,  positions in sorted(patt_dict.items(),  key=lambda t: (-len(t[1]),  t[0])):
            if len(positions) <= max_positions:
                pos_str = 'Entries: %s' %  ', '.join(positions)
            else:
                pos_str = 'Too many entries to list.'
            print "\t%5d:  %s %s" % (len(positions),  ':'.join(pattern),  pos_str)
            
    print "\n\n"
    print 'mkr\tcount\tnonblank'
    for mkr in mkr_counts:
        print '%s\t%5d\t%5d' % (mkr,  mkr_counts.get(mkr,  0),  nonblank_mkr_counts.get(mkr,  0))
    
    
if __name__ == "__main__":
    from optparse import OptionParser
    usage = "usage: %prog [options] toolbox_db1 [toolbox_db2] ..."
    parser = OptionParser(usage=usage)
    parser.add_option("-e", "--enc", dest="encoding", default="cp1252", 
                      help="encoding of toolbox database(s)")
    parser.add_option("-g", "--gram", dest="grammar", default="grammar", 
                      help="file containing chunk grammar describing the structure of the toolbox database(s)")
    parser.add_option("-x", "--xml", dest="xml", default=None, 
                      help="name of file for output of parsed contents of toolbox database(s) in indented xml")
    (options, args) = parser.parse_args()
    if len(args) == 0:
        parser.error("you must specify at least one toolbox_db file")
    process(args,  gram_fname=options.grammar,  xml=options.xml,  encoding=options.encoding)
