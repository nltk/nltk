# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A graphical tool for exploring chart parsing.

Chart parsing is a flexible parsing algorithm that uses a data
structure called a "chart" to record hypotheses about syntactic
constituents.  Each hypothesis is represented by a single "edge" on
the chart.  A set of "chart rules" determine when new edges can be
added to the chart.  This set of rules controls the overall behavior
of the parser (e.g., whether it parses top-down or bottom-up).

The chart parsing tool demonstrates the process of parsing a single
sentence, with a given grammar and lexicon.  Its display is divided
into three sections: the bottom section displays the chart; the middle
section displays the sentence; and the top section displays the
partial syntax tree corresponding to the selected edge.  Buttons along
the bottom of the window are used to control the execution of the
algorithm.

The chart parsing tool allows for flexible control of the parsing
algorithm.  At each step of the algorithm, you can select which rule
or strategy you wish to apply.  This allows you to experiment with
mixing different strategies (e.g., top-down and bottom-up).  You can
exercise fine-grained control over the algorithm by selecting which
edge you wish to apply a rule to.
"""

import Tkinter
import math

from nltk.parser.chart import *
from nltk.cfg import *
from nltk.token import WSTokenizer
from nltk.token import Token, Location
from nltk.tree import TreeToken

# Help text for ChartDemo
CHART_DEMO_HELP_TEXT = """\
The chart parsing demo allows you to interactively ...

"""

class ProductionView:
    """
    View a list of productions.  This can be used for the lexicon or for the
    grammar.
    """
    def __init__(self, productions, title='Production List'):
        self._productions = productions

        self._top = Tkinter.Tk()
        self._top.title(title)

        # Add a button list.
        buttons = Tkinter.Frame(self._top)
        buttons.pack(side='bottom')
        Tkinter.Button(buttons, text='Done', command=self.destroy).pack(side='right')

        # Create the list.
        listframe = Tkinter.Frame(self._top)
        listframe.pack(fill='both', expand='y')
        listscroll = Tkinter.Scrollbar(listframe, orient='vertical')
        self._listbox = listbox = Tkinter.Listbox(listframe)
        listbox.config(yscrollcommand = listscroll.set)
        listscroll.config(command=listbox.yview)
        listscroll.pack(side='right', fill='y')
        listbox.pack(side='left', fill='both', expand=1)

        # Add the productions.  We'll assume the production list is immutable..
        for production in self._productions:
            listbox.insert('end', production)

        # Add some keyboard bindings.
        #listbox.bind("<Double-Button-1>", self._ok)
        listbox.bind("q", self.destroy)

    def destroy(self, *args):
        if self._top == None: return
        self._top.destroy()
        self._top = None
        

class ChartView:
    """
    A component for viewing charts.  This is used by C{ChartDemo} to
    allow students to interactively experiment with various chart
    parsing techniques.  It is also used by C{Chart.draw()}.

    @ivar _chart: The chart that we are giving a view of.  This chart
       may be modified; after it is modified, you should call
       C{update}.
    @ivar _source: The list of tokens that the chart spans.

    @ivar _root: The root window.
    @ivar _chart_canvas: The canvas we're using to display the chart
        itself. 
    @ivar _tree_canvas: The canvas we're using to display the tree
        that each edge spans.  May be None, if we're not displaying
        trees. 
    @ivar _source_canvas: The canvas we're using to display the source
        text.  May be None, if we're not displaying the source text.
    @ivar _edgetags: A dictionary mapping from edges to the tags of
        the canvas elements (lines, etc) used to display that edge.
        The values of this dictionary have the form 
        C{(linetag, rhstag1, dottag, rhstag2, lhstag)}.
    @ivar _treetags: A list of all the tags that make up the tree;
        used to erase the tree (without erasing the loclines).
    @ivar _chart_height: The height of the chart canvas.
    @ivar _source_height: The height of the source canvas.
    @ivar _tree_height: The height of the tree

    @ivar _text_height: The height of a text string (in the normal
        font). 

    @ivar _edgelevels: A list of edges at each level of the chart (the
        top level is the 0th element).  This list is used to remember
        where edges should be drawn; and to make sure that no edges
        are overlapping on the chart view.

    @ivar _edgeselection: The currently selected edge; or None.
    
    @ivar _unitsize: Pixel size of one unit (from the location).  This
       is determined by the span of the chart's location, and the
       width of the chart display canvas.

    @ivar _fontsize: The current font size

    @ivar _marks: A dictionary from edges to marks.  Marks are
        strings, specifying colors (e.g. 'green').
    """
    
    _TOK_SPACING = 10
    _MARGIN = 10
    _TREE_LEVEL_SIZE = 15
    _CHART_LEVEL_SIZE = 45#40
    
    def __init__(self, chart, source=None, root=None, **kw):
        """
        Construct a new C{Chart} display.
        
        @type source: C{list} of C{Token}
        @param source: The list of Tokens that the chart spans.
        """
        # Process keyword args.
        draw_tree = kw.get('draw_tree', 0)
        draw_source = kw.get('draw_source', 1)
        self._fontsize = kw.get('fontsize', -12)
        
        if source is None:
            source = []
            draw_source = 0

        self._chart = chart
        self._source = source

        # Keep track of drawn edges
        self._edgelevels = []
        self._edgetags = {}

        # Keep track of which edges are marked.
        self._marks = {}

        # Keep track of a single "selected" edge
        self._edgeselection = None

        # Keep track of the tags used to draw the tree
        self._tree_tags = []

        # If they didn't provide a main window, then set one up.
        if root is None:
            top = Tkinter.Tk()
            top.title('Chart View')
            def destroy1(e, top=top): top.destroy()
            def destroy2(top=top): top.destroy()
            top.bind('q', destroy1)
            b = Tkinter.Button(top, text='Done', command=destroy2)
            b.pack(side='bottom')
            self._root = top
        else:
            self._root = root

        # Create the chart canvas.
        self._chart_canvas = self._sb_canvas(self._root)
        self._chart_canvas['height'] = 400
        self._chart_canvas['closeenough'] = 15

        # Create the source canvas.
        if draw_source:
            cframe = Tkinter.Frame(self._root, relief='sunk', border=2)
            cframe.pack(fill='both', side='bottom')
            self._source_canvas = Tkinter.Canvas(cframe, height=50)
            self._source_canvas.pack(fill='both')
            #self._source_canvas['height'] = self._source_height
        else:
            self._source_canvas = None

        # Create the tree canvas.
        if draw_tree:
            self._tree_canvas = self._sb_canvas(self._root, 'n', 'x')
            self._tree_canvas['height'] = 200
        else:
            self._tree_canvas = None

        # Do some analysis to figure out how big the window should be
        self._analyze()
        self.draw()     # ***** why do I need this draw?
        self._resize()
        self._grow()

        # Set up the configure callback, which will be called whenever
        # the window is resized.
        self._chart_canvas.bind('<Configure>', self._configure)
        
    def _sb_canvas(self, root, expand='y', 
                   fill='both', side='bottom'):
        """
        Helper for __init__: construct a canvas with a scrollbar.
        """
        cframe =Tkinter.Frame(root, relief='sunk', border=2)
        cframe.pack(fill=fill, expand=expand, side=side)
        canvas = Tkinter.Canvas(cframe)
        
        # Give the canvas a scrollbar.
        sb = Tkinter.Scrollbar(cframe, orient='vertical')
        sb.pack(side='right', fill='y')
        canvas.pack(side='left', fill=fill, expand='yes')

        # Connect the scrollbars to the canvas.
        sb['command']= canvas.yview
        canvas['yscrollcommand'] = sb.set

        return canvas


    def _grow(self):
        """
        Grow the window, if necessary
        """
        # Grow, if need-be
        loc = self._chart.loc()
        width = ( (loc.end() - loc.start())
                  * self._unitsize +
                  ChartView._MARGIN * 2 )
        self._chart_canvas['width'] = width
        unitwidth = loc.end() - loc.start()
        self._unitsize = ((width - 2*ChartView._MARGIN) /
                          unitwidth)

        # Reset the height for the source window.
        if self._source_canvas is not None:
            self._source_canvas['height'] = self._source_height
        
    def set_font_size(self, size):
        self._fontsize = -abs(size)
        self._analyze()
        self.draw()
        self._grow()
            
    def get_font_size(self):
        return abs(self._fontsize)
            
    def _configure(self, e):
        """
        The configure callback.  This is called whenever the window is
        resized.  It is also called when the window is first mapped.
        It figures out the unit size, and redraws the contents of each
        canvas.
        """
        loc = self._chart.loc()
        unitwidth = loc.end() - loc.start()
        self._unitsize = (e.width - 2*ChartView._MARGIN) / unitwidth
        self.draw()

    def update(self, chart=None):
        """
        Draw any edges that have not been drawn.  This is typically
        called when a after modifies the canvas that a CanvasView is
        displaying.  C{update} will cause any edges that have been
        added to the chart to be drawn.

        If update is given a C{chart} argument, then it will replace
        the current chart with the given chart.
        """
        if chart is not None:
            self._chart = chart
            self._edgelevels = []
            self._edgeselection = None
            self.draw()
        else:
            for edge in self._chart.edges():
                if not self._edgetags.has_key(edge):
                    self._add_edge(edge)
            self._resize()

    def _edge_conflict(self, edge, lvl):
        """
        Return 1 if the given edge overlaps with any edge on the given
        level.  This is used by _add_edge to figure out what level a
        new edge should be added to.
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
        """
        Given a new edge, recalculate:

            - _text_height
            - _unitsize (if the edge text is too big for the current
              _unitsize, then increase _unitsize)
        """
        c = self._chart_canvas

        for str in (' '.join([repr(t) for t in edge.prod().rhs()]),
                    edge.prod().lhs()):
            tag = c.create_text(0,0, text=str,
                                font=('helvetica', self._fontsize, 'bold'),
                                anchor='nw', justify='left')
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._TOK_SPACING
            edgelen = max(len(edge.loc()), 1)
            self._unitsize = max(width/edgelen, self._unitsize)
            self._text_height = max(self._text_height, bbox[3] - bbox[1])
    
    def _add_edge(self, edge, minlvl=0):
        """
        Add a single edge to the ChartView:

            - Call analyze_edge to recalculate display parameters
            - Find an available level
            - Call _draw_edge
        """
        if self._edgetags.has_key(edge): return
        self._analyze_edge(edge)
        self._grow()

        # Figure out what level to draw the edge on.
        lvl = 0
        while 1:
            # If this level doesn't exit yet, create it.
            if lvl >= len(self._edgelevels):
                self._edgelevels.append([])
                self._chart_height = (lvl+2)*self._chart_level_size

            # Check if we can fit the edge in this level.
            if lvl>=minlvl and not self._edge_conflict(edge, lvl):
                # Go ahead and draw it.
                self._edgelevels[lvl].append(edge)
                break

            # Try the next level.
            lvl += 1

        self._draw_edge(edge, lvl)

    def view_edge(self, edge):
        level = None
        for i in range(len(self._edgelevels)):
            if edge in self._edgelevels[i]:
                level = i
                break
        if level == None: return
        
        # Try to view the new edge..
        y = (level+1) * self._chart_level_size
        dy = self._text_height + 10
        self._chart_canvas.yview('moveto', 1.0)
        if self._chart_height != 0:
            self._chart_canvas.yview('moveto',
                                     float(y-dy)/self._chart_height)

    def _draw_edge(self, edge, lvl):
        """
        Draw a single edge on the ChartView.
        """
        c = self._chart_canvas
        loc = edge.loc()
        
        # Draw the arrow.
        x1 = (loc.start() * self._unitsize + ChartView._MARGIN)
        x2 = (loc.end() * self._unitsize + ChartView._MARGIN)
        if x2 == x1: x2 += max(4, self._unitsize/5)
        y = (lvl+1) * self._chart_level_size
        linetag = c.create_line(x1, y, x2, y, arrow='last', width=3)
                                

        # Draw a label for the edge.
        rhs = [str(t) for t in edge.prod().rhs()]
        pos = edge.dotpos()
        rhs1 = ' '.join(rhs[:pos])
        rhs2 = ' '.join(rhs[pos:])
        rhstag1 = c.create_text(x1+3, y, text=rhs1,
                                font=('helvetica', self._fontsize),
                                anchor='nw')
        dotx = c.bbox(rhstag1)[2] + 6
        doty = (c.bbox(rhstag1)[1]+c.bbox(rhstag1)[3])/2
        dottag = c.create_oval(dotx-2, doty-2, dotx+2, doty+2)
        rhstag2 = c.create_text(dotx+6, y, text=rhs2,
                                font=('helvetica', self._fontsize),
                                anchor='nw')
        lhstag =  c.create_text((x1+x2)/2, y, text=str(edge.prod().lhs()),
                                anchor='s',
                                font=('helvetica', self._fontsize, 'bold'))

        # Keep track of the edge's tags.
        self._edgetags[edge] = (linetag, rhstag1,
                                dottag, rhstag2, lhstag)

        # Register a callback for clicking on the edge.
        def cb(event, self=self, edge=edge): self.select_edge(edge)
        c.tag_bind(rhstag1, '<Button-1>', cb)
        c.tag_bind(rhstag2, '<Button-1>', cb)
        c.tag_bind(linetag, '<Button-1>', cb)
        c.tag_bind(dottag, '<Button-1>', cb)
        c.tag_bind(lhstag, '<Button-1>', cb)

        self._color_edge(edge)
        
    def _color_edge(self, edge, linecolor=None, textcolor=None):
        """
        Color in an edge with the given colors.
        If no colors are specified, use intelligent defaults
        (dependant on selection, etc.)
        """
        c = self._chart_canvas

        if linecolor is not None and textcolor is not None:
            tags = self._edgetags[edge]
            c.itemconfig(tags[0], fill=linecolor)
            c.itemconfig(tags[1], fill=textcolor)
            c.itemconfig(tags[2], fill=textcolor,
                         outline=textcolor)
            c.itemconfig(tags[3], fill=textcolor)
            c.itemconfig(tags[4], fill=textcolor)
            return
        else:
            if edge is self._edgeselection:
                self._color_edge(edge, '#f00', '#800')
            elif self._marks.has_key(edge):
                color = self._marks[edge]
                self._color_edge(edge, color, color)
            elif (edge.complete() and edge.loc() == self._chart.loc()):
                self._color_edge(edge, '#084', '#042')
            else:
                self._color_edge(edge, '#00f', '#008')

    def mark_edge(self, edge, mark='cyan4'):
        """
        Mark an edge
        """
        self._marks[edge] = mark
        self._color_edge(edge)

    def unmark(self, edge=None):
        """
        Unmark an edge (or all edges)
        """
        if edge == None:
            old_marked_edges = self._marks.keys()
            self._marks = {}
            for edge in old_marked_edges:
                self._color_edge(edge)
        else:
            del self._marks[edge]
            self._color_edge(edge)
                
    def select_edge(self, edge):
        """
        If the given edge is not currently selected, then unselect the
        old selected edge, and select the given edge.  If edge is
        currently selected, then deselect it.  If edge is None, then
        unselect the old edge.
        """
        c = self._chart_canvas

        # Unselect the old edge.
        oldedge = self._edgeselection
        if oldedge is not None:
            # If you select an already selected edge, then deselect it.
            if (edge and oldedge == edge): edge = None
            
            if not self._edgetags.has_key(oldedge):
                print 'Warning: _edgeselection is inconsistant'
                self._edgeselection = None
                return
            self._edgeselection = None
            self._color_edge(oldedge)

        if edge is None:
            self._edgeselection = None
            return

        # Select the new edge.
        self._edgeselection = edge
        self._color_edge(edge)

        # Draw the tree for the newly selected edge.
        if self._tree_canvas:
            self._draw_tree()
            
    def _analyze(self):
        """
        Analyze the source string, to figure out how big a unit needs 
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 70 # min unitsize
        text_height = 0
        c = self._chart_canvas

        # Check against all tokens
        for tok in self._source:
            tag = c.create_text(0,0, text=repr(tok.type()),
                                font=('helvetica', self._fontsize),
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

        # Size of chart levels
        self._chart_level_size = self._text_height * 2.5
        
        # Default tree size..
        self._tree_height = (3 * (ChartView._TREE_LEVEL_SIZE +
                                  self._text_height))
        self._chart_height = 0

        # Resize the scrollregions.
        self._resize()

    def _resize(self):
        """
        Update the scroll-regions for each canvas.  This ensures that
        everything is within a scroll-region, so the user can use the
        scrollbars to view the entire display.  This does I{not}
        resize the window.
        """
        c = self._chart_canvas

        # Reset the chart scroll region
        width = ( (self._chart._loc.end() -
                   self._chart._loc.start()) * self._unitsize +
                  ChartView._MARGIN * 2 )
        height = self._chart_height
        c['scrollregion']=(0,0,width,height)

        # Reset the tree scroll region
        if self._tree_canvas:
            self._tree_canvas['scrollregion'] = (0, 0, width,
                                                 self._tree_height)
            
        #if int(self._tree_canvas['height']) > self._tree_height:
        #    self._tree_canvas['height'] = self._tree_height

        # Reset the height for the source window.
        #self._source_canvas['height'] = self._source_height
                                         
    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        c1 = self._tree_canvas
        c2 = self._source_canvas
        c3 = self._chart_canvas
        margin = ChartView._MARGIN
        self._loclines = []
        for i in range(self._chart._loc.start()-1,
                       self._chart._loc.end()+1):
            x = i*self._unitsize + margin

            if c1:
                t1=c1.create_line(x, 0, x, 5000)
                c1.tag_lower(t1)
            if c2:
                t2=c2.create_line(x, 0, x, self._source_height)
                c2.tag_lower(t2)
            t3=c3.create_line(x, 0, x, 5000)
            c3.tag_lower(t3)
            t4=c3.create_text(x+2, 0, text=`i`, anchor='nw',
                              font=('helvetica', self._fontsize))
            c3.tag_lower(t4)
            #if i % 4 == 0:
            #    if c1: c1.itemconfig(t1, width=2, fill='gray60')
            #    if c2: c2.itemconfig(t2, width=2, fill='gray60')
            #    c3.itemconfig(t3, width=2, fill='gray60')
            if i % 2 == 0:
                if c1: c1.itemconfig(t1, fill='gray60')
                if c2: c2.itemconfig(t2, fill='gray60')
                c3.itemconfig(t3, fill='gray60')
            else:
                if c1: c1.itemconfig(t1, fill='gray80')
                if c2: c2.itemconfig(t2, fill='gray80')
                c3.itemconfig(t3, fill='gray80')

    def selected_edge(self):
        """Return the currently selected edge."""
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
                                font=('helvetica', self._fontsize),
                                anchor='n', justify='left')
            bbox = c.bbox(tag)
            rt=c.create_rectangle(x1+2, bbox[1]-(ChartView._TOK_SPACING/2),
                                  x2-2, bbox[3]+(ChartView._TOK_SPACING/2),
                                  fill='white', outline='white')
            c.tag_lower(rt)

    def _add_rhs(self, edge):
        """
        Edit the given tree to include nodes for the right hand side
        of its productions.  For each unexpanded node (i.e., elt to the
        right of the dot), add a new child whose token type is the
        empty string.
        """
        tree = edge.tree()
        rhs = edge.prod().rhs()
        pos = edge.dotpos()

        if tree.loc() is None:
            start_index = edge.loc().start()
            (unit, source) = (edge.loc().unit(), edge.loc().source())
        else:
            start_index = tree.loc().end() - 1
            (unit, source) = (tree.loc().unit(), tree.loc().source())
        
        rhchildren = []
        for i in range(pos, len(rhs)):
            tok = Token('', i+start_index, unit=unit, source=source)
            rhchildren.append(TreeToken(rhs[i], tok))
        children = list(tree.children()) + rhchildren
        return TreeToken(tree.node(), *children)

    def _draw_tree(self):
        """Draw the syntax tree for the selected edge"""
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)
        if not self._edgeselection: return
        if self._edgeselection.tree() is None: return
        if not isinstance(self._edgeselection.tree(), TreeToken): return
        treetok = self._add_rhs(self._edgeselection)
        
        self._draw_treetok(treetok, 0)
        self._tree_height = ((treetok.height()-1) *
                             (ChartView._TREE_LEVEL_SIZE +
                              self._text_height))
        self._resize()

    def _draw_treetok(self, treetok, depth):
        """
        Draw a treetoken.  Return the center x of this treetok.
        Return a negative x if treetok is not expanded.
        """
        c = self._tree_canvas
        margin = ChartView._MARGIN
        x1 = treetok.loc().start() * self._unitsize + margin
        x2 = treetok.loc().end() * self._unitsize + margin
        x = (x1+x2)/2
        y = depth * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        tag = c.create_text(x, y, anchor='n', justify='center',
                            text=str(treetok.node()),
                            font=('helvetica', self._fontsize, 'bold'),
                            fill='#042')
        self._tree_tags.append(tag)

        # If we're unexpanded, return a negative x.
        if (len(treetok.type()) == 1 and
            not isinstance(treetok[0], TreeToken) and
            treetok[0].type() == ''):
            c.itemconfig(tag, fill='#024')
            return -x

        for child in treetok:
            if isinstance(child, TreeToken):
                    childx = self._draw_treetok(child, depth+1)
                    if childx >= 0:
                        # Expanded child (left of dot)
                        tag = c.create_line(x, y + self._text_height, childx,
                                            y + ChartView._TREE_LEVEL_SIZE +
                                            self._text_height, width=2,
                                            fill='#084')
                    else:
                        # Unexpanded child (right of dot)
                        tag = c.create_line(x, y + self._text_height, -childx,
                                            y + ChartView._TREE_LEVEL_SIZE +
                                            self._text_height, width=2,
                                            fill='#048', dash='.')
            else:
                tag = c.create_line(x, y + self._text_height, x, 5000,
                                    width=2, fill='#084')
            self._tree_tags.append(tag)
        return x
            
    def draw(self):
        """
        Draw everything (from scratch).
        """
        if self._tree_canvas:
            self._tree_canvas.delete('all')
            self._draw_tree()

        if self._source_canvas:
            self._source_canvas.delete('all')
            self._draw_source()

        self._chart_canvas.delete('all')
        self._edgetags = {}
        
        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        # Add any new edges
        edges = self._chart.edges()
        edges.sort()
        for edge in edges:
            self._add_edge(edge)

        self._draw_loclines()

class ChartDemo:
    RULENAME = {'FundamentalRule': 'Fundamental Rule',
                'TopDownInitRule': 'Top-down Initialization',
                'TopDownRule': 'Top-down Rule',
                'BottomUpRule': 'Bottom-up Rule',
                }
    
    def __init__(self, grammar, text, title='Chart Parsing Demo'):

        self.root = None
        try:
            # Create the root window.
            self._root = Tkinter.Tk()
            self._root.title(title)
            self._root.bind('q', self.destroy)
            buttons3 = Tkinter.Frame(self._root)
            buttons3.pack(side='bottom', fill='x')
            buttons2 = Tkinter.Frame(self._root)
            buttons2.pack(side='bottom', fill='x')
            buttons1 = Tkinter.Frame(self._root)
            buttons1.pack(side='bottom', fill='x')

            self._lexiconview = self._grammarview = None
    
            self._grammar = grammar
            self._tok_sent = text
            self._cp = SteppingChartParser(self._grammar)
            self._cp.initialize(self._tok_sent)
            
            self._chart = self._cp.chart()
            self._cv = ChartView(self._chart, self._tok_sent,
                                 self._root, draw_tree=1, draw_source=1)

            ruletxt = 'Last edge generated by:'
            Tkinter.Label(buttons1,text=ruletxt).pack(side='left')
            self._rulelabel = Tkinter.Label(buttons1, width=30,
                                            font=('helvetica', 30, 'bold'),
                                            relief='groove', anchor='w')
            self._rulelabel.pack(side='left')
            
            Tkinter.Button(buttons2, text='Top down',
                           command=self.top_down).pack(side='left')
            Tkinter.Button(buttons2, text='Top down init',
                           command=self.top_down_init).pack(side='left')
            Tkinter.Button(buttons2, text='Bottom Up',
                           command=self.bottom_up).pack(side='left')
            Tkinter.Button(buttons2, text='Bottom Up init',
                           command=self.bottom_up_init).pack(side='left')
            Tkinter.Button(buttons2, text='Fundamental',
                           command=self.fundamental).pack(side='left')
            Tkinter.Button(buttons3, text='Reset Chart',
                           command=self.reset).pack(side='left')

            Tkinter.Button(buttons3, text='View Grammar',
                           command=self.view_grammar).pack(side='left')
            Tkinter.Button(buttons3, text='View Lexicon',
                           command=self.view_lexicon).pack(side='left')
    
            
            Tkinter.Button(buttons3, text='Done',
                           command=self.destroy).pack(side='right')
            Tkinter.Button(buttons3, text='Zoom out',
                           command=self.zoomout).pack(side='right')
            Tkinter.Button(buttons3, text='Zoom in',
                           command=self.zoomin).pack(side='right')
    
            # Set up a button to control stepping (default on)
            self._step = Tkinter.IntVar(self._root)
            step = Tkinter.Checkbutton(buttons1, text="Step", 
                                       variable=self._step)
            step.pack(side='right')
            step.select()

            # Initialize the rule-label font.
            size = self._cv.get_font_size()
            self._rulelabel.configure(font=('helvetica', size, 'bold'))
            Tkinter.mainloop()
        except:
            print 'Error creating Tree View'
            self.destroy()
            raise

    def zoomin(self):
        size = self._cv.get_font_size()+2
        self._cv.set_font_size(size)
        self._rulelabel['font'] = ('helvetica', size, 'bold')
        
    def zoomout(self):
        size = self._cv.get_font_size()-2
        if size > 6: self._cv.set_font_size(size)
        self._rulelabel['font'] = ('helvetica', size, 'bold')
        
    def view_lexicon(self):
        self._lexiconview = ProductionView(self._lexicon, 'Lexicon')

    def view_grammar(self):
        self._grammarview = ProductionView(self._grammar, 'Grammar')
        
    def reset(self):
        self._cp = SteppingChartParser(self._grammar, self._lexicon, 'S')
        self._cp.initialize(self._tok_sent, strategy=TD_STRATEGY)
        self._chart = self._cp.chart()
        self._cv.update(self._chart)

    def display_rule(self, rule):
        if rule == None:
            self._rulelabel['text'] = ''
        else:
            name = ChartDemo.RULENAME.get(rule.__class__.__name__, rule.__class__.__name__)
            self._rulelabel['text'] = name
            size = self._cv.get_font_size()
            self._rulelabel['font'] = ('helvetica', size, 'bold')
            
    def apply_strategy(self, strategy, edge_strategy=None):
        self.display_rule(None)
        self._cv.unmark()
        if self._step.get():
            edge = self._cv.selected_edge()
            if (edge is not None) and (edge_strategy is not None):
                print 'hm, not yet'
                #self._apply_strategy(edge_strategy(edge))
            else:
                self._apply_strategy(strategy)
        else:
            while self._cp.step(strategy=strategy):
                self._cv.update()

    def _apply_strategy(self, strategy):
        new_edge = self._cp.step(strategy=strategy)
                               
        if new_edge is not None:
            self.display_rule(self._cp.current_chartrule())
            self._cv.update()
            self._cv.mark_edge(new_edge)
            self._cv.view_edge(new_edge)
        return new_edge
    
    def top_down_init(self):
        self.apply_strategy([TopDownInitRule()], None)
        
    def top_down(self):
        self.apply_strategy([TopDownInitRule(), TopDownRule(),
                             FundamentalRule()], None)
        
    def fundamental(self):
        self.apply_strategy([FundamentalRule()], None)
    
    def bottom_up_init(self):
        self.apply_strategy([BottomUpRule()], None)
        
    def bottom_up(self):
        self.apply_strategy([BottomUpRule(), FundamentalRule()], None)
        
    def destroy(self, *args):
        if self._lexiconview: self._lexiconview.destroy()
        if self._grammarview: self._grammarview.destroy()
        if self._root is None: return
        self._root.destroy()
        self._root = None

def test():
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    grammar_rules1 = [
        CFGProduction(NP, Det, N), CFGProduction(NP, NP, PP),
        CFGProduction(NP, 'John'), CFGProduction(NP, 'I'), 
        CFGProduction(Det, 'the'), CFGProduction(Det, 'my'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'cookie'),

        CFGProduction(VP, VP, PP), CFGProduction(VP, V, NP),
        CFGProduction(VP, V),
        
        CFGProduction(V, 'ate'),  CFGProduction(V, 'saw'),

        CFGProduction(S, NP, VP),  CFGProduction(PP, P, NP),
        CFGProduction(P, 'with'), CFGProduction(P, 'under')]

    grammar = CFG(S, grammar_rules1)
    sent = 'I saw the dog with John with my cookie'
    tok_sent = WSTokenizer().tokenize(sent)

    print 'grammar= ('
    for rule in grammar.productions():
        print '    ', repr(rule)+','
    print ')'
    print 'sentence = %r' % sent
    print 'Calling "ChartDemo(grammar, tok_sent)"...'
    ChartDemo(grammar, tok_sent)

def test2():
    tok_sent = [Token('the', 0), Token('park', 1)]
    loc = Location(0,2)
    chart = Chart(loc)
    
    dr0 = DottedRule('Det', ('the',), 1)
    tt0 = TreeToken(dr0.lhs(), tok_sent[0])
    edge0 = Edge(dr0, tt0, Location(0))
    chart.insert(edge0)
    
    dr1 = DottedRule('N', ('park',), 1)
    tt1 = TreeToken(dr1.lhs(), tok_sent[1])
    edge1 = Edge(dr1, tt1, Location(1))
    chart.insert(edge1)
    
    dr2 = DottedRule('NP', ('Det','N'), 2)
    tt2 = TreeToken(dr2.lhs(), tt0, tt1)
    edge2 = Edge(dr2, tt2, Location(0,2))
    chart.insert(edge2)
    
    chart.draw()
    
    cv = ChartView(chart, tok_sent)

if __name__ == '__main__':
    test()
