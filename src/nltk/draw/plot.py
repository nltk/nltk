# Natural Language Toolkit: Simple Plotting
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
"""

#from chktype import chktype as _chktype 
from types import FunctionType as _FunctionType
from types import MethodType as _MethodType
from types import BuiltinFunctionType as _BuiltinFunctionType
from types import IntType as _IntType
from types import FloatType as _FloatType
import Tkinter

class Plot:
    def __init__(self, vals, rng=None):
        """
        @type vals: C{function} or C{list} of C{number}s
        @type rng: C{list} of C{number}s
        """
#         # Do type checking on the arguments.
#         _chktype('plot', 1, vals, ( [_IntType, _FloatType],
#                                     (_IntType, _FloatType),
#                                     _FunctionType, _BuiltinFunctionType,
#                                     _MethodType))
#         _chktype('plot', 2, rng, ( [_IntType, _FloatType],
#                                    (_IntType, _FloatType) ))

        # Derive vals and range.
        if type(vals) in (_FunctionType, _BuiltinFunctionType,
                            _MethodType):
            if rng == None: rng = [x*0.1 for x in range(-100, 100)]
            self._vals = [vals(i) for i in rng]
        else:
            if rng == None: rng = range(len(vals))
            self._vals = vals
        self._rng = rng

        # Do some basic error checking.
        if len(self._rng) != len(self._vals):
            raise ValueError("Rng and vals have different lengths")
        if len(self._rng) == 0:
            raise ValueError("Nothing to plot")

        # Set up the tk window
        self._root = Tkinter.Tk()
        self._root.bind('q', self.destroy)

        # Set up the buttons
        buttons = Tkinter.Frame(self._root)
        buttons.pack(side='bottom')
        quit = Tkinter.Button(buttons, text='quit',
                              command = self.destroy)
        quit.pack(side='left')
        zoomin = Tkinter.Button(buttons, text='zoom in',
                                command = self.zoomin)
        zoomin.pack(side='left')
        zoomout = Tkinter.Button(buttons, text='zoom out',
                                 command = self.zoomout)
        zoomout.pack(side='left')

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
        self._c['width'] = width
        self._c['height'] = height

        # If the scrollregion is smaller than the window was resized
        # to, then zoom out.
        scale = max(e.width/width, e.height/height)
        if scale > 1:
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

        return (min_i, min_j,
                max_i, max_j,
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


        
Plot(lambda x:x*x*x, range(-30,30))

    
