# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# To do:
#   - How should we handle traces and/or movement?

"""
Classes for representing hierarchical language structures over tokens,
such as syntax trees and morphological trees.  A single tree is
represented by a nested structure of X{tree tokens}, where each tree
token encodes a single hierarchical grouping.  Tree tokens are
specialized tokens that associate additional meaning with specific
properties.  Different tree token implementations associate different
meanings to these properties.  Three tree token implementations are
currently available:

  - L{TreeToken}s use the C{children} property to record the
    hierarchical content of a tree.

  - L{ParentedTreeToken}s use the C{children} property to record
    the hierarchical content of a tree; and the C{parent} property
    to record the tree's unique parent.

  - L{MultiParentedTreeToken}s use the C{children} property to
    record the hierarchical content of a tree; and the C{parents}
    property to record a list of the tree's parents.

For most purposes, the C{TreeToken} implementation is sufficient.  But
in cases where parent pointers are needed, the C{ParentedTreeToken} or
C{MultiParentedTreeToken} implementations can be used.  The
C{ParentedTreeToken} implementation is appropriate when each subtree
has a unique parent; and the C{MultiParentedTreeToken} implementation
is appropriate when a single subtree can be shared by multiple
parents.
"""

from nltk.token import Token, CharSpanLocation
from nltk.tokenizer import TokenizerI
from nltk.probability import ProbabilisticMixIn
import re
from nltk.chktype import chktype
from nltk.chktype import classeq as _classeq
import types

# Register some information about properties used by tree tokens.
Token.register_cyclic('parent')
Token.register_cyclic('parents')
Token.register_repr(['text','parent'], '<%(text)r>')
Token.register_repr(['text','parents'], '<%(text)r>')

######################################################################
## Tree Token
######################################################################

class TreeToken(Token):
    """
    A hierarchical structure over tokens.

    Each C{TreeToken} represents a single hierarchical grouping of
    leaves and subtrees.  For example, each constituent in a syntax
    tree is represented by a single C{TreeToken}.

    The C{children} property is used to record a C{TreeToken}'s
    hierarchical contents.  These contents are encoded as a C{list} of
    leaves and subtrees, where a X{leaf} is a basic (non-tree) token;
    and a X{subtree} is a nested C{TreeToken}.

    Any other properties that a C{TreeToken} defines are known as
    X{node properties}, and are used to add information about
    individual hierarchical groupings.  For eample, syntax trees use a
    node property to label syntactic constituents with phrase tags,
    such as \"NP\" and\"VP\".

    Several C{TreeToken} methods use X{tree positions} to specify
    children or descendants of a tree.  Tree positions are defined as
    follows:

      - The tree position M{i} specifies a C{TreeToken}'s M{i}th child.
      - The tree position C{()} specifies the C{TreeToken} itself.
      - If C{M{p}} is the tree position of descendant M{d}, then
        C{M{p}+(M{i})} specifies the C{M{i}}th child of M{d}.
    
    I.e., every tree position is either a single index C{M{i}},
    specifying C{self.get_child(M{i})}; or a sequence
    C{(M{i1}, M{i2}, ..., M{iN})}, specifying
    C{self.get_child(M{i1}).get_child(M{i2})...getchild(M{iN})}.
    """
    def __init__(self, **properties):
        """
        Construct a new tree token.

        @param properties: The initial set of properties that the new
            token should define.  Each element maps a property name to
            its value.  C{properties} must include the C{children}
            property, which should contain a list of C{Token}s and
            C{TreeToken}s.
        """
        super(TreeToken, self).__init__(**properties)
        if not self.has('children'):
            raise ValueError('TreeTokens must define the children property')
        if type(self['children']) is not list:
            self['children'] = list(self['children'])

    #////////////////////////////////////////////////////////////
    # Basic tree operations
    #////////////////////////////////////////////////////////////
    
    def leaves(self):
        """
        @return: a list containing this tree's leaf set.  The
            order of leaves in the tuple reflects the order of the
            leaves in the tree's hierarchical structure.
        @rtype: C{list} of L{Token}
        """
        leaves = []
        for child in self['children']:
            if isinstance(child, TreeToken):
                leaves.extend(child.leaves())
            else:
                leaves.append(child)
        return leaves

    def height(self):
        """
        @return: The height of this tree.  The height of a tree
            containing no children is 1; the height of a tree
            containing only leaves is 2; and the height of any other
            tree is one plus the maximum of its children's
            heights.
        @rtype: C{int}
        """
        max_child_height = 0
        for child in self['children']:
            if isinstance(child, TreeToken):
                max_child_height = max(max_child_height, child.height())
            else:
                max_child_height = max(max_child_height, 1)
        return 1 + max_child_height

    #////////////////////////////////////////////////////////////
    # Tree position accessors & modifiers
    #////////////////////////////////////////////////////////////
    
    def get_child(self, treepos):
        """
        @return: the child or descendant at the given tree position.
        
        @type treepos: C{int} or C{tuple} of C{int}
        @param treepos: The tree position of the child to return.
            See the class documentation for L{TreeToken} for a
            definition of tree positions.
        """
        assert chktype(1, treepos, int, (int,), [int,])
        
        # If it's an index, then return it directly.
        if type(treepos) is int:
            return self['children'][treepos]

        # If it's a path, then follow it.
        return_value = self
        for i in treepos: return_value = return_value['children'][i]
        return return_value

    def replace_child(self, treepos, new_value):
        """
        Replace the child or descendant at the given tree position
        with C{new_value}.
        
        @type treepos: C{int} or C{tuple} of C{int}
        @param treepos: The tree position of the child to replace.
            See the class documentation for L{TreeToken} for a
            definition of tree positions.
        """
        assert chktype(1, treepos, int, (int,), [int,])
        assert chktype(2, new_value, Token)

        # If it's an index, then set it directly.
        if type(treepos) is int:
            self['children'][treepos] = new_value

        # If it's the empty path, then fail (can't modify self!)
        if len(treepos) == 0:
            raise ValueError('The tree position "()" may not be used '+
                             'with replace_child')
        
        # If it's a path, then follow it to the penultimate subtree;
        # and then replace that subtree's child.
        parent = self
        for i in treepos[:-1]: parent = parent['children'][i]
        parent['children'][treepos[-1]] = new_value

    def remove_child(self, treepos):
        """
        Remove the child or descendant at the given tree position.
        
        @type treepos: C{int} or C{tuple} of C{int}
        @param treepos: The tree position of the child to remove.
            See the class documentation for L{TreeToken} for a
            definition of tree positions.
        """
        assert chktype(1, treepos, int, (int,), [int,])

        # If it's an index, then remove it directly.
        if type(treepos) is int:
            del self['children'][treepos]

        # If it's the empty path, then fail (can't modify self!)
        if len(treepos) == 0:
            raise ValueError('The tree position "()" may not be used '+
                             'with replace_child')
        
        # If it's a path, then follow it to the penultimate subtree;
        # and then remove that subtree's child.
        parent = self
        for i in treepos[:-1]: parent = parent['children'][i]
        del parent['children'][treepos[-1]]

    #////////////////////////////////////////////////////////////
    # Convert
    #////////////////////////////////////////////////////////////
    
    def convert(cls, token):
        """
        Convert the given token into a tree token.  C{cls} determines
        which class will be used to encode the new tree token.  E.g.:

           >>> # Convert tok into a TreeTok:
           >>> treetok = TreeToken.convert(tok)
           >>> # Convert tok into a ParentedTreeTok:
           >>> treetok = ParentedTreeToken.convert(tok)
           >>> # Convert tok into a MultiParentedTreeTok:
           >>> treetok = MultiParentedTreeToken.convert(tok)

        @type token: L{Token}
        @param token: The token that should be converted to a tree
            token.  C{token} can be any token that defines the
            C{children} property.  Note that C{token} may be a tree
            token (to convert between different tree token
            implementations), or a non-tree token.
        @return: The new C{TreeToken}.
        @raise ValueError: If C{token} does not define the
            C{children} property.
        """
        # Make a copy of the token's properties (in a dictionary)
        props = dict(token)

        # Remove the parent pointer, if it's defined.
        if props.has_key('parent'): del props['parent']
        if props.has_key('parents'): del props['parents']

        # Convert subtrees & remove parent pointers from leaves.
        props['children'] = []
        for child in token['children']:
            if child.has('children'):
                props['children'].append(cls.convert(child))
            else:
                child = child.exclude('parent', 'parents', deep=False)
                props['children'].append(child)

        # Create a new tree token with the given properties.
        return cls(**props)
    convert = classmethod(convert)

    #////////////////////////////////////////////////////////////
    # Visualization & String Representation
    #////////////////////////////////////////////////////////////
    
    def draw(self):
        """
        Open a new window containing a graphical diagram of this tree.
        """
        from nltk.draw.tree import draw_trees
        draw_trees(self)

    def __repr__(self):
        childstr = ' '.join([repr(c) for c in self['children']])
        return '(%s: %s)' % (self._noderepr(), childstr)

    def __str__(self):
        return self.pp()

    def _noderepr(self):
        # This is a bit of a hack. :-/
        if len(self) == 2 and self.has('node'): return self['node']

        # Remove children & parent pointers.
        return repr(Token(**self).exclude('children', 'parent',
                                          'parents', deep=False))

    def pp(self, margin=70, indent=0):
        """
        @return: A pretty-printed string representation of this tree.
        @rtype: C{string}
        @param margin: The right margin at which to do line-wrapping.
        @type margin: C{int}
        @param indent: The indentation level at which printing
            begins.  This number is used to decide how far to indent
            subsequent lines.
        @type indent: C{int}
        """
        assert chktype(1, margin, types.IntType)
        assert chktype(2, indent, types.IntType)

        # This is a bit of a hack. :-/
        rep = repr(self)
        if len(rep)+indent < margin:
            return rep
        
        str = '('+self._noderepr()+':'
        for child in self['children']:
            if isinstance(child, TreeToken):
                str += '\n'+' '*(indent+2)+child.pp(margin, indent+2)
            else:
                str += '\n'+' '*(indent+2)+repr(child)
        return str+')'

    # [XX] rename to print* or something
    # Contributed by trevorcohn1@users.sf.net
    def latex_qtree(self, first=True):
        r"""
        Returns a representation of the tree token compatible with the
        LaTeX qtree package. This consists of the string C{\Tree}
        followed by the parse tree represented in bracketed notation.

        For example, the following result was generated from a parse tree of
        the sentence C{The announcement astounded us}::

          \Tree [.I'' [.N'' [.D The ] [.N' [.N announcement ] ] ]
              [.I' [.V'' [.V' [.V astounded ] [.N'' [.N' [.N us ] ] ] ] ] ] ]

        See U{http://www.ling.upenn.edu/advice/latex.html} for the LaTeX
        style file for the qtree package.

        @return: A latex qtree representation of this tree.
        @rtype: C{string}
        @param first: Internal flag used in recursive call.
        @type first: boolean
        """
        str = ''
        if first:
            str = r'\Tree '
        str += '[.' + self._noderepr() + ' ' 
        for child in self['children']:
            if isinstance(child, TreeToken):
                str += child.latex_qtree(False) + ' '
            else:
                str += repr(child) + ' '
        str += ']'
        return str

    # [XX] add output-to-treebank method.

    #////////////////////////////////////////////////////////////
    # Parsing
    #////////////////////////////////////////////////////////////
    
    # [XX] rename to parse_treebank!
    def parse(s, addlocs=False, source=None, startpos=0):
        try:
            treetok, pos = TreeToken._parse(s, addlocs, source, startpos)
            if pos != len(s): raise ValueError
            return treetok
        except:
            raise #ValueError('Bad treebank tree')
    parse = staticmethod(parse)

    def _parse(s, addlocs=False, source=None, pos=0):
        SPACE = re.compile(r'\s*')
        WORD = re.compile(r'\s*([^\s\(\)]*)\s*')

        # Skip any initial whitespace.
        pos = SPACE.match(s, pos).end()

        stack = []
        while pos < len(s):
            # Beginning of a tree/subtree.
            if s[pos] == '(':
                match = WORD.match(s, pos+1)
                stack.append(TreeToken(node=match.group(1),
                                       children=[]))
                pos = match.end()

            # End of a tree/subtree.
            elif s[pos] == ')':
                pos = SPACE.match(s, pos+1).end()
                if len(stack) == 1: return stack[0], pos
                stack[-2]['children'].append(stack[-1])
                stack.pop()

            # Leaf token.
            else:
                match = WORD.match(s, pos)
                leaf = Token(text=match.group(1))
                if addlocs:
                    leaf['loc'] = CharSpanLocation(pos, match.end(),
                                                   source)
                stack[-1]['children'].append(leaf)
                pos = match.end()

        raise ValueError, 'mismatched parens'
    _parse = staticmethod(_parse)

class TreebankTokenizer(TokenizerI):
    def __init__(self, addlocs=True, propnames={}):
        self._addlocs = addlocs
        self._props = propnames

    def _subtoken_generator(self, token):
        text_prop = self._props.get('text', 'text')
        loc_prop = self._props.get('loc', 'loc')

        # [XX] currently these are ignored:
        subtokens_loc_prop = self._props.get('subtokens.loc', 'loc')
        tree_prop = self._props.get('subtokens.tree', 'tree')
        node_prop = self._props.get('subtokens.tree.node', 'tree')
        leaf_prop = self._props.get('subtokens.tree.leaf.text', 'text')

        # Extract the token's text.
        text = token[text_prop]
        if not isinstance(text, str): text = ''.join(text)
        text = text.strip()

        # Get the token's source & start position.
        source = token[loc_prop].source()
        pos = token[loc_prop].start()

        # Parse trees until we reach the end of the string
        trees = []
        while pos < len(text):
            tree, pos = TreeToken._parse(text, source, pos)
            yield tree

        # Add the trees to token.
        token[subtokens_prop] = trees

    def xtokenize(self, token):
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        token[subtokens_prop] = self._subtoken_generator(token)
        
    def tokenize(self, token):
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        token[subtokens_prop] = list(self._subtoken_generator(token))

    def raw_tokenize(self, token):
        "Not implemented by TreebankTokenizer"
        raise NotImplementedError, "Not implemented by TreebankTokenizer"
    
    def raw_xtokenize(self, token):
        "Not implemented by TreebankTokenizer"
        raise NotImplementedError, "Not implemented by TreebankTokenizer"
        
        
######################################################################
## Parented Tree Token & Multi-Parented Tree Token
######################################################################

class _AbstractChildList(list):
    """
    A specialized list that is used to hold the children of a
    C{(Multi)ParentedTreeToken}.  This class is responsible for
    maintaining all C{(Multi)ParentedTreeToken}s' parent pointers.  In
    particular:
    
      - Whenever a new child is added, L{_setparent} is called,
        which should update that child's parent pointer to point
        at self.
        
      - Whenever a child is removed, L{_delparent} is called, which
        should remove the child's parent pointer to self.

    The definitions of C{_delparent} and C{_setparent} are left to the
    subclasses, since they need to be different for
    C{ParentedTreeToken} and C{MultiParentedTreeToken}.
    """
    def __init__(self, parent, children):
        """
        Create a new child list.
        
        @param parent: The tree token that will use this child list
            to hold its children.
        @param children: The contents of the new child list.
        """
        self._parent = parent
        super(_AbstractChildList, self).__init__(children)
        for child in children:
            self._setparent(child)

    #////////////////////////////////////////////////////////////
    # Parent management
    #////////////////////////////////////////////////////////////

    def _setparent(self, child):
        """
        Update C{child}'s parent pointer to point to self.
        """
        raise AssertionError, 'Abstract base class'
    
    def _delparent(self, child):
        """
        Remove self from C{child}'s parent pointer.
        """
        raise AssertionError, 'Abstract base class'

    #////////////////////////////////////////////////////////////
    # Methods that add/remove children
    #////////////////////////////////////////////////////////////
    # Every method that adds or removes a child must make
    # appropriate calls to _setparent() and _delparent().
    
    def __delitem__(self, i):
        self._delparent(self[i])
        super(_AbstractChildList, self).__delitem__(i)

    def __delslice__(self, start, end):
        for i in range(start, end): self._delparent(self[i])
        super(_AbstractChildList, self).__delslice__(start, end)

    def __setitem__(self, i, child):
        self._delparent(self[i])
        self._setparent(child)
        super(_AbstractChildList, self).__setitem__(i, child)

    def __setslice__(self, start, end, children):
        for i in range(start, end): self._delparent(self[i])
        for val in children: self._setparent(val)
        super(_AbstractChildList, self).__setslice__(start, end, children)

    def append(self, child):
        self._setparent(child)
        super(_AbstractChildList, self).append(child)

    def extend(self, children):
        for val in children: self._setparent(val)
        super(_AbstractChildList, self).extend(children)

    def insert(self, i, child):
        self._setparent(child)
        super(_AbstractChildList, self).insert(i, child)

    def pop(self):
        self._delparent(self[-1])
        return super(_AbstractChildList, self).pop()

    def remove(self, child):
        i = self.index(child)
        self._delparent(self[i])
        super(_AbstractChildList, self).remove(child)

class _ParentedChildList(_AbstractChildList):
    """
    A specialized list that is used to hold the children of a
    C{ParentedTreeToken}.  This class is responsible for maintaining
    all C{ParentedTreeToken}s' parent pointers.
    """
    def _delparent(self, child):
        ## Ignore leaves.
        #if not isinstance(child, TreeToken): return
        
        # Sanity check: child's parent should be self._parent
        assert child.get('parent') == self._parent
        
        # Delete child's parent pointer.
        dict.__setitem__(child, 'parent', None)
        #child['parent'] = None

    def _setparent(self, child):
        ## Ignore leaves.
        #if not isinstance(child, TreeToken): return

        # If child is a non-parented tree, complain.
        if (isinstance(child, TreeToken) and
            not isinstance(child, ParentedTreeToken)):
            raise ValueError('inserting a non-parented subtree '+
                             'into a parented tree')

        # If child already has a parent, complain.
        if child.get('parent') is not None:
            raise ValueError, 'redefining parent for %r' % child

        # Set child's parent pointer.
        dict.__setitem__(child, 'parent', self._parent)
        #child['parent'] = self._parent
        
class _MultiParentedChildList(_AbstractChildList):
    """
    A specialized list that is used to hold the children of a
    C{MultiParentedTreeToken}.  This class is responsible for
    maintaining all C{MultiParentedTreeToken}s' parent pointers.
    """
    def _delparent(self, child):
        ## Ignore leaves.
        #if not isinstance(child, TreeToken): return
        
        # Sanity check: one of child's parents should be self._parent
        assert self._parent in child['parents']
        
        ## Delete one copy of child's parent pointer to self._parent
        #child['parents'].remove(self._parent)

    def _setparent(self, child):
        # Ignore leaves.
        #if not isinstance(child, TreeToken): return

        # If child is a non-parented tree, complain.
        if (isinstance(child, TreeToken) and
            not isinstance(child, MultiParentedTreeToken)):
            raise ValueError('inserting a non-multi-parented subtree '+
                             'into a multi-parented tree')

        # Add self._parent as a parent pointer.
        child.setdefault('parents',[]).append(self._parent)
    
class ParentedTreeToken(TreeToken):
    """
    A specialized version of C{TreeToken} that uses the C{parent}
    property to point a unique parent.  For C{ParentedTreeTokens} with
    no parent, the C{parent} property's value is C{None}.

    Each C{ParentedTreeToken} may have at most one parent.  In
    particular, subtrees may not be shared.  Any attempt to reuse a
    single C{ParentedTreeToken} as a child of more than one parent (or
    as multiple children of the same parent) will cause a
    C{ValueError} exception to be raised.
    
    The C{parent} property is maintained automatically.  Any attempt
    to directly modify or delete it will result in a C{ValueError}
    exception.

    C{ParentedTreeTokens} should never be used in the same tree as
    C{TreeTokens} or C{MultiParentedTreeTokens}.  Mixing tree token
    implementations may result in incorrect parent pointers and in
    C{ValueError} exceptions.
    """
    # The parent pointer is stored in the 'parent' property
    def __init__(self, **properties):
        dict.__setitem__(self, 'parent', None)
        dict.__setitem__(self, 'children', []) # Placeholder
        super(ParentedTreeToken, self).__init__(**properties)
        dict.__setitem__(self, 'children', 
                         _ParentedChildList(self, properties['children']))
        
    #////////////////////////////////////////////////////////////
    # Preserve the "parent" and "children" properties.
    #////////////////////////////////////////////////////////////
    def __setitem__(self, property, value):
        if property in ('parent', 'children'):
            raise ValueError('%r property may not be modified by hand' %
                             property)
        super(ParentedTreeToken, self).__setitem__(property, value)

    def __delitem__(self, property):
        if property in ('parent', 'children'):
            raise ValueError('%r property may not be deleted' % property)
        super(ParentedTreeToken, self).__delitem__(property)

    def copy(self):
        if self['parent'] is not None:
            raise ValueError('Only root trees may be copied.')

    def clear(self):
        p,c = self['parent'], self['children']
        super(ParentedTreeToken, self).clear()
        dict.__setitem__(self, 'parent', p)
        dict.__setitem__(self, 'children', c)

    def pop(self, property, default=None):
        if property in ('parent', 'children'):
            raise ValueError('%r property may not be deleted' % property)
        return super(ParentedTreeToken, self).pop(property, default)

    def popitem(self):
        if len(self) == 2:
            # [XX] Should we raise ValueError or KeyError here??
            raise ValueError('"children" and "parent" properties may '+
                             'not be deleted')
        p,c = self['parent'], self['children']
        del self['parent'], self['children']
        item = super(ParentedTreeToken, self).popitem()
        dict.__setitem__(self, 'parent', p)
        dict.__setitem__(self, 'children', c)
        return item

    def update(self, src):
        p,c = self['parent'], self['children']
        super(ParentedTreeToken, self).update(src)
        dict.__setitem__(self, 'parent', p)
        dict.__setitem__(self, 'children', c)

class MultiParentedTreeToken(TreeToken):
    """
    A specialized version of C{TreeToken} that uses the C{parents}
    property to store a list of pointers to its parents.  For
    C{ParentedTreeTokens} with no parent, the C{parents} property's
    value is C{[]}.

    Each C{MultiParentedTreeToken} may have zero or more parents.  In
    particular, subtrees may be shared.  If a single
    C{MultiParentedTreeToken} is used as multiple children of the same
    parent, then that parent will appear multiple times in its
    C{parents} property.
    
    The C{parents} property is maintained automatically, and should
    never be directly modified.  

    C{MultiParentedTreeTokens} should never be used in the same tree
    as C{TreeTokens} or C{ParentedTreeTokens}.  Mixing tree token
    implementations may result in incorrect parent pointers and in
    C{ValueError} exceptions.
    """
    def __init__(self, **properties):
        dict.__setitem__(self, 'parents', [])
        dict.__setitem__(self, 'children', []) # place-holder.
        super(MultiParentedTreeToken, self).__init__(**properties)
        dict.__setitem__(self, 'children', 
                   _MultiParentedChildList(self, properties['children']))
        
    #////////////////////////////////////////////////////////////
    # Preserve the "parents" and "children" properties.
    #////////////////////////////////////////////////////////////
    def __setitem__(self, property, value):
        if property in ('parents', 'children'):
            raise ValueError('%r property may not be modified by hand' %
                             property)
        super(MultiParentedTreeToken, self).__setitem__(property, value)

    def __delitem__(self, property):
        if property in ('parents', 'children'):
            raise ValueError('%r property may not be deleted' % property)
        super(MultiParentedTreeToken, self).__delitem__(property)

    def copy(self):
        if self['parents'] is not []:
            raise ValueError('Only root trees may be copied.')

    def clear(self):
        p,c = self['parents'], self['children']
        super(MultiParentedTreeToken, self).clear()
        dict.__setitem__(self, 'parents', p)
        dict.__setitem__(self, 'children', c)

    def pop(self, property, default=None):
        if property in ('parents', 'children'):
            raise ValueError('%r property may not be deleted' % property)
        return super(MultiParentedTreeToken, self).pop(property, default)

    def popitem(self):
        if len(self) == 2:
            # [XX] Should we raise ValueError or KeyError here??
            raise ValueError('"children" and "parent" properties may '+
                             'not be deleted')
        p,c = self['parents'], self['children']
        del self['parents'], self['children']
        item = super(MultiParentedTreeToken, self).popitem()
        dict.__setitem__(self, 'parents', p)
        dict.__setitem__(self, 'children', c)
        return item

    def update(self, src):
        p,c = self['parents'], self['children']
        super(MultiParentedTreeToken, self).update(src)
        dict.__setitem__(self, 'parents', p)
        dict.__setitem__(self, 'children', c)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration showing how C{Tree}s and C{TreeToken}s can be
    used.  This demonstration creates a C{Tree}, and loads a
    C{TreeToken} from the L{treebank<nltk.corpus.treebank>} corpus,
    and shows the results of calling several of their methods.
    """
    from nltk.util import DemoInterpreter
    d = DemoInterpreter()
    d.start('Tree Token Demo')
    d.silent("from nltk.tree import *")
    
    # Demonstrate tree parsing.
    d("s = '(S (NP (DT the) (NN cat)) "+
      "(VP (VBD ate) (NP (DT a) (NN cookie))))'")
    d("tree = TreeToken.parse(s)")
    d("print tree")
    d.hline()

    # Demonstrate basic tree accessors.
    d("print tree['node']                    # tree's constituant type")
    d("print tree['children'][0]             # tree's first child")
    d("print tree['children'][1]             # tree's second child")
    d("print tree.height()")
    d("print tree.leaves()")
    d("print tree.get_child([1])")
    d("print tree.get_child([1,1])")
    d("print tree.get_child([1,1,0])")
    d.hline()

    # Demonstrate tree modification.
    d("the_cat = tree.get_child(0)")
    d("the_cat['children'].insert(1, TreeToken.parse('(JJ big)'))")
    d("print tree")
    d("tree.replace_child([1,1,1], TreeToken.parse('(NN cake)'))")
    d("print tree")
    d.hline()

    # Demonstrate parented trees
    d("tree = ParentedTreeToken.convert(tree)   # Add parent pointers")
    d("cake = tree.get_child([1,1,0])")
    d("print cake")
    d("# The parent property holds a parent pointer:")
    d("print cake['parent']")
    d("print cake['parent']['parent']['parent']")
    d("# A root tree's parent is None:")
    d("print tree['parent']")
    d.end()

if __name__ == '__main__':
    demo()
    
