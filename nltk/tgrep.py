#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
TGrep search implementation for NTLK ParentedTrees.

(c) 16 March, 2013 Will Roberts

This module supports tgrep2 syntax for matching parts of NLTK Trees.
Note that many tgrep operators require the tree passed to be a
ParentedTree.

Tgrep tutorial:
http://www.stanford.edu/dept/linguistics/corpora/cas-tut-tgrep.html
Tgrep2 manual:
http://tedlab.mit.edu/~dr/Tgrep2/tgrep2.pdf
'''

import nltk.tree
import re

def _ancestors(node):
    '''
    Returns the list of all nodes dominating the given tree node.
    This method will not work with leaf nodes, since there is no way
    to recover the parent.
    '''
    results = []
    # if node is a leaf, we cannot retrieve its parent
    if not hasattr(node, 'parent'):
        return []
    current = node.parent()
    while current:
        results.append(current)
        current = current.parent()
    return results

def _descendants(node):
    '''
    Returns the list of all nodes which are descended from the given
    tree node in some way.
    '''
    if not hasattr(node, 'treepositions'):
        return []
    return [node[x] for x in node.treepositions()[1:]]

def _leftmost_descendants(node):
    '''
    Returns the set of all nodes descended in some way through
    left branches from this node.
    '''
    if not hasattr(node, 'treepositions'):
        return []
    return [node[x] for x in node.treepositions()[1:] if all(y == 0 for y in x)]

def _rightmost_descendants(node):
    '''
    Returns the set of all nodes descended in some way through
    right branches from this node.
    '''
    if not hasattr(node, 'treepositions'):
        return []
    rightmost_leaf = max(node.treepositions())
    return [node[rightmost_leaf[:i]] for i in range(1, len(rightmost_leaf) + 1)]

def _tgrep_operator (op, pred):
    '''
    Creates lambda functions for the various TGrep links.
    '''
    # handle negated operators
    if op.startswith('!'):
        not_function = _tgrep_operator(op[1:], pred)
        # capture not_function
        return (lambda f: (lambda n: not f(n)))(not_function)
    # A < B       A is the parent of (immediately dominates) B.
    if op == '<':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          any([pred(x) for x in n]))
    # A > B       A is the child of B.
    elif op == '>':
        return lambda n: (hasattr(n, 'parent') and
                          bool(n.parent()) and
                          pred(n.parent()))
    # A <, B      Synonymous with A <1 B.
    elif op == '<,' or op == '<1':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          bool(list(n)) and
                          pred(n[0]))
    # A >, B      Synonymous with A >1 B.
    elif op == '>,' or op == '>1':
        return lambda n: (hasattr(n, 'parent') and
                          bool(n.parent()) and
                          (n is n.parent()[0]) and
                          pred(n.parent()))
    # A <N B      B is the Nth child of A (the first child is <1).
    elif op[0] == '<' and op[1:].isdigit():
        idx = int(op[1:])
        # capture the index parameter
        return lambda i: (lambda n: (isinstance(n, nltk.tree.Tree) and
                                     bool(list(n)) and
                                     i < len(n) and
                                     pred(n[i])))(idx)
    # A >N B      A is the Nth child of B (the first child is >1).
    elif op[0] == '>' and op[1:].isdigit():
        idx = int(op[1:])
        # capture the index parameter
        return lambda i: (lambda n: (hasattr(n, 'parent') and
                                     bool(n.parent()) and
                                     i < len(n.parent()) and
                                     (n is n.parent()[i]) and
                                     pred(n.parent())))(idx)
    # A <' B      B is the last child of A (also synonymous with A <-1 B).
    # A <- B      B is the last child of A (synonymous with A <-1 B).
    elif op == '<\'' or op == '<-' or op == '<-1':
        return lambda n: (isinstance(n, nltk.tree.Tree) and bool(list(n))
                          and pred(n[-1]))
    # A >' B      A is the last child of B (also synonymous with A >-1 B).
    # A >- B      A is the last child of B (synonymous with A >-1 B).
    elif op == '>\'' or op == '>-' or op == '>-1':
        return lambda n: (hasattr(n, 'parent') and
                          bool(n.parent()) and
                          (n is n.parent()[-1]) and
                          pred(n.parent()))
    # A <-N B 	  B is the N th-to-last child of A (the last child is <-1).
    elif op[:2] == '<-' and op[2:].isdigit():
        idx = -int(op[2:])
        assert False, 'operator "<-N" is not yet implemented' # NYI
    # A >-N B 	  A is the N th-to-last child of B (the last child is >-1).
    elif op[:2] == '>-' and op[2:].isdigit():
        idx = -int(op[2:])
        assert False, 'operator ">-N" is not yet implemented' # NYI
    # A <: B      B is the only child of A
    elif op == '<:':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          len(n) == 1 and
                          pred(n[0]))
    # A >: B      A is the only child of B.
    elif op == '>:':
        return lambda n: (hasattr(n, 'parent') and
                          bool(n.parent()) and
                          len(n.parent()) == 1 and
                          pred(n.parent()))
    # A << B      A dominates B (A is an ancestor of B).
    elif op == '<<':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          any([pred(x) for x in _descendants(n)]))
    # A >> B      A is dominated by B (A is a descendant of B).
    elif op == '>>':
        return lambda n: any([pred(x) for x in _ancestors(n)])
    # A <<, B     B is a left-most descendant of A.
    elif op == '<<,' or op == '<<1':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          any([pred(x) for x in _leftmost_descendants(n)]))
    # A >>, B     A is a left-most descendant of B.
    elif op == '>>,':
        return lambda n: any([(pred(x) and n in _leftmost_descendants(x))
                              for x in _ancestors(n)])
    # A <<' B     B is a right-most descendant of A.
    elif op == '<<\'':
        return lambda n: (isinstance(n, nltk.tree.Tree) and
                          any([pred(x) for x in _rightmost_descendants(n)]))
    # A >>' B     A is a right-most descendant of B.
    elif op == '>>\'':
        return lambda n: any([(pred(x) and n in _rightmost_descendants(x))
                              for x in _ancestors(n)])
    # A <<: B     There is a single path of descent from A and B is on it.
    elif op == '<<:':
        assert False, 'operator "<<:" is not yet implemented' # NYI
    # A >>: B     There is a single path of descent from B and A is on it.
    elif op == '>>:':
        assert False, 'operator ">>:" is not yet implemented' # NYI
    # A . B       A immediately precedes B.
    elif op == '.':
        assert False, 'operator "." is not yet implemented' # NYI
    # A , B       A immediately follows B.
    elif op == ',':
        assert False, 'operator "," is not yet implemented' # NYI
    # A .. B      A precedes B.
    elif op == '..':
        assert False, 'operator ".." is not yet implemented' # NYI
    # A ,, B      A follows B.
    elif op == ',,':
        assert False, 'operator ",," is not yet implemented' # NYI
    # A $ B       A is a sister of B (and A != B).
    elif op == '$' or op == '%':
        return lambda n: (hasattr(n, 'parent') and
                          bool(n.parent()) and
                          any([pred(x) for x in n.parent() if x is not n]))
    # A $. B      A is a sister of and immediately precedes B.
    elif op == '$.' or op == '%.':
        return lambda n: (hasattr(n, 'left_sibling') and
                          bool(n.left_sibling()) and
                          pred(n.left_sibling()))
    # A $, B      A is a sister of and immediately follows B.
    elif op == '$,' or op == '%,':
        return lambda n: (hasattr(n, 'right_sibling') and
                          bool(n.right_sibling()) and
                          pred(n.right_sibling()))
    # A $.. B     A is a sister of and precedes B.
    elif op == '$..' or op == '%..':
        return lambda n: (hasattr(n, 'parent') and
                          hasattr(n, 'parent_index') and
                          bool(n.parent()) and
                          any([pred(x) for x in
                               n.parent()[n.parent_index() + 1:]]))
    # A $,, B     A is a sister of and follows B.
    elif op == '$,,' or op == '%,,':
        return lambda n: (hasattr(n, 'parent') and
                          hasattr(n, 'parent_index') and
                          bool(n.parent()) and
                          any([pred(x) for x in
                               n.parent()[:n.parent_index()]]))
    else:
        assert False, 'cannot interpret tgrep operator "{0}"'.format(op)

_TGREP_PATS = [ re.compile('^' + pattern) for pattern in
                (r'"([^"\\]|\\.)*"',                      # quoted strings
                 '&|(!?[%,.<>$][!%,.<>0-9-\':]*)',        # tgrep operators
                 '[ \t\n\r]+',                            # whitespace
                 '\'?/[^/]+/',                            # node name regex
                 '\(',                                    # open paren
                 '\)',                                    # close paren
                 '!?\[',                                  # open square bracket
                 '\]',                                    # close square bracket
                 '\|',                                    # pipe (OR)
                 '\'?\*',                                 # any node
                 '\'?[^][ \r\t\n;:.,&|<>()$!@%\'^=]+') ]  # node name literal

def _tokenize_tgrep(s):
    '''
    Tokenizes a TGrep search string into separate tokens.
    '''
    results = []
    while s:
        # match the TGrep token syntax (defined by regexes) in the
        # order they are preferred
        for p in _TGREP_PATS:
            m = p.match(s)
            if m:
                results.append(m.group(0))
                s = s[m.end():]
                break
        if not m:
            print 'ERROR: cannot tokenize "{0}"'.format(s)
            return None
    return [r for r in results if r.strip()]

def parse_tgrep(toks, hungry = True):
    '''
    Parses (and tokenizes, if necessary) a TGrep search string into a
    lambda function.
    '''
    if isinstance(toks, basestring):
        toks = _tokenize_tgrep(toks)
    #print 'parse_tgrep "{0}"'.format(' '.join(toks))
    parsed_function = None
    parsed_length = 0
    # strip apostrophe (print command) from beginning of token
    if toks[0][0] == "'":
        toks[0] = toks[0][1:]
    # match the first token
    if toks[0] == '(':
        depth = 1
        i = 1
        while depth > 0 and i < len(toks):
            if toks[i] == '(':
                depth += 1
            elif toks[i] == ')':
                depth -= 1
            i += 1
        if depth > 0:
            assert False, 'unbalanced brackets in tgrep string "{0}"'.format(
                ' '.join(toks))
        p, l = parse_tgrep(toks[1:i-1], True)
        assert l == i - 2, 'tokens in parenthesis not parsed: "{0}"'.format(
            ' '.join(toks[1+l:-1]))
        parsed_function, parsed_length = p, i
    elif toks[0] == '[' or toks[0] == '![':
        assert False, 'parsing square brackets not yet implemented' # NYI
    elif toks[0] == '&':
        assert False, 'parsing & not yet implemented' # NYI
    elif _TGREP_PATS[1].match(toks[0]):
        assert len(toks) > 1, 'no argument to operator "{0}"'.format(toks[0])
        (p, l) = parse_tgrep(toks[1:], False)
        p = _tgrep_operator(toks[0], p)
        l += 1
        parsed_function, parsed_length = (p, l)
    elif (toks[0] == '*' or
          toks[0] == '__' or
          toks[0].startswith('/') or
          toks[0].startswith('"') or
          re.match(_TGREP_PATS[-1], toks[0])):
        l = 1
        if toks[0].startswith('"'):
            toks[0] = toks[0].strip('"')
        if toks[0] == '*' or toks[0] == '__':
            p = lambda n: True
        elif toks[0].startswith('/'):
            p = lambda n: (n.node if isinstance(n, nltk.tree.Tree)
                           else n).startswith(toks[0].strip('/'))
        elif toks[0].startswith('i@'):
            p = lambda n: ((n.node if isinstance(n, nltk.tree.Tree)
                            else n).lower() == toks[0][2:].lower())
        else:
            p = lambda n: ((n.node if isinstance(n, nltk.tree.Tree)
                            else n) == toks[0])
        if len(toks) > 1 and toks[1] == '|':
            assert len(toks) > 2, 'no predicate following logical OR'
            (p2, l) = parse_tgrep(toks[2:], False)
            # combine with OR
            or_function = p
            p = lambda n: (or_function(n) or p2(n))
            l += 2
        parsed_function, parsed_length = (p, l)
    else:
        assert False, 'Could not parse token "{0}"'.format(toks[0])
    if hungry and parsed_length < len(toks):
        #print 'AND'
        (p, l) = parse_tgrep(toks[parsed_length:], True)
        parsed_length += l
        assert parsed_length == len(toks), (
            'could not parse tokens "{0}"'.format(
                ' '.join(toks[parsed_length:])))
        # combine with AND
        and_function = parsed_function
        # capture and_function and p
        parsed_function = (lambda a, b: 
                           (lambda n: a(n) and b(n)))(and_function, p)
    return (parsed_function, parsed_length)
