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

##//////////////////////////////////////////////////////
##  Tree Segment
##//////////////////////////////////////////////////////

class TreeSegmentWidget(CanvasWidget):
    """
    A canvas widget that displays a single segment of a hierarchical
    tree.  Each C{TreeSegmentWidget} connects a single X{node widget}
    to a sequence of zero or more X{subtree widgets}.  By default, the
    bottom of the node is connected to the top of each subtree by a
    single line.  However, if the C{roof} attribute is set, then a
    single triangular "roof" will connect the node to all of its
    children.  

    Attributes:
      - C{roof}: What sort of connection to draw between the node and
        its subtrees.  If C{roof} is true, draw a single triangular
        "roof" over the subtrees.  If C{roof} is false, draw a line
        between each subtree and the node.  Default value is false.
      - C{xspace}: The amount of horizontal space to leave between
        subtrees when managing this widget.  Default value is 10.
      - C{yspace}: The amount of space to place between the node and
        its children when managing this widget.  Default value is 15.
      - C{color}: The color of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is C{'#006060'}.
      - C{fill}: The fill color for the triangular roof.  Default
        value is C{''} (no fill).
      - C{width}: The width of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is 1.
      - C{orientation}: Determines whether the tree branches downwards
        or rightwards.  Possible values are C{'horizontal'} and
        C{'vertical'}.  The default value is C{'vertical'} (i.e.,
        branch downwards).
      - C{draggable}: whether the widget can be dragged by the user.

    The following attributes may also be added in the near future:
      - C{lineM{n}_color}: The color of the line connecting the node
        to its C{M{n}}th subtree.
      - C{lineM{n}_color}: The width of the line connecting the node
        to its C{M{n}}th subtree.
      - C{lineM{n}_color}: The dash pattern of the line connecting the
        node to its C{M{n}}th subtree.
        
    """
    def __init__(self, canvas, node, subtrees, **attribs):
        """
        @type node: 
        @type subtrees: C{list} of C{CanvasWidgetI}
        """
        self._node = node
        self._subtrees = subtrees

        # Attributes
        self._horizontal = 0
        self._roof = 0
        self._xspace = 10
        self._yspace = 15

        # Create canvas objects.
        self._lines = [canvas.create_line(0,0,0,0, fill='#006060')
                       for c in subtrees]
        self._polygon = canvas.create_polygon(0,0, fill='', state='hidden',
                                              outline='#006060')

        # Register child widgets (node + subtrees)
        self._add_child_widget(node)
        for subtree in subtrees:
            self._add_child_widget(subtree)

        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        canvas = self.canvas()
        if attr is 'roof':
            self._roof = value
            if self._roof:
                for l in self._lines: canvas.itemconfig(l, state='hidden')
                canvas.itemconfig(self._polygon, state='normal')
            else:
                for l in self._lines: canvas.itemconfig(l, state='normal')
                canvas.itemconfig(self._polygon, state='hidden')
        elif attr == 'orientation': 
            if value == 'horizontal': self._horizontal = 1
            elif value == 'vertical': self._horizontal = 0
            else:
                raise ValueError('orientation must be horizontal or vertical')
        elif attr == 'color':
            for l in self._lines: canvas.itemconfig(l, fill=value)
            canvas.itemconfig(self._polygon, outline=value)
        elif attr == 'fill':
            canvas.itemconfig(self._polygon, fill=value)
        elif attr == 'width':
            canvas.itemconfig(self._polygon, {attr:value})
            for l in self._lines: canvas.itemconfig(l, {attr:value})
        elif attr in ('xspace', 'yspace'):
            if attr == 'xspace': self._xspace = value
            elif attr == 'yspace': self._yspace = value
            self.update(self._node)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'roof': return self._roof
        elif attr == 'width':
            return self.canvas().itemcget(self._polygon, attr)
        elif attr == 'color':
            return self.canvas().itemcget(self._polygon, 'outline')
        elif attr == 'xspace': return self._xspace
        elif attr == 'yspace': return self._yspace
        elif attr == 'orientation':
            if self._horizontal: return 'horizontal'
            else: return 'vertical'
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
        if self._roof:
            return [self._polygon]
        else:
            return self._lines

    def _subtree_top(self, child):
        if isinstance(child, TreeSegmentWidget):
            bbox = child.node().bbox()
        else:
            bbox = child.bbox()
        if self._horizontal:
            return (bbox[0], (bbox[1]+bbox[3])/2.0)
        else:
            return ((bbox[0]+bbox[2])/2.0, bbox[1])

    def _node_bottom(self):
        bbox = self._node.bbox()
        if self._horizontal:
            return (bbox[2], (bbox[1]+bbox[3])/2.0)
        else:
            return ((bbox[0]+bbox[2])/2.0, bbox[3])

    def _update(self, child):
        if len(self._subtrees) == 0: return

        # Update the polygon.
        (nodex, nodey) = self._node_bottom()
        (xmin, ymin, xmax, ymax) = self._subtrees[0].bbox()
        for subtree in self._subtrees[1:]:
            bbox = subtree.bbox()
            xmin = min(xmin, bbox[0])
            ymin = min(ymin, bbox[1])
            xmax = max(xmax, bbox[2])
            ymax = max(ymax, bbox[3])
                
        if self._horizontal:
            self.canvas().coords(self._polygon, nodex, nodey, xmin, 
                                 ymin, xmin, ymax, nodex, nodey)
        else:
            self.canvas().coords(self._polygon, nodex, nodey, xmin, 
                                 ymin, xmax, ymin, nodex, nodey)

        # Which lines need to be redrawn?
        if child is self._node: need_update = self._subtrees
        else: need_update = [child]

        # Redraw all lines that need it.
        for subtree in need_update:
            (nodex, nodey) = self._node_bottom()
            line = self._lines[self._subtrees.index(subtree)]
            (subtreex, subtreey) = self._subtree_top(subtree)
            self.canvas().coords(line, nodex, nodey, subtreex, subtreey)

    def _manage_horizontal(self):
        (nodex, nodey) = self._node_bottom()

        # Put the subtrees in a line.
        y = 20
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dx = nodex - subtree_bbox[0] + self._xspace
            dy = y - subtree_bbox[1]
            subtree.move(dx, dy)
            y += subtree_bbox[3] - subtree_bbox[1] + self._yspace

        # Find the center of their tops.
        center = 0.0
        for subtree in self._subtrees:
            center += self._subtree_top(subtree)[1]
        center /= len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(0, nodey-center)

    def _manage_vertical(self):
        (nodex, nodey) = self._node_bottom()

        # Put the subtrees in a line.
        x = 0
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dy = nodey - subtree_bbox[1] + self._yspace
            dx = x - subtree_bbox[0]
            subtree.move(dx, dy)
            x += subtree_bbox[2] - subtree_bbox[0] + self._xspace

        # Find the center of their tops.
        center = 0.0
        for subtree in self._subtrees:
            center += self._subtree_top(subtree)[0]/len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(nodex-center, 0)

    def _manage(self):
        if len(self._subtrees) == 0: return
        
        if self._horizontal: self._manage_horizontal()
        else: self._manage_vertical()
            
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

##//////////////////////////////////////////////////////
##  Tree Widget
##//////////////////////////////////////////////////////

class TreeWidget(CanvasWidget):
    """
    A canvas widget that displays a single C{Tree} or C{TreeToken}.
    C{TreeWidget} manages a group of C{TreeSegmentWidget}s that are
    used to display a C{Tree} or a C{TreeToken}.

    Attributes:
    
      - C{node_M{attr}}: Sets the attribute C{M{attr}} on all of the
        node widgets for this C{TreeWidget}.
      - C{node_M{attr}}: Sets the attribute C{M{attr}} on all of the
        leaf widgets for this C{TreeWidget}.
      - C{loc_M{attr}}: Sets the attribute C{M{attr}} on all of the
        location widgets for this C{TreeWidget} (if it was built from
        a C{TreeToken}).  Note that location widgets are
        C{TextWidget}s. 
      
      - C{xspace}: The amount of horizontal space to leave between
        subtrees when managing this widget.  Default value is 10.
      - C{yspace}: The amount of space to place between the node and
        its children when managing this widget.  Default value is 15.
        
      - C{line_color}: The color of the lines connecting each expanded
        node to its subtrees.
      - C{roof_color}: The color of the outline of the triangular roof
        for collapsed trees.
      - C{roof_fill}: The fill color for the triangular roof for
        collapsed trees.
      - C{width}
      
      - C{orientation}: Determines whether the tree branches downwards
        or rightwards.  Possible values are C{'horizontal'} and
        C{'vertical'}.  The default value is C{'vertical'} (i.e.,
        branch downwards).
        
      - C{shapeable}: whether the subtrees can be independantly
        dragged by the user.  This property simply sets the
        C{draggable} property on all of the C{TreeWidget}'s tree
        segments. 
      - C{draggable}: whether the widget can be dragged by the user.
    """
    def __init__(self, canvas, tree, make_node=TextWidget,
                 make_leaf=TextWidget, **attribs):
        # Node & leaf canvas widget constructors
        self._make_node = make_node
        self._make_leaf = make_leaf
        self._tree = tree
        
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
        self._orientation = 'vertical'

        # Build trees.
        self._keys = {} # treeseg -> key
        self._expanded_trees = {}
        self._collapsed_trees = {}
        self._nodes = []
        self._leaves = []
        self._locs = []
        self._make_collapsed_trees(canvas, tree, ())
        self._treeseg = self._make_expanded_tree(canvas, tree, ())
        self._add_child_widget(self._treeseg)

        CanvasWidget.__init__(self, canvas, **attribs)

    def expanded_tree(self, *path_to_tree):
        """
        Return the C{TreeSegmentWidget} for the specified subtree.

        @param path_to_tree: A list of indices i1, i2, ..., in, where
            the desired widget is the widget corresponding to
            C{tree.children()[i1].children()[i2]....children()[in]}.
            For the root, the path is C{()}.
        """
        return self._expanded_trees[path_to_tree]

    def collapsed_tree(self, *path_to_tree):
        """
        Return the C{TreeSegmentWidget} for the specified subtree.

        @param path_to_tree: A list of indices i1, i2, ..., in, where
            the desired widget is the widget corresponding to
            C{tree.children()[i1].children()[i2]....children()[in]}.
            For the root, the path is C{()}.
        """
        return self._expanded_trees[path_to_tree]

    def bind_click_trees(self, callback, button=1):
        """
        Add a binding to all tree segments.
        """
        for tseg in self._expanded_trees.values():
            tseg.bind_click(callback, button)
        for tseg in self._collapsed_trees.values():
            tseg.bind_click(callback, button)

    def bind_drag_trees(self, callback, button=1):
        """
        Add a binding to all tree segments.
        """
        for tseg in self._expanded_trees.values():
            tseg.bind_drag(callback, button)
        for tseg in self._collapsed_trees.values():
            tseg.bind_drag(callback, button)

    def bind_click_leaves(self, callback, button=1):
        """
        Add a binding to all leaves.
        """
        for leaf in self._leaves: leaf.bind_click(callback, button)
        for leaf in self._leaves: leaf.bind_click(callback, button)
            
    def bind_drag_leaves(self, callback, button=1):
        """
        Add a binding to all leaves.
        """
        for leaf in self._leaves: leaf.bind_drag(callback, button)
        for leaf in self._leaves: leaf.bind_drag(callback, button)
            
    def bind_click_nodes(self, callback, button=1):
        """
        Add a binding to all nodes.
        """
        for node in self._nodes: node.bind_click(callback, button)
        for node in self._nodes: node.bind_click(callback, button)
            
    def bind_drag_nodes(self, callback, button=1):
        """
        Add a binding to all nodes.
        """
        for node in self._nodes: node.bind_drag(callback, button)
        for node in self._nodes: node.bind_drag(callback, button)
            
    def bind_click_locs(self, callback, button=1):
        """
        Add a binding to all locs.
        """
        for node in self._locs: node.bind_click(callback, button)
        for node in self._locs: node.bind_click(callback, button)
            
    def bind_drag_locs(self, callback, button=1):
        """
        Add a binding to all locs.
        """
        for node in self._locs: node.bind_drag(callback, button)
        for node in self._locs: node.bind_drag(callback, button)
            
    def _make_collapsed_trees(self, canvas, tree, key):
        if not (isinstance(tree, Tree) or isinstance(tree, TreeToken)):
            return
        make_node = self._make_node
        make_leaf = self._make_leaf

        if isinstance(tree, Tree):
            node = make_node(canvas, tree.node(), **self._nodeattribs)
            self._nodes.append(node)
            leaves = [make_leaf(canvas, l, **self._leafattribs)
                      for l in tree.leaves()]
            self._leaves += leaves
            treeseg = TreeSegmentWidget(canvas, node, leaves, roof=1,
                                        color=self._roof_color,
                                        fill=self._roof_fill)
        else:
            node = make_node(canvas, tree.node(), **self._nodeattribs)
            self._nodes.append(node)
            leaves = [make_leaf(canvas, l.type(), **self._leafattribs)
                      for l in tree.leaves()]
            self._leaves += leaves
            loc = TextWidget(canvas, str(tree.loc()), **self._locattribs)
            self._locs.append(loc)
            leaves_seq = SequenceWidget(canvas, align='top', *leaves)
            leaves_stack = StackWidget(canvas, leaves_seq, loc)
            treeseg = TreeSegmentWidget(canvas, node, [leaves_stack], 
                                        roof=1, color=self._roof_color,
                                        fill=self._roof_fill)

        self._collapsed_trees[key] = treeseg
        self._keys[treeseg] = key
        #self._add_child_widget(treeseg)
        treeseg.hide()

        # Build trees for children.
        for i in range(len(tree.children())):
            child = tree.children()[i]
            self._make_collapsed_trees(canvas, child, key + (i,))

    def _make_expanded_tree(self, canvas, tree, key):
        make_node = self._make_node
        make_leaf = self._make_leaf

        if isinstance(tree, Tree) or isinstance(tree, TreeToken):
            node = make_node(canvas, tree.node(), **self._nodeattribs)
            self._nodes.append(node)
            children = tree.children()
            subtrees = [self._make_expanded_tree(canvas, children[i], key+(i,))
                        for i in range(len(children))]
            treeseg = TreeSegmentWidget(canvas, node, subtrees,
                                        color=self._line_color)
            self._expanded_trees[key] = treeseg
            self._keys[treeseg] = key
            return treeseg
        elif isinstance(tree, Token):
            leaf = make_leaf(canvas, tree.type(), **self._leafattribs)
            self._leaves.append(leaf)
            loc = TextWidget(canvas, str(tree.loc()), **self._locattribs)
            self._locs.append(loc)
            return StackWidget(canvas, leaf, loc, align='center')
        else:
            leaf = make_leaf(canvas, tree, **self._leafattribs)
            self._leaves.append(leaf)
            return leaf

    def __setitem__(self, attr, value):
        if attr[:5] == 'node_':
            for node in self._nodes: node[attr[5:]] = value
        elif attr[:5] == 'leaf_':
            for leaf in self._leaves: leaf[attr[5:]] = value
        elif attr[:4] == 'loc_':
            for loc in self._locs: loc[attr[4:]] = value
        elif attr == 'line_color':
            self._line_color = value
            for tseg in self._expanded_trees.values(): tseg['color'] = value
        elif attr == 'roof_color':
            self._line_color = value
            for tseg in self._collapsed_trees.values(): tseg['color'] = value
        elif attr == 'roof_fill':
            self._line_color = value
            for tseg in self._collapsed_trees.values(): tseg['fill'] = value
        elif attr == 'shapeable':
            self._shapeable = value
            for tseg in self._expanded_trees.values():
                tseg['draggable'] = value
            for tseg in self._collapsed_trees.values():
                tseg['draggable'] = value
            for leaf in self._leaves: leaf['draggable'] = value
            for loc in self._locs: loc['draggable'] = value
        elif attr == 'xspace':
            self._xspace = value
            for tseg in self._expanded_trees.values():
                tseg['xspace'] = value
            for tseg in self._collapsed_trees.values():
                tseg['xspace'] = value
            self.manage()
        elif attr == 'yspace':
            self._yspace = value
            for tseg in self._expanded_trees.values():
                tseg['yspace'] = value
            for tseg in self._collapsed_trees.values():
                tseg['yspace'] = value
            self.manage()
        elif attr == 'orientation':
            self._orientation = value
            for tseg in self._expanded_trees.values():
                tseg['orientation'] = value
            for tseg in self._collapsed_trees.values():
                tseg['orientation'] = value
            self.manage()
        else: CanvasWidget.__setitem__(self, attr, value)

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
        elif attr == 'orientation': return self._orientation
        else: return CanvasWidget.__getitem__(self, attr)
        
    def _tags(self): return []

    def _manage(self):
        segs = self._expanded_trees.values() + self._collapsed_trees.values()
        for tseg in segs:
            if tseg.hidden():
                tseg.show()
                tseg.manage()
                tseg.hide()

    def toggle_collapsed(self, treeseg):
        """
        Collapse/expand a tree.
        """
        old_treeseg = treeseg
        if old_treeseg['roof']:
            new_treeseg = self._expanded_trees[self._keys[old_treeseg]]
        else:
            new_treeseg = self._collapsed_trees[self._keys[old_treeseg]]

        # Replace the old tree with the new tree.
        if old_treeseg.parent() is self:
            self._remove_child_widget(old_treeseg)
            self._add_child_widget(new_treeseg)
            self._treeseg = new_treeseg
        else:
            old_treeseg.parent().replace_child(old_treeseg, new_treeseg)

        # Move the new tree to where the old tree was.  Show it first,
        # so we can find its bounding box.
        new_treeseg.show()
        (newx, newy) = new_treeseg.node().bbox()[:2]
        (oldx, oldy) = old_treeseg.node().bbox()[:2]
        new_treeseg.move(oldx-newx, oldy-newy)

        # Hide the old tree
        old_treeseg.hide()

        # We could do parent.manage() here instead, if we wanted.
        new_treeseg.parent().update(new_treeseg)
        
##//////////////////////////////////////////////////////
##  Demo Code
##//////////////////////////////////////////////////////

import random
if __name__ == '__main__':
    def fill(cw):
        cw['fill'] = '#%06d' % random.randint(0,999999)
    
    cf = CanvasFrame(width=550, height=450, closeenough=2)
    
    tree = Tree('S', Tree('NP', 'the', 'very', 'big', 'cat'),
                Tree('VP', Tree('Adv', 'sorta'), Tree('V', 'saw'),
                     Tree('NP', Tree('Det', 'the'),
                          Tree('N', 'dog'))))
                
    tc = TreeWidget(cf.canvas(), tree, draggable=1, 
                    node_font=('helvetica', -14, 'bold'),
                    leaf_font=('helvetica', -12, 'italic'),
                    roof_fill='white', roof_color='black',
                    leaf_color='green4', node_color='blue2')
    cf.add_widget(tc,10,10)
    
    def boxit(canvas, text):
        big = ('helvetica', -16, 'bold')
        return BoxWidget(canvas, TextWidget(canvas, text,
                                            font=big), fill='green')
    def ovalit(canvas, text):
        return OvalWidget(canvas, TextWidget(canvas, text),
                          fill='cyan')
    
    treetok = TreeToken('S', TreeToken('NP', Token('this',0),
                                       Token('tree',1)),
                 TreeToken('VP', TreeToken('V', Token('is',2)),
                      TreeToken('AdjP', Token('shapeable', 3, 5))))
    tc2 = TreeWidget(cf.canvas(), treetok, boxit, ovalit, shapeable=1)
    
    def color(node):
        node['color'] = '#%04d00' % random.randint(0,9999)
    def color2(treeseg):
        treeseg.node()['fill'] = '#%06d' % random.randint(0,9999)
        treeseg.node().child()['color'] = 'white'

    tc.bind_click_trees(tc.toggle_collapsed)
    tc2.bind_click_trees(tc2.toggle_collapsed)
    tc.bind_click_nodes(color, 3)
    tc2.expanded_tree(1).bind_click(color2, 3)
    tc2.expanded_tree().bind_click(color2, 3)

    paren = ParenWidget(cf.canvas(), tc2)
    cf.add_widget(paren, tc.bbox()[2]+10, 10)

    tree3 = Tree('S', Tree('NP', 'this' ,'tree'),
                 Tree('AUX', 'was'),
                Tree('VP', Tree('V', 'built'),
                     Tree('PP', Tree('P', 'with'),
                          Tree('NP', (Tree('N',
                            'tree_to_treesegment'))))))
    tc3 = tree_to_treesegment(cf.canvas(), tree3, tree_color='green4',
                              tree_xspace=2, tree_width=2)
    tc3['draggable'] = 1
    cf.add_widget(tc3, 10, tc.bbox()[3]+10)

    def orientswitch(treewidget):
        if treewidget['orientation'] == 'horizontal':
            treewidget.expanded_tree(1,1).subtrees()[0].set_text('vertical')
            #treewidget.collapsed_tree(1,1).subtrees()[0].set_text('vertical')
            treewidget['orientation'] = 'vertical'
        else:
            treewidget.expanded_tree(1,1).subtrees()[0].set_text('horizontal')
            #treewidget.collapsed_tree(1,1).subtrees()[0].set_text('horizontal')
            treewidget['orientation'] = 'horizontal'

    text = """
Try clicking, right clicking, and dragging
different elements of each of the trees.
The top-left tree is a TreeWidget built from
a Tree.  The top-right is a TreeWidget built
from a TreeToken, using non-default widget
constructors for the nodes & leaves (BoxWidget
and OvalWidget).  The bottom-left tree is
built from tree_to_treesegment."""
    twidget = TextWidget(cf.canvas(), text.strip())
    textbox = BoxWidget(cf.canvas(), twidget, fill='white', draggable=1)
    cf.add_widget(textbox, tc3.bbox()[2]+10, tc2.bbox()[3]+10)
                     
    tree4 = Tree('S', Tree('NP', 'this', 'tree'),
                 Tree('VP', Tree('V', 'is'), Tree('Adj', 'horizontal')))
    tc4 = TreeWidget(cf.canvas(), tree4, draggable=1,
                     line_color='brown2', roof_color='brown2',
                     node_font=('helvetica', -12, 'bold'),
                     node_color='brown4', orientation='horizontal')
    tc4.manage()
    cf.add_widget(tc4, tc3.bbox()[2]+10, textbox.bbox()[3]+10)
    tc4.bind_click(orientswitch)
    tc4.bind_click_trees(tc4.toggle_collapsed, 3)
