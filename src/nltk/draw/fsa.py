"""
Draw a finite state automoton
"""

import Tkinter, random, math
from nltk.fsa import FSA

class _Node:
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

    def _motion_cb(self, event):
        (x,y) = (event.x, event.y)
        self.move(x, y)

    def _release_cb(self, event):
        self._canvas.unbind('<Motion>', self._mcb_id)
        self._canvas.unbind('<Motion>', self._rcb_id)

class _LevelNode(_Node):
    """
    A node whose position is specified (initially, at least) by a
    level and levelpos within that detph..
    """
    XWIDTH = 80
    YWIDTH = 70
    def __init__(self, level, levelpos, label, canvas):
        self._level = level
        self._levelpos = levelpos
        (x,y) = self._coords()
        _Node.__init__(self, x, y, label, canvas)

    def _coords(self):
        if self._level is None or self._levelpos is None:
            return (0, 0)
        else:
            return (self._level * _LevelNode.XWIDTH + 20,
                    self._levelpos * _LevelNode.YWIDTH + 20)

    def level(self): return self._level
    def levelpos(self): return self._levelpos
    def levelmove(self, level, levelpos):
        self._level = level
        self._levelpos = levelpos
        _Node.move(self, *self._coords())

    def __repr__(self):
        return '<Node %s level=%s, lpos=%s>' % (self.label(), self._level,
                                                self._levelpos)

class _Edge:
    CURVE = 0.15
    def __init__(self, node1, node2, label, canvas):
        self._node1 = node1
        self._node2 = node2
        self._label = label
        self._canvas = canvas
        self._tags = None
        self._linecolor = self._textcolor = 'black'
        self._font = None

    def draw(self):
        if self._tags is not None: return

        kw = {'arrow':'last', 'fill':self._linecolor, 'smooth':1}
        tag1 = self._canvas.create_line(*self._line_coords(), **kw)

        (textx, texty) = self._text_coords()
        tag2 = self._canvas.create_text(textx, texty, text=self._label,
                                        anchor='c', fill=self._textcolor)
        if self._font: self._canvas.itemconfig(tag2, font=self._font)
        self._tags = [tag1, tag2]

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
        r = math.sqrt((x1-x2)**2 + (y1-y2)**2)
        textx = (x1+x2)*0.5 + (y2-y1)*(_Edge.CURVE/2) + (y2-y1) * 8 / r
        texty = (y1+y2)*0.5 - (x2-x1)*(_Edge.CURVE/2) - (x2-x1) * 8 / r
        return (textx, texty)
    
    def _line_coords(self):
        x1 = self._node1.x()
        y1 = self._node1.y()
        x2 = self._node2.x()
        y2 = self._node2.y()
        x3 = (x1+x2)*0.5 + (y2-y1)*_Edge.CURVE
        y3 = (y1+y2)*0.5 - (x2-x1)*_Edge.CURVE
        # Adjust endpoints..
        r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
        x2 -= (x2-x1) * 5 / r
        y2 -= (y2-y1) * 5 / r
        x1 -= (x1-x2) * 5 / r
        y1 -= (y1-y2) * 5 / r
        return (x1, y1, x3, y3, x2, y2)

    def from_node(self): return self._node1
    def to_node(self): return self._node2
    def label(self): return self._label

    def update(self):
        """
        Respond to node movement.
        """
        if self._tags is not None:
            self._canvas.coords(self._tags[0], self._line_coords())
            self._canvas.coords(self._tags[1], self._text_coords())

class FSADraw:
    def __init__(self, fsa, canvas):
        self._fsa = fsa
        self._canvas = canvas

        nodes = self._nodes = {}
        edges = self._edges = []

        if canvas['scrollregion']:
            (self._left, self._top, self._right, self._bot) = canvas['scrollregion']
        else:
            self._left = self._top = 0
            self._right = int(canvas['width'])
            self._bot = int(canvas['height'])

        self._add_fsa(fsa)

    def _add_fsa(self, fsa):
        nodes = self._nodes
        edges = self._edges
        for (s1, label, s2s) in fsa.transitions():
            for s2 in s2s.elements():
                # Add nodes..
                if not nodes.has_key(s1): nodes[s1] = self._make_node(s1)
                if not nodes.has_key(s2): nodes[s2] = self._make_node(s2)

                # Add the edge
                edges.append(self._make_edge(nodes[s1], nodes[s2], label))

                # Tell the nodes about it the edge.
                nodes[s1].add_outgoing(edges[-1])
                nodes[s2].add_incoming(edges[-1])

        self._arrange()

        # Draw them
        for node in self._nodes.values(): node.draw()
        for edge in edges: edge.draw()

    def _make_node(self, state):
        node = _LevelNode(None, None, str(state), self._canvas)
        if state in self._fsa._finals: node.color('red')
        else: node.color('green3')
        return node

    def _make_edge(self, node1, node2, label):
        if label is not None: 
            edge = _Edge(node1, node2, label, self._canvas)
        else:
            edge = _Edge(node1, node2, 'e', self._canvas)
            edge.font(('symbol', 12))
        edge.color('blue4', 'blue3')
        return edge
    
    def _arrange(self):
        nodes = self._nodes
        edges = self._edges

        total_nodes = len(self._nodes)
        nodes_processed = 0
        
        # Get the 1st-level nodes.
        levels = [[]]
        for (state, node) in nodes.items():
            if len(node.incoming()) == 0:
                levels[0].append(node)
                node.levelmove(0, None)
                nodes_processed += 1

        # If there were none..
        if levels[-1] == []:
            levels[-1] = nodes.values()[:1]

        # Put the remaining nodes into levels
        levelnum = 0
        while (nodes_processed < total_nodes):
            if levelnum > 10: raise ValueError()
            levels.append([])
            for node1 in levels[levelnum]:
                for edge in node1.outgoing():
                    node2 = edge.to_node()
                    if node2.level() is None:
                        levels[-1].append(node2)
                        node2.levelmove(levelnum+1, None)
                        nodes_processed += 1
            levelnum += 1

        # Now we want to minimize crossing edges.. how, again? :)
        for i in range(len(levels)):
            for j in range(len(levels[i])):
                levels[i][j].levelmove(i, j)

def show_fsa(fsa):
    top = Tkinter.Tk()
    def destroy(e, top=top): top.destroy()
    top.bind('q', destroy)
    c = Tkinter.Canvas(top, closeenough='3.0', width=500, height=300)
    c.pack()
    f = FSADraw(fsa, c)
    top.mainloop()
                
# Main
if __name__ == '__main__':
    re = '(ab(c*)c)*'
    print 'Regular Expression:', re
    fsa = FSA(re)
    print fsa.pp()
    show_fsa(fsa)
