# Natural Language Toolkit: Probability and Statistics
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT


#
# tree -- An xml.etree implementation with linguistic tree operations
#         and parent pointers.


"""
This module defines three classes, extending the xml.etree.ElementTree
module:

  - Tree: Linguistic trees, with support for:
    convenient nested indexing t[1,1,1] instead of t[1][1][1];
    leaves() to return the trees leaf nodes;
    ...

  - ParentedTree: Each element keeps track of a single parent
    pointer, returned by the element's `parent()` method.  Elements
    may have at most one parent; i.e., subtrees may not be shared.
    Any attempt to do use a single element as a child for multiple
    parents will generate a ValueError.

  - MultiParentedTree: Each element keeps track of a list of
    parent pointers, returned by the element's `parents()` method.
    Elements may have zero or more parients; i.e., subtrees may be
    shraed.  If a single Element is used as multiple children of the
    same parent, then that parent will appear multiple times in the
    parents list.

Note: Mixing of etree implementations is not supported.  I.e., you
should never construct a tree that combines elements from ParentedTree
with elements from MultiParentedTree, or elements from either of these
implementations with elements from any other implementation.  Doing so
may result in incorrect parent pointers and ValueError exceptions.
"""

from nltk_lite.etree import ElementTree as ET


######################################################################
# Trees
######################################################################

class _AbstractElement(ET._ElementInterface):
    """
    An abstract base class for Elements.
      - Adds original NLTK functionality.
    """

    def __repr__(self):
        return "<%s %s at %x>" % (self.__class__.__name__,
                                  self.tag, id(self))

    #////////////////////////////////////////////////////////////
    # Indexing (with support for tree positions)
    #////////////////////////////////////////////////////////////

    def __getitem__(self, index):
        if isinstance(index, int):
            return ET._ElementInterface.__getitem__(self, index)
        else:
            if len(index) == 0:
                return self
            elif len(index) == 1:
                return self[int(index[0])]
            else:
                return self[int(index[0])][index[1:]]
    
    def __setitem__(self, index, value):
        if isinstance(index, int):
            return ET._ElementInterface.__setitem__(self, index, value)
        else:
            if len(index) == 0:
                raise IndexError('The tree position () may not be '
                                 'assigned to.')
            elif len(index) == 1:
                self[index[0]] = value
            else:
                self[index[0]][index[1:]] = value
    
    def __delitem__(self, index):
        if isinstance(index, int):
            return ET._ElementInterface.__delitem__(self, index)
        else:
            if len(index) == 0:
                raise IndexError('The tree position () may not be deleted.')
            elif len(index) == 1:
                del self[index[0]]
            else:
                del self[index[0]][index[1:]]
    
    #////////////////////////////////////////////////////////////
    # Basic tree operations
    #////////////////////////////////////////////////////////////

    # BROKEN:
    def leaves(self):
        """
        @return: a list containing this tree's leaves.
        @rtype: C{list}
        """
        leaves = []
        for child in self:
	    try:
                leaves.extend(child.leaves())
            except AttributeError:
                leaves.append(child)
        return leaves

    def flatten(self):
        raise NotImplementedError

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
        for child in self:
            try:
                max_child_height = max(max_child_height, child.height())
            except AttributeError:
                max_child_height = max(max_child_height, 1)
        return 1 + max_child_height

    def treepositions(self, order='preorder'):
        raise NotImplementedError

    def productions(self):
        raise NotImplementedError

    def subtrees(self, filter=None):
        """
        Generate all the subtrees of this tree, optionally restricted
        to trees matching the filter function.
        @type: filter: C{function}
        @param: filter: the function to filter all local trees
        """
        if not filter or filter(self):
            yield self
        for child in self:
            try:
                for subtree in child.subtrees(filter):
                    yield subtree
	    except AttributeError:
		pass

    def copy(self, deep=False):
        raise NotImplementedError

    def freeze(self, leaf_freezer=None):
        raise NotImplementedError

######################################################################
# Parented Trees
######################################################################

class _AbstractParentedElement(_AbstractElement):
    """
    An abstract base class for (multi)parented element tree Elements.
    
      - Whenever a new child is added, L{_setparent} is called,
        which should update that child's parent pointer to point
        at self.
        
      - Whenever a child is removed, L{_delparent} is called, which
        should remove the child's parent pointer to self.
    """
    def __repr__(self):
        return "<%s %s at %x>" % (self.__class__.__name__,
                                  self.tag, id(self))

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
    
    def __delitem__(self, index):
        self._delparent(self[index])
        _AbstractElement.__delitem__(self, index)

    def __delslice__(self, start, stop):
        for index in range(start, stop): self._delparent(self[index])
        _AbstractElement.__delslice__(self, start, stop)

    def __setitem__(self, index, element):
        self._delparent(self[index])
        self._setparent(element)
        _AbstractElement.__setitem__(self, index, element)

    def __setslice__(self, start, stop, elements):
        for index in range(start, stop): self._delparent(self[index])
        for val in elements: self._setparent(val)
        _AbstractElement.__setslice__(self, start, stop, elements)

    def append(self, element):
        self._setparent(element)
        _AbstractElement.append(self, element)

    def extend(self, elements):
        for val in elements: self._setparent(val)
        _AbstractElement.extend(self, elements)

    def insert(self, index, element):
        self._setparent(element)
        _AbstractElement.insert(self, index, element)

    def pop(self):
        self._delparent(self[-1])
        return _AbstractElement.pop(self, )

    def remove(self, element):
        index = self.index(element)
        self._delparent(self[index])
        _AbstractElement.remove(self, element)
    

class _ParentedElement(_AbstractParentedElement):
    """
    A specialized version of etree.ElementTree.Element that keeps
    track of a single parent pointer per element.

    Each _ParentedElement may have at most one parent.  In particular,
    subtrees may not be shared.  Any attempt to reuse a single
    _ParentedElement as a child of more than one parent (or as
    multiple children of the same parent) will cause a ValueError
    exception to be raised.
    
    _ParentedElements should never be used in the same tree as other
    Element implementation classes.  Mixing Element implementations
    may result in incorrect parent pointers and in C{ValueError}
    exceptions.
    """
    def __init__(self, tag, attrib):
        ET._ElementInterface.__init__(self, tag, attrib)
        self._parent = None

    def parent(self):
        return self._parent
        
    def _setparent(self, element):
        assert is_parented_element(element)
        if element._parent is not None:
            raise ValueError, '%r already has a parent' % element
        element._parent = self

    def _delparent(self, element):
        assert is_parented_element(element)
        assert element._parent == self
        element._parent = None

    def makeelement(self, tag, attrib):
        return _ParentedElement(tag, attrib)

def is_parented_element(element):
    return ET.iselement(element) and hasattr(element, '_parent')

class _MultiParentedElement(_AbstractParentedElement):
    """
    A specialized version of etree.ElementTree.Element that keeps
    track of a list of parent pointers for each element.

    Each _ParentedElement may have zero or more parents.  In
    particular, subtrees may be shared.  If a single
    _MultiParentedElement is used as multiple children of the same
    parent, then that parent will appear multiple times in the parents
    list.
    
    _MultiParentedElements should never be used in the same tree as
    other Element implementation classes.  Mixing Element
    implementations may result in incorrect parent pointers and in
    C{ValueError} exceptions.
    """
    def __init__(self, tag, attrib):
        ET._ElementInterface.__init__(self, tag, attrib)
        self._parents = []

    def parents(self):
        return tuple(self._parents)
        
    def _setparent(self, element):
        assert is_multiparented_element(element)
        element._parent.append(self)

    def _delparent(self, element):
        assert is_multiparented_element(element)
        assert self in element._parents
        element._parents.remove(self)

    def makeelement(self, tag, attrib):
        return _ParentedElement(tag, attrib)

def is_multiparented_element(element):
    return ET.iselement(element) and hasattr(element, '_parents')




class ElementTreeImplementation(object):
    """
    Instances of this class can be used as drop-in replacements for
    the xml.etree.ElementTree module.
    """
    def __init__(self, ElementClass):
        self._Element = ElementClass

    def Element(self, tag, attrib={}, **extra):
        attrib = attrib.copy()
        attrib.update(extra)
        return self._Element(tag, attrib)

    ##################################################################
    # Subclasses w/ new constructors
    #-----------------------------------------------------------------
    # These classes needed to have their constructer overridden, to
    # change the default values of tree-building functions to point
    # to the versions in *this file, not in ElementTree.

    def iterparse(self, source, events=None):
        # [XXX] We can't do this without poking around in other
        # people's internals!
        iterator = ET.iterparse(source, events)
        iterator._parser._target = TreeBuilder()
        return iterator

    ##################################################################
    # No dependencies on Element class
    #-----------------------------------------------------------------
    # These functions & classes do not depend, directly or indirectly,
    # on the class used to implement elements; so we can just copy
    # them.

    SubElement = staticmethod(ET.SubElement)
    QName = ET.QName
    iselement = staticmethod(ET.iselement)
    dump = staticmethod(ET.dump)
    tostring= staticmethod(ET.tostring)
    
    ##################################################################
    # Modified Constructor Defaults
    #-----------------------------------------------------------------
    # These classes have default constructor parameter that depend on
    # the class used to implement elements; so we wrap them in
    # functions that provide new defaults.
    
    def TreeBuilder(self, element_factory=None):
        if element_factory is None:
            element_factory = self._Element
        return ET.TreeBuilder(element_factory)

    def XMLTreeBuilder(self, html=0, target=None):
        if target is None:
            target = self.TreeBuilder()
        return ET.XMLTreeBuilder(html, target)

    XMLParser = XMLTreeBuilder

    ##################################################################
    # Modified Method Defaults
    #-----------------------------------------------------------------
    # The ElementTree class has a method parameter whose default value
    # depends on the class used to implement elements; so we replace
    # it with a new subclass (_ElementTree) that stores a private
    # pointer back to the ElementTreeImplementation instance; and uses it
    # to construct an appropriate default for the method parameter.

    def ElementTree(self, element=None, file=None):
        return self._ElementTree(self, element, file)
    class _ElementTree(ET.ElementTree):
        def __init__(self, etbase, element, file):
            self.__default_parser_class = etbase.XMLTreeBuilder
            ET.ElementTree.__init__(element, file)
        def parse(self, source, parser=None):
            if not parser:
                parser = self.__default_parser_class()
            ET.ElementTree.parse(self, source, parser)

    ##################################################################
    # Indirect dependencies on Element class
    #-----------------------------------------------------------------
    # These functions depend indirectly on the class used to implement
    # elements; so we need to redefine them.  Each method in this
    # section is copied verbatim from etree/ElementTree.py, with the
    # following exceptions: a 'self' parameter is added.  And global
    # variables that depend on the Element class are replaced with
    # local versions.  E.g., "XMLTreeBuilder" is replaced with
    # "self.XMLTreeBuilder".
    
    def Comment(self, text=None):
        element = self.Element(Comment)
        element.text = text
        return element
    
    def ProcessingInstruction(self, target, text=None):
        element = self.Element(self.ProcessingInstruction)
        element.text = target
        if text:
            element.text = element.text + " " + text
        return element

    PI = ProcessingInstruction

    def parse(self, source, parser=None):
        tree = self.ElementTree()
        tree.parse(source, parser)
        return tree
    
    def XML(self, text):
        parser = self.XMLTreeBuilder()
        parser.feed(text)
        return parser.close()
    
    def XMLID(self, text):
        parser = self.XMLTreeBuilder()
        parser.feed(text)
        tree = parser.close()
        ids = {}
        for elem in tree.getiterator():
            id = elem.get("id")
            if id:
                ids[id] = elem
        return tree, ids
    
    fromstring = XML


ParentedTree = ElementTreeImplementation(_ParentedElement)
MultiParentedTree = ElementTreeImplementation(_MultiParentedElement)


def demo():
    from nltk_lite.contrib.tree import ParentedTree as PT

    TREE = ("<s><np><jj>Snow</jj><nn>flakes</nn></np>"
            "<vp tense='past'><v>fell</v>"
            "<pp><p>on</p><np><dt>the</dt><nn>table</nn></np></pp>"
            "</vp></s>")

    sent = PT.fromstring(TREE)
    table = sent[1,1,1,1]
    print PT.tostring(table)
    print PT.tostring(table.parent())

    print "leaves:", sent.leaves()
    print "height:", sent.height()
    print "subtrees:", list(sent.subtrees())

    def spine(elt):
        if elt is None: return []
        return [elt.tag] + spine(elt.parent())
    print spine(table)

    def spine_with_attribs(elt):
        if elt is None: return []
        label = elt.tag
        if elt.attrib:
            attrib = ['%s=%s' % i for i in elt.attrib.items()]
            label += '<%s>' % ', '.join(attrib)
        return [label] + spine_with_attribs(elt.parent())
    print spine_with_attribs(table)

    print PT.tostring(sent)
    del sent[1][1][1]
    # del sent[1,1,1] BROKEN
    print PT.tostring(sent)


if __name__ == '__main__':
    demo()

