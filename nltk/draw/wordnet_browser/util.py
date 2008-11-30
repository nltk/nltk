# Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
#
# Copyright (C) 2007 - 2008 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


from urllib import quote_plus, unquote_plus
import itertools as it
import cPickle
import base64

from nltk import defaultdict
from nltk.corpus import wordnet
from nltk.internals import deprecated

__all__ = ['get_static_index_page',
           'get_static_page_by_path',
           'page_from_word',
           'page_from_href']

"""
WordNet Browser Utilities.

This provides a backend to both wxbrowse and browserver.py.
"""


#
# TODO: The following issues exist with this module, and should
# ideally be fixed.  These line numbers have changed since these items
# where recorded.
#
# All through: SHOULD add docstrings.
# Line 29: Some or all of relations_2 SHOULD be moved to synst.py
# Line 343: MAY re-write expression so that it's more readable.
# Line 395: MAY rewrite this and previous statment.
#           to avoid creating serperflous "<i>/</i>"
# Line 454: MAY replace lambda expression with 'first'.
# Line 695: MAY rewrite expression to build string so that it is more readable.
#


################################################################################
#
# Main logic for wordnet browser.
#

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
            synset = dictionary.synset(pos, offset)
            if target_ind >= 0:
                if word_match:
                    source_tuple = (synsetObj,source_ind)
                    target_tuple = (synset,target_ind)
                    relations[rel].append((source_tuple,target_tuple))
                else:
                    relations[rel].append(synset[target_ind])
            else:
                relations[rel].append(synset)
        synsetObj._relations = dict(relations)
        synsetObj._word_match_last_used = word_match
    if rel_name is not None:
        return synsetObj._relations.get(rel_name, [])
    else:
        return synsetObj._relations

_pos_tuples = [
    (wordnet.NOUN,'N','noun'), 
    (wordnet.VERB,'V','verb'),
    (wordnet.ADJ,'J','adj'), 
    (wordnet.ADV,'R','adv')]

def _pos_match(pos_tuple):
    """
    This function returns the complete pos tuple for the partial pos
    tuple given to it.  It attempts to match it against the first
    non-null component of the given pos tuple.
    """
    if pos_tuple[0] == 's':
        pos_tuple = ('a', pos_tuple[1], pos_tuple[2])
    for n,x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples:
        if pt[n] == pos_tuple[n]: return pt
    return None

# This structure is deprecated.

#implemented_rel_names = \
#    ['antonym',
#     'attribute',
#     'cause',
#     'derivationally related form',
#     'direct hypernym',
#     'direct hyponym',
#     'direct troponym',
#     'domain category',
#     'domain region',
#     'domain term category',
#     'domain term region',
#     'domain term usage',
#     'domain usage',
#     'entailment',
#     'full hyponym',
#     'full troponym',
#     'has instance',
#     'inherited hypernym',
#     'instance',
#     'member holonym',
#     'member meronym',
#     'Overview',
#     'part holonym',
#     'part meronym',
#     'participle',
#     'pertainym',
#     'phrasal verb',
#     'see also',
#     'sentence frame',
#     'similar to',
#     'sister term',
#     'substance holonym',
#     'substance meronym',
#     'synset',
#     'verb group'
#    ]

# This is deprecated.

# Relation names in the order they will displayed. The first item of a tuple
# is the internal i.e. DB name. The second item is the display name or if it
# contains parts separated by slashes, the parts are displayed as separate
# links.
#rel_order = \
#    [(HYPONYM,'direct hyponym/full hyponym'),
#     (HYPONYM,'direct troponym/full troponym'),
#     (CLASS_REGIONAL,'domain term region'),
#     (PART_HOLONYM,PART_MERONYM),
#     (ATTRIBUTE,ATTRIBUTE),
#     (SUBSTANCE_HOLONYM,SUBSTANCE_MERONYM),
#     (SUBSTANCE_MERONYM,SUBSTANCE_HOLONYM),
#     (MEMBER_MERONYM,MEMBER_HOLONYM),
#     (MEMBER_HOLONYM,MEMBER_MERONYM),
#     (VERB_GROUP,VERB_GROUP),
#     (CLASSIF_CATEGORY, CLASSIF_CATEGORY),
#     (INSTANCE_HYPONYM, 'has instance'),
#     (CLASS_CATEGORY,'domain term category'),
#     (CLASS_USAGE,'domain term usage'),
#     (HYPERNYM,'direct hypernym/inherited hypernym/sister term'),
#     (CLASSIF_REGIONAL, CLASSIF_REGIONAL),
#     (CLASSIF_USAGE,'domain usage'),
#     (PART_MERONYM,PART_HOLONYM),
#     (INSTANCE_HYPERNYM, 'instance'),
#     (CAUSE,CAUSE),
#     (ALSO_SEE,'see also'),
#     (ALSO_SEE,'phrasal verb'),
#     (SIMILAR,'similar to'),
#     (ENTAILMENT,ENTAILMENT),
#     (PARTICIPLE_OF, 'participle'),
#     (ANTONYM, 'antonym'),
#     (FRAMES,'derivationally related form'),
#     #sentence frame
#     (PERTAINYM,PERTAINYM)
#     ]

HYPONYM = 0
HYPERNYM = 1
CLASS_REGIONAL = 2
PART_HOLONYM = 3
PART_MERONYM = 4
ATTRIBUTE = 5
SUBSTANCE_HOLONYM = 6
SUBSTANCE_MERONYM = 7
MEMBER_HOLONYM = 8
MEMBER_MERONYM = 9
VERB_GROUP = 10
INSTANCE_HYPONYM = 12
INSTANCE_HYPERNYM = 13
CLAUSE = 14
ALSO_SEE = 15
SIMILAR = 16
ENTAILMENT = 17
ANTONYM = 18
FRAMES = 19
PERTAINYM = 20

CLASS_CATEGORY = 21
CLASS_USAGE = 22
CLASS_REGIONAL = 23
CLASS_USAGE = 24
CLASS_CATEGORY = 11

DERIVATIONALLY_RELATED_FORM = 25


def get_relations_data(synset): 
    """
    Get synset relations data for a synset.  Note that this doesn't
    yet support things such as full hyponym vs direct hyponym.
    """
    if synset.pos == wordnet.NOUN:
        return ((HYPONYM, ['Hyponyms'], synset.hyponyms()),
                (INSTANCE_HYPONYM , ['Instance hyponyms'], synset.instance_hyponyms()),
                (HYPERNYM, ['Direct hypernyms', 'Inherited hypernyms', 'Sister terms'], 
                   synset.hypernyms()),
                (INSTANCE_HYPERNYM , ['Instance hypernyms'], synset.instance_hypernyms()),
#            (CLASS_REGIONAL, ['domain term region'], ),
                (PART_HOLONYM, ['Part holonyms'], synset.part_holonyms()),
                (PART_MERONYM, ['Part meronyms'], synset.part_meronyms()),
                (SUBSTANCE_HOLONYM, ['Substance holonyms'], synset.substance_holonyms()),
                (SUBSTANCE_MERONYM, ['Substance meronyms'], synset.substance_meronyms()),
                (MEMBER_HOLONYM, ['Member holonyms'], synset.member_holonyms()),
                (MEMBER_MERONYM, ['Member meronyms'], synset.member_meronyms()),
                (ATTRIBUTE, ['Attributes'], synset.attributes()),
                (ANTONYM, ["antonyms"], synset.antonyms()),
                (DERIVATIONALLY_RELATED_FORM, ["Derivationally related form"], 
                   synset.derivationally_related_forms()))
#            (VERB_GROUP , ),
#            (CLAUSE , ),
#            (ALSO_SEE , ),
#            (SIMILAR , ),
#            (ENTAILMENT , ),
#            (FRAMES , ),
#            (PERTAINYM , ),
#            (CLASS_CATEGORY , ),
#            (CLASS_USAGE , ),
#            (CLASS_REGIONAL , ),
#            (CLASS_USAGE , ),
#            (CLASS_CATEGORY , ),
    else:
        return []

def hyponym_or_troponym(synset):
    if synset.pos == wordnet.VERB:
        return "Troponyms"
    else:
        return "Hyponyms"

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
<li>Clicking <u>S:</u> opens a section showing the relations for that synset.
</li>
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
    Return a HTML page of NLTK Browser format constructed from the
    word and body

    @param word: The word that the body corresponds to
    @type word: str
    @param body: The HTML body corresponding to the word
    @type body: str
    @return: a HTML page for the word-body combination
    @rtype: str
    '''
    return (html_header % word) + body + html_trailer

def _ul(txt): return '<ul>' + txt + '</ul>'

def _abbc(txt):
    """
    abbc = asterisks, breaks, bold, center
    """
    return _center(_bold('<br>'*10 + '*'*10 + ' ' + txt + ' ' + '*'*10))

full_hyponym_cont_text = \
    _ul(_li(_italic('(has full hyponym continuation)'))) + '\n'


_uniq_cntr = 0

@deprecated("unique counters arn't used anymore")
def uniq_cntr():
    """
    Return a unique counter, a state is kept to ensure that the same
    counter is not provided multiple times.

    @return: A unique integer for this module instance.
    @rtype: int
    """
    global _uniq_cntr
    _uniq_cntr += 1
    return _uniq_cntr

def _get_synset(synset_key):
    """
    The synset key is the unique name of the synset, this can be
    retrived via synset.name
    """
    return wordnet.synset(synset_key)

def _collect_one_synset(word, synset, synset_relations):
    '''
    Returns the HTML string for one synset or word

    @param word: the current word
    @type word: str
    @param synset: a synset
    @type synset: synset
    @param synset_relations: information about which synset relations
    to display.
    @type synset_relations: dict(synset_key, set(relation_id))
    @return: The HTML string built for this synset
    @rtype: str
    '''
    u_c = uniq_cntr()
    if isinstance(synset, tuple): # It's a word
        raise NotImplementedError("word not supported by _collect_one_synset")
#        form_str,(synset,oppo,forms) = s_or_w
#        pos,offset,ind = oppo
#        synset = dictionary.synset(pos, offset)
#        synset_key = _pos_match((None,None,synset.pos))[1] + str(synset.offset)
#        synset_key  += ':' + str(ind) + ',' + prev_synset_key
#        oppo = synset.words[ind]
#        oppo = oppo.replace('_', ' ')
#        typ = 'W'

    typ = 'S'
    pos_tuple = _pos_match((synset.pos, None, None))
    assert pos_tuple != None, "pos_tuple is null: synset.pos: %s" % synset.pos
    descr = pos_tuple[2]
    new_synset_relations = synset_relations.copy()
    new_synset_relations[synset.name] = set()
    ref = Reference(word, new_synset_relations)
    synset_label = typ + ";"
    if synset.name in synset_relations.keys():
        synset_label = _bold(synset_label)
    s = '<li>%s (%s) ' % (make_lookup_link(ref, synset_label), descr) 
#    if isinstance(s_o%r_w, tuple): # It's a word
#        s += '<a href="M' + quote_plus(oppo + '#' + str(uniq_cntr())) + \
#                        '">' + oppo + '</a> ' + form_str
#        for w in forms:
#            pos,offset,ind = w
#            w = dictionary.synset(pos, offset).words[ind]
#            w = w.replace('_', ' ')
#            s += '<a href="M' + quote_plus(w + '#' + str(uniq_cntr())) + \
#                            '">' + w + '</a>, '
#        s = s[:-2] + ']  '
#    else: # It's a synset
    def format_lemma(w):
        w = w.replace('_', '1 ')
        if w.lower() == word:
            return _bold(w)
        else:
            ref = Reference(w)
            return make_lookup_link(ref, w)

    s += ', '.join([format_lemma(l.name) for l in synset.lemmas])

    gl = " (%s) <i>%s</i> " % \
        (synset.definition, 
         "; ".join(["\"%s\"" % e for e in synset.examples]))
    return s + gl + _synset_relations(word, synset, synset_relations) + '</li>\n'

def _collect_all_synsets(word, pos, synset_relations=dict()):
    """
    Return a HTML unordered list of synsets for the given word and
    part of speach.
    """
    return '<ul>%s\n</ul>\n' % \
        ''.join((_collect_one_synset(word, synset, synset_relations) 
                 for synset 
                 in wordnet.synsets(word, pos)))

@deprecated("Use make_lookup_link")
def _rel_ref(word, synset_keys, rel):
    return '<a href="R%s"><i>%s</i></a>' % \
        (quote_plus('#'.join((word, synset_keys, rel, str(uniq_cntr())))),
         rel)

def _anto_or_similar_anto(synset):
    anto = relations_2(synset, rel_name=ANTONYM, word_match=True)
    if anto: return synset
    similar = relations_2(synset, rel_name=SIMILAR)
    for simi in similar:
        anto = relations_2(simi, rel_name=ANTONYM, word_match=True)
        if anto: return simi
    return False

def _synset_relations(word, synset, synset_relations):
    '''
    Builds the HTML string for the relations of a synset

    @param word: The current word
    @type word: str
    @param synset: The synset for which we're building the relations.
    @type synset: Synset
    @param synset_relations: synset keys and relation types for which to display relations.
    @type synset_relations: dict(synset_key, set(relation_type))
    @return: The HTML for a synset's relations
    @rtype: str
    '''

    if not synset.name in synset_relations.keys():
        return ""
    
    def make_synset_html((db_name, disp_names, rels)):
        return ' / '.join("<i>%s</i>" % r for r in disp_names) + '\n'
#            (_rel_ref(word, synset_keys, r) for r in disp_names)) \
#            + '\n'

    html = '<ul>' + \
        '\n'.join(("<li>%s</li>" % make_synset_html(x) for x 
                   in get_relations_data(synset)
                   if x[2] != [])) + \
        '</ul>'


# This code will be deleted completely later, it remains here but
# commented out so that it is easy to see how this program used to
# work.

#    if link_type == 'W':
#        rel_names = [(ANTONYM, 'antonym'),
#                     (FRAMES,'derivationally related form')]
#    else:

#    rel_names = rel_order
#    for rel in rel_names:
#        db_name,disp_name = rel
#        if db_name == ALSO_SEE:
#            if synset.pos == 'verb' and disp_name != 'phrasal verb' or \
#               synset.pos != 'verb' and disp_name == 'phrasal verb':
#                continue
#        if db_name == HYPONYM:
#            if synset.pos == 'verb':
#                if disp_name.find('tropo') == -1:
#                    continue
#            else:
#                if disp_name.find('hypo') == -1:
#                    continue
#        if synset[db_name] or \
#                  db_name == ANTONYM and _anto_or_similar_anto(synset):
#            lst = [' <i>/</i> ' + _rel_ref(word, synset_keys, r)
#                   for r in disp_name.split('/')]
#            html += ''.join(lst)[10:] # drop the extra ' <i>/</i> '
#            html += '\n'
#            if db_name in rel_keys: rel_keys.remove(db_name)
#    if link_type == 'W':
#        html += _rel_ref(word, synset_keys, 'Overview') + '\n'
#        html += _rel_ref(word, synset_keys, 'synset') + '\n'
#    else:
#    for rel in rel_keys:
#        html += _rel_ref(word, synset_keys, rel) + '\n'
#    if synset.pos == 'verb' and synset.verbFrameStrings:
#        html += _rel_ref(word, synset_keys, 'sentence frame') + '\n'
    return html

def _hyponym_ul_structure(word, tree):
    #print 'tree:', tree
    if tree == []: return ''
    if tree == ['...']: return full_hyponym_cont_text
    head = tree[0]
    tail = tree[1:]
    htm = _collect_one(word, head[0], '') + '\n'
    if isinstance(head, list) and len(head) > 1:
        htm += '<ul>'
        htm += _hyponym_ul_structure(word, head[1:])
        htm += '\n</ul>'
    htm += _hyponym_ul_structure(word, tail)
    return htm

def _hypernym_ul_structure(word, tree):
    htm = '<ul>\n' + _collect_one(word, tree[0], '') + '\n'
    if len(tree) > 1:
        htm += ''.join((_hypernym_ul_structure(word, t) for t in tree[1:]))
    return htm + '\n</ul>\n'

def _word_ul_structure(word, synset, rel_name, synset_keys):
    synset_key,prev_synset_key = synset_keys.split(',')
    rel_name = _dispname_to_dbname(rel_name)
    if rel_name == ANTONYM:
        rel_form = ' [Opposed to: '
    else:
        rel_form = ' [Related to: '
    s = ''
    rel = relations_2(synset, rel_name=rel_name, word_match=True)
    if rel:
        hlp = [((s1.pos,s1.offset,i1),(s0.pos,s0.offset,i0))
                  for ((s0,i0),(s1,i1)) in rel]
        if prev_synset_key:
            sk,prev_sk = synset_keys.split(',')
            sk0,sk1 = sk.split(':')
            syns = _get_synset(sk0)
            ind = int(sk1)
            hlp = [((s1.pos,s1.offset,i1),(s0.pos,s0.offset,i0))
                      for ((s0,i0),(s1,i1))
                      in rel
                      if (s0.pos == syns.pos) 
                         and (s0.offset == syns.offset)
                         and (i0 == ind)]
        hlp = it.groupby(hlp,key=lambda x:x[0])
        hlp_2 = []
        for h in hlp:
            forms = []
            for h2 in h[1]:
                forms.append(h2[1])
            forms.sort()
            hlp_2 = [(h[0],forms)] + hlp_2
        for h,f in hlp_2:
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
            depth = synset.min_depth()
            if depth <= 2: depth = 1
            elif depth == 3: depth = 2
        else: depth = -1
        tree = synset.tree(HYPONYM, depth, cut_mark='...')
        html = '\n' + _hyponym_ul_structure(word, tree[1:]) + '\n'
        html += ''.join((_collect_one(word, x, '') 
                         for x 
                         in synset[INSTANCE_HYPONYM]))
        return _ul(html + '\n')
    elif rel_name == 'inherited hypernym':
        tree = synset.tree(HYPERNYM)
        return _hypernym_ul_structure(word, tree[1:][0]) # + '\n</ul>'
    elif rel_name == 'sister term':
        s = ''
        for x in synset[HYPERNYM]:
            s += _collect_one(word, x, '')
            s += '<ul>'
            s += ''.join((_collect_one(word, y, '') for y in x[HYPONYM]))
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
                    if not isinstance(wlr, tuple):
                        continue
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
        # word level
        if rel == ANTONYM or \
                isinstance(relations_2(synset)[rel][0], basestring): 
            s = _word_ul_structure(word, synset, rel_name, synset_keys)
            return _ul(s + '\n')
        else:
            s = ''.join((_collect_one(word, x, '') for x in synset[rel]))
            if rel == HYPONYM:
                s += ''.join((_collect_one(word, x, '') 
                              for x 
                              in synset[INSTANCE_HYPONYM]))
            return _ul(s + '\n')

@deprecated("Use page_from_word")
def _w_b(word, overview):
    pos_forms = defaultdict(list)
    words = word.split(',')
    words = [w for w in [w.strip().lower().replace(' ', '_') 
                         for w in words]
             if w != ""]
    if len(words) == 0:
        # No words were found.
        return "", "Please specify a word to search for."
    
    # This looks up multiple words at once.  This is probably not
    # necessary and may lead to problems.
    for pos in [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]:
        form = wordnet.morphy(w, pos)
        if form and form not in pos_forms[pos]:
            pos_forms[pos].append(form)
    body = ''
    for pos,pos_str,name in _pos_tuples:
        if pos in pos_forms:
            if not overview:
                body += _hlev(3, name) + '\n'
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    body += _collect_all_synsets(w, pos)
                except KeyError:
                    pass
    if not body:
        body = "The word or words '%s' where not found in the dictonary." % word
    return word,body

@deprecated("Use page_from_word")
def new_word_and_body(word):
    '''
    Return a 2-tuple of a new word and the HTML body consisting of all the
    synsets for all the POS that the word was found in

    @param word: The word for which the HTML body is to be constructed
    @type word: str
    @return: The tuple (word,body)
    @rtype: Tuple (str,str)
    '''
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


class Reference(object):
    """
    A reference to a page that may be generated by page_word
    """

    def __init__(self, word, synset_relations=dict()):
        """
        Build a reference to a new page.
        
        word is the word or words (seperated by commas) for which to
        search for synsets of

        synset_relations is a dictionary of synset keys to sets of
        synset relation identifaiers to unfold a list of synset
        relations for.
        """
        self.word = word
        self.synset_relations = synset_relations

    def encode(self):
        """
        Encode this reference into a string to be used in a URL.
        """
        # This uses a tuple rather than an object since the python
        # pickle representation is much smaller and there is no need
        # to represent the complete object.
        string = cPickle.dumps((self.word, self.synset_relations), -1)
        return base64.urlsafe_b64encode(string)

def decode_reference(string):
    """
    Decode a reference encoded with Reference.encode
    """
    string = base64.urlsafe_b64decode(string)
    word, synset_relations = cPickle.loads(string)
    return Reference(word, synset_relations)

def make_lookup_link(ref, label):
    return '<a href="lookup_%s">%s</a>' % (ref.encode(), label)


def page_from_word(word):
    """
    Return a HTML page for the given word.

    @param word: The currently active word
    @type word: str
    @return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    @rtype: A tuple (str,str)
    """
    return page_from_reference(Reference(word))

def page_from_href(href):
    '''
    Returns a tuple of the HTML page built and the new current word

    @param href: The hypertext reference to be solved
    @type href: str
    @return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    @rtype: A tuple (str,str)
    '''
    return page_from_reference(decode_reference(href))

def page_from_reference(href):
    '''
    Returns a tuple of the HTML page built and the new current word

    @param href: The hypertext reference to be solved
    @type href: str
    @return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    @rtype: A tuple (str,str)
    '''
    word = href.word
    pos_forms = defaultdict(list)
    words = word.split(',')
    words = [w for w in [w.strip().lower().replace(' ', '_') 
                         for w in words]
             if w != ""]
    if len(words) == 0:
        # No words were found.
        return "", "Please specify a word to search for."
    
    # This looks up multiple words at once.  This is probably not
    # necessary and may lead to problems.
    for pos in [wordnet.NOUN, wordnet.VERB, wordnet.ADJ, wordnet.ADV]:
        form = wordnet.morphy(w, pos)
        if form and form not in pos_forms[pos]:
            pos_forms[pos].append(form)
    body = ''
    for pos,pos_str,name in _pos_tuples:
        if pos in pos_forms:
            body += _hlev(3, name) + '\n'
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    body += _collect_all_synsets(w, pos, href.synset_relations)
                except KeyError:
                    pass
    if not body:
        body = "The word or words '%s' where not found in the dictonary." % word
    return body, word
    
#    link_type = href[0]
#    q_link = href[1:]
#    u_link = unquote_plus(q_link)i
#
#    if link_type == 'M' or link_type == 'N': # Search for this new word
#        word, u_c = u_link.split('#')
#        word,body = new_word_and_body(word)
#        return pg(word, body), word
#
#    elif link_type == 'R': # Relation links
#        # A relation link looks like this:
#        # word#synset_keys#relation_name#uniq_cntr
#        word,synset_keys,rel_name,u_c = u_link.split('#')
#        ind = page.find(q_link) + len(q_link) + 2
#        # If the link text is in bold, the user wants to
#        # close the section beneath the link
#        if page[ind:ind+3] == '<b>':
#            page = _ul_section_removed(page, ind)
#            page = page[:ind] + '<i>' + rel_name + \
#                    '</i>' + page[ind + len(rel_name) + 14:]
#            return page, word
#        else:
#            # First check if another link is bold on the same line
#            # and if it is, then remove boldness & close the section below
#            end = page.find('\n', ind)
#            start = page.rfind('\n', 0, ind)
#            start = page.find('<b>', start, end)
#            if start != -1:
#                page = _ul_section_removed(page, ind)
#                end = page.find('</b>', start, end)
#                page = page[:start] + page[start+3:end] + page[end+4:]
#
#            # Make this selection bold on page
#            #
#            if rel_name in implemented_rel_names:
#                ind = page.find(q_link) + len(q_link) + 2
#                ind_2 = ind + len(rel_name) + 7
#                page = page[:ind] + _bold(page[ind:ind_2]) + \
#                       page[ind_2:]
#                # find the start of the next line
#                ind = page.find('\n', ind) + 1
#                section = \
#                    _relation_section(rel_name, word, synset_keys)
#                page = page[:ind] + section + page[ind:]
#                return page, word
#            else:
#                return None, None
#    else:
#        # A word link looks like this:
#        # Wword#synset_key,prev_synset_key#link_counter
#        # A synset link looks like this:
#        # Sword#synset_key,prev_synset_key#link_counter
#        l_t = link_type + ':'
#        word,syns_keys,link_counter = u_link.split('#')
#        ind = page.find(q_link) + len(q_link) + 2
#        # If the link text is in bold, the user wants to
#        # close the section beneath the link
#        if page[ind:ind+3] == '<b>':
#            page = _ul_section_removed(page, ind)
#            page = page[:ind] + l_t + page[ind + 9:]
#            return page, word
#        else: # The user wants to see the relation names
#            # Make this link text bold on page
#            page = page[:ind] + _bold(l_t) + page[ind + 2:]
#            # Insert the relation names
#            ind = page.find('\n', ind) + 1
#            # First remove the full_hyponym_cont_text if found here
#            if page[ind+5:].startswith(full_hyponym_cont_text):
#                page = page[0:ind+5] + \
#                        page[ind+5+len(full_hyponym_cont_text):]
#            s_r = _synset_relations(word, link_type, syns_keys)
#            s_r = s_r.split('\n')[:-1]
#            s_r = [_li(sr) for sr in s_r]
#            s_r = _ul('\n' + '\n'.join(s_r) + '\n') + '\n'
#            page = page[:ind] + s_r + page[ind:]
#            return page, word


################################################################################
#
# Static pages.
#

def get_static_page_by_path(path):
    """
    Return a static HTML page from the path given.
    """
    if path == "index_2.html":
        return get_static_index_page(False)
    elif path == "index.html":
        return get_static_index_page(True)
    elif path == "NLTK Wordnet Browser Database Info.html":
        return "Display of Wordnet Database Statistics is not supported"
    elif path == "upper_2.html":
        return get_static_upper_page(False)
    elif path == "upper.html":
        return get_static_upper_page(True)
    elif path == "web_help.html":
        return get_static_web_help_page()
    elif path == "wx_help.html":
        return get_static_wx_help_page()
    else:
        return "Internal error: Path for static page '%s' is unknown" % path

    f = open(path)
    page = f.read()
    f.close()
    return page


def get_static_web_help_page():
    """
    Return the static web help page.
    """
    return \
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2007 - 2008 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <http://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database.
<p><b>You are using the Javascript client part of the NLTK Wordnet BrowseServer.</b> We assume your browser is in tab sheets enabled mode.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <a href="http://wordnet.princeton.edu/"><b> http://wordnet.princeton.edu/</b></a>. For more information on the NLTK project, see the project home:
<a href="http://nltk.sourceforge.net/"><b>http://nltk.sourceforge.net/</b></a>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>New Word</b> field and the search started with Enter or by clicking the <b>Search</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by using the <b>Alt+LeftArrow</b> key combination. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>The Buttons</h3>
<p>The <b>Search</b> and <b>Help</b> buttons need no more explanation. </p>
<p>The <b>Show Database Info</b> button shows a collection of Wordnet database statistics.</p>
<p>The <b>Shutdown the Server</b> button is shown for the first client of the BrowServer program i.e. for the client that is automatically launched when the BrowServer is started but not for the succeeding clients in order to protect the server from accidental shutdowns.
</p></body>
</html>
"""

def get_static_wx_help_page():
    """
    Return static WX help page.
    """
    return \
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2007 - 2008 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <http://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <head>
          <meta http-equiv='Content-Type' content='text/html; charset=us-ascii'>
          <title>NLTK Wordnet Browser display of: * Help *</title>
     </head>
<body bgcolor='#F5F5F5' text='#000000'>
<h2>NLTK Wordnet Browser Help</h2>
<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database. The NLTK Wordnet Browser has only a part of normal browser functionality and it is <b>not</b> an Internet browser.</p>
<p>For background information on Wordnet, see the Wordnet project home page: <b>http://wordnet.princeton.edu/</b>. For more information on the NLTK project, see the project home: <b>http://nltk.sourceforge.net/</b>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>
<h3>The User Interface</h3>
<p>The user interface is a so called <b>notebook</b> interface. This
is familiar nowadays for almost everyone from Internet browsers,
for example. It consists of one or more independent pages often
(and here also) called <b>tabsheets</b>.</p>
<p>Every tabsheet contains its own search history which can be
browsed back and forth at will. The result of a new word search
will be shown on the currently active tabsheet if nothing else is
wanted. It is also possible to open a new tabsheet for the search
word given.</p>
<p>The position and size of the browser window as well as font size can be adjusted and the selections are retained between sessions.</p>
<h3>Word search</h3>
<p>The word to be searched is typed into the <b>Word(s):</b> field and the search started with Enter or by clicking the <b>Search the word(s)</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>
<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions. Typing <b>fLIeS</b> as an obscure example gives one <a href="MfLIeS">this</a>. Click the previous link to see what this kind of search looks like and then come back to this page by clicking the <b>Previous Page</b> button.</p>
<p>The result of a search is a display of one or more
<b>synsets</b> for every part of speech in which a form of the
search word was found to occur. A synset is a set of words
having the same sense or meaning. Each word in a synset that is
underlined is a hyperlink which can be clicked to trigger an
automatic search for that word.</p>
<p>Every synset has a hyperlink <b>S:</b> at the start of its
display line. Clicking that symbol shows you the name of every
<b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again. Clicking another relation name on a line that has an opened relation closes the open relation and opens the clicked relation.</p>
<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma like this <a href="Mcheer up,clear up">cheer up,clear up</a>, for example. Click the previous link to see what this kind of search looks like and then come back to this page by clicking the <b>Previous Page</b> button. As you could see the search result includes the synsets found in the same order than the forms were given in the search field.</p>
<p>
There are also word level (lexical) relations recorded in the Wordnet database. Opening this kind of relation displays lines with a hyperlink <b>W:</b> at their beginning. Clicking this link shows more info on the word in question.</p>
<h3>Menu Structure</h3>
The browser has a menubar that you can use to invoke a set of
different operations. Most of the menu selections also have a
corresponding keyboard shortcut.
<h4>The File Menu</h4>
<p>Using the file menu you can <b>open</b> a previously saved NLTK
Wordnet Browser page. Note that only pages saved with this browser
can be read.</p>
<p>And as indicated above you can <b>save</b> a search page. The
resulting file is a normal HTML mode file which can be viewed,
printed etc. as any other HTML file.</p>
<p>You can also <b>print</b> a page and <b>preview</b> a page to be
printed. The selected printing settings are remembered during the
session.</p>
<h4>The Tabsheets Menu</h4>
<p>You can <b>open an empty tabsheet</b> and <b>close</b> the
currently active tabsheet.</p>
<p>When you enter a new search word in the search word field you
can make the search result be shown in a <b>new tabsheet</b>.</p>
<h4>Page History</h4>
You can browse the page history of the currently active tabsheet
either <b>forwards</b> or <b>backwards</b>. <b>Next Page</b>
browses towards the newer pages and <b>Previous Page</b> towards
the older pages.
<h4>The View Menu</h4>
<p>You can <b>increase</b>, <b>decrease</b> and <b>normalize</b>
the font size. The font size chosen is retained between
sessions.</p>
<p>You can choose <b>Show Database Info</b> to see the word, synset and relation counts by POS as well as one example word (as a hyperlink) for every relation&amp;POS pair occuring.</p>
<p>You can view the <b>HTML source</b> of a page if you are
curious.</p>
<h4>The Help Menu</h4>
You can view this <b>help text</b> as you already know. The
<b>about</b> selection tells you something about the program.
<h3>The Keyboard Shortcuts</h3>
<p>The following keyboard shortcuts can be used to quickly launch
the desired operation.</p>
<table border="1" cellpadding="1" cellspacing="1" summary="">
<col align="center">
<col align="center">
<tr>
<th>Keyboard Shortcut</th>
<th>Operation</th>
</tr>
<tr>
<td>Ctrl+O</td>
<td>Open a file</td>
</tr>
<tr>
<td>Ctrl+S</td>
<td>Save current page as</td>
</tr>
<tr>
<td>Ctrl+P</td>
<td>Print current page</td>
</tr>
<tr>
<td>Ctrl+T</td>
<td>Open a new (empty) tabsheet</td>
</tr>
<tr>
<td>Ctrl+W</td>
<td>Close the current tabsheet</td>
</tr>
<tr>
<td>Ctrl+LinkClick</td>
<td>Open the link in a new unfocused tabsheet</td>
</tr>
<tr>
<td>Ctrl+Shift+LinkClick</td>
<td>Opent the link in a new focused tabsheet</td>
</tr>
<tr>
<td>Alt+Enter (1)</td>
<td>Show the word in search word field in a new tabsheet</td>
</tr>
<tr>
<td>Alt+LeftArrow</td>
<td>Previous page in page history</td>
</tr>
<tr>
<td>Ctrl+LeftArrow (2)</td>
<td>Previous page in page history</td>
</tr>
<tr>
<td>Alt+RightArrow</td>
<td>Next page in page history</td>
</tr>
<tr>
<td>Ctlr+RightArrow (2)</td>
<td>Next page in page history</td>
</tr>
<tr>
<td>Ctrl++/Ctrl+Numpad+/Ctrl+UpArrow (3)</td>
<td>Increase font size</td>
</tr>
<tr>
<td>Ctrl+-/Ctrl+Numpad-/Ctrl+DownArrow (3)</td>
<td>Decrease font size</td>
</tr>
<tr>
<td>Ctrl+0 (4)</td>
<td>Normal font size</td>
</tr>
<tr>
<td>Ctrl+U</td>
<td>Show HTML source</td>
</tr>
</table>
<dl>
<dt>(1)</dt>
<dd>This works only when the search word field is active i.e. the
caret is in it.</dd>
<dt>(2)</dt>
<dd>These are nonstandard combinations, the usual ones being
Alt+LeftArrow and Alt+RightArrow. These are still functional because there used to be difficulties with the standard ones earlier in the life of this program. Use these if the standard combinations do not work properly for you.</dd>
<dt>(3)</dt>
<dd>There are so many of these combinations because the usual i.e.
Ctrl++/Ctrl+- combinations did not work on the author's laptop and
the Numpad combinations were cumbersome to use. Hopefully the first
ones work on the computers of others.</dd>
<dt>(4)</dt>
<dd>This combination Ctrl+0 is "Ctrl+zero" not "Ctrl+ou".</dd>
</dl>
</body>
</html>
"""


def get_static_welcome_message():
    """
    Get the static welcome page.
    """
    return \
"""
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
<li>Type a search word in the <b>Next Word</b> field and start the search by the
<b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
"""

def get_static_index_page(with_shutdown):
    """
    Get the static index page.
    """
    template = \
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"  "http://www.w3.org/TR/html4/frameset.dtd">
<HTML>
     <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
            Copyright (C) 2007 - 2008 NLTK Project
            Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
            URL: <http://www.nltk.org/>
            For license information, see LICENSE.TXT -->
     <HEAD>
	     <TITLE>NLTK Wordnet Browser</TITLE>
     </HEAD>

<frameset rows="7%%,93%%">
    <frame src="%s" name="header">
    <frame src="start_page" name="body">
</frameset>
</HTML>
"""
    if with_shutdown:
        upper_link = "upper.html"
    else:
        upper_link = "upper_2.html"

    return template % upper_link


def get_static_upper_page(with_shutdown):
    """
    Return the upper frame page,

    If with_shutdown is True then a 'shutdown' button is also provided
    to shutdown the server.
    """
    template = \
"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <!-- Natural Language Toolkit: Wordnet Interface: Graphical Wordnet Browser
        Copyright (C) 2007 - 2008 NLTK Project
        Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
        URL: <http://www.nltk.org/>
        For license information, see LICENSE.TXT -->
	<head>
                <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
		<title>Untitled Document</title>
	</head>
	<body>
	<form method="GET" action="search" target="body">
	        Current Word:&nbsp;<input type="text" id="currentWord" size="10" disabled>
			Next Word:&nbsp;<input type="text" id="nextWord" name="nextWord" size="10">
			<input name="searchButton" type="submit" value="Search">
	</form>
        <a target="body" href="web_help.html">Help</a>
        %s

</body>
</html>
"""
    if with_shutdown:
        shutdown_link = "<a href=\"SHUTDOWN THE SERVER\">Shutdown</a>"
    else:
        shutdown_link = ""
    
    return template % shutdown_link
