from Tkinter import *

from nltk.tree import Tree, TreeToken
from nltk.token import Token, Location

class TreeView:

    _X_SPACING = 20
    _Y_SPACING = 25
    
    
    def __init__(self, tree):
        """
        Construct a new view of a Tree or a TreeToken.
        """
        self._tree = tree
        
        # Create the tree window
        self._top = top = Tk()
        top.title('Tree Display')
        self._top.bind('q', self.destroy)

        # Create the button frame.
        self._buttons = buttons = Frame(top)
        Button(buttons, text='Done', command=self.destroy).pack(side='right')
        Button(buttons, text='Bigger Font',
               command=self._font_grow).pack(side='left')
        Button(buttons, text='Smaller Font',
               command=self._font_shrink).pack(side='left')
        Button(buttons, text='Print',
               command=self._to_postscript).pack(side='left')
        Button(buttons, text='Expand All',
               command=self._expand_all).pack(side='left')
        buttons.pack(side='bottom', fill='both')
        
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
        self._expand(tree)

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

    def _find_textheight(self):
        # Find the height of text.
        c = self._canvas
        tag = c.create_text(0, 0, text='Al^|qp', anchor='se',
                            font=('helvetica', self._points, 'bold'))
        bbox = c.bbox(tag)
        self._textheight = bbox[3]-bbox[1]
        c.delete(tag)

    def _font_grow(self):
        self._points += 2
        self._find_textheight()
        self._redraw()

    def _font_shrink(self):
        if self._points <= 6: return
        self._points -= 2
        self._find_textheight()
        self._redraw()

    def _expand(self, tree):
        """
        Un-collapse the given tree and all of its descendants.
        """
        self._collapsed[tree] = 0
        for child in tree:
            if isinstance(child, Tree) or isinstance(child, TreeToken):
                self._expand(child)

    def _expand_all(self):
        self._expand(self._tree)
        self._redraw()

    def _redraw(self):
        """
        Redraw the tree.
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
        # Returns the right edge...
        c = self._canvas

        # Draw children.
        children = ' '.join([repr(t) for t in tree.leaves()])
        right = self._draw_leaf(children, left, depth+1)

        # Draw triangle
        node_y = (self._textheight + TreeView._Y_SPACING) * depth
        node_x = (left+right)/2
        tag = c.create_polygon(node_x, node_y+self._textheight,
                               left, node_y+self._textheight+TreeView._Y_SPACING,
                               right, node_y+self._textheight+TreeView._Y_SPACING,
                               outline='black', fill='gray')

        # Set up a callback.
        cb = lambda e, self=self, tree=tree: self._toggle(tree)
        c.tag_bind(tag, '<Button-1>', cb)

        return right
        
    def _draw_expanded_children(self, tree, left, depth):
        # Returns the right edge...
        c = self._canvas
        left += (TreeView._X_SPACING/2)

        # Recurse to draw the children.
        child_centers = []
        x = new_x = left
        for child in tree:
            if isinstance(child, Tree) or isinstance(child, TreeToken):
                new_x = self._draw_tree(child, x, depth+1)
            else:
                new_x = self._draw_leaf(repr(child), x, depth+1)
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
        # Returns right edge...
        c = self._canvas
        
        # Draw children
        import random
        if self._collapsed[tree]:
            x = self._draw_collapsed_children(tree, left, depth)
        else:
            x = self._draw_expanded_children(tree, left, depth)
            
        # Draw node value.
        y = (self._textheight + TreeView._Y_SPACING) * depth
        node_x = (left+x)/2
        tag = c.create_text(node_x, y, text=repr(tree.node()),
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
        y = (self._textheight + TreeView._Y_SPACING) * depth
        tag = self._canvas.create_text(x, y, text=text,
                                       anchor='nw', justify='left',
                                       font=('helvetica', self._points))
        return self._canvas.bbox(tag)[2]

    def _toggle(self, tree):
        self._collapsed[tree] = not self._collapsed[tree]
        self._redraw()

    def destroy(self, *args):
        if self._top == None: return
        self._top.destroy()
        self._top = None

    def _to_postscript(self):
        warning = ('Warning: only the portion of the '+
                   'tree currently shown will be saved')
        _FileSelector(self.print_to_file, warning)

    def print_to_file(self, filename):
        ps_str = self._canvas.postscript()
        open(filename, 'w').write(ps_str)

class _FileSelector:
    def __init__(self, cb, txt):
        self._cb = cb
        
        # Create the tree window
        self._top = Tk()
        self._top.title('Printing to file...')
        self._top.bind('q', self.destroy)
        self._top.bind('<Enter>', self.ok)
        self._top.bind('<Return>', self.ok)
        if txt:
            Label(self._top, text=txt).pack(side='top')
        f = Frame(self._top, relief='groove', border=3)
        Label(f, text='Filename:').pack(side='left')
        self._e=Entry(f, width=30)
        self._e.pack(side='right', expand='yes', fill='x')
        f.pack(side='top', fill='x', expand='yes')
        Button(self._top, text='Ok', command=self.ok).pack(side='left')
        Button(self._top, text='Cancel', command=self.destroy).pack(side='right')

    def destroy(self, *args):
        if self._top == None: return
        self._top.destroy()
        self._top = None

    def ok(self, *args):
        filename = self._e.get()
        if not filename: return
        self._cb(filename)
        self.destroy()
        
# Temporary test code.
if __name__ == '__main__':
    from random import randint
    def randomtree(depth=0, bf=None):
        if bf == None: bf = randint(1,2)
        if randint(0,7-depth) == 0 and depth>1:
            return 'L%d' % randint(0, 10)
        else:
            numchildren = randint(1,bf)
            children = [randomtree(depth+1, bf) for x in range(numchildren)]
            return Tree('Node %d' % randint(0,10000), *children)

    def randomtreetok(depth=0, left=0, bf=None):
        if bf == None: bf = randint(1,2)
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
