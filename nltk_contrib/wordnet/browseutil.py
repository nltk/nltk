# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 University of Pennsylvania
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

__version__ = '$Revision: 9 $'
# $Source$

from urllib import quote_plus, unquote_plus
import itertools as it

# The following is only possible starting with Python version 2.5
# and the NLTK download pages says that NLTK requires at least 2.4 so:
# from collections import defaultdict

from nltk import defaultdict
from nltk.wordnet.util import *
from nltk.wordnet.dictionary import *
from nltk.wordnet.morphy import _morphy
from nltk.wordnet.synset import *
from nltk.wordnet.synset import _RELATION_TABLE

__all__ = ['page_word','relations_2', 'new_word_and_body', 'uniq_cntr']

# The following function probably should be a method of the Synset class in synset.py

def relations_2(synsetObj, rel_name=None, word_match=False):
    """
    Return a dict of relations or a list of word match pairs for synsetObj.

    The dictionary keys are the names for the relations found.
    The dictionary items are lists of either synsets or words
    depending on the relation.

    If rel_name is specified, a list of eiher synsets or words for only
    that relation type is returned.

    If word_match is True a list of pairs (source,target) of matching
    word information is returned . Here source and target are tuples
    of form (synset,word_index), where 'word_index' is the 0-based index of
    the word in synset 'synset'
    @param synsetObj: The synset whose relations we are using
    @type synsetObj: synset
    @param rel_name: A relation name we are interested in
    @type rel_name: str
    @param word_match: Tells if we want word-level matching or not
    @type word_match: truth value
    @return: A relation dict or a list of word match pairs for synsetObj.
    @rtype: A dict or list
    """

    # Load the pointers from the Wordnet files if necessary.
    if not hasattr(synsetObj, '_relations') or \
                word_match != synsetObj._word_match_last_used:
        relations = defaultdict(list)
        for (type, offset, pos, indices) in synsetObj._pointerTuples:
            rel = _RELATION_TABLE[type]
            source_ind = int(indices[0:2], 16) - 1
            target_ind = int(indices[2:], 16) - 1
            pos = normalizePOS(pos)
            offset = int(offset)
            synset = getSynset(pos, offset)
            if target_ind >= 0:
                if word_match:
                    source_tuple = (synsetObj,source_ind)
                    target_tuple = (synset,target_ind)
                    relations[rel].append((source_tuple,target_tuple))
                    #relations[rel].append( \
                    #   (synsetObj.words[source_ind],synset[target_ind]))
                else:
                    relations[rel].append(synset[target_ind])
                    #relations[rel].append(synset[target_ind - 1])
            else:
                relations[rel].append(synset)
        synsetObj._relations = dict(relations)
        synsetObj._word_match_last_used = word_match
    if rel_name is not None:
        return synsetObj._relations.get(rel_name, [])
    else:
        return synsetObj._relations


_pos_tuples = [(N,'N','noun'), (V,'V','verb'), (ADJ,'J','adj'), (ADV,'R','adv')]

def _pos_match(pos_tuple):
    for n,x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples:
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

def _dispname_to_dbname(dispname):
    for dbn,dispn in rel_order:
        if dispname in dispn.split('/'):
            return dbn
    return None

def _dbname_to_dispname(dbname):
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
<title>NLTK Wordnet Browser display of: %s</title></head>
<body bgcolor='#F5F5F5' text='#000000'>
'''
html_trailer = '''
</body>
</html>
'''

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

def _bold(txt): return '<b>%s</b>' % txt

def _center(txt): return '<center>%s</center>' % txt

def _hlev(n,txt): return '<h%d>%s</h%d>' % (n,txt,n)

def _italic(txt): return '<i>%s</i>' % txt

def _li(txt): return '<li>%s</li>' % txt

def pg(word, body):
    '''
    Return a HTML page of NLTK Browser format constructed from the word and body

    @param word: The word that the body corresponds to
    @type word: str
    @param body: The HTML body corresponding to the word
    @type body: str
    @return: a HTML page for the word-body combination
    @rtype: str
    '''
    return (html_header % word) + body + html_trailer

def _ul(txt): return '<ul>' + txt + '</ul>'

# abbc = asterisks, breaks, bold, center
def _abbc(txt):
    return _center(_bold('<br>'*10 + '*'*10 + ' ' + txt + ' ' + '*'*10))

full_hyponym_cont_text = \
    _ul(_li(_italic('(has full hyponym continuation)'))) + '\n'

# This counter function is used to guarantee unique counter values
#uniq_cntr = it.count().next

_uniq_cntr = 0

def uniq_cntr():
    global _uniq_cntr
    _uniq_cntr += 1
    return _uniq_cntr

def _get_synset(synset_key):
    pos = _pos_match((None,synset_key[0],None))[2]
    offset = int(synset_key[1:])
    return getSynset(pos, offset)

def _collect_one(word, s_or_w, prev_synset_key):
    '''
    Returns the HTML string for one synset or word

    @param word: the current word
    @type word: str
    @param s_or_w: a tuple containing word information or a synset
    @type s_or_w: tuple or synset
    @param prev_synset_key: key of previous synset
    @type prev_synset_key: str
    @return: The HTML string built for this synset or word
    @rtype: str
    '''
    u_c = uniq_cntr()
    if isinstance(s_or_w, tuple): # It's a word
        form_str,(synset,oppo,forms) = s_or_w
        pos,offset,ind = oppo
        synset = getSynset(pos, offset)
        synset_key = _pos_match((None,None,synset.pos))[1] + str(synset.offset)
        synset_key  += ':' + str(ind) + ',' + prev_synset_key
        oppo = synset.words[ind]
        oppo = oppo.replace('_', ' ')
        typ = 'W'
    else: # It's a synset
        synset = s_or_w
        typ = 'S'
        synset_key = _pos_match((None,None,synset.pos))[1] + str(synset.offset)
        synset_key  += ',' + prev_synset_key
    if synset.pos.startswith('ad'):  descr = synset.pos
    else:                            descr = synset.pos[0]
    s = '<li><a href="' + typ + quote_plus(word + '#' + synset_key + '#' + \
            str(u_c)) + '">' + typ + ':</a>' + ' (' + descr + ') '
    if isinstance(s_or_w, tuple): # It's a word
        s += '<a href="M' + quote_plus(oppo + '#' + str(uniq_cntr())) + \
                        '">' + oppo + '</a> ' + form_str
        for w in forms:
            pos,offset,ind = w
            w = getSynset(pos, offset).words[ind]
            w = w.replace('_', ' ')
            s += '<a href="M' + quote_plus(w + '#' + str(uniq_cntr())) + \
                            '">' + w + '</a>, '
        s = s[:-2] + ']  '
    else: # It's a synset
        for w in synset:
            w = w.replace('_', ' ')
            if w.lower() == word:
                s+= _bold(w) + ', '
            else:
                s += '<a href="M' + quote_plus(w + '#' + str(uniq_cntr())) + \
                                '">' + w + '</a>, '
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

def _collect_all(word, pos):
    s = '<ul>'
    for synset in pos[word]:
        s += _collect_one(word, synset, '')
    return s + '\n</ul>\n'

def _rel_ref(word, synset_keys, rel):
    return '<a href="R' + quote_plus(word + '#' + synset_keys + '#' + \
            rel + '#' + str(uniq_cntr())) + '"><i>' + rel + '</i></a>'

def _anto_or_similar_anto(synset):
    anto = relations_2(synset, rel_name=ANTONYM, word_match=True)
    if anto: return synset
    similar = relations_2(synset, rel_name=SIMILAR)
    for simi in similar:
        anto = relations_2(simi, rel_name=ANTONYM, word_match=True)
        if anto: return simi
    return False

def _synset_relations(word, link_type, synset_keys):
    '''
    Builds the HTML string for the relations of a synset

    @param word: The current word
    @type word: str
    @param link_type: The link type, word or synset
    @type link_type: str
    @param synset_keys: synset keys for this and the previous synset
    @type synset_keys: str
    @return: The HTML for a synset's relations
    @rtype: str
    '''
    sk,prev_sk = synset_keys.split(',')
    synset = _get_synset(sk.split(':')[0])
    rel_keys = relations_2(synset).keys()

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
                  db_name == ANTONYM and _anto_or_similar_anto(synset):
            lst = [' <i>/</i> ' + _rel_ref(word, synset_keys, r)
                   for r in disp_name.split('/')]
            html += ''.join(lst)[10:] # drop the extra ' <i>/</i> '
            html += '\n'
            if db_name in rel_keys: rel_keys.remove(db_name)
    if link_type == 'W':
        html += _rel_ref(word, synset_keys, 'Overview') + '\n'
        html += _rel_ref(word, synset_keys, 'synset') + '\n'
    else:
        for rel in rel_keys:
            html += _rel_ref(word, synset_keys, rel) + '\n'
        if synset.pos == 'verb' and synset.verbFrameStrings:
            html += _rel_ref(word, synset_keys, 'sentence frame') + '\n'
    return html

def _hyponym_ul_structure(word, tree):
    #print 'tree:', tree
    if tree == []: return ''
    if tree == ['...']: return full_hyponym_cont_text
    head = tree[0]
    tail = tree[1:]
    #print 'head, tail:', head, tail
    htm = _collect_one(word, head[0], '') + '\n'
    if isinstance(head, list) and len(head) > 1:
        #print 'head[1:]:', head[1:]
        htm += '<ul>'
        htm += _hyponym_ul_structure(word, head[1:])
        htm += '\n</ul>'
    htm += _hyponym_ul_structure(word, tail)
    return htm

def _hypernym_ul_structure(word, tree):
    htm = '<ul>\n' + _collect_one(word, tree[0], '') + '\n'
    if len(tree) > 1:
        tree = tree[1:]
        for t in tree: htm += _hypernym_ul_structure(word, t)
        #htm += '\n</ul>\n'
    return htm  + '\n</ul>\n'

def _word_ul_structure(word, synset, rel_name, synset_keys):
    synset_key,prev_synset_key = synset_keys.split(',')
    rel_name = _dispname_to_dbname(rel_name)
    if rel_name == ANTONYM:
        rel_form = ' [Opposed to: '
    else:
        rel_form = ' [Related to: '
    s = ''
    rel = relations_2(synset, rel_name=rel_name, word_match=True)
    #print 'rel:', rel
    if rel:
        hlp = [((s1.pos,s1.offset,i1),(s0.pos,s0.offset,i0))
                  for ((s0,i0),(s1,i1)) in rel]
        if prev_synset_key:
            sk,prev_sk = synset_keys.split(',')
            sk0,sk1 = sk.split(':')
            syns = _get_synset(sk0)
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
            s += _collect_one(word, (rel_form,(s1,h[0],forms)), synset_key)
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
            s += _collect_one(word, (rel_form,(s1,h,f)), synset_key)
    elif rel_name == ANTONYM:
        similar = relations_2(synset, rel_name=SIMILAR)
        for simi in similar:
            anto = relations_2(simi, rel_name=ANTONYM, word_match=True)
            if anto:
                for a in anto:
                    ((s0,i0),(s1,i1)) = a
                    form = (s0.pos,s0.offset,i0)
                    oppo = (s1.pos,s1.offset,i1)
                    s += _collect_one(word, \
                                (' [Indirect via ',(s1,oppo,[form])), synset_key)
    return s

def _relation_section(rel_name, word, synset_keys):
    synset_key,prev_synset_key = synset_keys.split(',')
    synset = _get_synset(synset_key.split(':')[0])
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
            return '<ul>\n' + _li(_bold(_italic(msg))) + \
                              _hyponym_ul_structure(word, tree[1:]) + '\n</ul>'
        else:
        '''
        html = '\n' + _hyponym_ul_structure(word, tree[1:]) + '\n'
        for x in synset[INSTANCE_HYPONYM]:
            html += _collect_one(word, x, '')
        return _ul(html + '\n')
    elif rel_name == 'inherited hypernym':
        tree = synset.tree(HYPERNYM)
        #print tree
        return _hypernym_ul_structure(word, tree[1:][0]) # + '\n</ul>'
    elif rel_name == 'sister term':
        s = ''
        for x in synset[HYPERNYM]:
            s += _collect_one(word, x, '')
            s += '<ul>'
            for y in x[HYPONYM]:
                s += _collect_one(word, y, '')
            s += '\n</ul>'
        return _ul(s + '\n')
    elif rel_name == 'sentence frame':
        verb_frame_strings = [(VERB_FRAME_STRINGS[i] % _bold(word)) \
                                for i in synset.verbFrames]
        s = '\n'.join(['<li>' + vfs + '</li>' for vfs
                                          in verb_frame_strings])
        return _ul(s + '\n')
    elif rel_name == 'Overview':
        ind = int(synset_key.split(':')[1])
        w,b = _w_b(synset.words[ind], True)
        if not w: return ''
        return _ul(b + '\n')
    elif rel_name == 'synset':
        s = _collect_one(word, synset, '')
        return _ul(s + '\n')
    elif rel_name == 'domain term region':
        rel = _dispname_to_dbname(rel_name)
        s = ''
        word_collection = []
        for x in synset[rel]:
            if isinstance(x, basestring):
                word_collection.append(x)
            else:
                s += _collect_one(word, x, '')

        for wrd in word_collection:
            w = _pos_match((None,None,synset.pos))[0][wrd]
            oppo = None
            for syns in w:
                for wlr in relations_2(syns, CLASSIF_REGIONAL,True):
                    if not isinstance(wlr, tuple): continue
                    syn,i = wlr[1]
                    syns,j = wlr[0]
                    if syn == synset and syns.words[j] == wrd:
                        form = (syn.pos,syn.offset,i)
                        oppo = (syns.pos,syns.offset,j)
                        break
                if oppo: break
            if oppo:
                s += _collect_one(word, \
                                (' [Related to: ',(synset,oppo,[form])), synset_key)
        return _ul(s + '\n')
    else:
        rel = _dispname_to_dbname(rel_name)
        if rel == ANTONYM or \
                isinstance(relations_2(synset)[rel][0], basestring): # word level
            s = _word_ul_structure(word, synset, rel_name, synset_keys)
            return _ul(s + '\n')
        else:
            s = ''
            for x in synset[rel]:
                s += _collect_one(word, x, '')
            if rel == HYPONYM:
                for x in synset[INSTANCE_HYPONYM]:
                    s += _collect_one(word, x, '')
            return _ul(s + '\n')

def _w_b(word, overview):
    pos_forms = defaultdict(list)
    words = word.split(',')
    words = [w.strip() for w in words]
    for pos_str in ['noun', 'verb', 'adj', 'adv']:
        for w in words:
            '''
            if overview:
                pos_forms[pos_str].append(w)
            else:
                for form in _morphy(w, pos=pos_str):
                    if form not in pos_forms[pos_str]:
                        pos_forms[pos_str].append(form)
            '''
            for form in _morphy(w, pos=pos_str):
                if form not in pos_forms[pos_str]:
                    pos_forms[pos_str].append(form)
    body = ''
    for pos,pos_str,name in \
        ((N,'noun','Noun'), (V,'verb','Verb'),
         (ADJ,'adj','Adjective'), (ADV,'adv','Adverb')):
        if pos_str in pos_forms:
            if not overview:
                body += _hlev(3, name) + '\n'
            for w in pos_forms[pos_str]:
                # Not all words of exc files are in the database, so:
                try:
                    body += _collect_all(w, pos)
                except KeyError:
                    pass
    if not body:
        word = None
    return word,body

def new_word_and_body(word):
    '''
    Return a 2-tuple of a new word and the HTML body consisting of all the
    synsets for all the POS that the word was found in

    @param word: The word for which the HTML body is to be constructed
    @type word: str
    @return: The tuple (word,body)
    @rtype: Tuple (str,str)
    '''
    word = word.lower().replace('_', ' ')
    return _w_b(word, False)

def _ul_section_removed(page, index):
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

def page_word(page, word, href):
    '''
    Returns a tuple of the HTML page built and the new current word

    @param page: The currently active HTML page
    @type page: str
    @param word: The currently active word
    @type word: str
    @param href: The hypertext reference to be solved
    @type href: str
    @return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    @rtype: A tuple (str,str)
    '''
    link_type = href[0]
    q_link = href[1:]
    u_link = unquote_plus(q_link)
    #print link_type, q_link, u_link
    if link_type == 'M' or link_type == 'N': # Search for this new word
        word, u_c = u_link.split('#')
        word,body = new_word_and_body(word)
        if word:
            return pg(word, body), word
        else:
            return pg(word, 'The word s%s" was not found!' % word), word
    elif link_type == 'R': # Relation links
        # A relation link looks like this:
        # word#synset_keys#relation_name#uniq_cntr
        #print 'u_link:', u_link
        word,synset_keys,rel_name,u_c = u_link.split('#')
        '''
        word = word.strip()
        synset_keys = synset_keys.strip()
        rel_name = rel_name.strip()
        u_c = u_c.strip()
        '''
        #print 'word,synset_keys,rel_name,u_c:',word,synset_keys,rel_name,u_c
        ind = page.find(q_link) + len(q_link) + 2
        #print page[ind:]
        # If the link text is in bold, the user wants to
        # close the section beneath the link
        if page[ind:ind+3] == '<b>':
            page = _ul_section_removed(page, ind)
            page = page[:ind] + '<i>' + rel_name + \
                    '</i>' + page[ind + len(rel_name) + 14:]
            return page, word
        else:
            # First check if another link is bold on the same line
            # and if it is, then remove boldness & close the section below
            end = page.find('\n', ind)
            start = page.rfind('\n', 0, ind)
            #print 'page[start:end]:', page[start:end]
            start = page.find('<b>', start, end)
            #print 'start:', start
            if start != -1:
                page = _ul_section_removed(page, ind)
                end = page.find('</b>', start, end)
                page = page[:start] + page[start+3:end] + page[end+4:]

            # Make this selection bold on page
            #
            if rel_name in implemented_rel_names:
                ind = page.find(q_link) + len(q_link) + 2
                ind_2 = ind + len(rel_name) + 7
                #print 'page[:ind]:', page[:ind]
                page = page[:ind] + _bold(page[ind:ind_2]) + \
                       page[ind_2:]
                # find the start of the next line
                ind = page.find('\n', ind) + 1
                section = \
                    _relation_section(rel_name, word, synset_keys)
                #print 'page[:ind]:', page[:ind]
                page = page[:ind] + section + page[ind:]
                return page, word
            else:
                return None, None
    else:
        # A word link looks like this:
        # Wword#synset_key,prev_synset_key#link_counter
        # A synset link looks like this:
        # Sword#synset_key,prev_synset_key#link_counter
        l_t = link_type + ':'
        #print 'l_t, u_link:', l_t, u_link
        word,syns_keys,link_counter = u_link.split('#')
        #print 'word,syns_keys,link_counter:',word,syns_keys,link_counter
        #syns_key,prev_syns_key = syns_keys.split(',')
        ind = page.find(q_link) + len(q_link) + 2
        #print page[ind:]
        # If the link text is in bold, the user wants to
        # close the section beneath the link
        if page[ind:ind+3] == '<b>':
            page = _ul_section_removed(page, ind)
            #page = page[:ind] + 'S:' + page[ind + 9:]
            page = page[:ind] + l_t + page[ind + 9:]
            return page, word
        else: # The user wants to see the relation names
            # Make this link text bold on page
            #page = page[:ind] + _bold('S:') + page[ind + 2:]
            page = page[:ind] + _bold(l_t) + page[ind + 2:]
            # Insert the relation names
            ind = page.find('\n', ind) + 1
            # First remove the full_hyponym_cont_text if found here
            #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
            if page[ind+5:].startswith(full_hyponym_cont_text):
                page = page[0:ind+5] + \
                        page[ind+5+len(full_hyponym_cont_text):]
            #print page[:ind+5] + '>>>>><<<<<' + page[ind+5:]
            s_r = _synset_relations(word, link_type, syns_keys)
            s_r = s_r.split('\n')[:-1]
            s_r = [_li(sr) for sr in s_r]
            s_r = _ul('\n' + '\n'.join(s_r) + '\n') + '\n'
            page = page[:ind] + s_r + page[ind:]
            return page, word

