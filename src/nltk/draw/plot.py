# Natural Language Toolkit: Simple Plotting
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A simple tool for plotting functions.
"""

# Delegate to BLT?
#   <http://sourceforge.net/projects/blt/>
#   

#from chktype import chktype as _chktype 
from types import FunctionType as _FunctionType
from types import MethodType as _MethodType
from types import BuiltinFunctionType as _BuiltinFunctionType
from types import IntType as _IntType
from types import FloatType as _FloatType
from math import log
import Tkinter, sys

class BLTPlot:
    def __init__(self, vals, rng=None, **kwargs):
        self._dragging = 0
        self._x0 = self._y0 = self._x1 = self._y1 = 0
        
        self._root = Tkinter.Tk()
        self._root.bind('q', self.destroy)
        try:
            import Pmw
            # This import is needed to prevent an error if we create
            # more than 1 graph in the same interactive session:
            reload(Pmw.Blt)
            
            Pmw.initialise()
            self._graph = Pmw.Blt.Graph(self._root)
            self._graph.pack(expand=1, fill='both')
        except:
            self._root.destroy()
            raise
            raise AssertionError('Pwm not installed!')

        self._graph.configure(title='Left: zoom in.  Right: zoom out.')
        
        # Derive vals and range.
        if type(vals) in (_FunctionType, _BuiltinFunctionType,
                            _MethodType):
            if rng == None: rng = [x*0.1 for x in range(-100, 100)]
            vals = [vals(i) for i in rng]
        elif len(vals) > 0 and type(vals[0]) in (type(()), type([])):
                rng = [x for (x,y) in vals]
                vals = [y for (x,y) in vals]
        elif rng == None:
            rng = range(len(vals))
        self._vals = tuple(vals)
        self._rng = tuple(rng)

        self._graph.line_create(kwargs.get('title', 'Plot'),
                                xdata=self._rng,
                                ydata=self._vals,
                                symbol='')
        self._graph.grid_on()
        if not kwargs.has_key('title'):
            print self._graph.legend_configure(hide=1)
        
        scale = kwargs.get('scale', 'linear')
        self._xscale = self._yscale = 'linear'
        if scale in ('log-linear', 'log_linear', 'log'):
            self._graph.xaxis_configure(logscale=1)
            self._xscale = 'log'
        if scale in ('linear-log', 'linear_log', 'log'):
            self._graph.yaxis_configure(logscale=1)
            self._yscale = 'log'

        # Find max/min's.
        self._xmax = max(rng)
        self._xmin = min(rng)
        self._ymax = max(vals)
        self._ymin = min(vals)

        # Set up zooming
        self._graph.bind(sequence="<ButtonPress>", func=self.mouseDown)
        self._graph.bind(sequence="<ButtonRelease>", func=self.mouseUp)
        
    def zoom(self, x0, y0, x1, y1):
        if x0 < self._xmin:
            x1 += (self._xmin - x0)
            x0 = self._xmin
        if y0 < self._ymin:
            y1 += (self._ymin - y0)
            y0 = self._ymin
        x1 = min(self._xmax, x1)
        y1 = min(self._ymax, y1)
        self._graph.xaxis_configure(min=x0, max=x1)
        self._graph.yaxis_configure(min=y0, max=y1)

    def mouseDrag(self, event):
        if not self._dragging: return
        (x0, y0) = (self._x0, self._y0)
        (x1, y1) = self._graph.invtransform(event.x, event.y)
        (self._x1, self._y1) = (x1, y1)
        
        self._graph.marker_configure("zoom", 
                                     coords = (x0, y0, x1, y0, x1,
                                               y1, x0, y1, x0, y0))
    
    def mouseUp(self, event):
        (x0, y0) = (self._x0, self._y0)
        (x1, y1) = (self._x1, self._y1)
        if self._dragging:
            self._graph.unbind("<Motion>", self._bindid)
            self._graph.marker_delete("zoom")
            
            if x0 != x1 and y0 != y1:
                # make sure the coordinates are sorted
                if x0 > x1: x0, x1 = x1, x0
                if y0 > y1: y0, y1 = y1, y0
         
                if event.num == 1:
                   self.zoom(x0, y0, x1, y1) # zoom in
                else:
                   (X0, X1) = self._graph.xaxis_limits()
                   k  = (X1-X0)/(x1-x0)
                   x0 = X0 -(x0-X0)*k
                   x1 = X1 +(X1-x1)*k
                   
                   (Y0, Y1) = self._graph.yaxis_limits()
                   k  = (Y1-Y0)/(y1-y0)
                   y0 = Y0 -(y0-Y0)*k
                   y1 = Y1 +(Y1-y1)*k
                   
                   self.zoom(x0, y0, x1, y1) # zoom out
                           
    def mouseDown(self, event):
        self._dragging = 0
        
        if self._graph.inside(event.x, event.y):
            self._dragging = 1
            (x0, y0) = self._graph.invtransform(event.x, event.y)
            (self._x0, self._y0) = (x0, y0)
            
            self._graph.marker_create("line", name="zoom",
                                      dashes=(2, 2))
            self._bindid = self._graph.bind("<Motion>", self.mouseDrag)
    
    def destroy(self, *args):
        if self._root is None: return
        self._root.destroy()
        self._root = None

    def mainloop(self, *varargs, **kwargs):
        self._root.mainloop(*varargs, **kwargs)
        

class SimplePlot:
    def __init__(self, vals, rng=None, **kwargs):
        """
        @type vals: C{function} or (C{list} of C{number}s) or (C{list} of
            C{pair} of C{number}s)
        @type rng: C{list} of C{number}s
        @param kwargs: Keyword arguments:
            - C{scale}: what scale to use to plot the graph.
              Currently, the options are C{"linear"}, C{"log"},
              C{"log-linear"}, and C{"linear-log"}.
        """
        # Handle keyword arguments.
        self._xscale = 'linear'
        self._yscale = 'linear'
        for (key, val) in kwargs.items():
            if key.lower() == 'scale':
                if val.lower() == 'linear':
                    self._xscale = self._yscale = 'linear'
                elif val.lower() == 'log':
                    self._xscale = self._yscale = 'log'
                elif val.lower() in ('log-linear', 'log_linear'):
                    self._xscale = 'log'
                    self._yscale = 'linear'
                elif val.lower() in ('linear-log', 'linear_log'):
                    self._xscale = 'linear'
                    self._yscale = 'log'
                else:
                    raise ValueError('Bad scale value %s' % val)
            else:
                raise ValueError('Bad keyword argument %s' % arg)

        # Derive vals and range.
        if type(vals) in (_FunctionType, _BuiltinFunctionType,
                            _MethodType):
            if rng == None: rng = [x*0.1 for x in range(-100, 100)]
            vals = [vals(i) for i in rng]
        elif len(vals) > 0 and type(vals[0]) in (type(()), type([])):
                rng = [x for (x,y) in vals]
                vals = [y for (x,y) in vals]
        elif rng == None:
            rng = range(len(vals))
            
        self._vals = vals
        self._rng = rng

        # Do some basic error checking.
        if len(self._rng) != len(self._vals):
            raise ValueError("Rng and vals have different lengths")
        if len(self._rng) == 0:
            raise ValueError("Nothing to plot")

        # Handle scale.
        if self._xscale == 'log' or self._yscale == 'log':
            rng = []
            vals = []
            for (x,y) in zip(self._rng, self._vals):
                if x>0 and y>0:
                    rng.append(x)
                    vals.append(y)
            self._rng = rng
            self._vals = vals
        if self._xscale == 'log':
            self._rng = [log(x) for x in self._rng]
        if self._yscale == 'log':
            self._vals = [log(x) for x in self._vals]

        # Set up the tk window
        self._root = Tkinter.Tk()
        self._root.bind('q', self.destroy)

        # Set up the buttons
        buttons = Tkinter.Frame(self._root)
        buttons.pack(side='bottom', fill='x')
        Tkinter.Button(buttons, text='Done',
                       command = self.destroy).pack(side='right')
        Tkinter.Button(buttons, text='Zoom In',
                       command = self.zoomin).pack(side='left')
        Tkinter.Button(buttons, text='Zoom Out',
                       command = self.zoomout).pack(side='left')
        Tkinter.Button(buttons, text='Print',
                       command = self.printps).pack(side='left')

        # Set up the canvas.
        cframe = Tkinter.Frame(self._root)
        cframe.pack(fill='both', expand='yes')
        self._c = Tkinter.Canvas(cframe, relief='sunk', border=2)

        # Give the canvas scrollbars.
        sb1 = Tkinter.Scrollbar(cframe, orient='vertical')
        sb1.pack(side='right', fill='y')
        sb2 = Tkinter.Scrollbar(cframe, orient='horizontal')
        sb2.pack(side='bottom', fill='x')
        self._c.pack(side='left', fill='both', expand='yes')

        # Connect the scrollbars to the canvas.
        sb1.config(command=self._c.yview)
        sb2['command']=self._c.xview
        self._c['yscrollcommand'] = sb1.set
        self._c['xscrollcommand'] = sb2.set

        # Bind configure (for resize, etc)
        self._width = float(self._c['width'])
        self._height = float(self._c['height'])
        self._c['scrollregion'] = (0, 0, self._width, self._height)
        self._c.bind('<Configure>', self._configure)

    def _configure(self, e):
        # Get the current scollregion size
        (_1, _2, width, height) = self._c['scrollregion'].split()
        width = float(width)
        height = float(height)

        scale = max(e.width/width, e.height/height)
        self._c['scrollregion'] = (0, 0, width*scale, height*scale)

        self._plot()

    def zoom(self, z, *args):
        (_1, _2, width, height) = self._c['scrollregion'].split()
        width = float(width)
        height = float(height)
        self._c['scrollregion'] = (0, 0, width*z, height*z)
        self._c.delete('all')
        self._plot()

    def zoomin(self, *args): self.zoom(1.2, *args)
    def zoomout(self, *args): self.zoom(1/1.2, *args)
    def printps(self, *args):
        from tkFileDialog import asksaveasfilename
        ftypes = [('Postscript files', '.ps'),
                  ('All files', '*')]
        filename = asksaveasfilename(filetypes=ftypes, defaultextension='.ps')
        if not filename: return
        (x0, y0, w, h) = self._c['scrollregion'].split()
        self._c.postscript(file=filename, x=float(x0), y=float(y0),
                           width=float(w)+2, height=float(h)+2)
        
    def destroy(self, *args):
        if self._root is None: return
        self._root.destroy()
        self._root = None

    def _scale(self):
        (_1, _2, width, height) = self._c['scrollregion'].split()
        width = float(width)
        height = float(height)
        
        min_i = self._rng[0]
        max_i = self._rng[0]
        for i in self._rng[1:]:
            if i < min_i: min_i = i
            if i > max_i: max_i = i
        
        min_j = self._vals[0]
        max_j = self._vals[0]
        for j in self._vals[1:]:
            if j < min_j: min_j = j
            if j > max_j: max_j = j

        # Add a little bit of border..
        isize = max_i-min_i
        jsize = max_j-min_j
        min_i -= isize/10
        max_i += isize/10
        min_j -= jsize/10
        max_j += jsize/10

        return (min_i, min_j, max_i, max_j,
                width/(max_i-min_i), height/(max_j-min_j),
                height)

    def _plot(self, *args):
        self._c.delete('all')
        (i0, j0, maxi, maxj, dx, dy, height) = self._scale()

        # Axes
        xzero = -i0*dx
        yzero = height+j0*dy
        neginf = min(i0, j0, -1000)*1000
        posinf = max(maxi, maxj, 1000)*1000
        self._c.create_line(neginf,yzero,posinf,yzero, fill='gray')
        self._c.create_line(xzero,neginf,xzero,posinf, fill='gray')

        # The plot
        line = []
        for (i,j) in zip(self._rng, self._vals):
            x = (i-i0) * dx
            y = height-((j-j0) * dy)
            line.append( (x,y) )
        self._c.create_line(line)

    def mainloop(self, *varargs, **kwargs):
        self._root.mainloop(*varargs, **kwargs)

def Plot(vals, rng=None, **kwargs):
    """
    A factory function that creates a Plot graph.  The Plot graph will
    either be a L{BLTPlot} (if BLT is installed), or a L{SimplePlot}
    (if BLT is not installed).
    """
    return BLTPlot(vals, rng, **kwargs)
    try: return BLTPlot(vals, rng, **kwargs)
    except: return SimplePlot(vals, rng, **kwargs)

if __name__ == '__main__':
    Plot(lambda x:x**2-x**3,
         [0.01*x for x in range(1,100)],
         scale='log').mainloop()
    

    
