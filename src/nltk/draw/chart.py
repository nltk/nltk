# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Drawing charts, etc.
"""

import Tkinter
import math
from nltk.chartparser import Chart, edgesort
from nltk.token import Token, Location

class ChartView:
    """
    @ivar _source: The list of tokens that the chart maps over.
    @ivar _chart: The chart we're drawing.
    @ivar _root: The root window.
    @ivar _canvas: The canvas we're drawing on.
    @ivar _height: The max height of a tree over the tokens
    @ivar _unitsize: Pixel size of a unit.
    @ivar _edgelevels: Edges on each level
    @ivar _edgetags: Canvas tags for each edge.
    """
    
    _TOK_SPACING = 10
    _MARGIN = 10
    _TREE_LEVEL_SIZE = 50
    _CHART_LEVEL_SIZE = 40
    
    def __init__(self, root, chart, source=None):
        """
        @type source: C{list} of C{Token}
        """
        self._chart = chart
        
        # Initialize source
        if source == None:
            loc = chart.loc()
            source = [Token(i, i) for i in
                      range(loc.start(), loc.end())]
        self._source = source

        # Keep track of drawn edges
        self._edgelevels = []
        self._edgetags = {}

        # Keep track of a single "selected" edge
        self._edgeselection = None

        # Create the chart window.
        self._root = root
        self._canvas = Tkinter.Canvas(self._root, width=600,
                                      height=600)
        self._canvas.pack(expand='true', fill='both')

        self._analyze()
        #self.draw()

        self._canvas.bind('<Configure>', self._configure)

    def _configure(self, e):
        loc = self._chart.loc()
        unitwidth = loc.end() - loc.start()
        self._unitsize = (e.width - 2*ChartView._MARGIN) / unitwidth
        self.draw()

    def update(self):
        """
        Draw any edges that have not been drawn.
        """
        self.draw()
        return
        drawnedges = self._edgetags.keys()
        for edge in self._chart.edges():
            if edge not in drawnedges:
                self._draw_edge(edge)

        self._resize()

    def _edge_conflict(self, edge, lvl):
        """
        Does the given edge conflict with (overlap) another edge on
        the same level?
        """
        loc = edge.loc()
        for otheredge in self._edgelevels[lvl]:
            otherloc = otheredge.loc()
            if loc.overlaps(otherloc):
                return 1
            if ((len(loc) == 0 or len(otherloc)==0) and
                (loc.start() == otherloc.end() or
                 loc.start() == otherloc.start() or
                 loc.end() == otherloc.end() or
                 loc.end() == otherloc.start())):
                return 1
        return 0

    def _analyze_edge(self, edge):
        c = self._canvas
        str = ' '.join([repr(t) for t in edge.dr()])
        tag = c.create_text(0,0, text=str,
                            anchor='nw', justify='left')
        bbox = c.bbox(tag)
        c.delete(tag)
        width = bbox[2] + ChartView._TOK_SPACING
        edgelen = max(len(edge.loc()), 1)
        self._unitsize = max(width/edgelen, self._unitsize)
        self._text_height = max(self._text_height, bbox[1], bbox[3])
    
    def _add_edge(self, edge, minlvl=0):
        """
        Draw a single edge.
        """
        if self._edgetags.has_key(edge): return
        self._analyze_edge(edge)
        
        # Figure out what level to draw the edge on.
        lvl = 0
        while 1:
            # If this level doesn't exit yet, create it.
            if lvl >= len(self._edgelevels):
                self._edgelevels.append([])
                self._chart_height = (lvl+2)*ChartView._CHART_LEVEL_SIZE

            # Check if we can fit the edge in this level.
            if lvl>=minlvl and not self._edge_conflict(edge, lvl):
                # Go ahead and draw it.
                self._edgelevels[lvl].append(edge)
                break

            # Try the next level.
            lvl += 1

        self._draw_edge(edge, lvl)

    def _draw_edge(self, edge, lvl):
        c = self._canvas
        loc = edge.loc()
        
        # Draw the arrow.
        x1 = (loc.start() * self._unitsize + ChartView._MARGIN)
        x2 = (loc.end() * self._unitsize + ChartView._MARGIN)
        if x2 == x1: x2 += max(4, self._unitsize/5)
        y = (self._tree_height + self._text_height +
             (lvl+1) * ChartView._CHART_LEVEL_SIZE)
        linetag = c.create_line(x1, y, x2, y, arrow='last',
                                width=3, fill='blue')

        # Draw a label for the edge.
        rhs = [repr(t) for t in edge.dr()]
        pos = edge.dr().pos()
        rhs1 = ' '.join(rhs[:pos])
        rhs2 = ' '.join(rhs[pos:])
        rhstag1 = c.create_text(x1+3, y, text=rhs1,
                                anchor='nw', fill='blue')
        dotx = c.bbox(rhstag1)[2] + 6
        doty = (c.bbox(rhstag1)[1]+c.bbox(rhstag1)[3])/2
        dottag = c.create_oval(dotx-2, doty-2, dotx+2, doty+2, 
                               fill='#008', outline='#008')        
        rhstag2 = c.create_text(dotx+6, y, text=rhs2,
                                anchor='nw', fill='#008')
        lhstag =  c.create_text((x1+x2)/2, y, text=str(edge.dr().lhs()),
                                anchor='s', fill='#008',
                                font=('helvetica', 12, 'bold'))

        # Keep track of the edge's tags.
        self._edgetags[edge] = (linetag, rhstag1,
                                dottag, rhstag2, lhstag)

        # Register a callback for clicking on the arrow.
        def cb(event, self=self, edge=edge): self.select_edge(edge)
        c.tag_bind(rhstag1, '<Button-1>', cb)
        c.tag_bind(rhstag2, '<Button-1>', cb)
        c.tag_bind(linetag, '<Button-1>', cb)
        c.tag_bind(dottag, '<Button-1>', cb)
        c.tag_bind(lhstag, '<Button-1>', cb)

        # If it's selected, highlight it.
        if edge is self._edgeselection:
            self._canvas.itemconfig(linetag, fill='#f00')
            self._canvas.itemconfig(rhstag1, fill='#800')
            self._canvas.itemconfig(dottag, fill='#800',
                                    outline='#800')
            self._canvas.itemconfig(rhstag2, fill='#800')

    def select_edge(self, edge, state=None):
        if self._edgeselection != None:
            # Unselect the old edge.
            oldtags = self._edgetags[self._edgeselection]
            self._canvas.itemconfig(oldtags[0], fill='#00f')
            self._canvas.itemconfig(oldtags[1], fill='#008')
            self._canvas.itemconfig(oldtags[2], fill='#008',
                                    outline='#008')
            self._canvas.itemconfig(oldtags[3], fill='#008')
            if self._edgeselection == edge and state == None:
                self._edgeselection = None
                return
            
        tags = self._edgetags[edge]
        if state == 0:
            self._canvas.itemconfig(tags[0], fill='#00f')
            self._canvas.itemconfig(tags[1], fill='#008')
            self._canvas.itemconfig(tags[2], fill='#008', outline='#008')
            self._canvas.itemconfig(tags[3], fill='#008')
            self._edgeselection = None
        else:
            self._canvas.itemconfig(tags[0], fill='#f00')
            self._canvas.itemconfig(tags[1], fill='#800')
            self._canvas.itemconfig(tags[2], fill='#800', outline='#800')
            self._canvas.itemconfig(tags[3], fill='#800')
            self._edgeselection = edge
            
    def _analyze(self):
        """
        Analyze the source string, to figure out how big a unit needs 
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 1
        text_height = 0
        c = self._canvas

        # Check against all tokens
        for tok in self._source:
            tag = c.create_text(0,0, text=repr(tok.type()),
                                anchor='nw', justify='left')
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._TOK_SPACING
            unitsize = max(width/len(tok.loc()), unitsize)
            text_height = max(text_height, bbox[1], bbox[3])

        self._unitsize = unitsize
        self._text_height = text_height
        
        # Check against edges.
        for edge in self._chart.edges():
            self._analyze_edge(edge)

        self._text_height +=  ChartView._TOK_SPACING

        # Figure out the tree height.  Assume no unary productions??
        maxdepth = math.log(len(self._source))/math.log(2)
        self._tree_height = maxdepth * ChartView._TREE_LEVEL_SIZE
        
        self._chart_height = 0
        self._resize()

    def _resize(self):
        # Grow, if need be.
        c = self._canvas
        width = ( (self._chart._loc.end() -
                   self._chart._loc.start()) * self._unitsize +
                  ChartView._MARGIN * 2 )
        height = (self._tree_height + self._text_height +
                  self._chart_height)
        if int(c['width']) < width:
            c['width' ] = width
        if int(c['height']) < height:
            c['height' ] = height

    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        c = self._canvas
        margin = ChartView._MARGIN
        for i in range(self._chart._loc.start()-1,
                       self._chart._loc.end()+1):
            x = i*self._unitsize + margin
            y1 = self._tree_height + self._text_height
            y2 = y1 + self._chart_height
            if i % 10 == 0:
                t=c.create_line(x, y1, x, y2, width=2)
                c.tag_lower(t)
                t=c.create_text(x+2, y1, text=`i`, anchor='nw')
                c.tag_lower(t)
            elif i % 5 == 0:
                t=c.create_line(x, y1, x, y2, fill='gray60')
                c.tag_lower(t)
                t=c.create_text(x+2, y1, text=`i`, anchor='nw')
                c.tag_lower(t)
            else:
                t=c.create_line(x, y1, x, y2, fill='gray80')
                c.tag_lower(t)

    def selected_edge(self):
        return self._edgeselection

    def _draw_source(self):
        """Draw the source string."""
        if len(self._source) == 0: return
        c = self._canvas
        margin = ChartView._MARGIN
        y = self._tree_height
        
        for tok in self._source:
            x1 = tok.loc().start() * self._unitsize + margin
            x2 = tok.loc().end() * self._unitsize + margin
            x = (x1+x2)/2
            tag = c.create_text(x, y, text=repr(tok.type()),
                                anchor='n', justify='left')
            bbox = c.bbox(tag)
            c.create_rectangle(x1, bbox[1]-(ChartView._TOK_SPACING/2),
                               x2, bbox[3]+(ChartView._TOK_SPACING/2))
        
    def draw(self):
        """
        Draw everything (from scratch).
        """
        self._canvas.delete('all')

        self._draw_source()

        self._edgetags = {}
        
        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        # Add any new edges
        edges = self._chart.edges()
        edges.sort(edgesort)
        for edge in edges:
            self._add_edge(edge)

        # Grow, if need-be
        self._resize()
        self._draw_loclines()

from nltk.chartparser import Rule, ChartParser
from nltk.token import WSTokenizer
class Demo:
    def __init__(self):
        # Create the root window.
        self._root = Tkinter.Tk()
        self._root.bind('q', self.destroy)

        grammar = (
            Rule('S',('NP','VP')),
            Rule('NP',('Det','N')),
            Rule('NP',('NP','PP')),
            Rule('VP',('V','PP')),
            Rule('PP',('P','NP'))
            )
        
        lexicon = (
            Rule('Det',('the',)),
            Rule('N',('cat',)),
            Rule('V',('sat',)),
            Rule('P',('on',)),
            Rule('N',('mat',))
            )
        
        sent = 'the cat sat on the mat on the mat'

        cp = ChartParser(grammar, 'S', lexicon)
        tok_sent = WSTokenizer().tokenize(sent)
        self._chart = cp.load_sentence(tok_sent)
        self._cv = ChartView(self._root, self._chart, tok_sent)

        def bottom_up(chart=self._chart, cv=self._cv, cp=cp):
            cp.bottom_up(chart)
            cv.update()
        def fundamental(chart=self._chart, cv=self._cv, cp=cp):
            edge1 = cv.selected_edge()
            new_edge = None
            if edge1 is not None and not edge1.final():
                for edge2 in chart.final_edges():
                    if new_edge != None: break
                    if (edge1.next() == edge2.lhs() and
                        edge1.end() == edge2.start()):
                        new_edge = edge1.fundamental(edge2)
                        if not chart.add_edge(new_edge):
                            new_edge = None

            if new_edge is None:
                chart_edges = chart.edges()
                chart_edges.sort(edgesort)
                for edge1 in chart_edges:
                    if edge1.final(): continue
                    if new_edge != None: break
                    for edge2 in chart.final_edges():
                        if new_edge != None: break
                        if (edge1.next() == edge2.lhs() and
                            edge1.end() == edge2.start()):
                            test_edge = edge1.fundamental(edge2)
                            if test_edge not in chart_edges:
                                new_edge = edge1

            cv.update()
            if new_edge != None: 
                cv.select_edge(new_edge, 1)

        buttons = Tkinter.Frame(self._root)
        buttons.pack()
        b1=Tkinter.Button(buttons, text='Bottom Up',
                          command=bottom_up)
        b2=Tkinter.Button(buttons, text='Fundamental',
                          command=fundamental)
        b1.pack(side='left')
        b2.pack(side='left')

    def destroy(self, *args):
        if self._root == None: return
        self._root.destroy()
        self._root = None

Demo()    

        

