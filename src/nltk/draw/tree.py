# Natural Language Toolkit: Graphical Representations for Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Graphically display a C{Tree} or C{TreeToken}.
"""

from Tkinter import *
from nltk.tree import Tree, TreeToken
from nltk.token import Token, Location
from nltk.draw import *

class TreeSegmentWidget(CanvasWidget):
    """
    A canvas widget that displays a single segment of a hierarchical tree.
    """
    def __init__(self, canvas, node, subtrees, **attribs):
        """
        @type node: 
        @type subtrees: C{list} of C{CanvasWidgetI}
        """
        self._node = node
        self._subtrees = subtrees
        
        self._roof = 0
        self._color = 'black'
        self._fill = ''
        self._xspace = 10
        self._yspace = 15
        self._width = 1

        self._lines = [canvas.create_line(0,0,0,0) for c in subtrees]
        self._polygon = canvas.create_polygon(0,0,0,0,0,0, fill='',
                                              outline='')
        CanvasWidget.__init__(self, canvas, **attribs)
        self._add_child_widget(node)
        for subtree in subtrees:
            self._add_child_widget(subtree)

    def __setitem__(self, attr, value):
        if attr == 'width':
            self._width = value
            self.canvas().itemconfig(self._polygon, width=value)
            for l in self._lines: self.canvas().itemconfig(l, width=value)
        elif attr in ('roof', 'color', 'fill'):
            if attr == 'roof': self._roof = value
            elif attr == 'color': self._color = value
            elif attr == 'fill': self._fill = value
            
            if self._roof:
                for l in self._lines: self.canvas().itemconfig(l, fill='')
                self.canvas().itemconfig(self._polygon, fill=self._fill,
                                         outline=self._color)
            else:
                for line in self._lines:
                    self.canvas().itemconfig(line, fill=self._color)
                self.canvas().itemconfig(self._polygon, outline='', fill='')
        elif attr in ('xspace', 'yspace'):
            if attr == 'xspace': self._xspace = value
            elif attr == 'yspace': self._yspace = value
            self.update(self._node)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'roof': return self._roof
        elif attr == 'color': return self._color
        elif attr == 'fill' : return self._fill
        elif attr == 'xspace': return self._xspace
        elif attr == 'yspace': return self._yspace
        elif attr == 'yspace': return self._width
        else:
            return CanvasWidget.__getitem__(self, attr)
        
    def node(self):
        return self._node

    def subtrees(self):
        return self._subtrees

    def set_node(self, node):
        """
        Set the node to C{node}.
        """
        self._remove_child_widget(self._node)
        self._add_child_widget(node)
        self._node = node
        self.update(self._node)

    def replace_child(self, oldchild, newchild):
        """
        Replace the child C{oldchild} with C{newchild}.
        """
        index = self._subtrees.index(oldchild)
        self._subtrees[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        index = self._subtrees.index(child)
        del self._subtrees[index]
        self._remove_child_widget(child)
        self.update(self._node)

    def insert_child(self, index, child):
        self._subtrees.insert(index, child)
        self._add_child_widget(child)

    def _tags(self):
        return self._lines + [self._polygon]

    def _top(self, child):
        if isinstance(child, TreeSegmentWidget):
            bbox = child.node().bbox()
        else:
            bbox = child.bbox()
        return ((bbox[2]+bbox[0])/2.0, bbox[1])

    def _update(self, child):
        # Update the polygon.
        (nodex1, nodey1, nodex2, nodey2) = self._node.bbox()
        nodecenter = (nodex1+nodex2)/2.0

        (xmin, ymin, xmax, ymax) = self._subtrees[0].bbox()
        for subtree in self._subtrees[1:]:
            bbox = subtree.bbox()
            xmin = min(xmin, bbox[0])
            ymin = min(ymin, bbox[1])
            xmax = max(xmax, bbox[2])

        self.canvas().coords(self._polygon, nodecenter, nodey2, xmin, 
                             ymin, xmax, ymin, nodecenter, nodey2)
        
        # Redraw the lines that touch child.
        if child is self._node:
            # The node changed; redraw all lines.
            for subtree in self._subtrees:
                self._update(subtree)
            return
        else:
            # A subtree changed; redraw its line.
            node_bbox = self._node.bbox()
            nodex = (node_bbox[2]+node_bbox[0])/2.0
            nodey = node_bbox[3]

            line = self._lines[self._subtrees.index(child)]
            
            (childx, childy) = self._top(child)
            self.canvas().coords(line, nodex, nodey, childx, childy-3)

    def _manage(self):
        # Position the children.
        if len(self._subtrees) == 0: return
        
        node_bbox = self._node.bbox()
        nodex = (node_bbox[2]+node_bbox[0])/2.0
        nodey = node_bbox[3]

        # Put the subtrees in a line.
        x = 0
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dy = nodey - subtree_bbox[1] + self._yspace
            dx = x - subtree_bbox[0]
            subtree.move(dx, dy)
            x += subtree_bbox[2] - subtree_bbox[0] + self._xspace

        # Find the center of their tops.
        center = 0
        for subtree in self._subtrees:
            center += self._top(subtree)[0]
        center /= len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(nodex-center, 0)

        # Update lines to subtrees.
        for subtree in self._subtrees:
            self._update(subtree)

    def __repr__(self):
        return '[TreeSeg %s: %s]' % (self._node, self._subtrees)

def _tree_to_treeseg(canvas, tree, make_node, make_leaf,
                         tree_attribs, node_attribs,
                         leaf_attribs, loc_attribs):
    if isinstance(tree, Tree) or isinstance(tree, TreeToken):
        node = make_node(canvas, tree.node(), **node_attribs)
        subtrees = [_tree_to_treeseg(canvas, child, make_node, make_leaf, 
                                     tree_attribs, node_attribs,
                                     leaf_attribs, loc_attribs)
                    for child in tree.children()]
        return TreeSegmentWidget(canvas, node, subtrees, **tree_attribs)
    elif isinstance(tree, Token):
        leaf = make_leaf(canvas, tree.type(), **leaf_attribs)
        loc = TextWidget(canvas, str(tree.loc()), **loc_attribs)
        return StackWidget(canvas, leaf, loc, align='center')
    else:
        return make_leaf(canvas, tree, **leaf_attribs)

def tree_to_treesegment(canvas, tree, make_node=TextWidget,
                        make_leaf=TextWidget, **attribs):
    """
    Convert a C{Tree} or a C{TreeToken} into a C{TreeSegmentWidget}.

    @param make_node: A C{CanvasWidget} constructor or a function that
        creates C{CanvasWidgets}.  C{make_node} is used to convert
        the C{Tree}'s nodes into C{CanvasWidgets}.  If no constructor
        is specified, then C{TextWidget} will be used.
    @param make_leaf: A C{CanvasWidget} constructor or a function that
        creates C{CanvasWidgets}.  C{make_leaf} is used to convert
        the C{Tree}'s leafs into C{CanvasWidgets}.  If no constructor
        is specified, then C{TextWidget} will be used.
    @param attribs: Attributes for the canvas widgets that make up the
        returned C{TreeSegmentWidget}.  Any attribute beginning with
        C{'tree_'} will be passed to all C{TreeSegmentWidget}s (with
        the C{'tree_'} prefix removed.  Any attribute beginning with
        C{'node_'} will be passed to all nodes.  Any attribute
        beginning with C{'leaf_'} will be passed to all leaves.  And
        any attribute beginning with C{'loc_'} will be passed to all
        text locations (for C{TreeToken}s).
    """
    # Process attribs.
    tree_attribs = {}
    node_attribs = {}
    leaf_attribs = {}
    loc_attribs = {}

    for (key, value) in attribs.items():
        if key[:5] == 'tree_': tree_attribs[key[5:]] = value
        elif key[:5] == 'node_': node_attribs[key[5:]] = value
        elif key[:5] == 'leaf_': leaf_attribs[key[5:]] = value
        elif key[:4] == 'loc_': loc_attribs[key[4:]] = value
        else: raise ValueError('Bad attribute: %s' % key)
    return _tree_to_treeseg(canvas, tree, make_node, make_leaf,
                                tree_attribs, node_attribs,
                                leaf_attribs, loc_attribs)

class TreeWidget(CanvasWidget):
    """
    This class will likely be restructured or deleted.
    
    Display a tree; keep a 2-way map from TreeSegmentWidget to Tree.

    collapse() and expand() and toggle_collapsed().

    User interface should use *trees only*; and whatever CanvasWidgets
    they specified for nodes & leaves.  It should *not* include
    TreeSegmentWidgets.  Actually, it shouldn't even include node/leaf
    widgets, since I keep destroying & recreating them.

    Add callbacks:
      - C{bind_subtree_click}
      - C{bind_subtree_drag} [turns on shapeable]
      - C{bind_node_click}
      - C{bind_leaf_click}
      - C{bind_leaf_drag} [turns on shapeable]
      - C{bind_loc_click}

    Attributes:
      - node_*
      - leaf_*
      - loc_*
      - roof_color
      - roof_fill
      - line_color
      - shapeable
      - draggable
      - xspace
      - yspace
    """
    def __init__(self, canvas, tree, make_node=TextWidget,
                 make_leaf=TextWidget, **attribs):
        self._widget = {} # Tree -> widget
        self._tree = {} # widget -> Tree
        self._collapsed = {}

        # Attributes.
        self._nodeattribs = {}
        self._leafattribs = {}
        self._locattribs = {'color': '#008000'}
        self._line_color = '#008080'
        self._roof_color = '#008080'
        self._roof_fill = '#c0c0c0'
        self._shapeable = 0
        self._xspace = 10
        self._yspace = 10

        # Node & leaf canvas widget constructors
        self._make_node = make_node
        self._make_leaf = make_leaf

        self._top_treeseg = None
        self._top_tree = None
        CanvasWidget.__init__(self, canvas, **attribs)
        self._set_tree(tree)

    def _set_tree(self, tree):
        self._top_tree = tree
        self._widget = {} # Tree -> widget
        self._tree = {} # widget -> Tree
        oldseg = self._top_treeseg

        # Create the new tree segment.
        self._top_treeseg = self._make_treeseg(tree)

        # Remove the old segemnt and add the new one.
        if oldseg is not None: self._remove_child_widget(oldseg)
        self._add_child_widget(self._top_treeseg)

        # Put the new segment where the old one was.
        if oldseg is not None:
            (oldx1, oldy1, oldx2, oldy2) = oldseg.node().bbox()
            (newx1, newy1, newx2, newy2) = self._top_treeseg.node().bbox()
            self._top_treeseg.move((oldx1+oldx2-newx1-newx2)/2.0, oldy1-newy1)
        
    def __setitem__(self, attr, value):
        if attr[:5] == 'node_': self._nodeattribs[attr[5:]] = value
        elif attr[:5] == 'leaf_': self._leafattribs[attr[5:]] = value
        elif attr[:4] == 'loc_': self._locattribs[attr[4:]] = value
        elif attr == 'line_color': self._line_color = value
        elif attr == 'roof_color': self._roof_color = value
        elif attr == 'roof_fill': self._roof_fill = value
        elif attr == 'shapeable': self._shapeable = value
        elif attr == 'xspace': self._xspace = value
        elif attr == 'yspace': self._yspace = value
        else:
            CanvasWidget.__setitem__(self, attr, value)
            return

        # Redraw the tree.
        if self._top_treeseg:
            old_treeseg = self._top_treeseg
            self._set_tree(self._top_tree)
            old_treeseg.destroy()

    def __getitem__(self, attr):
        if attr[:5] == 'node_':
            return self._nodeattribs.get(attr[5:], None)
        elif attr[:5] == 'leaf_':
            return self._leafattribs.get(attr[5:], None)
        elif attr[:4] == 'loc_':
            return self._locattribs.get(attr[4:], None)
        elif attr == 'line_color': return self._line_color
        elif attr == 'roof_color': return self._roof_color
        elif attr == 'roof_fill': return self._roof_fill
        elif attr == 'shapeable': return self._shapeable
        elif attr == 'xspace': return self._xspace
        elif attr == 'yspace': return self._yspace
        else: return CanvasWidget.__getitem__(self, attr)
        
    def _tags(self): return []

    def toggle_collapsed(self, treeseg):
        """
        """
        tree = self._tree[treeseg]
        self._remove_tree(treeseg)
        
        if treeseg['roof']:
            self._collapsed[tree] = 0
            newseg = self._make_treeseg(tree)
        else:
            self._collapsed[tree] = 1
            newseg = self._make_treeseg(tree)
        
        # Put the new segment where the old one was.
        (oldx1, oldy1, oldx2, oldy2) = treeseg.node().bbox()
        (newx1, newy1, newx2, newy2) = newseg.node().bbox()
        newseg.move((oldx1+oldx2-newx1-newx2)/2.0, oldy1-newy1)

        if treeseg.parent() is self:
            self._top_treeseg = newseg
            self._remove_child_widget(treeseg)
            self._add_child_widget(newseg)
        elif isinstance(treeseg.parent(), TreeSegmentWidget):
            treeseg.parent().replace_child(treeseg, newseg)
        else:
            treeseg.parent().replace_child(treeseg, newseg)
        treeseg.destroy()

        # We could call self.manage here; but we shouldn't have to

    def collapsed(self, tree):
        """
        @return: 1 if the specified tree is collapsed.
        """
        return self._collapsed.get(tree, 0)
    
    def expand(self, treeseg):
        if treeseg['roof']: self.toggle_collapsed(treeseg)
    def collapse(self, treeseg):
        if not treeseg['roof']: self.toggle_collapsed(treeseg)

    def _remove_tree(self, treeseg):
        """
        Remove all entries in _tree and _widget that have to do with
        C{tree}. 
        """
        if isinstance(treeseg, TreeSegmentWidget):
            del self._widget[self._tree[treeseg]]
            del self._tree[treeseg]
            for subtree in treeseg.subtrees(): self._remove_tree(subtree)

    def _make_treeseg(self, tree):
        """
        Create a new tree segment from C{tree}.
        """
        make_node = self._make_node
        make_leaf = self._make_leaf
        collapsed = self._collapsed.get(tree, 0)

        # Convert a tree or treetoken.
        if isinstance(tree, Tree) or isinstance(tree, TreeToken):
            # Create the node canvas widget
            node = make_node(self.canvas(), tree.node(),
                             **self._nodeattribs)

            # Create the subtree canvas widgets.
            if collapsed and isinstance(tree, Tree):
                leaves = [self._make_treeseg(l) for l in tree.leaves()]
                seq = SequenceWidget(self.canvas(), align='top',
                                 space=self._xspace, *leaves)
                subtrees = [seq]
            elif collapsed and isinstance(tree, TreeToken):
                leaves = [self._make_treeseg(l.type()) for
                          l in tree.leaves()]
                seq = SequenceWidget(self.canvas(), align='top',
                                 space=self._xspace, *leaves)
                loc = TextWidget(self.canvas(), str(tree.loc()),
                             **self._locattribs)
                stack = StackWidget(self.canvas(), seq, loc, align='center')
                stack['draggable'] = self._shapeable
                subtrees = [stack]
            else: 
                subtrees = [self._make_treeseg(c) for c in tree.children()]

            # Create the tree segment.
            if collapsed:
                treeseg = TreeSegmentWidget(self.canvas(), node, subtrees,
                                        roof=1, fill=self._roof_fill,
                                        color=self._roof_color,
                                        xspace=self._xspace,
                                        yspace=self._yspace)
            else:
                treeseg = TreeSegmentWidget(self.canvas(), node, subtrees,
                                        color=self._line_color,
                                        xspace=self._xspace,
                                        yspace=self._yspace)

            treeseg['draggable'] = self._shapeable
            treeseg.bind_click(self.toggle_collapsed)
            
            self._widget[tree] = treeseg
            self._tree[treeseg] = tree
            return treeseg
        elif isinstance(tree, Token):
            leaf = make_leaf(self.canvas(), tree.type(), **self._leafattribs)
            loc = TextWidget(self.canvas(), str(tree.loc()), **self._locattribs)
            stack = StackWidget(self.canvas(), leaf, loc, align='center')
            stack['draggable'] = self._shapeable
            return stack
        else:
            leaf = make_leaf(self.canvas(), tree, **self._leafattribs)
            leaf['draggable'] = self._shapeable
            return leaf

import random
if __name__ == '__main__':
    def fill(cw):
        cw['fill'] = '#%06d' % random.randint(0,999999)
    
    cf = CanvasFrame(width=600, closeenough=2)
    
    tree = Tree('S', Tree('NP', 'the', 'very', 'big', 'cat'),
                Tree('VP', Tree('Adv', 'sorta'), Tree('V', 'saw'),
                     Tree('NP', Tree('Det', 'the'),
                          Tree('N', 'dog'))))
    tc = TreeWidget(cf.canvas(), tree, draggable=1,
                node_font=('helvetica', 14, 'bold'),
                leaf_font=('helvetica', 12, 'italic'),
                leaf_color='orange4', node_color='blue')
    cf.add_widget(tc, 10, 10)

    def boxit(canvas, text):
        return BoxWidget(canvas, TextWidget(canvas, text))

    treetok = TreeToken('S', TreeToken('NP', Token('the',0),
                                       Token('cat',1)),
                TreeToken('VP', TreeToken('V', Token('saw',2)),
                     TreeToken('NP', TreeToken('Det', Token('the',3)),
                          TreeToken('N', Token('dog',4)))))
    tc2 = TreeWidget(cf.canvas(), treetok, TextWidget, boxit, shapeable=1)

    #def color(cw, tc2=tc2):
    #    tree = tc2.tree(cw)
    #    tc2.toggle_collapsed(cw)
    #    widget = tc2.treesegment(tree)
    #    widget['color'] = '#%06d' % random.randint(0,999999)
    #    
    #tc2.treesegment(treetok.children()[1]).bind_click(color)

    cf.add_widget(tc2, 300, 10)

    tc3 = tree_to_treesegment(cf.canvas(), treetok, tree_color='green4')
    tc3['draggable'] = 1
    cf.add_widget(tc3, 200, 100)

