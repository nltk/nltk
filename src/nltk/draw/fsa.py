"""
Draw a finite state automoton

  - CanvasNode: a node, displayed on a canvas.
  - CanvasEdge: an edge, displayed on a canvas.
  - CanvasFSA: an FSA, displayed on a canvas.
  - FSAView: A widget showing an FSA
  
"""

import Tkinter, random, math, nltk.fsa

# How much extra space should we add around the FSA, to make it
# viewable.  If this were zero, then all nodes at the edges would be
# only half-visible.
VIEWBORDER = 70

# How much extra scroll-space should we provide, to let the user move
# nodes around?  This is in addition to the view border. 
SCROLLBORDER = 50

class CanvasNode:
    def __init__(self, x, y, label, canvas):
        self._x = x
        self._y = y
        self._label = label
        self._canvas = canvas
        self._incoming = []
        self._outgoing = []
        self._tags = None
        self._nodecolor = self._textcolor = 'black'

    def draw(self):
        if self._tags is not None: return
        
        # Draw the node
        (x, y) = (self._x, self._y)
        tag1 = self._canvas.create_oval(x-5, y-5, x+5, y+5, fill=self._nodecolor)
        tag2 = self._canvas.create_text(x, y-5, text=self._label, anchor='s',
                                        font=('helvetica', 10, 'bold'),
                                        fill=self._textcolor)
        self._tags = [tag1, tag2]

        # Set up a movement callback
        self._canvas.tag_bind(tag1, '<ButtonPress-1>', self._press_cb)
        self._canvas.tag_bind(tag2, '<ButtonPress-1>', self._press_cb)

    def erase(self):
        if self._tags is None: return
        self._canvas.destroy(*self._tags)

    def color(self, nodecolor, textcolor='black'):
        if self._tags is not None:
            self._canvas.itemconfig(self._tags[0], fill=nodecolor)
            self._canvas.itemconfig(self._tags[1], fill=textcolor)
        self._nodecolor = nodecolor
        self._textcolor = textcolor

    def x(self): return self._x
    def y(self): return self._y
    def label(self): return self._label
    def incoming(self): return self._incoming
    def outgoing(self): return self._outgoing
    def add_incoming(self, edge): self._incoming.append(edge)
    def add_outgoing(self, edge): self._outgoing.append(edge)
    def move(self, newx, newy):
        if self._tags is not None:
            self._canvas.move(self._tags[0], (newx-self._x), (newy-self._y))
            self._canvas.move(self._tags[1], (newx-self._x), (newy-self._y))
        self._x = newx
        self._y = newy
        for edge in self._incoming + self._outgoing:
            edge.update()

    def _press_cb(self, event):
        self._mcb_id = self._canvas.bind('<Motion>', self._motion_cb)
        self._rcb_id = self._canvas.bind('<ButtonRelease-1>', self._release_cb)
        self._scrollregion = [int(n) for n in self._canvas['scrollregion'].split()]

    def _motion_cb(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)

        # Bounds checking:
        x = max(self._scrollregion[0], min(self._scrollregion[2], x))
        y = max(self._scrollregion[1], min(self._scrollregion[3], y))
        
        self.move(x, y)

    def _release_cb(self, event):
        self._canvas.unbind('<Motion>', self._mcb_id)
        self._canvas.unbind('<Motion>', self._rcb_id)

    def __repr__(self):
        return '<Node %s @%sx%s>' % (self._label, self._x, self._y)
    def __str__(self):
        return '<Node %s>' % (self._label)

class CanvasEdge:
    def __init__(self, node1, node2, label, canvas):
        self._node1 = node1
        self._node2 = node2
        self._label = label
        self._canvas = canvas
        self._tags = None
        self._linecolor = self._textcolor = 'black'
        self._font = None
        self._collapse_edges = 0

        # How curvey should we be?
        other_edges = 1
        for edge in node1.outgoing():
            if edge.to_node() is node2: other_edges += 1
        self._curve = 0.2 * other_edges

    def draw(self):
        if self._tags is not None: return

        kw = {'arrow':'last', 'fill':self._linecolor, 'smooth':1}
        tag1 = self._canvas.create_line(*self._line_coords(), **kw)

        (textx, texty) = self._text_coords()
        tag2 = self._canvas.create_text(textx, texty, text=self._label,
                                        anchor='c', fill=self._textcolor)
        if self._font: self._canvas.itemconfig(tag2, font=self._font)
        self._tags = [tag1, tag2]

        # Lower the edge, so the tag_binds of nodes take precedence
        self._canvas.lower(tag1)
        self._canvas.lower(tag2)

    def erase(self):
        if self._tags is None: return
        self._canvas.destroy(*self._tags)

    def color(self, linecolor, textcolor='black'):
        if self._tags is not None: 
            self._canvas.itemconfig(self._tags[0], fill=linecolor)
            self._canvas.itemconfig(self._tags[1], fill=textcolor)
        self._linecolor = linecolor
        self._textcolor = textcolor

    def font(self, font):
        if self._tags is not None: 
            self._canvas.itemconfig(self._tags[1], font=font)
        self._font = font

    def _text_coords(self):
        x1 = self._node1.x()
        y1 = self._node1.y()
        x2 = self._node2.x()
        y2 = self._node2.y()
        if self._node1 is self._node2:
            # Self-loops.
            return (x1, y1+150*self._curve)
        else:
            # Normal edges.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
            textx = (x1+x2)*0.5 + (y2-y1)*(self._curve/2) + (y2-y1) * 8 / r
            texty = (y1+y2)*0.5 - (x2-x1)*(self._curve/2) - (x2-x1) * 8 / r
            return (textx, texty)
    
    def _line_coords(self):
        x1 = self._node1.x()
        y1 = self._node1.y()
        x2 = self._node2.x()
        y2 = self._node2.y()
        
        if self._node1 is self._node2:
            # Self-loops
            x3 = x1 - 70*self._curve
            y3 = y1 + 70*self._curve
            x4 = x1
            y4 = y1 + 140*self._curve
            x5 = x1 + 70*self._curve
            y5 = y1 + 70*self._curve
            return (x1, y1, x3, y3, x4, y4, x5, y5, x2, y2)
        else:
            # Normal edges.
            x3 = (x1+x2)*0.5 + (y2-y1)*self._curve
            y3 = (y1+y2)*0.5 - (x2-x1)*self._curve
            # Adjust endpoints so they end at the node parimeter.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
            x2 -= (x2-x1) * 5 / r
            y2 -= (y2-y1) * 5 / r
            x1 -= (x1-x2) * 5 / r
            y1 -= (y1-y2) * 5 / r
            return (x1, y1, x3, y3, x2, y2)

    def from_node(self): return self._node1
    def to_node(self): return self._node2
    def label(self): return self._label
    def set_label(self, newlabel): self._label = newlabel

    def update(self):
        """
        Respond to node movement.
        """
        if self._tags is not None:
            self._canvas.coords(self._tags[0], self._line_coords())
            self._canvas.coords(self._tags[1], self._text_coords())

    def __repr__(self):
        return '%s-->%s' % (self._node1, self._node2)

class CanvasFSA:
    def __init__(self, fsa, canvas, collapse_edges = 1):
        self._fsa = fsa
        self._canvas = canvas
        self._collapse_edges = collapse_edges

        nodes = self._nodes = {}
        edges = self._edges = []

        self._add_fsa(fsa)

        # Adjust the canvas size...
        minx = miny = maxx = maxy = 0
        for node in self._nodes.values():
            (x, y) = (node.x(), node.y())
            minx = min(x, minx)
            miny = min(y, miny)
            maxx = max(x, maxx)
            maxy = max(y, maxy)

        minx -= VIEWBORDER
        miny -= VIEWBORDER
        maxx += VIEWBORDER
        maxy += VIEWBORDER
        canvas['scrollregion'] = (minx-SCROLLBORDER, miny-SCROLLBORDER,
                                  maxx+SCROLLBORDER, maxy+SCROLLBORDER)
        canvas.xview('moveto', (SCROLLBORDER / (2.0 * SCROLLBORDER + maxx-minx)))
        canvas.yview('moveto', (SCROLLBORDER / (2.0 * SCROLLBORDER + maxy-miny)))

    def _add_fsa(self, fsa):
        nodes = self._nodes
        edges = self._edges
        for (s1, label, s2s) in fsa.transitions():
            for s2 in s2s.elements():
                # Add nodes..
                if not nodes.has_key(s1): nodes[s1] = self._make_node(s1)
                if not nodes.has_key(s2): nodes[s2] = self._make_node(s2)

                # Add the edge
                if not self._collapse_edges:
                    edges.append(self._make_edge(nodes[s1], nodes[s2], label))
                    # Tell the nodes about it the edge.
                    nodes[s1].add_outgoing(edges[-1])
                    nodes[s2].add_incoming(edges[-1])
                else:
                    edge_collapsed = 0
                    for edge in nodes[s1].outgoing():
                        if edge.to_node() is nodes[s2]:
                            edge.set_label(edge.label()+', '+label)
                            edge_collapsed = 1
                            break
                    if not edge_collapsed:
                        edges.append(self._make_edge(nodes[s1], nodes[s2], label))
                        # Tell the nodes about it the edge.
                        nodes[s1].add_outgoing(edges[-1])
                        nodes[s2].add_incoming(edges[-1])

        self.arrange()

        # Draw them
        for node in self._nodes.values(): node.draw()
        for edge in edges: edge.draw()

    def _make_node(self, state):
        node = CanvasNode(None, None, str(state), self._canvas)
        if state in self._fsa._finals: node.color('red')
        else: node.color('green3')
        return node

    def _make_edge(self, node1, node2, label):
        # Handle epsilon transitions
        if label != nltk.fsa.epsilon:
            edge = CanvasEdge(node1, node2, label, self._canvas)
            edge.color('cyan4', 'blue4')
        else:
            edge = CanvasEdge(node1, node2, 'e', self._canvas)
            edge.font(('symbol', 12))
            edge.color('gray50', 'gray40')
        return edge
    
    def arrange(self):
        """
        Set the node positions.  This routine should attempt to
        minimize the number of crossing edges, in order to make the
        graph easier to read.
        """
        self._arrange_into_levels()

        self._arrange_levels()

        # Now we want to minimize crossing edges.. how, again? :)
        for i in range(len(self._levels)):
            for j in range(len(self._levels[i])):
                self._levels[i][j].move(i*80, j*70)

    def _arrange_levels(self):
        """
        Re-arrange each level to (locally) minimize the number of
        crossing edges.
        """
        # For now, put nodes with more incoming edges further down.
        for level in self._levels:
            level.sort(lambda n1,n2:cmp(len(n1.incoming()), len(n2.incoming())))

    def _arrange_into_levels(self):
        """
        Assign a level to each node.
        """
        # Mapping from node to level.
        self._nodelevel = {}
        self._levels = []

        nodelist = self._nodes.values()
        
        # Find any nodes that have no incoming edges; put all of these
        # in level 0.
        toplevel = []
        for node in nodelist:
            if len(node.incoming()) == 0:
                toplevel.append(node)
                self._nodelevel[node] = 0

        # Expand all of their children.
        self._levels = [toplevel]
        self._add_descendants(toplevel, 1)

        # If we didn't get all the nodes, we'll have to start picking
        # nodes that do have incoming transitions.  Pick the ones that
        # have the most reachable nodes.  (n.b., this implementation
        # isn't terribly efficient, but we dont' expect to be
        # displaying huge FSAs, so it should be ok)
        while len(self._nodelevel) < len(self._nodes):
            expand_node = None
            max_reachable = -1

            for node in nodelist:
                reachable = self._reachable(node)
                if reachable >= max_reachable:
                    max_reachable = reachable
                    expand_node = node
            
            # Expand the new node's children.
            self._levels[0].append(expand_node)
            self._nodelevel[expand_node] = 0
            self._add_descendants(toplevel, 1)
    
    def _reachable(self, node, reached=None):
        """
        How many *unexpanded* nodes can be reached from the given node?
        """
        if self._nodelevel.has_key(node): return 0
        if reached is None: reached = {}
        if not reached.has_key(node):
            reached[node] = 1
            for edge in node.outgoing():
                self._reachable(edge.to_node(), reached)
        return len(reached)

    def _add_descendants(self, parent_level, levelnum):
        """
        Add all the descendants of the nodes in the list parent_level
        to the structures self._level and self._nodelevel.
        """
        self._add_descendants_dfs(parent_level, levelnum)

    def _add_descendants_dfs(self, parent_level, levelnum):
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            # Add the parent node
            if not self._nodelevel.has_key(parent_node):
                self._levels[levelnum-1].append(parent_node)
                self._nodelevel[parent_node] = levelnum-1

            # Recurse to its children
            child_nodes = [edge.to_node() for edge in parent_node.outgoing()
                           if not self._nodelevel.has_key(edge.to_node())]
            if len(child_nodes) > 0:
                self._add_descendants_dfs(child_nodes, levelnum+1)

    def _add_descendants_bfs(self, parent_level, levelnum):
        all_child_nodes = []
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            print ('  '*levelnum), parent_node
            child_nodes = [edge.to_node() for edge in parent_node.outgoing()
                           if not self._nodelevel.has_key(edge.to_node())]
            for node in child_nodes:
                self._levels[levelnum].append(node)
                self._nodelevel[node] = levelnum
            all_child_nodes += child_nodes
        if len(all_child_nodes) > 0:
            self._add_descendants_bfs(all_child_nodes, levelnum+1)

class FSAFrame:
    "Widget to view FSA's."

    MINX = MINY = 60
    MAXX = 800
    MAXY = 400
    
    def __init__(self, parent, fsa, **kw):
        self._parent = parent
        self._fsa = fsa

        self._frame = frame = Tkinter.Frame(parent)
        self._canvas = canvas = Tkinter.Canvas(frame, closeenough='10.0', **kw)
        xscrollbar = Tkinter.Scrollbar(parent, orient='horizontal')
        yscrollbar = Tkinter.Scrollbar(parent, orient='vertical')
        xscrollbar['command'] = canvas.xview
        yscrollbar['command'] = canvas.yview
        canvas['xscrollcommand'] = xscrollbar.set
        canvas['yscrollcommand'] = yscrollbar.set
        
        canvas.pack(expand=1, fill='both', side='left')
        yscrollbar.pack(fill='y', side='right')
        xscrollbar.pack(fill='x', side='bottom')
        
        self._canvas_fsa = CanvasFSA(fsa, canvas)

    def pack(self, cnf={}, **kw):
        self._frame.pack(cnf, **kw)
        (minx, miny, maxx, maxy) = self._canvas['scrollregion'].split()
        self._canvas['width'] = max(FSAFrame.MINX, min(FSAFrame.MAXX,
                                            int(maxx)-int(minx)-2*SCROLLBORDER))
        self._canvas['height'] = max(FSAFrame.MINY, min(FSAFrame.MAXY,
                                             int(maxy)-int(miny)-2*SCROLLBORDER))

class FSAWindow:
    "Window to view FSA's."
    def __init__(self, fsa):
        self._top = Tkinter.Tk()
        self._top.bind('q', self.destroy)

        # Ok button.
        buttonframe = Tkinter.Frame(self._top)
        buttonframe.pack(fill='x', side='bottom')
        ok = Tkinter.Button(buttonframe, text='Done', command=self.destroy)
        ok.pack(side='left')
        help = Tkinter.Button(buttonframe, text='Help')
        help.pack(side='right')

        # FSAFrame.
        fsaframe = FSAFrame(self._top, fsa, background='white')
        fsaframe.pack(side='bottom', expand=1, fill='both')

    def destroy(self, *e):
        if self._top is not None: self._top.destroy()
        self._top = None

    def mainloop(self, n=0):
        self._top.mainloop(n)

def show_fsa(fsa):
    top = Tkinter.Tk()
    def destroy(e, top=top): top.destroy()
    top.bind('q', destroy)
    c = Tkinter.Canvas(top, closeenough='10.0', width=500, height=300)
    c.pack()
    f = CanvasFSA(fsa, c)
    top.mainloop()
                
# Test
if __name__ == '__main__':
    from nltk.set import Set
    #re = 'ab'
    #re = '(ab(c*)c)*dea(b*)'
    re = '(ab(c*)c)*'
    fsa = nltk.fsa.FSA("abcde")
    nltk.fsa.re2nfa(fsa, re)
    fsa = fsa.dfa()
    fsa.prune()
    #fsa.insert_transition(3,'hi',0)
    #fsa.delete_transition(0, nltk.fsa.epsilon, Set(1))
    w = FSAWindow(fsa)

    # n.b., this is optional, as long as you're running this from an
    # interactive Python shell..
    #w.mainloop()
