import sys
from Tkinter import *
from tkFileDialog import *
from tkSimpleDialog import *
from tkMessageBox import showinfo, showwarning
import math
import re
import copy 


if not '/home/zayats/lib/python/Numeric' in sys.path:
    sys.path.append('/home/zayats/lib/python/Numeric')
    
if not '/home/zayats/lib/python/Scientific' in sys.path:
    sys.path.append('/home/zayats/lib/python/Scientific')

from Scientific.TkWidgets.TkPlotCanvas import *
import Numeric


def log_x(point):
    if Numeric.equal(point[0], 0.0):
        point[0] = 0.01
    else:
        point[0] = Numeric.log(point[0])

def log_y(point):
    if Numeric.equal(point[1], 0.0):
        point[1] = 0.01
    else:
        point[1] = Numeric.log(point[1])


class Marker(PolyMarker):
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
        PlotCanvas.draw(self, graphics, xaxis, yaxis)

    def log_draw(self, graphics, xaxis, yaxis):
        altered = copy.deepcopy(graphics) 
        if self.x_log == 1 :   #then it is logarithmic  
            for o in altered.objects: 
                if isinstance(o, PlotGraphics):  
                    self.draw(o)  
                elif isinstance(o, PolyLine):  
                    for p in o.points:
                        log_x(p)
                elif isinstance(o, Marker):
                    for p in o.points:
                        log_x(p)
            
        if self.y_log == 1 : 
            for o in altered.objects:
                if isinstance(o, PlotGraphics):
                    self.draw(o)
                elif isinstance(o, PolyLine): 
                    for p in o.points:
                        log_y(p) 
                elif isinstance(o, PolyMarker): 
                    for p in o.points: 
                        log_y(p)  
        
        PlotCanvas.draw(self, altered, xaxis, yaxis)
        temp = (graphics, xaxis,yaxis)
        self.last_draw = temp 

    def clear(self):
        PlotCanvas.clear(self)
        self.drawn_on = 1
        
    def redraw(self):
        "Redraws the last canvas contents."
	if self.last_draw is not None:
            apply(self.draw, self.last_draw)
    def postscript(self, name):
        self.canvas.postscript(file=name)

    def _showValue(self, event):
        scale, shift = self.transformation
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        point = Numeric.array([x, y])
        point = (point-shift)/scale
        if self.x_log is 1:
            point[0] = Numeric.power(Numeric.e, point[0])
        if self.y_log is 1:
            point[1] = Numeric.power(Numeric.e, point[1])
        text = "x = %f\ny = %f" % tuple(point)
        self.label = self.canvas.create_window(x, y,
                                               window=Label(self.canvas,
                                                            text=text))




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
            print value
            print type(value)
        
        self.c = c = MyPlotCanvas(window, "300", "200",
                                  zoom = 1, select = foo)
        
        c.pack(side=TOP, fill=BOTH, expand=YES)

        def fillLegend(object, self=self):
            for o in object:
                if isinstance(o, PlotGraphics):
                    fillLegend(o)
                elif isinstance(o, PolyLine):
                    #draw a line in the canvas
                    pass
                else:
                    #draw the marker width the given attributes
                    pass
        self.object = graphics

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
        filemenu.add_command(label='Open(NA)')
        filemenu.add_command(label='Save As...', command=lambda x=self:
                             x.onSave(x.object))
        filemenu.add_command(label='Save PS...', command=lambda x=self:
                             x.onSavePS())
        filemenu.add_command(label='Exit', command=lambda x=self:
                             x.root.destroy())

        menubar.add_cascade(label='File', menu=filemenu)

        #the submenu for Visualization
        vismenu = Menu(menubar, tearoff=0)
        vismenu.add_command(label='Function...', command=lambda x=self:
                            x.OverlayFunc())
        vismenu.add_separator()
        vismenu.add_command(label='X-Y Axes', command=lambda x=self:
                            x.ScaleAxes())
        menubar.add_cascade(label='Visualization', menu=vismenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label='Show Info', command=lambda x=self:
                             x.help())
    
        menubar.add_cascade(label='Help', menu=helpmenu)
    
        self.root.config(menu=menubar)


    def onSavePS(self, forcefile=None):
        foo = asksaveasfilename(filetypes=ftypes, defaultextension='.ps')
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
            self.c.x_log = log['resultx'].get()
            self.c.y_log = log['resulty'].get()
            self.c.clear()
            self.c.redraw()
        
    def help(self):
        showinfo('About NLTK',
                 'Write whatever you want here')

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
        self.result = {'resultx':self.resultx, 'resulty':self.resulty}
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
        #buttonCancel = Button(bottom, text='Cancel', command=self.cancel)
        #buttonCancel.pack(side=LEFT, padx=5, pady=5)
        bottom.pack(side=BOTTOM)
        self.geometry("+%d+%d" %(parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))
        self.wait_window(self)

    def ok(self, event=None):
        if not self.validate():
            self.focus_set() # put focus back
            return
        
        self.withdraw()
        self.update_idletasks()
        self.cancel()

    def validate(self):
        result = self.result
        resultx = result['resultx'].get()
        resulty = result['resulty'].get()
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
        print self.resultx.get(), self.resulty.get()

        
        
if __name__ == '__main__':

    

    ftypes = [('Postscript files', '.ps'),
              ('All files', '*')
              ]
    pi = Numeric.pi
    
    data2 = Numeric.arange(-10.0,10.0,0.2)
    data2.shape = (50,2)
    
    
    for i in data2:
        i[1] = Numeric.cosh(i[0])

    lines2 = PolyLine(data2, color='green') 

    marks = Marker([(0., 0.), (pi/2., 1.), (pi, 0.), (3.*pi/2., -1),
                          (2.*pi, 0.)], color='blue', fillcolor='blue', 
                         marker='triangle')


    
    object = PlotGraphics([lines2])

    w = Window(object)
    w.c.draw(w.object, 'automatic','automatic')



    """
    def onSaveAs(forcefile=None):
        foo = asksaveasfilename(filetypes=ftypes, defaultextension='.ps')
        c.postscript(file=foo)


    root = Tk()
    window = Frame(root)
    window.pack(fill=BOTH, expand=YES, side=TOP)
    
    def display(value):
        select(value)
        print value

    y_label = 'Something'
    y_units = '(Amps)'
    x_label = 'Something Else'
    x_units = '(secs)'

    if len(y_label.split(' ')) > 1:
        temp = y_label.split(' ')
        y_label = ''
        for word in temp:
            y_label = y_label + word + '\n'
    
    c = MyPlotCanvas(window, "300", "200",
                     zoom = 1, select = display)
    
    c.pack(side=TOP, fill=BOTH, expand=YES)


    def select(value):
        c.select(value)

    def onSavePS(forcefile=None):
        foo = asksaveasfilename(filetypes=ftypes, defaultextension='.ps')
        c.postscript(foo)

    def onSave(graphics, forcefile=None):
        foo = asksaveasfilename()
        if not foo:
            pass
        else :
            file = open(foo, 'w')
            graphics.writeToFile(file, '--------')
            file.close()
        
    def help():
        showinfo('About NLTK',
                 'Write whatever you want here')



    def OverlayFunc():
        func = askstring('Overlay a Function', 'Plot function: ')
        print func


    Button(window, text='Draw', command=lambda o=object:
	   c.my_draw(o, 'automatic', 'automatic')).pack(side=LEFT)
    Button(window, text='Clear', command=c.clear).pack(side=LEFT)
    Button(window, text='Quit', command=root.destroy).pack(side=RIGHT)
    Button(window, text='Save PS', command=onSavePS).pack(side=RIGHT)

    #main menubar
    menubar=Menu(root)
    
    #the submenu for File
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label='Open(NA)')
    filemenu.add_command(label='Save As...',
                         command=(lambda x=object:onSave(x)))
    filemenu.add_command(label='Save PS...', command=onSavePS)
    filemenu.add_command(label='Exit', command=root.destroy)

    menubar.add_cascade(label='File', menu=filemenu)

    #the submenu for Visualization
    vismenu = Menu(menubar, tearoff=0)
    vismenu.add_command(label='Function...', command=OverlayFunc)

    logmenu = Menu(vismenu, tearoff=0)
    logmenu.add_checkbutton(label='Normal X',)
    logmenu.add_checkbutton(label='Log X')
    logmenu.add_checkbutton(label='Normal Y')
    logmenu.add_checkbutton(label='Log Y')
    
    vismenu.add_cascade(label='Normal/Log Axis', menu=logmenu)

    menubar.add_cascade(label='Visualization', menu=vismenu)

    helpmenu = Menu(menubar, tearoff=0)
    helpmenu.add_command(label='Show Info', command=help)
    
    menubar.add_cascade(label='Help', menu=helpmenu)
    
    root.config(menu=menubar)
    
    #root.mainloop()

    """
