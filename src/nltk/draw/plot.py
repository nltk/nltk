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

# Implementation note:
#   For variable names, I use x,y for pixel coordinates; and i,j for
#   plot coordinates.

# Delegate to BLT?
#   <http://sourceforge.net/projects/blt/>
#   

#from chktype import chktype as _chktype 
from types import FunctionType as _FunctionType
from types import MethodType as _MethodType
from types import BuiltinFunctionType as _BuiltinFunctionType
from types import IntType as _IntType
from types import FloatType as _FloatType
from math import log, log10, ceil, floor
import Tkinter, sys, time
from nltk.draw import ShowText

class PlotFrameI:
    """
    A frame for plotting graphs.  If BLT is present, then we use
    BLTPlotFrame, since it's nicer.  But we fall back on
    CanvasPlotFrame if BLTPlotFrame is unavaibale.
    """
    def postscript(self, filename):
        """
        """
    def config_axes(self, xlog, ylog):
        """
        """
    def invtransform(self, x, y):
        """
        """
    def zoom(self, i1, j1, i2, j2):
        """
        """
    def visible_area(self):
        """
        """
    def create_zoom_marker(self):
        """
        """
    def adjust_zoom_marker(self, x0, y0, x1, y1):
        """
        """
    def delete_zoom_marker(self):
        """
        """
    def bind(self, *args): 
        """
        """
    def unbind(self, *args): 
        """
        """




class CanvasPlotFrame(PlotFrameI):
    def __init__(self, root, vals, rng):
        self._root = root
        self._original_rng = rng
        self._original_vals = vals
        
        self._frame = Tkinter.Frame(root)
        self._frame.pack(expand=1, fill='both')

        # Set up the canvas
        self._canvas = Tkinter.Canvas(self._frame, background='white')
        self._canvas['scrollregion'] = (0,0,200,200)

        # Give the canvas scrollbars.
        sb1 = Tkinter.Scrollbar(self._frame, orient='vertical')
        sb1.pack(side='right', fill='y')
        sb2 = Tkinter.Scrollbar(self._frame, orient='horizontal')
        sb2.pack(side='bottom', fill='x')
        self._canvas.pack(side='left', fill='both', expand=1)

        # Connect the scrollbars to the canvas.
        sb1.config(command=self._canvas.yview)
        sb2['command']=self._canvas.xview
        self._canvas['yscrollcommand'] = sb1.set
        self._canvas['xscrollcommand'] = sb2.set

        # Start out with linear coordinates.
        self._xlog = self._ylog = 0
        
        self._width = self._height = -1
        self._canvas.bind('<Configure>', self._configure)

    def _configure(self, event):
        if self._width != event.width or self._height != event.height:
            self._width = event.width
            self._height = event.height
            (i1, j1, i2, j2) = self.visible_area()
            self.zoom(i1, j1, i2, j2)

    def postscript(self, filename):
        (x0, y0, w, h) = self._canvas['scrollregion'].split()
        self._canvas.postscript(file=filename, x=float(x0), y=float(y0),
                                width=float(w)+2, height=float(h)+2)

    def _plot(self, *args):
        self._canvas.delete('all')
        (i1, j1, i2, j2) = self.visible_area()

        # Draw the Axes
        xzero = -self._imin*self._dx
        yzero = self._ymax+self._jmin*self._dy
        neginf = min(self._imin, self._jmin, -1000)*1000
        posinf = max(self._imax, self._jmax, 1000)*1000
        self._canvas.create_line(neginf,yzero,posinf,yzero,
                                 fill='gray', width=2)
        self._canvas.create_line(xzero,neginf,xzero,posinf,
                                 fill='gray', width=2)

        # Draw the X grid.
        if self._xlog:
            (i1, i2) = (10**(i1), 10**(i2))
            (imin, imax) = (10**(self._imin), 10**(self._imax))
            # Grid step size.
            di = (i2-i1)/1000.0
            # round to a power of 10
            di = 10.0**(int(log10(di)))
            # grid start location
            i = ceil(imin/di)*di
            while i <= imax:
                if i > 10*di: di *= 10
                x = log10(i)*self._dx - log10(imin)*self._dx
                self._canvas.create_line(x, neginf, x, posinf, fill='gray')
                i += di
        else:
            # Grid step size.
            di = max((i2-i1)/10.0, (self._imax-self._imin)/100)
            # round to a power of 2
            di = 2.0**(int(log(di)/log(2)))
            # grid start location
            i = int(self._imin/di)*di
            # Draw the grid.
            while i <= self._imax:
                x = (i-self._imin)*self._dx
                self._canvas.create_line(x, neginf, x, posinf, fill='gray')
                i += di

        # Draw the Y grid
        if self._ylog:
            (j1, j2) = (10**(j1), 10**(j2))
            (jmin, jmax) = (10**(self._jmin), 10**(self._jmax))
            # Grid step size.
            dj = (j2-j1)/1000.0
            # round to a power of 10
            dj = 10.0**(int(log10(dj)))
            # grid start locatjon
            j = ceil(jmin/dj)*dj
            while j <= jmax:
                if j > 10*dj: dj *= 10
                y = log10(jmax)*self._dy - log10(j)*self._dy
                self._canvas.create_line(neginf, y, posinf, y, fill='gray')
                j += dj
        else:
            # Grid step size.
            dj = max((j2-j1)/10.0, (self._jmax-self._jmin)/100) 
            # round to a power of 2
            dj = 2.0**(int(log(dj)/log(2))) 
            # grid start location
            j = int(self._jmin/dj)*dj
            # Draw the grid
            while j <= self._jmax:
                y = (j-self._jmin)*self._dy
                self._canvas.create_line(neginf, y, posinf, y, fill='gray')
                j += dj

        # The plot
        line = []
        for (i,j) in zip(self._rng, self._vals):
            x = (i-self._imin) * self._dx
            y = self._ymax-((j-self._jmin) * self._dy)
            line.append( (x,y) )
        self._canvas.create_line(line, fill='black')

    def config_axes(self, xlog, ylog):
        self._xlog = xlog
        self._ylog = ylog
        if xlog: self._rng = [log10(x) for x in self._original_rng]
        else: self._rng = self._original_rng
        if ylog: self._vals = [log10(x) for x in self._original_vals]
        else: self._vals = self._original_vals
            
        self._imin = min(self._rng)
        self._imax = max(self._rng)
        self._jmin = min(self._vals)
        self._jmax = max(self._vals)
        self.zoom(self._imin, self._jmin, self._imax, self._jmax)

    def invtransform(self, x, y):
        x = self._canvas.canvasx(x)
        y = self._canvas.canvasy(y)
        return (self._imin+x/self._dx, self._jmin+(self._ymax-y)/self._dy)

    def zoom(self, i1, j1, i2, j2):
        w = self._width
        h = self._height
        self._xmax = (self._imax-self._imin)/(i2-i1) * w
        self._ymax = (self._jmax-self._jmin)/(j2-j1) * h
        self._canvas['scrollregion'] = (0, 0, self._xmax, self._ymax)
        self._dx = self._xmax/(self._imax-self._imin)
        self._dy = self._ymax/(self._jmax-self._jmin)
        self._plot()

        # Pan to the correct place
        self._canvas.xview('moveto', (i1-self._imin)/(self._imax-self._imin))
        self._canvas.yview('moveto', (self._jmax-j2)/(self._jmax-self._jmin))

    def visible_area(self):
        xview = self._canvas.xview()
        yview = self._canvas.yview()
        i1 = self._imin + xview[0] * (self._imax-self._imin)
        i2 = self._imin + xview[1] * (self._imax-self._imin)
        j1 = self._jmax - yview[1] * (self._jmax-self._jmin)
        j2 = self._jmax - yview[0] * (self._jmax-self._jmin)
        return (i1, j1, i2, j2)

    def create_zoom_marker(self):
        self._canvas.create_rectangle(0,0,0,0, tag='zoom')

    def adjust_zoom_marker(self, x0, y0, x1, y1):
        x0 = self._canvas.canvasx(x0)
        y0 = self._canvas.canvasy(y0)
        x1 = self._canvas.canvasx(x1)
        y1 = self._canvas.canvasy(y1)
        self._canvas.coords('zoom', x0, y0, x1, y1)

    def delete_zoom_marker(self):
        self._canvas.delete('zoom')

    def bind(self, *args): self._canvas.bind(*args)
    def unbind(self, *args): self._canvas.unbind(*args)

class BLTPlotFrame(PlotFrameI):
    def __init__(self, root, vals, rng):
        #raise ImportError     # for debugging CanvasPlotFrame

        # Find ranges
        self._imin = min(rng)
        self._imax = max(rng)
        self._jmin = min(vals)
        self._jmax = max(vals)

        # Create top-level frame.
        self._root = root
        self._frame = Tkinter.Frame(root)
        self._frame.pack(expand=1, fill='both')
        
        # Create the graph.
        try:
            import Pmw
            # This reload is needed to prevent an error if we create
            # more than 1 graph in the same interactive session:
            reload(Pmw.Blt)
            
            Pmw.initialise()
            self._graph = Pmw.Blt.Graph(self._frame)
        except:
            raise ImportError('Pwm not installed!')

        # Add scrollbars.
        sb1 = Tkinter.Scrollbar(self._frame, orient='vertical')
        sb1.pack(side='right', fill='y')
        sb2 = Tkinter.Scrollbar(self._frame, orient='horizontal')
        sb2.pack(side='bottom', fill='x')
        self._graph.pack(side='left', fill='both', expand='yes')
        self._yscroll = sb1
        self._xscroll = sb2
            
        # Connect the scrollbars to the canvas.
        sb1['command'] = self._yview
        sb2['command'] = self._xview
        
        # Create the plot.
        self._graph.line_create('plot', xdata=tuple(rng),
                                ydata=tuple(vals), symbol='')
        self._graph.legend_configure(hide=1)
        self._graph.grid_configure(hide=0)
        self._set_scrollbars()

    def _set_scrollbars(self):
        (i1, j1, i2, j2) = self.visible_area()
        (imin, imax) = (self._imin, self._imax)
        (jmin, jmax) = (self._jmin, self._jmax)

        self._xscroll.set((i1-imin)/(imax-imin), (i2-imin)/(imax-imin))
        self._yscroll.set(1-(j2-jmin)/(jmax-jmin), 1-(j1-jmin)/(jmax-jmin))

    def _xview(self, *command):
        (i1, j1, i2, j2) = self.visible_area()
        (imin, imax) = (self._imin, self._imax)
        (jmin, jmax) = (self._jmin, self._jmax)
        
        if command[0] == 'moveto':
            f = float(command[1])
        elif command[0] == 'scroll':
            dir = int(command[1])
            if command[2] == 'pages':
                f = (i1-imin)/(imax-imin) + dir*(i2-i1)/(imax-imin)
            elif command[2] == 'units':
                f = (i1-imin)/(imax-imin) + dir*(i2-i1)/(10*(imax-imin))
            else: return
        else: return

        f = max(f, 0)
        f = min(f, 1-(i2-i1)/(imax-imin))
        self.zoom(imin + f*(imax-imin), j1,
                  imin + f*(imax-imin)+(i2-i1), j2)
        self._set_scrollbars()

    def _yview(self, *command):
        (i1, j1, i2, j2) = self.visible_area()
        (imin, imax) = (self._imin, self._imax)
        (jmin, jmax) = (self._jmin, self._jmax)
        
        if command[0] == 'moveto':
            f = 1.0-float(command[1]) - (j2-j1)/(jmax-jmin)
        elif command[0] == 'scroll':
            dir = -int(command[1])
            if command[2] == 'pages':
                f = (j1-jmin)/(jmax-jmin) + dir*(j2-j1)/(jmax-jmin)
            elif command[2] == 'units':
                f = (j1-jmin)/(jmax-jmin) + dir*(j2-j1)/(10*(jmax-jmin))
            else: return
        else: return
            
        f = max(f, 0)
        f = min(f, 1-(j2-j1)/(jmax-jmin))
        self.zoom(i1, jmin + f*(jmax-jmin),
                  i2, jmin + f*(jmax-jmin)+(j2-j1))
        self._set_scrollbars()

    def config_axes(self, xlog, ylog):
        self._graph.xaxis_configure(logscale=xlog)
        self._graph.yaxis_configure(logscale=ylog)

    def invtransform(self, x, y):
        return self._graph.invtransform(x, y)
                                
    def zoom(self, i1, j1, i2, j2):
        self._graph.xaxis_configure(min=i1, max=i2)
        self._graph.yaxis_configure(min=j1, max=j2)
        self._set_scrollbars()

    def visible_area(self):
        (i1, i2) = self._graph.xaxis_limits()
        (j1, j2) = self._graph.yaxis_limits()
        return (i1, j1, i2, j2)

    def create_zoom_marker(self):
        self._graph.marker_create("line", name="zoom", dashes=(2, 2))

    def adjust_zoom_marker(self, press_x, press_y, release_x, release_y):
        (i1, j1) = self._graph.invtransform(press_x, press_y)
        (i2, j2) = self._graph.invtransform(release_x, release_y)
        coords = (i1, j1, i2, j1, i2, j2, i1, j2, i1, j1)
        self._graph.marker_configure("zoom", coords=coords)

    def delete_zoom_marker(self):
        self._graph.marker_delete("zoom")
        
    def bind(self, *args): self._graph.bind(*args)
    def unbind(self, *args): self._graph.unbind(*args)

    def postscript(self, filename):
        self._graph.postscript_output(filename)


class Plot:
    def __init__(self, vals, rng=None, **kwargs):
        # Derive vals and range.
        if type(vals) in (_FunctionType, _BuiltinFunctionType,
                            _MethodType):
            if rng == None: rng = [x*0.1 for x in range(-100, 100)]
            vals = [vals(i) for i in rng]
        elif len(vals) > 0 and type(vals[0]) in (type(()), type([])):
            (rng, vals) = zip(*vals)
        elif rng == None:
            rng = range(len(vals))
        self._vals = vals
        self._rng = rng

        # Find max/min's.
        self._imin = min(rng)
        self._imax = max(rng)
        self._jmin = min(vals)
        self._jmax = max(vals)
        
        # Do some basic error checking.
        if len(self._rng) != len(self._vals):
            raise ValueError("Rng and vals have different lengths")
        if len(self._rng) == 0:
            raise ValueError("Nothing to plot")
        
        # Set up the tk window
        self._root = Tkinter.Tk()
        self._init_bindings(self._root)

        # Create the actual plot frame
        try:
            self._plot = BLTPlotFrame(self._root, vals, rng)
        except ImportError:
            self._plot = CanvasPlotFrame(self._root, vals, rng)

        # Set up the axes
        self._ilog = Tkinter.IntVar(self._root); self._ilog.set(0)
        self._jlog = Tkinter.IntVar(self._root); self._jlog.set(0)
        scale = kwargs.get('scale', 'linear')
        if scale in ('log-linear', 'log_linear', 'log'): self._ilog.set(1)
        if scale in ('linear-log', 'linear_log', 'log'): self._jlog.set(1)
        self._plot.config_axes(self._ilog.get(), self._jlog.get())

        ## Set up zooming
        self._plot.bind("<ButtonPress-1>", self.zoom_in_buttonpress)
        self._plot.bind("<ButtonRelease-1>", self.zoom_in_buttonrelease)
        self._plot.bind("<ButtonPress-2>", self.zoom_out)
        self._plot.bind("<ButtonPress-3>", self.zoom_out)

        self._init_menubar(self._root)

    def _init_bindings(self, parent):
        self._root.bind('<Control-q>', self.destroy)
        self._root.bind('<Control-x>', self.destroy)
        self._root.bind('<Control-p>', self.postscript)
        self._root.bind('<Control-a>', self.zoom_all)
        self._root.bind('<F1>', self.help)
        
    def _init_menubar(self, parent):
        menubar = Tkinter.Menu(parent)

        filemenu = Tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Print to Postscript', underline=0,
                             command=self.postscript, accelerator='Ctrl-p')
        filemenu.add_command(label='Exit', underline=1,
                             command=self.destroy, accelerator='Ctrl-x')
        menubar.add_cascade(label='File', underline=0, menu=filemenu)

        zoommenu = Tkinter.Menu(menubar, tearoff=0)
        zoommenu.add_command(label='Zoom in', underline=5,
                             command=self.zoom_in, accelerator='left click')
        zoommenu.add_command(label='Zoom out', underline=5,
                             command=self.zoom_out, accelerator='right click')
        zoommenu.add_command(label='View 100%', command=self.zoom_all,
                             accelerator='Ctrl-a')
        menubar.add_cascade(label='Zoom', underline=0, menu=zoommenu)

        axismenu = Tkinter.Menu(menubar, tearoff=0)
        if self._imin > 0: xstate = 'normal'
        else: xstate = 'disabled'
        if self._jmin > 0: ystate = 'normal'
        else: ystate = 'disabled'
        axismenu.add_checkbutton(label='Log X axis', underline=4,
                                 variable=self._ilog, state=xstate,
                                 command=self._log)
        axismenu.add_checkbutton(label='Log Y axis', underline=4,
                                 variable=self._jlog, state=ystate,
                                 command=self._log)
        menubar.add_cascade(label='Axes', underline=0, menu=axismenu)

        helpmenu = Tkinter.Menu(menubar, tearoff=0)
        helpmenu.add_command(label='About', underline=0,
                             command=self.about)
        helpmenu.add_command(label='Instructions', underline=0,
                             command=self.help, accelerator='F1')
        menubar.add_cascade(label='Help', underline=0, menu=helpmenu)
        
        parent.config(menu=menubar)

    def _log(self, *e):
        self._plot.config_axes(self._ilog.get(), self._jlog.get())

    def about(self, *e):
        ABOUT = ("NLTK Plot Tool\n"
                 "Written by Edward Loper")
        TITLE = 'About: Plot Tool'
        if isinstance(self._plot, BLTPlotFrame):
            ABOUT += '\n\nBased on the BLT Widget'
        try:
            from tkMessageBox import Message
            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._root, TITLE, ABOUT)
            
    def help(self, *e):
        self._autostep = 0
        # The default font's not very legible; try using 'fixed' instead. 
        try:
            ShowText(self._root, 'Help: Plot Tool',
                     (__doc__).strip(), width=75, font='fixed')
        except:
            ShowText(self._root, 'Help: Plot Tool',
                     (__doc__).strip(), width=75)

    def postscript(self, *e):
        from tkFileDialog import asksaveasfilename
        ftypes = [('Postscript files', '.ps'),
                  ('All files', '*')]
        filename = asksaveasfilename(filetypes=ftypes, defaultextension='.ps')
        if not filename: return
        self._plot.postscript(filename)
        
    def destroy(self, *args):
        if self._root is None: return
        self._root.destroy()
        self._root = None

    def mainloop(self, *varargs, **kwargs):
        self._root.mainloop(*varargs, **kwargs)

    def _zoom(self, i1, j1, i2, j2):
        # Make sure they're ordered correctly.
        if i1 > i2: (i1,i2) = (i2,i1)
        if j1 > j2: (j1,j2) = (j2,j1)

        # Bounds checking: x
        if i1 < self._imin:
            i2 = min(self._imax, i2 + (self._imin - i1))
            i1 = self._imin
        if i2 > self._imax:
            i1 = max(self._imin, i1 - (i2 - self._imax))
            i2 = self._imax
            
        # Bounds checking: y
        if j1 < self._jmin:
            j2 = min(self._jmax, j2 + self._jmin - j1)
            j1 = self._jmin
        if j2 > self._jmax:
            j1 = max(self._jmin, j1 - (j2 - self._jmax))
            j2 = self._jmax

        if self._ilog.get(): i1 = max(1e-100, i1)
        if self._jlog.get(): j1 = max(1e-100, j1)
        
        # Do the actual zooming.
        self._plot.zoom(i1, j1, i2, j2)

    def zoom_in_buttonpress(self, event):
        self._press_x = event.x
        self._press_y = event.y
        self._press_time = time.time()
        self._plot.create_zoom_marker()
        self._bind_id = self._plot.bind("<Motion>", self.zoom_in_drag)

    def zoom_in_drag(self, event):
        self._plot.adjust_zoom_marker(self._press_x, self._press_y,
                                      event.x, event.y)

    def zoom_in_buttonrelease(self, event):
        self._plot.delete_zoom_marker()
        self._plot.unbind("<Motion>", self._bind_id)
        if ((time.time() - self._press_time > 0.1) and
            abs(self._press_x-event.x) + abs(self._press_y-event.y) > 5):
            (i1, j1) = self._plot.invtransform(self._press_x, self._press_y)
            (i2, j2) = self._plot.invtransform(event.x, event.y)
            self._zoom(i1, j1, i2, j2)
        else:
            self.zoom_in()
        
    def zoom_in(self, *e): 
        (i1, j1, i2, j2) = self._plot.visible_area()
        di = (i2-i1)*0.1
        dj = (j2-j1)*0.1
        self._zoom(i1+di, j1+dj, i2-di, j2-dj)

    def zoom_out(self, *e):
        (i1, j1, i2, j2) = self._plot.visible_area()
        di = -(i2-i1)*0.1
        dj = -(j2-j1)*0.1
        self._zoom(i1+di, j1+dj, i2-di, j2-dj)

    def zoom_all(self, *e):
        self._zoom(self._imin, self._jmin, self._imax, self._jmax)


if __name__ == '__main__':
    from math import sin
    #Plot(lambda v: sin(v)**2+0.01)
    Plot(lambda x:abs(x**2-sin(20*x**3))+.1,
         [0.01*x for x in range(1,100)], scale='log').mainloop()
    

    
