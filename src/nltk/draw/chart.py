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
#import math
from nltk.chartparser import Chart, edgecmp
from nltk.token import Token, Location

class ChartView:
    """
    @ivar _root: The root window.
    @ivar _chart_canvas: The canvas we're drawing on.
    @ivar _tree_canvas: The canvas we're drawing on.
    @ivar _source_canvas: The canvas we're drawing on.
    
    @ivar _chart: The chart we're drawing.
    @ivar _source: The list of tokens that the chart maps over.
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
        self._tree_canvas = self._sb_canvas(root, 'n', 'x')
        cframe = Tkinter.Frame(self._root, relief='sunk', border=2)
        cframe.pack(fill='both')
        self._source_canvas = Tkinter.Canvas(cframe, width=600,
                                             height=50)
        self._source_canvas.pack(fill='both')
        self._chart_canvas = self._sb_canvas(root)
        self._chart_canvas['height'] = 400

        self._analyze()
        self._chart_canvas.bind('<Configure>', self._configure)

    def _sb_canvas(self, root, expand='y', fill='both'):
        cframe =Tkinter.Frame(root, relief='sunk', border=2)
        cframe.pack(fill=fill, expand=expand)
        canvas = Tkinter.Canvas(cframe)
        
        # Give the canvas a scrollbar.
        sb = Tkinter.Scrollbar(cframe, orient='vertical')
        sb.pack(side='right', fill='y')
        canvas.pack(side='left', fill=fill, expand='yes')

        # Connect the scrollbars to the canvas.
        sb['command']=canvas.yview
        canvas['yscrollcommand'] = sb.set

        return canvas

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
                loc.start() == otherloc.start()):
                return 1
        return 0

    def _analyze_edge(self, edge):
        c = self._chart_canvas
        str = ' '.join([repr(t) for t in edge.dr()])
        tag = c.create_text(0,0, text=str,
                            anchor='nw', justify='left')
        bbox = c.bbox(tag)
        c.delete(tag)
        width = bbox[2] + ChartView._TOK_SPACING
        edgelen = max(len(edge.loc()), 1)
        self._unitsize = max(width/edgelen, self._unitsize)
        self._text_height = max(self._text_height, bbox[3] - bbox[1])
    
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
        c = self._chart_canvas
        loc = edge.loc()
        
        # Draw the arrow.
        x1 = (loc.start() * self._unitsize + ChartView._MARGIN)
        x2 = (loc.end() * self._unitsize + ChartView._MARGIN)
        if x2 == x1: x2 += max(4, self._unitsize/5)
        y = (lvl+1) * ChartView._CHART_LEVEL_SIZE
        linetag = c.create_line(x1, y, x2, y, arrow='last',
                                width=3, fill='#00f')

        # Draw a label for the edge.
        rhs = [repr(t) for t in edge.dr()]
        pos = edge.dr().pos()
        rhs1 = ' '.join(rhs[:pos])
        rhs2 = ' '.join(rhs[pos:])
        rhstag1 = c.create_text(x1+3, y, text=rhs1,
                                anchor='nw', fill='#00f')
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
            c.itemconfig(linetag, fill='#f00')
            c.itemconfig(rhstag1, fill='#800')
            c.itemconfig(dottag, fill='#800',
                                    outline='#800')
            c.itemconfig(rhstag2, fill='#800')

    def select_edge(self, edge, state=None):
        c = self._chart_canvas
        if self._edgeselection != None:
            # Unselect the old edge.
            oldtags = self._edgetags[self._edgeselection]
            c.itemconfig(oldtags[0], fill='#00f')
            c.itemconfig(oldtags[1], fill='#008')
            c.itemconfig(oldtags[2], fill='#008',
                                    outline='#008')
            c.itemconfig(oldtags[3], fill='#008')
            if self._edgeselection == edge and state == None:
                self._edgeselection = None
                return
            
        tags = self._edgetags[edge]
        if state == 0:
            c.itemconfig(tags[0], fill='#00f')
            c.itemconfig(tags[1], fill='#008')
            c.itemconfig(tags[2], fill='#008', outline='#008')
            c.itemconfig(tags[3], fill='#008')
            self._edgeselection = None
        else:
            c.itemconfig(tags[0], fill='#f00')
            c.itemconfig(tags[1], fill='#800')
            c.itemconfig(tags[2], fill='#800', outline='#800')
            c.itemconfig(tags[3], fill='#800')
            self._edgeselection = edge
            
    def _analyze(self):
        """
        Analyze the source string, to figure out how big a unit needs 
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 1
        text_height = 0
        c = self._tree_canvas

        # Check against all tokens
        for tok in self._source:
            tag = c.create_text(0,0, text=repr(tok.type()),
                                anchor='nw', justify='left')
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._TOK_SPACING
            unitsize = max(width/len(tok.loc()), unitsize)
            text_height = max(text_height, bbox[3] - bbox[1])

        self._unitsize = unitsize
        self._text_height = text_height
        self._source_height = (self._text_height +
                               2*ChartView._MARGIN)
        
        # Check against edges.
        for edge in self._chart.edges():
            self._analyze_edge(edge)

        # Figure out the tree height.  Assume no unary productions??
        maxdepth = 3#math.log(len(self._source))/math.log(2)
        self._tree_height = maxdepth * ChartView._TREE_LEVEL_SIZE
        self._chart_height = 0
        self._resize()

    def _resize(self):
        # Grow, if need be.
        c = self._chart_canvas
        width = ( (self._chart._loc.end() -
                   self._chart._loc.start()) * self._unitsize +
                  ChartView._MARGIN * 2 )
        height = self._chart_height
        if int(c['width']) < width:
            c['width' ] = width
        self._tree_canvas['height'] = self._tree_height
        c['scrollregion']=(0,0,width,height)

        self._source_canvas['height'] = self._source_height
                                         

    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        c1 = self._tree_canvas
        c2 = self._source_canvas
        c3 = self._chart_canvas
        margin = ChartView._MARGIN
        for i in range(self._chart._loc.start()-1,
                       self._chart._loc.end()+1):
            x = i*self._unitsize + margin
            
            t1=c1.create_line(x, 0, x, self._tree_height)
            c1.tag_lower(t1)
            t2=c2.create_line(x, 0, x, self._source_height)
            c2.tag_lower(t2)
            t3=c3.create_line(x, 0, x, self._chart_height)
            c3.tag_lower(t3)
            t4=c3.create_text(x+2, 0, text=`i`, anchor='nw')
            c3.tag_lower(t4)
            if i % 5 == 0:
                c1.itemconfig(t1, width=2, fill='gray40')
                c2.itemconfig(t2, width=2, fill='gray40')
                c3.itemconfig(t3, width=2, fill='gray40')
            elif i % 2 == 0:
                c1.itemconfig(t1, fill='gray40')
                c2.itemconfig(t2, fill='gray40')
                c3.itemconfig(t3, fill='gray40')
            else:
                c1.itemconfig(t1, fill='gray70')
                c2.itemconfig(t2, fill='gray70')
                c3.itemconfig(t3, fill='gray70')

    def selected_edge(self):
        return self._edgeselection

    def _draw_source(self):
        """Draw the source string."""
        if len(self._source) == 0: return
        c = self._source_canvas
        margin = ChartView._MARGIN
        y = ChartView._MARGIN
        
        for tok in self._source:
            x1 = tok.loc().start() * self._unitsize + margin
            x2 = tok.loc().end() * self._unitsize + margin
            x = (x1+x2)/2
            tag = c.create_text(x, y, text=repr(tok.type()),
                                anchor='n', justify='left')
            bbox = c.bbox(tag)
            rt=c.create_rectangle(x1+2, bbox[1]-(ChartView._TOK_SPACING/2),
                                  x2-2, bbox[3]+(ChartView._TOK_SPACING/2),
                                  fill='white', outline='white')
            c.tag_lower(rt)
        
    def draw(self):
        """
        Draw everything (from scratch).
        """
        self._tree_canvas.delete('all')
        self._source_canvas.delete('all')
        self._chart_canvas.delete('all')

        self._draw_source()

        self._edgetags = {}
        
        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        # Add any new edges
        edges = self._chart.edges()
        edges.sort(edgecmp)
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
        buttons = Tkinter.Frame(self._root)
        buttons.pack(side='bottom')

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

        cp = ChartParser(grammar, lexicon, 'S')
        tok_sent = WSTokenizer().tokenize(sent)
        self._chart = cp.load_sentence(tok_sent)
        self._cv = ChartView(self._root, self._chart, tok_sent)

        def bottom_up(chart=self._chart, cv=self._cv, cp=cp):
            cp.bottom_up_init(chart)
            cv.update()
        def fundamental(chart=self._chart, cv=self._cv, cp=cp):
            edge1 = cv.selected_edge()
            new_edge = None
            if edge1 is not None and not edge1.complete():
                for edge2 in chart.final_edges():
                    if new_edge != None: break
                    if (edge1.next() == edge2.lhs() and
                        edge1.end() == edge2.start()):
                        new_edge = edge1.fundamental(edge2)
                        if not chart.add_edge(new_edge):
                            new_edge = None

            if new_edge is None:
                chart_edges = chart.edges()
                chart_edges.sort(edgecmp)
                for edge1 in chart_edges:
                    if edge1.complete(): continue
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

        

