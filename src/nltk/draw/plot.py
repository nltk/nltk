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

#from chktype import chktype as _chktype 
from types import FunctionType as _FunctionType
from types import MethodType as _MethodType
from types import BuiltinFunctionType as _BuiltinFunctionType
from types import IntType as _IntType
from types import FloatType as _FloatType
from math import log
import Tkinter

class Plot:
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
#         # Do type checking on the arguments.
#         _chktype('plot', 1, vals, ( [_IntType, _FloatType],
#                                     (_IntType, _FloatType),
#                                     _FunctionType, _BuiltinFunctionType,
#                                     _MethodType))
#         _chktype('plot', 2, rng, ( [_IntType, _FloatType],
#                                    (_IntType, _FloatType) ))

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


if __name__ == '__main__':        
    Plot(lambda x:x*x*x, range(-30,30))

    
