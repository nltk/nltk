# Natural Language Toolkit: Graphical Representations for Trees
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from Tkinter import *
from tkFileDialog import asksaveasfilename

from nltk.tree import Tree, TreeToken
from nltk.token import Token, Location

class TreeView:

    _X_SPACING = 5
    _Y_SPACING = 20

    def __init__(self, tree, root=None):
        """
        Construct a new view of a Tree or a TreeToken.
        """
        self._tree = tree
        
        # If we were not given a root window, then create one.
        # Include buttons for performing common functions.
        if root is None:
            self._top = top = Tk()
            top.title('Tree Display')
            self._top.bind('q', self.destroy)

            # Create the button frame.
            self._buttons = buttons = Frame(top)
            Button(buttons, text='Done',
                   command=self.destroy).pack(side='right')
            Button(buttons, text='Zoom in',
                   command=self._font_grow).pack(side='left')
            Button(buttons, text='Zoom out',
                   command=self._font_shrink).pack(side='left')
            Button(buttons, text='Print',
                   command=self._to_postscript).pack(side='left')
            Button(buttons, text='Expand All',
                   command=self._expand_all).pack(side='left')
            buttons.pack(side='bottom', fill='both')
        else:
            self._top = top = root
        
        # Create the canvas view.
        self._view = view = Frame(top, relief='sunk', border=2)
        self._v_scroll = v_scroll= Scrollbar(view)
        v_scroll.pack(side=RIGHT, fill=Y)
        self._h_scroll= h_scroll = Scrollbar(view, orient='horizontal')
        h_scroll.pack(side=BOTTOM, fill=X)
        self._canvas = c = Canvas(view, width=400, height=300,
                                  yscrollcommand=v_scroll.set,
                                  xscrollcommand=h_scroll.set,
                                  closeenough=5)
        c.pack(side=LEFT, expand='yes', fill='both')
        v_scroll.config (command=c.yview)
        h_scroll.config (command=c.xview)
        self._view.pack(expand='yes', fill='both')

        # Keep track of which nodes are collapsed
        self._collapsed = {}
        self._expand_all(tree)

        self._points = 12
        self._find_textheight()

        self._tree_height = tree.height()

        # Should leaves all be at the bottom?
        self._leaves_at_bottom = 1

        self._redraw()
        cregion = self._canvas['scrollregion'].split()
        width = min(int(cregion[2])-int(cregion[0]), 800)
        height = min(int(cregion[3])-int(cregion[1]), 300)
        self._canvas['width'] = width
        self._canvas['height'] = height

        # Enter main loop???
        #if root is None:
        #    mainloop()

    # ////////////////////////////////////
    # //  Private methods
    # ////////////////////////////////////
    
    def _find_textheight(self):
        """
        Determine the value of _textheight.  This instance variable
        records the maximum height of a letter, and is used when
        deciding how much space to leave for the text at trees' nodes
        and leaves.  It should be called whenever the font size
        (_points) is changed.

        @rtype: C{None}
        """
        c = self._canvas
        tag = c.create_text(0, 0, text='Al^|qp', anchor='se',
                            font=('helvetica', self._points, 'bold'))
        bbox = c.bbox(tag)
        self._textheight = bbox[3]-bbox[1]
        c.delete(tag)

    def _font_grow(self): set_text_size(self._points+2)
    def _font_shrink(self): set_text_size(self._points-2)

    def _expand_all(self, tree=None):
        """
        Un-collapse the given tree and all of its descendants.  If no
        tree is given, then the top-level tree will be un-collapsed.
        If the given tree is not shown, then this will have no effect.

        This does I{not} redraw the tree.

        @param tree: The tree to expand.
        @type tree: C{Tree}
        """
        if tree is None: tree = self._tree
        
        self._collapsed[tree] = 0
        for child in tree:
            if isinstance(child, Tree) or isinstance(child, TreeToken):
                self._expand_all(child)

    def _redraw(self):
        """
        Redraw the tree.  This includes resetting the canvas region. 

        @rtype: C{None}
        """
        # Draw the new before we delete the old; this sometimes
        # prevents blinking..
        old = self._canvas.find(ALL)
        width = self._draw_tree(self._tree, TreeView._X_SPACING, 0)
        width += TreeView._X_SPACING
        height = self._canvas_height(self._tree)
        self._canvas['scrollregion'] = (0, -5, width, height)
        self._canvas.delete(*old)

    def _canvas_height(self, tree):
        """
        @rtype: C{int}
        @return: the height needed to display the given tree, taking
            collapsed nodes into account.
        @type tree: C{Tree}
        @param tree: The tree for which to display the needed height.
        """
        if self._collapsed[tree]:
            return 2*self._textheight + TreeView._Y_SPACING
        else:
            height = 0
            for child in tree:
                if isinstance(child, Tree) or isinstance(child, TreeToken):
                    height = max(height, self._canvas_height(child))
                else:
                    height = max(height, self._textheight)

            return height + (self._textheight + TreeView._Y_SPACING)
                
    def _draw_collapsed_children(self, tree, left, depth):
        """
        Draw the children of a collapsed node.  All children are drawn
        on a single line, separated by space characters.  A callback
        is added to the triangle over the children, which will expand
        them.

        @param tree: The tree whose children should be displayed
        @type tree: C{Tree}
        @param left: The x position of the left edge at which the
            children should be drawn.
        @type left: C{int}
        @param depth: The depth in self._tree of given tree.
        @type depth: C{int}
        @return: The x position of the right edge of the drawn
            children.
        @rtype: C{int}
        """
        c = self._canvas

        # Draw children.
        children = ' '.join([str(t) for t in tree.leaves()])
        right = self._draw_leaf(children, left, depth+1)

        # Draw triangle
        node_y = (self._textheight + TreeView._Y_SPACING) * depth
        node_x = (left+right)/2
        triangle_bottom = node_y+self._textheight+TreeView._Y_SPACING
        tag = c.create_polygon(node_x, node_y+self._textheight,
                               left, bottom, right, bottom,
                               outline='black', fill='gray')

        # Set up a callback.
        cb = lambda e, self=self, tree=tree: self._toggle(tree)
        c.tag_bind(tag, '<Button-1>', cb)

        return right
        
    def _draw_expanded_children(self, tree, left, depth):
        """
        Draw the children of an un-collapsed node, including lines to
        the child.

        @param tree: The tree whose children should be displayed
        @type tree: C{Tree}
        @param left: The x position of the left edge at which the
            children should be drawn.
        @type left: C{int}
        @param depth: The depth in self._tree of given tree.
        @type depth: C{int}
        @return: The x position of the right edge of the drawn
            children.
        @rtype: C{int}
        """
        c = self._canvas
        left += (TreeView._X_SPACING/2)

        # Recurse to draw the children.
        child_centers = []
        x = new_x = left
        for child in tree:
            if isinstance(child, Tree) or isinstance(child, TreeToken):
                new_x = self._draw_tree(child, x, depth+1)
            else:
                new_x = self._draw_leaf(str(child), x, depth+1)
            child_centers.append((x+new_x)/2)
            x = new_x + TreeView._X_SPACING
        right = new_x
            
        # Draw lines to the child.
        node_y = ((self._textheight + TreeView._Y_SPACING) * depth +
                  self._textheight)
        node_x = (left+right)/2
        child_y = node_y + TreeView._Y_SPACING
        for child_x in child_centers:
            c.create_line(node_x, node_y, child_x, child_y)
                          
        return right + (TreeView._X_SPACING/2)
        
    def _draw_tree(self, tree, left, depth):
        """
        Draw the given tree.  Set up a callback on each node, which
        expands/collapses the node.

        @param tree: The tree that should be displayed.
        @type tree: C{Tree}
        @param left: The x position of the left edge at which the
            tree should be drawn.
        @type left: C{int}
        @param depth: The depth in self._tree of given tree.
        @type depth: C{int}
        @return: The x position of the right edge of the drawn
            tree.
        @rtype: C{int}
        """
        # Returns right edge...
        c = self._canvas
        
        # Draw children
        if self._collapsed[tree]:
            x = self._draw_collapsed_children(tree, left, depth)
        else:
            x = self._draw_expanded_children(tree, left, depth)
            
        # Draw node value.
        y = (self._textheight + TreeView._Y_SPACING) * depth
        node_x = (left+x)/2
        tag = c.create_text(node_x, y, text=str(tree.node()),
                            anchor='n', justify='center',
                            font=('helvetica', self._points, 'bold'))
        node_right = c.bbox(tag)[2] + (TreeView._X_SPACING/2)

        # Set up a callback.
        if len(tree) > 1 or tree.height() > 2:
            cb = lambda e, self=self, tree=tree: self._toggle(tree)
            c.tag_bind(tag, '<Button-1>', cb)

        # If the node value was wider than its children, then we have
        # to shift everything over to the right.
        if node_right > x:
            dx = (left - c.bbox(tag)[0]) + (TreeView._X_SPACING/2)
            tags = c.find_overlapping(left, y+5, x, 10000)
            for tag in tags:
                c.move(tag, dx, 0)
            x = node_right+dx

        return x

    def _draw_leaf(self, text, x, depth):
        """
        Draw an individual leaf.
        """
        y = (self._textheight + TreeView._Y_SPACING) * depth
        tag = self._canvas.create_text(x, y, text=text,
                                       anchor='nw', justify='left',
                                       font=('helvetica', self._points))
        return self._canvas.bbox(tag)[2]

    def _toggle(self, tree):
        """
        Collapse/expand the given tree.
        """
        self._collapsed[tree] = not self._collapsed[tree]
        self._redraw()

    def _to_postscript(self):
        ftypes = [('Postscript files', '.ps'),
                  ('All files', '*')]
        filename = asksaveasfilename(filetypes=ftypes,
                                     defaultextension='.ps')
        if filename:
            self.print_to_file(filename)

    # ////////////////////////////////////
    # //  Public methods
    # ////////////////////////////////////

    def set_text_size(self, points):
        """
        Set the size of the text used to render nodes and leaves.

        @type points: C{int}
        @param points: The desired font size, in points.  This should
            typically be a number between 6 and 30; if a size smaller
            than 4 points is given, 4 will be used.
        @rtype: C{None}
        """
        if points < 4: points = 4
        self._points = points
        self._find_textheight()
        self._redraw()

    def destroy(self, *args):
        """
        Destroy the root window.
        @rtype: C{None}
        """
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def expand(self, tree=None):
        """
        Expand the given tree.  If no tree is given, then all trees
        will be expanded.

        @param tree: The tree to expand.
        @type tree: C{Tree}
        @rtype: C{None}
        """
        if tree is None:
            self._expand_all()
        else:
            if not self._collapsed.has_key(tree):
                raise ValueError('The given tree is not displayed')
            self._collapsed[tree] = 0
            self._redraw()

    def collapse(self, tree=None):
        """
        Collapse the given tree.  If no tree is given, then the top-
        level tree will be collapsed.

        @param tree: The tree to collapse.
        @type tree: C{Tree}
        @rtype: C{None}
        """
        if tree is None:
            tree = self._tree
        if not self._collapsed.has_key(tree):
            raise ValueError('The given tree is not displayed')
        self._collapsed[tree] = 0
        self._redraw()

    def print_to_file(self, filename):
        """
        Print this tree to the given file.

        @param filename: The name of the file to print the tree to.
        @type filename: C{string}
        @rtype: C{None}
        """
        (x0, y0, w, h) = self._canvas['scrollregion'].split()
        self._canvas.postscript(file=filename,
                                width=int(w)+10, height=int(h)+10)

def print_tree(tree, filename):
    """
    Print the given tree to the given filename.  This uses a TreeView
    to display the tree, but hopefully will never actually open a
    window.

    @rtype: C{None}
    """
    top = Tk()
    treeview = TreeView(tree, top)
    top.mainloop(1)
    treeview.print_to_file(filename)
    top.destroy()
        
# Temporary test code.
if __name__ == '__main__':
    from random import randint
    def randomtree(depth=0, bf=None):
        if bf is None: bf = randint(1,2)
        if randint(0,7-depth) == 0 and depth>1:
            return 'L%d' % randint(0, 10)
        else:
            numchildren = randint(1,bf)
            children = [randomtree(depth+1, bf) for x in range(numchildren)]
            return Tree('Node %d' % randint(0,10000), *children)

    def randomtreetok(depth=0, left=0, bf=None):
        if bf is None: bf = randint(1,2)
        if randint(0,7-depth) == 0 and depth>1:
            len = randint(1,5)
            return Token('L%d' % randint(0, 10), left, left+len)
        else:
            numchildren = randint(1,bf)
            children = []
            for x in range(numchildren):
                children.append(randomtreetok(depth+1, left, bf))
                left = children[-1].loc().end()
            return TreeToken('Node %d' % randint(0,10000), *children)

    if randint(1,1) ==0:
        t = randomtree()
        while not (5 < len(t.leaves()) < 25):
            t = randomtree()
    else:
        t = randomtreetok()
        while not (5 < len(t.leaves()) < 25):
            t = randomtreetok()

    TreeView(t)
