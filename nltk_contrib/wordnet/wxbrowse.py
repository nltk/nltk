# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

__version__ = '$Revision: 9 $'
# $Source$

import  os
import  os.path
import  sys
from time import sleep
from threading import Timer
import itertools as it
import sys
from collections import defaultdict
from pprint import pprint
import pickle
import platform
import math
import itertools as it
from itertools import groupby


import  wx
import  wx.html as  html
import  wx.lib.wxpTag

from util import *
from dictionary import *
from morphy import morphy

__all__ = ['demo']

frame_title = 'NLTK Wordnet Browser'
help_about = frame_title + \
'''

Copyright (C) 2007 University of Pennsylvania

Author: Jussi Salmela <jtsalmela@users.sourceforge.net>

URL: <http://nltk.sf.net>

For license information, see LICENSE.TXT
'''

# This is used to save options in and to be pickled at exit
options_dict = {}
pickle_file_name = frame_title + '.pkl'


pos_tuples = [(N,'N','noun'), (V,'V','verb'), (ADJ,'J','adj'), (ADV,'R','adv')]

def pos_match(pos_tuple):
    for n,x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in pos_tuples:
            if pt[n] == pos_tuple[n]: return pt
    return None

implemented_rel_names = \
    ['antonym',
     'attribute',
     'cause',
     'derivationally related form',
     'direct hypernym',
     'direct hyponym',
     'direct troponym',
     'domain category',
     'domain region',
     'domain term category',
     'domain term region',
     'domain term usage',
     'domain usage',
     'entailment',
     'full hyponym',
     'full troponym',
     'has instance',
     'inherited hypernym',
     'instance',
     'member holonym',
     'member meronym',
     'Overview',
     'part holonym',
     'part meronym',
     'participle',
     'pertainym',
     'phrasal verb',
     'see also',
     'sentence frame',
     'similar to',
     'sister term',
     'substance holonym',
     'substance meronym',
     'synset',
     'verb group'
    ]

# Relation names in the order they will displayed. The first item of a tuple
# is the internal i.e. DB name. The second item is the display name or if it
# contains parts separated by slashes, the parts are displayed as separate
# links.
rel_order = \
    [(HYPONYM,'direct hyponym/full hyponym'),
     (HYPONYM,'direct troponym/full troponym'),
     (CLASS_REGIONAL,'domain term region'),
     (PART_HOLONYM,PART_MERONYM),
     (ATTRIBUTE,ATTRIBUTE),
     (SUBSTANCE_HOLONYM,SUBSTANCE_MERONYM),
     (SUBSTANCE_MERONYM,SUBSTANCE_HOLONYM),
     (MEMBER_MERONYM,MEMBER_HOLONYM),
     (MEMBER_HOLONYM,MEMBER_MERONYM),
     (VERB_GROUP,VERB_GROUP),
     (CLASSIF_CATEGORY, CLASSIF_CATEGORY),
     (INSTANCE_HYPONYM, 'has instance'),
     (CLASS_CATEGORY,'domain term category'),
     (CLASS_USAGE,'domain term usage'),
     (HYPERNYM,'direct hypernym/inherited hypernym/sister term'),
     (CLASSIF_REGIONAL, CLASSIF_REGIONAL),
     (CLASSIF_USAGE,'domain usage'),
     (PART_MERONYM,PART_HOLONYM),
     (INSTANCE_HYPERNYM, 'instance'),
     (CAUSE,CAUSE),
     (ALSO_SEE,'see also'),
     (ALSO_SEE,'phrasal verb'),
     (SIMILAR,'similar to'),
     (ENTAILMENT,ENTAILMENT),
     (PARTICIPLE_OF, 'participle'),
     (ANTONYM, 'antonym'),
     (FRAMES,'derivationally related form'),
     #sentence frame
     (PERTAINYM,PERTAINYM)
     ]

def dispname_to_dbname(dispname):
    for dbn,dispn in rel_order:
        if dispname in dispn.split('/'):
            return dbn
    return None

def dbname_to_dispname(dbname):
    for dbn,dispn in rel_order:
        if dbn == dbname:
            return dispn
    return '???'

html_header = '''
<!DOCTYPE html PUBLIC '-//W3C//DTD HTML 4.01//EN'
'http://www.w3.org/TR/html4/strict.dtd'>
<html>
<head>
<meta name='generator' content=
'HTML Tidy for Windows (vers 14 February 2006), see www.w3.org'>
<meta http-equiv='Content-Type' content=
'text/html; charset=us-ascii'>
</head>
<body bgcolor='#F5F5F5' text='#000000'>
'''
#html_header = ''

html_trailer = '''
</body>
</html>
'''
#html_trailer = ''

explanation  = '''
<h3>Search Help</h3>
<ul><li>The display below the line is an example of the output the browser
shows you when you enter a search word. The search word was <b>green</b>.</li>
<li>The search result shows for different parts of speech the <b>synsets</b>
i.e. different meanings for the word.</li>
<li>All underlined texts are hypertext links. There are two types of links:
word links and others. Clicking a word link carries out a search for the word
in the Wordnet database.</li>
<li>Clicking a link of the other type opens a display section of data attached
to that link. Clicking that link a second time closes the section again.</li>
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
<li>Clicking on a relation name opens a section that displays the associated
synsets.</li>
<li>Type a search word in the <b>Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr width='100%'>
'''

# HTML oriented functions

def bold(txt): return '<b>%s</b>' % txt

def center(txt): return '<center>%s</center>' % txt

def hlev(n,txt): return '<h%d>%s</h%d>' % (n,txt,n)

def italic(txt): return '<i>%s</i>' % txt

def li(txt): return '<li>%s</li>' % txt

def pg(body): return html_header + body + html_trailer

def ul(txt): return '<ul>' + txt + '</ul>'

# abbc = asterisks, breaks, bold, center
def abbc(txt):
    return center(bold('<br>'*10 + '*'*10 + ' ' + txt + ' ' + '*'*10))

full_hyponym_cont_text = \
    ul(li(italic('(has full hyponym continuation)'))) + '\n'

# This counter function is used to guarantee unique counter values
uniq_cntr = it.count().next

def get_synset(synset_key):
    pos = pos_match((None,synset_key[0],None))[2]
    offset = int(synset_key[1:])
    return getSynset(pos, offset)

def collect_one(word, s_or_w, prev_synset_key):
    u_c = uniq_cntr()
    if isinstance(s_or_w, tuple): # It's a word
        form_str,(synset,oppo,forms) = s_or_w
        pos,offset,ind = oppo
        synset = getSynset(pos, offset)
        synset_key = pos_match((None,None,synset.pos))[1] + str(synset.offset)
        synset_key  += ':' + str(ind) + ',' + prev_synset_key
        oppo = synset.words[ind]
        oppo = oppo.replace('_', ' ')
        typ = 'W'
    else: # It's a synset
        synset = s_or_w
        typ = 'S'
        synset_key = pos_match((None,None,synset.pos))[1] + str(synset.offset)
        synset_key  += ',' + prev_synset_key
    if synset.pos.startswith('ad'):  descr = synset.pos
    else:                            descr = synset.pos[0]
    s = '<li><a href="' + typ + word + '#' + synset_key + '#' + \
            str(u_c) + '">' + typ + ':</a>' + ' (' + descr + ') '
    if isinstance(s_or_w, tuple): # It's a word
        s += '<a href="?' + oppo + '">' + oppo + '</a> ' + form_str
        for w in forms:
            pos,offset,ind = w
            w = getSynset(pos, offset).words[ind]
            w = w.replace('_', ' ')
            s += '<a href="?' + w + '">' + w + '</a>, '
        s = s[:-2] + ']  '
    else: # It's a synset
        for w in synset:
            w = w.replace('_', ' ')
            if w.lower() == word:
                s+= bold(w) + ', '
            else:
                s += '<a href="?' + w + '">' + w + '</a>, '
    s = s[:-2] + ' ('
    # Format the gloss part
    gl = ''
    hyph_not_found = True
    for g in synset.gloss.split('; '):
        if not g.startswith('"'):
            if gl: gl += '; '
            gl += g
        else:
            if hyph_not_found:
                gl += ') <i>'
                hyph_not_found = False
            else:
                gl += '; '
            gl += g
    if hyph_not_found: gl += ')'
    if not hyph_not_found: gl += '</i>'
    return s + gl + '</li>\n'

def collect_all(word, pos):
    s = '<ul>'
    for synset in pos[word]:
        s += collect_one(word, synset, '')
    return s + '\n</ul>\n'

def rel_ref(word, synset_keys, rel):
    return '<a href="*' + word + '#' + synset_keys + '#' + \
            rel + '#' + str(uniq_cntr()) + '"><i>' + rel + '</i></a>'

def anto_or_similar_anto(synset):
    anto = synset.relations(rel_name=ANTONYM, word_match=True)
    if anto: return synset
    similar = synset.relations(rel_name=SIMILAR)
    for simi in similar:
        anto = simi.relations(rel_name=ANTONYM, word_match=True)
        if anto: return simi
    return False

def synset_relations(word, link_type, synset_keys):
    sk,prev_sk = synset_keys.split(',')
    synset = get_synset(sk.split(':')[0])
    rel_keys = synset.relations().keys()

    html = ''
    if link_type == 'W':
        rel_names = [(ANTONYM, 'antonym'),
                     (FRAMES,'derivationally related form')]
    else:
        rel_names = rel_order
    for rel in rel_names:
        db_name,disp_name = rel
        if db_name == ALSO_SEE:
            if synset.pos == 'verb' and disp_name != 'phrasal verb' or \
               synset.pos != 'verb' and disp_name == 'phrasal verb':
                   continue
        if db_name == HYPONYM:
            if synset.pos == 'verb':
                if disp_name.find('tropo') == -1:
                    continue
            else:
                if disp_name.find('hypo') == -1:
                    continue
        if synset[db_name] or \
                  db_name == ANTONYM and anto_or_similar_anto(synset):
            lst = [' <i>/</i> ' + rel_ref(word, synset_keys, r)
                   for r in disp_name.split('/')]
            html += ''.join(lst)[10:] # drop the extra ' <i>/</i> '
            html += '\n'
            if db_name in rel_keys: rel_keys.remove(db_name)
    if link_type == 'W':
        html += rel_ref(word, synset_keys, 'Overview') + '\n'
        html += rel_ref(word, synset_keys, 'synset') + '\n'
    else:
        for rel in rel_keys:
            html += rel_ref(word, synset_keys, rel) + '\n'
        if synset.pos == 'verb' and synset.verbFrameStrings:
            html += rel_ref(word, synset_keys, 'sentence frame') + '\n'
    return html

def hyponym_ul_structure(word, tree):
    #print 'tree:', tree
    if tree == []: return ''
    if tree == ['...']: return full_hyponym_cont_text
    head = tree[0]
    tail = tree[1:]
    #print 'head, tail:', head, tail
    htm = collect_one(word, head[0], '') + '\n'
    if isinstance(head, list) and len(head) > 1:
        #print 'head[1:]:', head[1:]
        htm += '<ul>'
        htm += hyponym_ul_structure(word, head[1:])
        htm += '\n</ul>'
    htm += hyponym_ul_structure(word, tail)
    return htm

def hypernym_ul_structure(word, tree):
    htm = '<ul>\n' + collect_one(word, tree[0], '') + '\n'
    if len(tree) > 1:
        tree = tree[1:]
        for t in tree: htm += hypernym_ul_structure(word, t)
        #htm += '\n</ul>\n'
    return htm  + '\n</ul>\n'

def word_ul_structure(word, synset, rel_name, synset_keys):
    synset_key,prev_synset_key = synset_keys.split(',')
    rel_name = dispname_to_dbname(rel_name)
    if rel_name == ANTONYM:
        rel_form = ' [Opposed to: '
    else:
        rel_form = ' [Related to: '
    s = ''
    rel = synset.relations(rel_name=rel_name, word_match=True)
    #print 'rel:', rel
    if rel:
        hlp = [((s1.pos,s1.offset,i1),(s0.pos,s0.offset,i0))
                  for ((s0,i0),(s1,i1)) in rel]
        if prev_synset_key:
            sk,prev_sk = synset_keys.split(',')
            sk0,sk1 = sk.split(':')
            syns = get_synset(sk0)
            ind = int(sk1)
            hlp = [((s1.pos,s1.offset,i1),(s0.pos,s0.offset,i0))
                      for ((s0,i0),(s1,i1)) in rel
                      if s0.pos == syns.pos and s0.offset == syns.offset
                      and i0 == ind]
        hlp = it.groupby(hlp,key=lambda x:x[0])
        '''
        for h in hlp:
            forms = []
            for h2 in h[1]:
                forms.append(h2[1])
            forms.sort()
            print 'h[0], forms:', h[0], forms
            s += collect_one(word, (rel_form,(s1,h[0],forms)), synset_key)
        '''
        hlp_2 = []
        for h in hlp:
            forms = []
            for h2 in h[1]:
                forms.append(h2[1])
            forms.sort()
            #print 'h[0], forms:', h[0], forms
            hlp_2 = [(h[0],forms)] + hlp_2
        for h,f in hlp_2:
            #print 'h, f:', h, f
            s += collect_one(word, (rel_form,(s1,h,f)), synset_key)
    elif rel_name == ANTONYM:
        similar = synset.relations(rel_name=SIMILAR)
        for simi in similar:
            anto = simi.relations(rel_name=ANTONYM, word_match=True)
            if anto:
                for a in anto:
                    ((s0,i0),(s1,i1)) = a
                    form = (s0.pos,s0.offset,i0)
                    oppo = (s1.pos,s1.offset,i1)
                    s += collect_one(word, \
                                (' [Indirect via ',(s1,oppo,[form])), synset_key)
    return s

def relation_section(rel_name, word, synset_keys):
    synset_key,prev_synset_key = synset_keys.split(',')
    synset = get_synset(synset_key.split(':')[0])
    if rel_name == 'full hyponym' or rel_name == 'full troponym':
        if rel_name == 'full hyponym':
            #depth = max(1, 2**int(math.sqrt(synset.min_depth())) - 1)
            depth = synset.min_depth()
            if depth <= 2: depth = 1
            elif depth == 3: depth = 2
            #else: depth += 1
        else: depth = -1
        tree = synset.tree(HYPONYM, depth, cut_mark='...')
        #print tree
        '''
        if pruned:
            msg = '(The following list is pruned; max. depth = %d)' % depth
            return '<ul>\n' + li(bold(italic(msg))) + \
                              hyponym_ul_structure(word, tree[1:]) + '\n</ul>'
        else:
        '''
        html = '\n' + hyponym_ul_structure(word, tree[1:]) + '\n'
        for x in synset[INSTANCE_HYPONYM]:
            html += collect_one(word, x, '')
        return ul(html + '\n')
    elif rel_name == 'inherited hypernym':
        tree = synset.tree(HYPERNYM)
        #print tree
        return hypernym_ul_structure(word, tree[1:][0]) # + '\n</ul>'
    elif rel_name == 'sister term':
        s = ''
        for x in synset[HYPERNYM]:
            s += collect_one(word, x, '')
            s += '<ul>'
            for y in x[HYPONYM]:
                s += collect_one(word, y, '')
            s += '\n</ul>'
        return ul(s + '\n')
    elif rel_name == 'sentence frame':
        verb_frame_strings = [(VERB_FRAME_STRINGS[i] % bold(word)) \
                                for i in synset.verbFrames]
        s = '\n'.join(['<li>' + vfs + '</li>' for vfs
                                          in verb_frame_strings])
        return ul(s + '\n')
    elif rel_name == 'Overview':
        ind = int(synset_key.split(':')[1])
        w,b = w_b(synset.words[ind], True)
        if not w: return ''
        return ul(b + '\n')
    elif rel_name == 'synset':
        s = collect_one(word, synset, '')
        return ul(s + '\n')
    elif rel_name == 'domain term region':
        rel = dispname_to_dbname(rel_name)
        s = ''
        word_collection = []
        for x in synset[rel]:
            if isinstance(x, basestring):
                word_collection.append(x)
            else:
                s += collect_one(word, x, '')

        for wrd in word_collection:
            w = pos_match((None,None,synset.pos))[0][wrd]
            oppo = None
            for syns in w:
            	for wlr in syns.relations(CLASSIF_REGIONAL,True):
                    if not isinstance(wlr, tuple): continue
                    syn,i = wlr[1]
                    syns,j = wlr[0]
                    if syn == synset and syns.words[j] == wrd:
             			form = (syn.pos,syn.offset,i)
             			oppo = (syns.pos,syns.offset,j)
             			break
                if oppo: break
            if oppo:
                s += collect_one(word, \
                                (' [Related to: ',(synset,oppo,[form])), synset_key)
        return ul(s + '\n')
    else:
        rel = dispname_to_dbname(rel_name)
        if rel == ANTONYM or \
                isinstance(synset.relations()[rel][0], basestring): # word level
            s = word_ul_structure(word, synset, rel_name, synset_keys)
            return ul(s + '\n')
        else:
            s = ''
            for x in synset[rel]:
                s += collect_one(word, x, '')
            if rel == HYPONYM:
                for x in synset[INSTANCE_HYPONYM]:
                    s += collect_one(word, x, '')
            return ul(s + '\n')

def w_b(word, overview):
    pos_forms = defaultdict(list)
    words = word.split(',')
    words = [w.strip() for w in words]
    for pos_str in ['noun', 'verb', 'adj', 'adv']:
        for w in words:
            '''
            if overview:
                pos_forms[pos_str].append(w)
            else:
                for form in morphy(w, pos=pos_str):
                    if form not in pos_forms[pos_str]:
                        pos_forms[pos_str].append(form)
            '''
            for form in morphy(w, pos=pos_str):
                if form not in pos_forms[pos_str]:
                    pos_forms[pos_str].append(form)
    body = ''
    for pos,pos_str,name in \
        ((N,'noun','Noun'), (V,'verb','Verb'),
         (ADJ,'adj','Adjective'), (ADV,'adv','Adverb')):
        if pos_str in pos_forms:
            if not overview:
                body += hlev(3, name) + '\n'
            for w in pos_forms[pos_str]:
                # Not all words of exc files are in the database, so:
                try:
                    body += collect_all(w, pos)
                except KeyError:
                    pass
    if not body:
        word = None
    return word,body

def new_word_and_body(word):
    word = word.lower().replace('_', ' ')
    return w_b(word, False)

def ul_section_removed(page, index):
    '''Removes the first string <ul>...stuff...</ul> from the html page.
    The search starts at index. Note: ...stuff... may contain embedded
    <ul>-</ul> pairs but the search continues to the </ul> that is the
    pair of the starting <ul>
    '''
    ind = page.find('<ul>', index)
    if ind == -1: return page
    ul_count = 1
    ul_start = ind
    ind += 4
    while ul_count:
        ind = page.find('ul>', ind)
        if ind == -1: return page
        if page[ind - 1] == '/': # </ul> found
            ul_count -= 1
            ul_end = ind + 3
        else:
            ul_count += 1
        ind += 3
    return page[:ul_start] + page[ul_end:]


class MyHtmlWindow(html.HtmlWindow):
    def __init__(self, parent, id):
        html.HtmlWindow.__init__(self, parent, id,
                                    style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.parent = parent
        #if 'gtk2' in wx.PlatformInfo:
        #self.SetStandardFonts()
        self.font_size = self.normal_font_size = \
                         options_dict['font_size']
        #print 'self.font_size:', self.font_size
        self.incr_decr_font_size(0) # Keep it as it is

    def OnLinkClicked(self, linkinfo):
        href = linkinfo.GetHref()
        tab_to_return_to = None
        word = self.parent.parent.search_word.GetValue()
        if linkinfo.Event.ControlDown():
            if linkinfo.Event.ShiftDown():
                        self.parent.add_html_page(activate=True)
            else:
                tab_to_return_to = self.parent.current_page
                self.parent.add_html_page(activate=True)
        self.parent.SetPageText(self.parent.current_page, word)
        self.parent.parent.search_word.SetValue(word)
        link_type = href[0]
        link = href[1:]
        if link_type == '?': # one of the words in a synset
            word,body = new_word_and_body(link)
            if word:
                self.parent.SetPageText(self.parent.current_page, word)
                self.parent.parent.show_page_and_word(pg(body), word)
            else:
                self.show_msg('The word was not found!')
        elif link_type == '*': # Relation links
            # A relation link looks like this:
            # word#synset_keys#relation_name#uniq_cntr
            #print 'link:', link
            word,synset_keys,rel_name,u_c = link.split('#')
            #print 'word,synset_keys,rel_name,u_c:',word,synset_keys,rel_name,u_c
            page = self.GetParser().GetSource()
            ind = page.find(link) + len(link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                page = page[:ind] + '<i>' + rel_name + \
                        '</i>' + page[ind + len(rel_name) + 14:]
                self.parent.parent.show_page_and_word(page)
            else:
                # First check if another link is bold on the same line
                # and if it is, then remove boldness & close the section below
                end = page.find('\n', ind)
                start = page.rfind('\n', 0, ind)
                #print 'page[start:end]:', page[start:end]
                start = page.find('<b>', start, end)
                #print 'start:', start
                if start != -1:
                    page = ul_section_removed(page, ind)
                    end = page.find('</b>', start, end)
                    page = page[:start] + page[start+3:end] + page[end+4:]

                # Make this selection bold on page
                #
                if rel_name in implemented_rel_names:
                    ind = page.find(link) + len(link) + 2
                    ind_2 = ind + len(rel_name) + 7
                    #print 'page[:ind]:', page[:ind]
                    page = page[:ind] + bold(page[ind:ind_2]) + \
                           page[ind_2:]
                    # find the start of the next line
                    ind = page.find('\n', ind) + 1
                    section = \
                        relation_section(rel_name, word, synset_keys)
                    #print 'page[:ind]:', page[:ind]
                    page = page[:ind] + section + page[ind:]
                    self.parent.parent.show_page_and_word(page)
                else:
                    self.show_msg('Not implemented yet!')
        else:
            # A word link looks like this:
            # Wword#synset_key,prev_synset_key#link_counter
            # A synset link looks like this:
            # Sword#synset_key,prev_synset_key#link_counter
            l_t = link_type + ':'
            #print 'l_t, link:', l_t, link
            word,syns_keys,link_counter = link.split('#')
            #print 'word,syns_keys,link_counter:',word,syns_keys,link_counter
            #syns_key,prev_syns_key = syns_keys.split(',')
            page = self.GetParser().GetSource()
            ind = page.find(link) + len(link) + 2
            #print page[ind:]
            # If the link text is in bold, the user wants to
            # close the section beneath the link
            if page[ind:ind+3] == '<b>':
                page = ul_section_removed(page, ind)
                #page = page[:ind] + 'S:' + page[ind + 9:]
                page = page[:ind] + l_t + page[ind + 9:]
                self.parent.parent.show_page_and_word(page)
            else: # The user wants to see the relation names
                # Make this link text bold on page
                #page = page[:ind] + bold('S:') + page[ind + 2:]
                page = page[:ind] + bold(l_t) + page[ind + 2:]
                # Insert the relation names
                ind = page.find('\n', ind) + 1
                # First remove the full_hyponym_cont_text if found here
                #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
                if page[ind+5:].startswith(full_hyponym_cont_text):
                    page = page[0:ind+5] + \
                            page[ind+5+len(full_hyponym_cont_text):]
                #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
                s_r = synset_relations(word, link_type, syns_keys)
                s_r = s_r.split('\n')[:-1]
                s_r = [li(sr) for sr in s_r]
                s_r = ul('\n' + '\n'.join(s_r) + '\n') + '\n'
                page = page[:ind] + s_r + page[ind:]
                self.parent.parent.show_page_and_word(page)
        '''
        else:
            print 'We should be in a Help Window now! Are we?'
            super(MyHtmlWindow, self).OnLinkClicked(linkinfo)
        '''
        if tab_to_return_to is not None:
            self.parent.switch_html_page(tab_to_return_to)
            '''
            self.parent.current_page = tab_to_return_to
            self.parent.SetSelection(tab_to_return_to)
            self.parent.h_w = self.parent.GetPage(tab_to_return_to)
            if self.parent.h_w.prev_wp_list == []:
                self.parent.prev_btn.Enable(False)
            if self.parent.h_w.next_wp_list == []:
                self.parent.next_btn.Enable(False)
            '''

    def OnSetTitle(self, title):
        pass
        #super(MyHtmlWindow, self).OnSetTitle(title)

    def OnCellMouseHover(self, cell, x, y):
        #super(MyHtmlWindow, self).OnCellMouseHover(cell, x, y)
        pass

    def OnOpeningURL(self, type, url):
        #super(MyHtmlWindow, self).OnCellMouseHover(cell, x, y)
        pass

    def OnCellClicked(self, cell, x, y, evt):
        linkinfo = cell.GetLink()
        if linkinfo is not None:
            #html.HtmlCellEvent.SetLinkClicked(True)
            #evt.SetLinkClicked(True)
            pass
        else:
            pass
        super(MyHtmlWindow, self).OnCellClicked(cell, x, y, evt)

    def incr_decr_font_size(self, change=None):
        global options_dict
        page_to_restore = self.GetParser().GetSource()
        if change:
            self.font_size += change
            if self.font_size <= 0: self.font_size = 1
        else:
            self.font_size  = self.normal_font_size
        options_dict['font_size'] = self.font_size
        # Font size behavior is very odd. This is a hack
        #self.SetFonts('times new roman', 'courier new', [self.font_size]*7)
        self.SetStandardFonts(size=self.font_size)
        self.SetPage(page_to_restore)

    def show_body(self, body):
        self.SetPage(html_header + body + html_trailer)

    def show_help(self):
        self.parent.parent.show_page_and_word(explanation, 'green')

    def show_msg(self, msg):
        msg1 = '*'*8 + '   ' + msg + '   ' + '*'*8
        msg2 = '*'*100
        for i in range(5):
            for msg in [msg1, msg2]:
                self.parent.parent.statusbar.SetStatusText(msg)
                wx.Yield()
                sleep(0.2)
        self.parent.parent.statusbar.SetStatusText(' ')
        wx.Yield()

    def show_page(self, page):
        self.SetPage(page)


#----------------------------------------------------------------------------
class NB(wx.Notebook):
    def __init__(self, parent):
        wx.Notebook.__init__(self, parent, -1, size=(21,21), style=
                             wx.BK_DEFAULT
                             #wx.BK_TOP
                             #wx.BK_BOTTOM
                             #wx.BK_LEFT
                             #wx.BK_RIGHT
                             # | wx.NB_MULTILINE
                             )
        self.parent = parent
        self.add_html_page()
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnPageChanging)

    def OnPageChanged(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        if old != new: #  and self.current_page != new:
            self.switch_html_page(new)
        event.Skip()

    def OnPageChanging(self, event):
        old = event.GetOldSelection()
        new = event.GetSelection()
        sel = self.GetSelection()
        event.Skip()

    def switch_html_page(self, new_page):
        self.current_page = new_page
        self.ChangeSelection(new_page)
        self.h_w = self.GetPage(new_page)
        self.parent.prev_btn.Enable(self.h_w.prev_wp_list != [])
        self.parent.next_btn.Enable(self.h_w.next_wp_list != [])
        self.parent.search_word.SetValue(self.h_w.current_word)

    def add_html_page(self, tab_text='', activate=True):
        h_w = MyHtmlWindow(self, -1)
        if 'gtk2' in wx.PlatformInfo:
            h_w.SetStandardFonts()
        h_w.SetRelatedFrame(self.parent.frame, self.parent.titleBase + ' -- %s')
        h_w.SetRelatedStatusBar(0)
        h_w.current_word = ''
        # Init the word-page list for history browsing
        h_w.prev_wp_list = []
        h_w.next_wp_list = []
        self.AddPage(h_w, tab_text, activate)
        if activate:
            self.current_page = self.GetSelection()
            self.h_w = h_w
            if self.h_w.prev_wp_list == []:
                self.parent.prev_btn.Enable(False)
            if self.h_w.next_wp_list == []:
                self.parent.next_btn.Enable(False)
        return self.current_page


class HtmlPanel(wx.Panel):
    def __init__(self, frame):
        wx.Panel.__init__(self, frame, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.frame = frame
        self.cwd = os.path.split(sys.argv[0])[0]

        if not self.cwd:
            self.cwd = os.getcwd()
        if frame:
            self.titleBase = frame.GetTitle()

        self.statusbar = self.frame.CreateStatusBar()

        self.printer = html.HtmlEasyPrinting(frame_title)

        self.box = wx.BoxSizer(wx.VERTICAL)

        subbox_1 = wx.BoxSizer(wx.HORIZONTAL)

        self.prev_btn = wx.Button(self, -1, 'Previous Page')
        self.Bind(wx.EVT_BUTTON, self.on_prev_page, self.prev_btn)
        subbox_1.Add(self.prev_btn, 5, wx.GROW | wx.ALL, 2)

        self.next_btn = wx.Button(self, -1, 'Next Page')
        self.Bind(wx.EVT_BUTTON, self.on_next_page, self.next_btn)
        subbox_1.Add(self.next_btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, 'Help')
        self.Bind(wx.EVT_BUTTON, self.on_help, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        btn = wx.Button(self, -1, 'Search the word(s)')
        self.Bind(wx.EVT_BUTTON, self.on_word_enter, btn)
        subbox_1.Add(btn, 5, wx.GROW | wx.ALL, 2)

        lbl = wx.StaticText(self, -1, 'Word(s): ',
                            style=wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM)
        subbox_1.Add(lbl, 5, wx.GROW | wx.ALL, 2)

        self.search_word = wx.TextCtrl(self, -1, '', style=wx.TE_PROCESS_ENTER)
        #self.Bind(wx.EVT_TEXT, self.on_word_change, self.search_word)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_word_enter, self.search_word)
        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down, self.search_word)
        #self.Bind(wx.EVT_KEY_UP, self.on_key_up, self.search_word)
        #self.Bind(wx.EVT_CHAR, self.on_char, self.search_word)
        self.search_word.Bind(wx.EVT_LEFT_UP, self.on_mouse_up)
        subbox_1.Add(self.search_word, 20, wx.GROW | wx.ALL, 2)

        self.box.Add(subbox_1, 0, wx.GROW)
        self.nb = NB(self)
        self.box.Add(self.nb, 1, wx.GROW)

        self.SetSizer(self.box)
        self.SetAutoLayout(True)

    def on_key_down(self, event):
        event.Skip()

    def on_key_up(self, event):
        event.Skip()

    def on_char(self, event):
        event.Skip()

    def on_mouse_up(self, event):
        self.search_word.SetSelection(-1, -1)
        event.Skip()

    def on_prev_page(self, event):
        if self.nb.h_w.prev_wp_list:
            # Save current word&page&viewStart
            page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,page,(x,y))
            self.nb.h_w.next_wp_list = [entry] + self.nb.h_w.next_wp_list
            self.next_btn.Enable(True)
            # Restore previous word&page
            word,page,(x,y) = self.nb.h_w.prev_wp_list[-1]
            self.nb.h_w.prev_wp_list = self.nb.h_w.prev_wp_list[:-1]
            if self.nb.h_w.prev_wp_list == []:
                self.prev_btn.Enable(False)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.SetPage(page)
            self.nb.h_w.Scroll(x, y)
        #else:
        #    self.nb.h_w.show_msg('At the start of page history already')

    def on_next_page(self, event):
        if self.nb.h_w.next_wp_list:
            # Save current word&page&viewStart
            page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,page,(x,y))
            self.nb.h_w.prev_wp_list.append(entry)
            self.prev_btn.Enable(True)
            # Restore next word&page
            word,page,(x,y) = self.nb.h_w.next_wp_list[0]
            self.nb.h_w.next_wp_list = self.nb.h_w.next_wp_list[1:]
            if self.nb.h_w.next_wp_list == []:
                self.next_btn.Enable(False)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
            self.search_word.SetValue(word)
            self.nb.h_w.SetPage(page)
            self.nb.h_w.Scroll(x, y)
        #else:
        #    self.nb.h_w.show_msg('At the end of page history already!')

    def on_help(self, event):
        self.frame.on_help_help(None)

    def on_word_change(self, event):
        word = self.search_word.GetValue()
        if word.isalnum(): return
        word_2 = ''.join([x for x in word if
                            x.isalnum() or x == ' ' or x == '-'])
        self.search_word.SetValue(word_2)
        event.Skip()

    def on_word_enter(self, event):
        if not self.nb.GetPageCount():
            self.frame.on_ssw_nt(None)
            return
        word = self.search_word.GetValue()
        word = word.strip()
        if word == '': return
        word,body = new_word_and_body(word)
        if word:
            self.show_page_and_word(pg(body), word)
            self.nb.h_w.current_word = word
            self.nb.SetPageText(self.nb.current_page, word)
        else:
            self.nb.h_w.show_msg('The word was not found!')

    def show_page_and_word(self, page, word=None):
        if self.nb.h_w.current_word:
            # Save current word&page&viewStart
            curr_page = self.nb.h_w.GetParser().GetSource()
            x,y = self.nb.h_w.GetViewStart()
            entry = (self.nb.h_w.current_word,curr_page,(x,y))
            self.nb.h_w.prev_wp_list.append(entry)
            self.prev_btn.Enable(True)
            # Clear forward history
            self.nb.h_w.next_wp_list = []
            self.next_btn.Enable(False)
        if not word: x,y = self.nb.h_w.GetViewStart()
        self.nb.h_w.SetPage(page)
        if not word: self.nb.h_w.Scroll(x, y)
        if word:
            self.search_word.SetValue(word)
            self.nb.h_w.current_word = word


class MyHtmlFrame(wx.Frame):
    def __init__(self, parent, title): #, pos, size)
        wx.Frame.__init__(self, parent, -1, title)#, pos, size)

        menu_bar = wx.MenuBar()

        menu_1 = wx.Menu()
        o_f = menu_1.Append(-1, 'Open File...\tCtrl+O')
        s_a = menu_1.Append(-1, 'Save Page As...\tCtrl+S')
        menu_1.AppendSeparator()
        print_ = menu_1.Append(-1, 'Print...\tCtrl+P')
        preview = menu_1.Append(-1, 'Preview')
        menu_1.AppendSeparator()
        ex = menu_1.Append(-1, 'Exit')
        menu_bar.Append(menu_1, '&File')

        menu_1_2 = wx.Menu()
        nt = menu_1_2.Append(-1, 'New tabsheet\tCtrl+T')
        ct = menu_1_2.Append(-1, 'Close tabsheet\tCtrl+W')
        menu_1_2.AppendSeparator()
        ssw_nt = menu_1_2.Append(-1, 'Show search word in new tabsheet\tAlt+Enter')
        menu_bar.Append(menu_1_2, '&Tabsheets')

        menu_2 = wx.Menu()
        prev_p = menu_2.Append(-1, 'Previous\tCtrl+Left Arrow')
        next_p = menu_2.Append(-1, 'Next\tCtrl+Right Arrow')
        menu_bar.Append(menu_2, '&Page History')

        menu_3 = wx.Menu()
        i_f = menu_3.Append(-1,
                'Increase Font Size\tCtrl++ or Ctrl+Numpad+ or Ctrl+UpArrow')
        d_f = menu_3.Append(-1,
            'Decrease Font Size\tCtrl+-  or Ctrl+Numpad-  or Ctrl+DownArrow')
        n_f = menu_3.Append(-1, 'Normal Font Size\tCtrl+0')
        menu_3.AppendSeparator()
        db_i = menu_3.Append(-1, 'Show Database Info')
        menu_3.AppendSeparator()
        s_s = menu_3.Append(-1, 'Show HTML Source\tCtrl+U')
        menu_bar.Append(menu_3, '&View')

        menu_4 = wx.Menu()
        h_h = menu_4.Append(-1, 'Help')
        h_a = menu_4.Append(-1, 'About...')
        menu_bar.Append(menu_4, '&Help')

        self.SetMenuBar(menu_bar)

        self.Bind(wx.EVT_MENU, self.on_open_file, o_f)
        self.Bind(wx.EVT_MENU, self.on_save_as, s_a)
        self.Bind(wx.EVT_MENU, self.on_print, print_)
        self.Bind(wx.EVT_MENU, self.on_preview, preview)
        self.Bind(wx.EVT_MENU, self.on_exit, ex)
        self.Bind(wx.EVT_MENU, self.on_new_tab, nt)
        self.Bind(wx.EVT_MENU, self.on_close_tab, ct)
        self.Bind(wx.EVT_MENU, self.on_ssw_nt, ssw_nt)
        self.Bind(wx.EVT_MENU, self.on_prev_page, prev_p)
        self.Bind(wx.EVT_MENU, self.on_next_page, next_p)
        self.Bind(wx.EVT_MENU, self.on_incr_font, i_f)
        self.Bind(wx.EVT_MENU, self.on_decr_font, d_f)
        self.Bind(wx.EVT_MENU, self.on_norm_font, n_f)
        self.Bind(wx.EVT_MENU, self.on_db_info, db_i)
        self.Bind(wx.EVT_MENU, self.on_show_source, s_s)
        self.Bind(wx.EVT_MENU, self.on_help_help, h_h)
        self.Bind(wx.EVT_MENU, self.on_help_about, h_a)

        acceltbl = wx.AcceleratorTable([
                            (wx.ACCEL_CTRL,ord('O'),o_f.GetId()),
                            (wx.ACCEL_CTRL,ord('S'),s_a.GetId()),
                            (wx.ACCEL_CTRL,ord('P'),print_.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_ADD,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_UP,i_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_NUMPAD_SUBTRACT,d_f.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_DOWN,d_f.GetId()),
                            (wx.ACCEL_CTRL,ord('0'),n_f.GetId()),
                            (wx.ACCEL_CTRL,ord('U'),s_s.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_LEFT,prev_p.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_LEFT,prev_p.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_RIGHT,next_p.GetId()),
                            (wx.ACCEL_CTRL,wx.WXK_RIGHT,next_p.GetId()),
                            (wx.ACCEL_ALT,wx.WXK_RETURN,ssw_nt.GetId()),
                            ])

        self.SetAcceleratorTable(acceltbl)

        self.Bind(wx.EVT_SIZE, self.on_frame_resize)
        self.Bind(wx.EVT_MOVE, self.on_frame_move)
        self.Bind(wx.EVT_CLOSE, self.on_frame_close)

        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        #self.Bind(wx.EVT_KEY_UP, self.on_key_up)

        self.panel = HtmlPanel(self)

    def on_key_down(self, event):
        event.Skip()

    def on_key_up(self, event):
        event.Skip()

    def  on_frame_close(self, event):
        pos = self.GetPosition()
        size = self.GetSize()
        if pos == (-32000, -32000): # The frame is minimized, ignore pos
            pos = (0,0)
        options_dict['frame_pos'] = pos
        options_dict['frame_size'] = size
        pkl = open(pickle_file_name, 'wb')
        pickle.dump(options_dict, pkl, -1)
        pkl.close()
        event.Skip()

    def  on_frame_resize(self, event):
        event.Skip()

    def  on_frame_move(self, event):
        event.Skip()

    def  on_open_file(self, event):
        self.load_file()

    def  on_open_URL(self, event):
        self.load_url()

    def  on_save_as(self, event):
        self.save_file()

    def  on_print(self, event):
        self.print_()

    def  on_preview(self, event):
        self.preview()

    def  on_exit(self, event):
        self.Close()

    def  on_new_tab(self, event):
        current_page = self.panel.nb.add_html_page()

    def  on_close_tab(self, event):
        self.panel.nb.DeletePage(self.panel.nb.current_page)

    def  on_ol_ut(self, event):
        pass

    def  on_ol_ft(self, event):
        pass

    def  on_ssw_nt(self, event):
        word = self.panel.search_word.GetValue()
        if word == '': return
        current_page = self.panel.nb.add_html_page()
        word,body = new_word_and_body(word)
        if word:
            self.panel.show_page_and_word(pg(body), word)
            self.panel.nb.h_w.current_word = word
            self.panel.nb.SetPageText(current_page, word)
        else:
            self.panel.nb.h_w.show_msg('The word was not found!')

    def  on_prev_page(self, event):
        self.panel.on_prev_page(event)

    def  on_next_page(self, event):
        self.panel.on_next_page(event)

    def  on_incr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(+1)

    def  on_decr_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size(-1)

    def  on_norm_font(self, event):
        self.panel.nb.h_w.incr_decr_font_size()

    def  on_db_info(self, event):
        self.show_db_info()

    def  on_show_source(self, event):
        self.show_source()

    def  on_help_help(self, event):
        self.read_file('NLTK Wordnet Browser Help.html')

    def  on_help_about(self, event):
        wx.MessageBox(help_about)

    def show_db_info(self):
        word = '* Database Info *'
        current_page = self.panel.nb.add_html_page()
        self.panel.nb.SetPageText(current_page,word)
        html = html_header + \
        '''
        <h2>Database information is being gathered!</h2>
        <p>Producing this summary information may,
        depending on your computer, take a minute or two.</p>
        <p>Please be patient! If this operation seems to last too long,
        it might be a good idea to save the resulting page on disk for possible
        later viewings.</p>
        '''
        self.panel.show_page_and_word(html + html_trailer, word)
        wx.Yield()
        all_pos = ['noun', 'verb', 'adj', 'adv']
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
                         
        col_heads = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Total']
        #counts = [[0] * len(col_heads)] * len(display_names)
        counts = [[0 for i in range(len(col_heads))] for j in range(len(display_names))]
        rel_counts = defaultdict(int)
        rel_words = {}
        unique_beginners = defaultdict(list)

        for n_pos,pos in enumerate(all_pos): #all_pos): ['adj', 'adv']):
            html += '<br><br>Starting the summary for POS: %s' % col_heads[n_pos]
            self.panel.show_page_and_word(html + html_trailer, word)
            wx.Yield()
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
                syn_rel = synset.relations()
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
        html += '<br><br>Starting the construction of result tables'
        self.panel.show_page_and_word(html + html_trailer, word)
        wx.Yield()
        html = html_header + hlev(2, 'Word, synset and relation counts by POS')
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
                        + '</tr>'
            html += '<tr><th align="left">' + '%s' % y + '</th>'
            if  x == 'apimw' or x == 'apemw':
                html += ''.join('<td align="right">' + '%6.2f ' % c + '</td>' \
                                                for c in counts[n]) + '</tr>'
            else:
                html += ''.join('<td align="right">' + '%6d ' % c + '</td>' \
                                                for c in counts[n]) + '</tr>'

        # Format the relation counts
        r_counts = [0 for i in range(len(col_heads))]
        for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
            for i in range(len(col_heads)):
                r_counts[i] = 0
            dn = dbname_to_dispname(rk[0]).split('/')
            if dn[0] == '???':
                dn = rk[0] + '(???)'
            else:
                dn = dn[0]
            html += '<tr><th align="left">' + '%s' % ('--- ' + dn) + '</th>'
            for y in rk[1]:
            	r_counts[y[1]] = rel_counts[y]
            r_counts[len(col_heads) - 1] = sum(r_counts)
            html += ''.join('<td align="right">' + '%6d ' % rc + '</td>'
                             for rc in r_counts) + '</tr>'
        html += '</table>'

        html += '<br><br>' + hlev(2, 'Example words for relations, 1 per POS')

        # Format the example words for relations
        html += '''
        <table border="1" cellpadding="1" cellspacing="1"
        summary="">
        <caption></caption>
        <col align="center"><col align="center"><col align="center">
        <col align="center"><col align="center">
        <tr><th>Relation</th><th>Noun</th><th>Verb</th><th>Adjective</th><th>Adverb</th></tr>
        '''

        for rk in groupby(sorted(rel_counts.keys()),key=lambda x:x[0]):
            dn = dbname_to_dispname(rk[0]).split('/')
            if dn[0] == '???':
                dn = rk[0] + '(???)'
            else:
                dn = dn[0]
            #html += '<tr><th align="center">' + '%s' % (dn) + '</th>'
            html += '<tr><th align="center">' + dn + '</th>'
            rel_word_examples = [''] * 4
            for y in rk[1]:
            	rel_word_examples[y[1]] = rel_words[y]
            hlp = ''.join('<td align="center"><a href="?' + x + '">' + x.replace('_', ' ') +
                            '</a></td>' for x in rel_word_examples)
            hlp = hlp.replace('<a href="?"></a>','-')
            html += hlp + '</tr>'
        html += '</table>' + html_trailer

        '''
        display
        for ch in col_heads:
            display '%20.20s' % ch,
        display
        #display ' ' * 16,
        for i in range(4):
            display '%20d' % len(unique_beginners[i]),
        display 'Unique beginners',
        for ch in col_heads:
            display '%20.20s' % ch,
        ub = []
        for i in range(4):
            ub.append(unique_beginners[i])
        for i in range(4):
            ub[i].sort()
        max_count = min(max(len(x) for x in ub), 100)
        for count in range(max_count):
            display ('%5.5d' + ' '* 11) % count,
            for i in range(4):
                if count < len(ub[i]):
                    display ub[i][count],
                else:
                    display ' ' * 19,
            display
        '''
        self.panel.show_page_and_word(html, word)
        return current_page

    def read_file(self, path):
        try:
            if not path.endswith('.htm') and not path.endswith('.html'):
                path += '.html'
            f = open(path)
            page = f.read()
            f.close()
            if path == 'NLTK Wordnet Browser Help.html':
                word = '* Help *'
            else:
                txt = '<title>' + frame_title + ' display of: '
                ind_0 = page.find(txt)
                if ind_0 == -1:
                    err_mess = 'This file is not in NLTK Browser format!'
                    self.panel.nb.h_w.show_msg(err_mess)
                    return
                ind_1 = page.find('of: ') + len('of: ')
                ind_2 = page.find('</title>')
                word = page[ind_1:ind_2]
                page = page[:ind_0] + page[ind_2+len('</title>'):]
            current_page = self.panel.nb.add_html_page()
            self.panel.nb.SetPageText(current_page,word)
            self.panel.show_page_and_word(page, word)
            return current_page
        except:
            excpt = str(sys.exc_info())
            self.panel.nb.h_w.show_msg('Unexpected error; File: ' + \
                                                path + ' ; ' + excpt)

    def load_file(self):
        dlg = wx.FileDialog(self, wildcard = '*.htm*',
                            style=wx.OPEN|wx.CHANGE_DIR)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == '': return
            self.read_file(path)
        dlg.Destroy()

    def save_file(self):
        dlg = wx.FileDialog(self, wildcard='*.html',
                            style=wx.SAVE|wx.CHANGE_DIR|wx.OVERWRITE_PROMPT)
        if dlg.ShowModal():
            path = dlg.GetPath()
            if path == '':
                self.panel.nb.h_w.show_msg('Empty Filename!')
                return
            source = self.panel.nb.h_w.GetParser().GetSource()
            try:
                if not path.endswith('.htm') and not path.endswith('.html'):
                    path += '.html'
                f = open(path, 'w')
                txt = '<title>' + frame_title + ' display of: ' + \
                      self.panel.nb.h_w.current_word  + '</title></head>'
                source = source.replace('</head>', txt)
                f.write(source)
                f.close()
            except:
                excpt = str(sys.exc_info())
                self.panel.nb.h_w.show_msg('Unexpected error; File: ' + \
                                                    path + ' ; ' + excpt)
            dlg.Destroy()

    def load_url(self):
        dlg = wx.TextEntryDialog(self, 'Enter the URL')
        if dlg.ShowModal():
            url = dlg.GetValue()
            self.panel.nb.h_w.LoadPage(url)
        dlg.Destroy()

    def show_source(self):
        import  wx.lib.dialogs
        source = self.panel.nb.h_w.GetParser().GetSource()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, source,
                                             'HTML Source', size=(1000, 800))
        dlg.ShowModal()
        dlg.Destroy()

    def print_(self):
        self.panel.printer.GetPrintData().SetFilename('onnaax ???')
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PrintText(html)

    def preview(self):
        html = self.panel.nb.h_w.GetParser().GetSource()
        self.panel.printer.PreviewText(html)

def initalize_options():
    global options_dict
    if os.path.exists(pickle_file_name):
        pkl = open(pickle_file_name, 'rb')
        options_dict = pickle.load(pkl)
        pkl.close()
    else:
        options_dict = {}
    if 'font_size' not in options_dict:
        options_dict['font_size'] = 11
    if 'frame_pos' not in options_dict:
        options_dict['frame_pos'] = (-1,-1)
    if 'frame_size' not in options_dict:
        options_dict['frame_size'] = (-1,-1)

def adjust_pos_and_size(frame):
    # Try to catch the screen dimensions like this because no better
    # method is known i.e. start maximized, get the dims, adjust if
    # pickled info requires
    max_width,max_height = frame.GetSize()
    x,y = frame.GetPosition()
    # The following assumes that, as it seems, when wxPython frame
    # is created maximized, it is symmetrically oversized the same
    # amount of pixels. In my case (WinXP, wxPython 2.8) x==y==-4
    # and the width and  height are 8 pixels too large. In the
    # frame init it is not possible to give negative values except
    # (-1,-1) which has the special meaning of using the default!
    if x < 0:
        max_width += 2 * x
        x = 0
    if y < 0:
        max_height += 2 * y
        y = 0
    # If no pos_size_info was found pickled, we're OK
    if options_dict['frame_pos'] == (-1,-1):
        return
    # Now let's try to assure we've got sane values
    x,y = options_dict['frame_pos']
    width,height = options_dict['frame_size']
    if x < 0:
        width += x
        x = 0
    if y < 0:
        height += y
        y = 0
    width = min(width, max_width)
    height = min(height, max_height)
    if x + width > max_width:
        x -= x + width - max_width
        if x < 0:
            width += x
            width = min(width, max_width)
            x = 0
    if y + height > max_height:
        y -= y + height - max_height
        if y < 0:
            height += y
            height = min(height, max_height)
            y = 0
    frame.Maximize(False)
    frame.SetSize((width,height))
    frame.SetPosition((x,y))
    frame.Iconize(False)

def demo():
    global explanation
    global options_dict

    app = wx.PySimpleApp()
    initalize_options()
    frm = MyHtmlFrame(None, frame_title) #, -1, -1)
    # Icon handling may not be portable - don't know
    # This succeeds in Windows, so let's make it conditional
    if platform.system() == 'Windows':
        ico = wx.Icon('favicon.ico', wx.BITMAP_TYPE_ICO)
        # ??? tbi = wx.TaskBarIcon()
        # ??? tbi.SetIcon(ico, 'this is the tip, you know')
        frm.SetIcon(ico)
    word,body = new_word_and_body('green')
    frm.panel.nb.SetPageText(0,word)
    frm.panel.nb.h_w.current_word  = word
    frm.panel.search_word.SetValue(word)
    body = explanation + body
    frm.panel.nb.h_w.show_page(pg(body))
    page = frm.panel.nb.h_w.GetParser().GetSource()
    page = frm.panel.nb.GetPage(0).GetParser().GetSource()
    explanation = body
    frm.Show()
    frm.Maximize(True)
    adjust_pos_and_size(frm)
    app.MainLoop()


if __name__ == '__main__':
    demo()
