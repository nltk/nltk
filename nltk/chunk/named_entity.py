# Natural Language Toolkit: Chunk parsing API
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Named entity chunker
"""

import os, re, pickle
from nltk.etree import ElementTree as ET
from nltk.chunk.api import *
from nltk.chunk.util import *
import nltk

# This really shouldn't be loaded at import time.  But it's used by a
# static method.  Do a lazy loading?
_short_en_wordlist = set(nltk.corpus.words.words('en-basic'))


class NEChunkParserTagger(nltk.tag.ClassifierBasedTagger):
    """
    The IOB tagger used by the chunk parser.
    """
    def __init__(self, train):
        nltk.tag.ClassifierBasedTagger.__init__(
            self, train=train,
            classifier_builder=self._classifier_builder)

    def _classifier_builder(self, train):
        return nltk.MaxentClassifier.train(train, algorithm='megam',
                                           gaussian_prior_sigma=1)
    
    def _feature_detector(self, tokens, index, history):
        word = tokens[index][0]
        pos = simplify_pos(tokens[index][1])
        if index == 0:
            prevword = prevprevword = None
            prevpos = prevprevpos = None
            prevtag = prevprevtag = None
        elif index == 1:
            prevword = tokens[index-1][0].lower()
            prevprevword = None
            prevpos = simplify_pos(tokens[index-1][1])
            prevprevpos = None
            prevtag = history[index-1][0]
            prevprevtag = None
        else:
            prevword = tokens[index-1][0].lower()
            prevprevword = tokens[index-2][0].lower()
            prevpos = simplify_pos(tokens[index-1][1])
            prevprevpos = simplify_pos(tokens[index-2][1])
            prevtag = history[index-1]
            prevprevtag = history[index-2]
        if index == len(tokens)-1:
            nextword = nextnextword = None
            nextpos = nextnextpos = None
        elif index == len(tokens)-2:
            nextword = tokens[index+1][0].lower()
            nextpos = tokens[index+1][1].lower()
            nextnextword = None
            nextnextpos = None
        else:
            nextword = tokens[index+1][0].lower()
            nextpos = tokens[index+1][1].lower()
            nextnextword = tokens[index+2][0].lower()
            nextnextpos = tokens[index+2][1].lower()

        # 89.6
        features = {
            'bias': True,
            'shape': shape(word),
            'wordlen': len(word),
            'prefix3': word[:3].lower(),
            'suffix3': word[-3:].lower(),
            'pos': pos,
            'word': word,
            'en-wordlist': (word in _short_en_wordlist), # xx!
            'prevtag': prevtag,
            'prevpos': prevpos,
            'nextpos': nextpos,
            'prevword': prevword,
            'nextword': nextword,
            'word+nextpos': '%s+%s' % (word.lower(), nextpos),
            'pos+prevtag': '%s+%s' % (pos, prevtag),
            'shape+prevtag': '%s+%s' % (shape, prevtag),
            }
        
        return features

class NEChunkParser(ChunkParserI):
    """
    Expected input: list of pos-tagged words
    """
    def __init__(self, train):
        self._train(train)

    def parse(self, tokens):
        """
        Each token should be a pos-tagged word
        """
        tagged = self._tagger.tag(tokens)
        tree = self._tagged_to_parse(tagged)
        return tree

    def _train(self, corpus):
        # Convert to tagged sequence
        corpus = [self._parse_to_tagged(s) for s in corpus]

        self._tagger = NEChunkParserTagger(train=corpus)

    def _tagged_to_parse(self, tagged_tokens):
        """
        Convert a list of tagged tokens to a chunk-parse tree.
        """
        sent = nltk.Tree('S', [])
        
        for (tok,tag) in tagged_tokens:
            if tag == 'O':
                sent.append(tok)
            elif tag.startswith('B-'):
                sent.append(nltk.Tree(tag[2:], [tok]))
            elif tag.startswith('I-'):
                if (sent and isinstance(sent[-1], Tree) and
                    sent[-1].node == tag[2:]):
                    sent[-1].append(tok)
                else:
                    sent.append(nltk.Tree(tag[2:], [tok]))
        return sent

    def _parse_to_tagged(self, sent):
        """
        Convert a chunk-parse tree to a list of tagged tokens.
        """
        toks = []
        for child in sent:
            if isinstance(child, nltk.Tree):
                toks.append((child[0], 'B-%s' % child.node))
                for tok in child[1:]:
                    toks.append((tok, 'I-%s' % child.node))
            else:
                toks.append((child, 'O'))
        return toks

def shape(word):
    if re.match('[0-9]+(\.[0-9]*)?|[0-9]*\.[0-9]+$', word):
        return 'number'
    elif re.match('\W+$', word):
        return 'punct'
    elif re.match('[A-Z][a-z]+$', word):
        return 'upcase'
    elif re.match('[a-z]+$', word):
        return 'downcase'
    elif re.match('\w+$', word):
        return 'mixedcase'
    else:
        return 'other'

def simplify_pos(s):
    if s.startswith('V'): return "V"
    else: return s.split('-')[0]

def postag_tree(tree):
    # Part-of-speech tagging.
    words = tree.leaves()
    tag_iter = (pos for (word, pos) in nltk.pos_tag(words))
    newtree = Tree('S', [])
    for child in tree:
        if isinstance(child, nltk.Tree):
            newtree.append(Tree(child.node, []))
            for subchild in child:
                newtree[-1].append( (subchild, tag_iter.next()) )
        else:
            newtree.append( (child, tag_iter.next()) )
    return newtree

def load_ace_data(root, fmt='binary'):
    for f in os.listdir(root):
        if not f.endswith('.sgm'): continue
        print f
        f = os.path.join(root, f)
        g = f+'.tmx.rdc.xml'
    
        # Read the xml file, and get a list of entities
        entities = []
        xml = ET.parse(open(g)).getroot()
        for entity in xml.findall('document/entity'):
            typ = entity.find('entity_type').text
            for mention in entity.findall('entity_mention'):
                if mention.get('TYPE') != 'NAME': continue # only NEs
                s = int(mention.find('head/charseq/start').text)
                e = int(mention.find('head/charseq/end').text)+1
                entities.append( (s, e, typ) )
    
        # Read the text file, and mark the entities.
        text = open(f).read()
        
        # Strip XML tags, since they don't count towards the indices
        text = re.sub('<(?!/?TEXT)[^>]+>', '', text)
    
        # Blank out anything before/after <TEXT>
        def subfunc(m): return ' '*(m.end()-m.start()-6)
        text = re.sub('[\s\S]*<TEXT>', subfunc, text)
        text = re.sub('</TEXT>[\s\S]*', '', text)
    
        # Simplify quotes
        text = re.sub("``", ' "', text)
        text = re.sub("''", '" ', text)
    
        entity_types = set(typ for (s,e,typ) in entities)
    
        # Binary distinction (NE or not NE)
        if fmt == 'binary':
            i = 0
            toks = nltk.Tree('S', [])
            for (s,e,typ) in sorted(entities):
                if s < i: s = i # Overlapping!  Deal with this better?
                if e <= s: continue
                toks.extend(nltk.word_tokenize(text[i:s]))
                toks.append(nltk.Tree('NE', text[s:e].split()))
                i = e
            toks.extend(nltk.word_tokenize(text[i:]))
            yield toks

        # Multiclass distinction (NE type)
        elif fmt == 'multiclass':
            i = 0
            toks = nltk.Tree('S', [])
            for (s,e,typ) in sorted(entities):
                if s < i: s = i # Overlapping!  Deal with this better?
                if e <= s: continue
                toks.extend(nltk.word_tokenize(text[i:s]))
                toks.append(nltk.Tree(typ, text[s:e].split()))
                i = e
            toks.extend(nltk.word_tokenize(text[i:]))
            yield toks

        else:
            raise ValueError('bad fmt value')
            

def train(root):
    print 'Loading data...'
    trees = load_ace_data(root)
    train = [postag_tree(t) for t in trees]
    print 'Training chunk parser...'
    cp = NEChunkParser(train[10:])
    print 'Evaluating...'
    chunkscore = ChunkScore()
    for correct in train[:10]:
        guess = cp.parse(correct.leaves())
        chunkscore.score(correct, guess)
    print chunkscore
    return cp

def build_model():
    # Make sure that the pickled object has the right class name:
    from nltk.chunk.named_entity import train
    
    cp = train('/tmp/ace.old/data/ace.dev/text/')
    out = open('/tmp/ne_chunker.pickle', 'wb')
    pickle.dump(cp, out, -1)
    out.close()

