"""
Draw a finite state automoton
"""

import Tkinter, random
from nltk.fsa import FSA

class _Node:
    def __init__(self, x, y, label, canvas, **kw):
        self._x = x
        self._y = y
        self._label = label
        self._canvas = canvas
        self._incoming = []
        self._outgoing = []

        # Draw the node
        tag1 = canvas.create_oval(x-5, y-5, x+5, y+5, **kw)
        tag2 = canvas.create_text(x, y-5, text=label, anchor='s')
        self._tags = [tag1, tag2]

        # Set up a movement callback
        canvas.tag_bind(tag1, '<ButtonPress-1>', self._press_cb)
        canvas.tag_bind(tag2, '<ButtonPress-1>', self._press_cb)

    def x(self): return self._x
    def y(self): return self._y
    def label(self): return self._label
    def incoming(self): return self._incoming
    def outgoing(self): return self._outgoing
    def add_incoming(self, edge): self._incoming.append(edge)
    def add_outgoing(self, edge): self._outgoing.append(edge)
    def move(self, newx, newy):
        self._canvas.move(self._tags[0], (newx-self._x), (newy-self._y))
        self._canvas.move(self._tags[1], (newx-self._x), (newy-self._y))
        self._x = newx
        self._y = newy
        for edge in self._incoming:
            edge.move_end(newx, newy)
        for edge in self._outgoing:
            edge.move_start(newx, newy)

    def _press_cb(self, event):
        self._mcb_id = self._canvas.bind('<Motion>', self._motion_cb)
        self._rcb_id = self._canvas.bind('<ButtonRelease-1>', self._release_cb)

    def _motion_cb(self, event):
        (x,y) = (event.x, event.y)
        self.move(x, y)

    def _release_cb(self, event):
        self._canvas.unbind('<Motion>', self._mcb_id)
        self._canvas.unbind('<Motion>', self._rcb_id)

class _Edge:
    def __init__(self, x1, y1, x2, y2, label, canvas, **kw):
        self._x1 = x1
        self._y1 = y1
        self._x2 = x2
        self._y2 = y2
        self._label = label
        self._canvas = canvas

        kw['arrow'] = 'last'
        kw['smooth'] = 1
        tag1 = canvas.create_line(*(self._line_coords()), **kw)

        (textx, texty) = self._text_coords()
        tag2 = canvas.create_text(textx, texty, text=label, anchor='sw')
        self._tags = [tag1, tag2]

    def _text_coords(self):
        x1 = self._x1
        y1 = self._y1
        x2 = self._x2
        y2 = self._y2
        textx = (x1+x2)*0.5 + (y2-y1)*0.1
        texty = (y1+y2)*0.5 - (x2-x1)*0.1
        return (textx, texty)
    
    def _line_coords(self):
        x1 = self._x1
        y1 = self._y1
        x2 = self._x2
        y2 = self._y2
        x3 = (x1+x2)*0.5 + (y2-y1)*0.1
        y3 = (y1+y2)*0.5 - (x2-x1)*0.1
        # Adjust endpoints..
        r = math.sqrt((x1-x2)**2 + (y1-y2)**2)
        x2 -= (x2-x1) * 5 / r
        y2 -= (y2-y1) * 5 / r
        x1 -= (x1-x2) * 5 / r
        y1 -= (y1-y2) * 5 / r
        return (x1, y1, x3, y3, x2, y2)

    def x1(self): return self._x1
    def y1(self): return self._y1
    def x2(self): return self._x2
    def y2(self): return self._y2
    def label(self): return self._label

    def move_start(self, newx, newy):
        self._x1 = newx
        self._y1 = newy
        self._canvas.coords(self._tags[0], self._line_coords())
        self._canvas.coords(self._tags[1], self._text_coords())
    def move_end(self, newx, newy):
        self._x2 = newx
        self._y2 = newy
        self._canvas.coords(self._tags[0], self._line_coords())
        self._canvas.coords(self._tags[1], self._text_coords())


class FSADraw:
    def __init__(self, fsa, canvas):
        self._fsa = fsa
        self._canvas = canvas

        nodes = self._nodes = {}
        edges = self._edges = {}

        if canvas['scrollregion']:
            (self._left, self._top, self._right, self._bot) = canvas['scrollregion']
        else:
            self._left = self._top = 0
            self._right = int(canvas['width'])
            self._bot = int(canvas['height'])

        # Edges.
        for (s1, label, s2s) in fsa.transitions():
            for s2 in s2s.elements():
                # Add nodes..
                if not nodes.has_key(s1):
                    nodes[s1] = self.new_node(s1)
                if not nodes.has_key(s2):
                    nodes[s2] = self.new_node(s2)

                # Draw the edge.
                key = (s1, s2)
                edges[key] = _Edge(nodes[s1].x(), nodes[s1].y(),
                                   nodes[s2].x(), nodes[s2].y(),
                                   label, canvas, fill='blue')

                # Tell the nodes about it.
                nodes[s1].add_outgoing(edges[key])
                nodes[s2].add_incoming(edges[key])

    def new_node(self, state):
        x = random.randint(self._left+10, self._right-10)
        y = random.randint(self._top+10, self._bot-10)
        if state in self._fsa._finals:
            return _Node(x, y, str(state), self._canvas, fill='red')
        else:
            return _Node(x, y, str(state), self._canvas, fill='green3')
        
# Main
if __name__ == '__main__':
    re = 'a(b*)c'
    print 'Regular Expression:', re
    fsa = FSA(re)
    fsa.pp()
    top = Tkinter.Tk()
    def destroy(e, top=top): top.destroy()
    top.bind('q', destroy)
    c = Tkinter.Canvas(top, closeenough='3.0')
    c.pack()
    f = FSADraw(fsa, c)
    top.mainloop()
    
                
                
