import sys
from Tkinter import *
from tkFileDialog import *
from tkSimpleDialog import *
from tkMessageBox import showinfo, showwarning
import math
import re
import copy 
import string
from Canvas import Line as CanvasLine, CanvasText
path = '/pkg/p/Python-2.1.1/lib/python2.1/site-packages/Numeric'

version = sys.version.split()
v = version[0]

if (v == '2.1.1') or (v == '2.1'):
    pass

else:
    if not path in sys.path:
        sys.path.append(path)
        import Numeric
        from Scientific.TkWidgets.TkPlotCanvas import *
    else:
        pass

    

from Scientific.TkWidgets.TkPlotCanvas import *
import Numeric

# log_x and log_y just take a point and change the x or y coordinate
# to log base 10 of the appropriate number

def log_x(point):
    if Numeric.equal(point[0], 0.0):
        point[0] = 0.01
    else:
        point[0] = Numeric.log10(point[0])

def log_y(point):
    if Numeric.equal(point[1], 0.0):
        point[1] = 0.01
    else:
        point[1] = Numeric.log10(point[1])

class Function(PolyLine):
    def __init__(self, func, range, incr, **attr):
        self.func = func
        self.range=range
        self.incr = incr

        steps = (range[1]-range[0])/incr

        self.points = points = Numeric.arange(self.range[0],
                                              self.range[1]+self.incr,
                                              self.incr/2.)
        points.shape = ((len(points))/2,2)
        
    
        for i in points:
            i[1] = self.func(i[0])
        
        PolyPoints.__init__(self, points, attr)
    _attributes = {'color': 'black',
                   'width': 1,
                   'stipple': None}

    def my_copy(self):
        l = Line(self.points, **self.attributes)
        return l

class Line(PolyLine):
    def __init__(self, points, **attr):
        #self.name = name
        points = [(float(x), float(y)) for (x,y) in points]
        PolyLine.__init__(self, points, **attr)
    _attributes = {'color': 'black',
                   'width': 1,
                   'stipple': None}
    def my_copy(self):
        return copy.deepcopy(self)

class Marker(PolyMarker):

    def __init__(self, points, **attr):
        points = [(float(x), float(y)) for (x,y) in points]
        PolyMarker.__init__(self, points, **attr)

    def my_copy(self):
        return copy.deepcopy(self)
    
    def draw(self, canvas, bbox):
        
	color = self.attributes['color']
        size = self.attributes['size']
        fillcolor = self.attributes['fillcolor']
        marker = self.attributes['marker']
        fillstyle = self.attributes['fillstyle']

	l = self._drawmarkers(canvas, self.scaled, marker, color, fillstyle,
                              fillcolor, size)
        for mark in l:

            #setting a callback function for the plotted marks
            #depending on what the function is, you may need to write this
            #functionality in another class (say, if you need to access
            #something from the MyPlotCanvas class)
            
            def cb(event, tag=mark, color2=fillcolor, canvas=canvas):
                if color2 is 'yellow':
                    canvas.itemconfig(tag, fill='red')
                else :
                    canvas.itemconfig(tag, fill='yellow')
            def cb2(event, tag=mark, color2=fillcolor, canvas=canvas):
                canvas.itemconfig(tag, fill=color2)
            canvas.tag_bind(mark, '<Enter>', cb)
            canvas.tag_bind(mark, '<Leave>', cb2)


class MyPlotCanvas(PlotCanvas):
    x_log = 0
    y_log = 0
    drawn_on = 0

    def set_scale(self, xaxis_type, yaxis_type):
        if xaxis_type is 'log':
            self.x_log = 1
        if yaxis_type is 'log':
            self.y_log = 1

    def draw(self, graphics, xaxis = None, yaxis = None):
        if self.drawn_on is 1:
            self.clear()
        if self.x_log == 1 or self.y_log == 1:
            self.log_draw(graphics, xaxis, yaxis)
        else:
            self.normal_draw(graphics, xaxis, yaxis)

        self.drawn_on = 1
        #print self.transformation

    def normal_draw(self, graphics, xaxis, yaxis):
        #PlotCanvas.draw(self, graphics, xaxis, yaxis)
        self.draw2(graphics, xaxis, yaxis)

    def log_draw(self, graphics, xaxis, yaxis):
        #altered = copy.deepcopy(graphics)
        temp = []
        for o in graphics.objects:
            temp.append(o.my_copy())
        altered = PlotGraphics(temp)
        if self.x_log == 1 :   #then it is logarithmic  
            for o in altered.objects: 
                if isinstance(o, PlotGraphics):  
                    self.draw(o)  
                elif isinstance(o, Line):  
                    for p in o.points:
                        log_x(p)
                elif isinstance(o, Marker):
                    for p in o.points:
                        log_x(p)
            
        if self.y_log == 1 : 
            for o in altered.objects:
                if isinstance(o, PlotGraphics):
                    self.draw(o)
                elif isinstance(o, Line): 
                    for p in o.points:
                        log_y(p) 
                elif isinstance(o, Marker): 
                    for p in o.points: 
                        log_y(p)  
        #PlotCanvas.draw(self, altered, xaxis, yaxis)
        self.draw2(altered, xaxis, yaxis)
        temp = (graphics, xaxis,yaxis)
        self.last_draw = temp 

    def clear(self):
        """
        Clear the canvas
        """
        PlotCanvas.clear(self)
        self.drawn_on = 0
    
    def postscript(self, name):
        """
        calls the postscript method of the canvas
        """
        self.canvas.postscript(file=name)
    
    def _showValue(self, event):
        """
        Basically the same _showValue method that is in PlotCanvas,
        only it pops the same value regardless of whether the axes
        are logged or not
        """
        scale, shift = self.transformation
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        point = Numeric.array([x, y])
        point = (point-shift)/scale
        if self.x_log == 1:
            point[0] = Numeric.power(10., point[0])
        if self.y_log == 1:
            point[1] = Numeric.power(10., point[1])
        text = "x = %f\ny = %f" % tuple(point)
        self.label = self.canvas.create_window(x, y,
                                               window=Label(self.canvas,
                                                            text=text))
#####################################################################
#######                  SPLIT                        ###############
#####################################################################

        
    def draw2(self, graphics, xaxis = None, yaxis = None): 
        """
        the same draw method of PlotCanvas, only with one slight change:
        the call to _ticks takes one extra variable which determines whether
        the axis in question is the x or y one.  This is important for proper
        labels on the hash marks when the axes are logged.
        """
	self.last_draw = (graphics, xaxis, yaxis) 
	p1, p2 = graphics.boundingBox() 
	xaxis = self._axisInterval(xaxis, p1[0], p2[0])
	yaxis = self._axisInterval(yaxis, p1[1], p2[1])
	text_width = [0., 0.]
	text_height = [0., 0.]
	if xaxis is not None:
	    p1[0] = xaxis[0]
	    p2[0] = xaxis[1]
	    xticks = self._ticks(xaxis[0], xaxis[1], 'x')
	    bb = self._textBoundingBox(xticks[0][1])
	    text_height[1] = bb[3]-bb[1]
	    text_width[0] = 0.5*(bb[2]-bb[0])
	    bb = self._textBoundingBox(xticks[-1][1])
	    text_width[1] = 0.5*(bb[2]-bb[0])
	else:
	    xticks = None
	if yaxis is not None:
	    p1[1] = yaxis[0]
	    p2[1] = yaxis[1]
	    yticks = self._ticks(yaxis[0], yaxis[1], 'y')
	    for y in yticks:
		bb = self._textBoundingBox(y[1])
		w = bb[2]-bb[0]
		text_width[0] = max(text_width[0], w)
	    h = 0.5*(bb[3]-bb[1])
	    text_height[0] = h
	    text_height[1] = max(text_height[1], h)
	else:
	    yticks = None
	text1 = Numeric.array([text_width[0], -text_height[1]])
	text2 = Numeric.array([text_width[1], -text_height[0]])
	scale = (self.plotbox_size-text1-text2) / (p2-p1)
	shift = -p1*scale + self.plotbox_origin + text1
        self.transformation = (scale, shift)
        self.bbox = (p1, p2)
        
	self._drawAxes(self.canvas, xaxis, yaxis, p1, p2,
                       scale, shift, xticks, yticks)
       	graphics.scaleAndShift(scale, shift)
	graphics.draw(self.canvas, (scale*p1+shift, scale*p2+shift)) 



    def _ticks(self, lower, upper, axis):
        """
        Same method as it is in PlotCanvas, only this one checks whether the
        axis in question is x or y.  Then you can check the x_log or y_log
        value to see whether to write out hashmarks with appropriate values.
        If this method were not overwritten, then a graph with a logged axis
        would show increments of 1, 2, 3 instead of 10,100,1000.
        """
        if axis == 'x':
            log_axis = self.x_log
        else:
            log_axis = self.y_log
	ideal = (upper-lower)/7.
        if ideal == 0.:
            ideal = 1./7.
	log = Numeric.log10(ideal)
	power = Numeric.floor(log)
	fraction = log-power
	factor = 1.
	error = fraction
	for f, lf in self._multiples:
	    e = Numeric.fabs(fraction-lf)
	    if e < error:
		error = e
		factor = f
	grid = factor * 10.**power
        if power > 3 or power < -3:
            format = '%+7.0e'
        elif power >= 0:
            digits = max(1, int(power))
            format = '%' + `digits`+'.0f'
        else:
            digits = -int(power)
            format = '%'+`digits+2`+'.'+`digits`+'f'
	ticks = []
	t = -grid*Numeric.floor(-lower/grid)

        ######################################
        ####               FIX            ####
        ######################################


	while t <= upper and len(ticks) < 200:
            if log_axis == 1:
                #print t
                n = math.pow(10., t)
            else:
                n = t
            ticks.append((t, format % (n)))
	    t = t + grid
	return ticks        

    
class Window:
    startfiledir = '.'

    ftypes = [('Postscript files', '.ps'),
              ('All files', '*')
              ]

    def __init__(self, graphics):
        self.root = root = Tk()
        self.window = window = Frame(root)
        window.pack(fill=BOTH, expand=YES, side=TOP)

        def foo(value, self=self):
            self.c.select(value)
            #print value
            #print type(value)
        
        self.c = c = MyPlotCanvas(window, "300", "200",
                                  zoom = 1, select = foo)
        
        c.pack(side=TOP, fill=BOTH, expand=YES)

        self.object = graphics
        self.label = None

        Button(window, text='Draw', command=lambda x=self:
               x.c.draw(x.object, 'automatic',
                        'automatic')).pack(side=LEFT)
        Button(window, text='Resize', command=lambda x=self:
               x.c._autoScale()).pack(side=LEFT)
        Button(window, text='Clear', command=lambda x=self:
               x.c.clear()).pack(side=LEFT)
        Button(window, text='Quit', command=lambda x=self:
               x.root.destroy()).pack(side=RIGHT)
        Button(window, text='Save PS', command=lambda x=self:
               x.onSavePS()).pack(side=RIGHT)


        #main menubar
        menubar=Menu(self.root)
    
        #the submenu for File
        filemenu = Menu(menubar, tearoff=0)
        #filemenu.add_command(label='Open(NA)')
        #filemenu.add_command(label='Save As...', command=lambda x=self:
        #                     x.onSave(x.object))
        filemenu.add_command(label='Save PS...', command=lambda x=self:
                             x.onSavePS())
        filemenu.add_command(label='Exit', command=lambda x=self:
                             x.root.destroy())

        menubar.add_cascade(label='File', menu=filemenu)

        #the submenu for Visualization
        vismenu = Menu(menubar, tearoff=0)
        #vismenu.add_command(label='Function...', command=lambda x=self:
        #                    x.OverlayFunc())
        #vismenu.add_separator()
        vismenu.add_command(label='X-Y Axes...', command=lambda x=self:
                            x.ScaleAxes())
        menubar.add_cascade(label='Visualization', menu=vismenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label='Show Info', command=lambda x=self:
                             x.help())
    
        menubar.add_cascade(label='Help', menu=helpmenu)
    
        self.root.config(menu=menubar)


    def onSavePS(self, forcefile=None):
        foo = asksaveasfilename(filetypes=self.ftypes, defaultextension='.ps')
        self.c.postscript(foo)
        
    def onSave(self, graphics, forcefile=None):
        foo = asksaveasfilename()
        if not foo:
            pass
        else :
            file = open(foo, 'w')
            graphics.writeToFile(file, '--------')
            file.close()

    def OverlayFunc(self):
        """
        Eventually I want to include the ability to parse the func string
        and yield a plot given the domain already present
        The parse though, probably using the re module, will take a little
        time to work out
        """

        func = askstring('Overlay a Function', 'Plot function: ')
        print func    

    def ScaleAxes(self):
        minx = None
        miny = None
        for o in self.object:
            min = Numeric.minimum.reduce(o.points)
            if (minx is None) or (Numeric.less(minx, min[0])):
                minx = min[0]
            if (miny is None) or (Numeric.less(miny, min[1])):
                miny = min[1]
        log = ScalePopup(self.root, minx, miny).result
        if not log :
            pass
        else:
            self.c.x_log = log[0]
            self.c.y_log = log[1]
            self.c._autoScale()
            #self.c.clear()
            #self.c.redraw()
        
    def help(self):
        showinfo('About NLTK',
                 'Natural Language Toolkit\nPlotter v 1.0')

    
        
class ScalePopup(Toplevel):
    def __init__(self, parent, xmin=None, ymin=None):
        Toplevel.__init__(self, parent)
        self.title('Set Axis Type')
        self.parent = parent
        self.transient(parent)
        
        self.xmin = xmin
        self.ymin = ymin
        
        self.resultx = IntVar()
        self.resulty = IntVar()
        self.result = None
        top = Frame(self)
        left = Frame(top)
        right = Frame(top)
        bottom = Frame(self)
        
        Label(self, text='Radio demos').pack(side=TOP)
        Radiobutton(left, text='Normal X',
                    command=self.onPress,
                    variable=self.resultx,
                    value=0).pack(anchor=NW)
        Radiobutton(left, text='Log X',
                    command=self.onPress,
                    variable=self.resultx,
                    value=1).pack(anchor=NW)
        left.pack(side=LEFT)
        top.pack(side=TOP, padx=5, pady=5)
        Radiobutton(right, text='Normal Y',
                    command=self.onPress,
                    variable=self.resulty,
                    value=0).pack(anchor=NW)
        Radiobutton(right, text='Log Y',
                    command=self.onPress,
                    variable=self.resulty,
                    value=1).pack(anchor=NW)
        right.pack(side=RIGHT)
        
        buttonOk = Button(bottom, text='Done', command=self.ok)
        buttonOk.pack(side=LEFT, padx=5, pady=5)
        buttonCancel = Button(bottom, text='Cancel', command=self.cancel)
        buttonCancel.pack(side=LEFT, padx=5, pady=5)
        bottom.pack(side=BOTTOM)
        self.geometry("+%d+%d" %(parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))
        self.wait_window(self)

    def ok(self, event=None):
        if not self.validate():
            self.focus_set() # put focus back
            return
        self.result = (self.resultx.get(), self.resulty.get())
        self.withdraw()
        self.update_idletasks()
        self.cancel()

    def validate(self):
        resultx = self.resultx.get()
        resulty = self.resulty.get()

        if resultx is 1:
            if Numeric.less(self.xmin, 0.0):
                showwarning("Negative Value",
                            "Cannot do that.\nNeg. value in the domain.",
                            parent=self)
                return 0
            else:
                pass
        if resulty is 1:
            if Numeric.less(self.ymin, 0.0):
                showwarning("Negative Value",
                            "Cannot do that.\nNeg. value in the range.",
                            parent=self)
                return 0
            else:
                pass
        return 1
                
                
    def destroy(self, event=None):
        Toplevel.destroy(self)

    def cancel(self, event=None):
        self.parent.focus_set()
        self.destroy()
        
    def onPress(self):
        pass
        #print self.resultx.get(), self.resulty.get()

def plot(*list):
    color = ['red', 'blue', 'lightblue', 'green', 'yellow', 'grey', 'black']
    marker = ['circle', 'dot', 'square', 'triangle',
              'triangle_down', 'cross', 'plus']

    # quick method to see whether i or j are still within the bounds of
    # their requisite lists, and if not, to return the index of the first
    # member
    
    def checkNumber(number,list):
        if number < len(list)-1:
            return number
        else :
            return 0

    i = 0      #keeps track of colors
    j = 0      #keeps track of markers
    for item in list:
        i = checkNumber(i, color)
        j = checkNumber(j, marker)
        
        if isinstance(item, Marker):
            item.attributes['color'] = color[i]
            item.attributes['fillcolor'] = color[i]
            item.attributes['marker'] = marker[j]
            i += 1
            j += 1
        elif isinstance(item, Function) or isinstance(item, Line):
            item.attributes['color'] = color[i]
            i += 1
        else:
            raise NameError
            pass
        
    object = PlotGraphics(list)
    w = Window(object)
    w.c.draw(w.object, 'automatic', 'automatic')
    # Necessary for non-interactive sessions:
    mainloop()

if __name__ == '__main__':

    pi = Numeric.pi

    points = [(0., 0.), (pi/2., 1.), (pi, 0.), (3.*pi/2., -1),(2.*pi, 0.)]

    """
    plot([Line(points, color='lightblue'),
          Function(lambda x:math.sin(x), [0., 2.*pi], (pi/8.), color='red'),
          #Function(lambda x:math.cosh(x), [-10., 10.], 1, color='yellow')
          Marker(points, color='blue',
                 fillcolor='blue', marker='triangle')
          ])
    
    """

    plot([Line(points),
          #False(points),
          Function(lambda x:math.sin(x), [0., 2.*pi], (pi/8.)),
          #Function(lambda x:math.cosh(x), [-10., 10.], 1),
          Marker(points)
          ])
    
