# Natural Language Toolkit: POS Tag Simplification
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


######################################################################
#{ Brown
######################################################################

# http://khnt.hit.uib.no/icame/manuals/brown/INDEX.HTM

brown_mapping1 = {
    'j': 'ADJ', 'p': 'PRO', 'm': 'MOD', 'q': 'DET',
    'w': 'WH', 'r': 'ADV', 'i': 'P',
    'u': 'UH', 'e': 'EX', 'o': 'NUM', 'b': 'V',
    'h': 'V', 'f': 'FW', 'a': 'DET', 't': 'TO',
    'cc': 'CNJ', 'cs': 'CNJ', 'cd': 'NUM',
    'do': 'V', 'dt': 'DET',
    'nn': 'N', 'nr': 'N', 'np': 'NP', 'nc': 'N'
    }
brown_mapping2 = {
    'vb': 'V', 'vbd': 'VD', 'vbg': 'VG', 'vbn': 'VN'
    }

def simplify_brown_tag(tag):
    tag = tag.lower()
    if tag[0] in brown_mapping1:
        return brown_mapping1[tag[0]]
    elif tag[:2] in brown_mapping1:   # still doesn't handle DOD tag correctly
        return brown_mapping1[tag[:2]]
    try:
        if '-' in tag:
            tag = tag.split('-')[0]
        return brown_mapping2[tag]
    except KeyError:
        return tag.upper()

######################################################################
#{ Wall Street Journal tags (Penn Treebank)
######################################################################

wsj_mapping = {
    '-lrb-': '(',   '-rrb-': ')',    '-lsb-': '(',
    '-rsb-': ')',   '-lcb-': '(',    '-rcb-': ')',
    '-none-': '',   'cc': 'CNJ',     'cd': 'NUM',
    'dt': 'DET',    'ex': 'EX',      'fw': 'FW', # existential "there", foreign word
    'in': 'P',      'jj': 'ADJ',     'jjr': 'ADJ',
    'jjs': 'ADJ',   'ls': 'L',       'md': 'MOD',  # list item marker
    'nn': 'N',      'nnp': 'NP',     'nnps': 'NP',
    'nns': 'N',     'pdt': 'DET',    'pos': '',
    'prp': 'PRO',   'prp$': 'PRO',   'rb': 'ADV',
    'rbr': 'ADV',   'rbs': 'ADV',    'rp': 'PRO',
    'sym': 'S',     'to': 'TO',      'uh': 'UH',
    'vb': 'V',      'vbd': 'VD',     'vbg': 'VG',
    'vbn': 'VN',    'vbp': 'V',      'vbz': 'V',
    'wdt': 'WH',    'wp': 'WH',      'wp$': 'WH',
    'wrb': 'WH',
    'bes': 'V',     'hvs': 'V',     'prp^vbp': 'PRO'   # additions for NPS Chat corpus
    }

def simplify_wsj_tag(tag):
    if tag and tag[0] == '^':
        tag = tag[1:]
    try:
        tag = wsj_mapping[tag.lower()]
    except KeyError:
        pass
    return tag.upper()

indian_mapping = {
    'nn': 'N', 'vm': 'MOD', 'jj': 'ADJ', 'nnp': 'NP',
    'prp': 'PRO', 'prep': 'PRE', 'vaux': 'V', 'vfm': 'V',
    'cc': 'CNJ', 'nnpc': 'NP', 'nnc': 'N', 'qc': 'QC',
    'dem': 'DET', 'vrb': 'V', 'qfnum': 'NUM', 'rb': 'ADV',
    'qf': 'DET', 'punc': '.', 'rp': 'PRT', 'psp': 'PSP',
    'nst': 'N', 'nvb': 'N', 'vjj': 'V', 'neg': 'NEG',
    'vnn': 'V', 'xc': 'XC', 'intf': 'INTF', 'nloc': 'N',
    'jvb': 'ADJ', 'wq': 'WH', 'qw': 'WH', 'jj:?': 'ADJ',
    '"cc': 'CNJ', 'nnp,': 'NP', 'sym\xc0\xa7\xb7': 'SYM',
    'symc': 'SYM'}

def simplify_indian_tag(tag):
    if ':' in tag:
        tag = tag.split(':')[0]
    try:
        tag = indian_mapping[tag.lower()]
    except KeyError:
        pass
    return tag.upper()


######################################################################
#{ Alpino tags
######################################################################

alpino_mapping = {
    'noun':'N', 'name': 'NP', 'vg': 'VG', 'punct':'.',
    'verb':'V', 'pron': 'PRO', 'prep':'P'
    }

def simplify_alpino_tag(tag):
    try:
        tag = alpino_mapping[tag]
    except KeyError:
        pass
    return tag.upper()

######################################################################
#{ Default tag simplification
######################################################################

def simplify_tag(tag):
    return tag[0].upper()
