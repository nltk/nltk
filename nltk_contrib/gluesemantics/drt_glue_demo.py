# Natural Language Toolkit: GUI Demo for Glue Semantics with Discourse 
#                           Represtation Theory (DRT) as meaning language 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.draw.tree import *
from nltk.draw import *
from nltk import parse, tokenize
from nltk.draw.cfg import *
import string
from nltk_contrib.gluesemantics import drt_glue
from Tkinter import *
import tkFont
from tkFont import Font
from nltk_contrib.drt import DRT


class DrtGlueDemo(object):
    def __init__(self, examples):
        # Set up the main window.
        self._top = Tk()
        self._top.title('DRT Glue Demo')

        # Set up key bindings.
        self._init_bindings()

        # Initialize the fonts.
        self._init_fonts(self._top)

        self._examples = examples

        # The user can hide the grammar.
        self._show_grammar = IntVar(self._top)
        self._show_grammar.set(1)

        # Set the data to None
        self._readings = []
        self._drs = None
        self._drsWidget = None
        self._remove_duplicates = False

        # Create the basic frames.
        self._init_menubar(self._top)
        self._init_buttons(self._top)
        self._init_exampleListbox(self._top)
        self._init_readingListbox(self._top)
        self._init_canvas(self._top)

        # Resize callback
        self._canvas.bind('<Configure>', self._configure)
        
    #########################################
    ##  Initialization Helpers
    #########################################
        
    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = tkFont.Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)
        
        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget('size'))

        self._boldfont = tkFont.Font(family='helvetica', weight='bold',
                                    size=self._size.get())
        self._font = tkFont.Font(family='helvetica',
                                    size=self._size.get())
        if self._size.get() < 0: big = self._size.get()-2
        else: big = self._size.get()+2
        self._bigfont = tkFont.Font(family='helvetica', weight='bold',
                                    size=big)

    def _init_exampleListbox(self, parent):
        self._exampleFrame = listframe = Frame(parent)
        self._exampleFrame.pack(fill='both', side='left', padx=2)
        self._exampleList_label = Label(self._exampleFrame, font=self._boldfont, 
                                     text='Examples')
        self._exampleList_label.pack()
        self._exampleList = Listbox(self._exampleFrame, selectmode='single',
                                 relief='groove', background='white',
                                 foreground='#909090', font=self._font,
                                 selectforeground='#004040',
                                 selectbackground='#c0f0c0')

        self._exampleList.pack(side='right', fill='both', expand=1)

        for example in self._examples:
            self._exampleList.insert('end', ('  %s' % example))
        self._exampleList.config(height=min(len(self._examples), 25), width=40)

        # Add a scrollbar if there are more than 25 examples.
        if len(self._examples) > 25:
            listscroll = Scrollbar(self._exampleFrame,
                                   orient='vertical')
            self._exampleList.config(yscrollcommand = listscroll.set)
            listscroll.config(command=self._exampleList.yview)
            listscroll.pack(side='left', fill='y')

        # If they select a example, apply it.
        self._exampleList.bind('<<ListboxSelect>>', self._exampleList_select)

    def _init_readingListbox(self, parent):
        self._readingFrame = listframe = Frame(parent)
        self._readingFrame.pack(fill='both', side='left', padx=2)
        self._readingList_label = Label(self._readingFrame, font=self._boldfont, 
                                     text='Readings')
        self._readingList_label.pack()
        self._readingList = Listbox(self._readingFrame, selectmode='single',
                                 relief='groove', background='white',
                                 foreground='#909090', font=self._font,
                                 selectforeground='#004040',
                                 selectbackground='#c0f0c0')

        self._readingList.pack(side='right', fill='both', expand=1)
        
        # Add a scrollbar if there are more than 25 examples.
        listscroll = Scrollbar(self._readingFrame,
                               orient='vertical')
        self._readingList.config(yscrollcommand = listscroll.set)
        listscroll.config(command=self._readingList.yview)
        listscroll.pack(side='right', fill='y')

        self._populate_readingListbox()

    def _populate_readingListbox(self):
        # Populate the listbox with integers
        self._readingList.delete(0, 'end')
        for i in range(len(self._readings)):
            self._readingList.insert('end', ('  %s' % (i+1)))
        self._readingList.config(height=min(len(self._readings), 25), width=5)

        # If they select a example, apply it.
        self._readingList.bind('<<ListboxSelect>>', self._readingList_select)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind('<Control-q>', self.destroy)
        self._top.bind('<Control-x>', self.destroy)
        self._top.bind('<Escape>', self.destroy)       
        self._top.bind('n', self.next)
        self._top.bind('<space>', self.next)
        self._top.bind('p', self.prev)
        self._top.bind('<BackSpace>', self.prev)
        self._top.bind('<h>', self.help)
        self._top.bind('<F1>', self.help)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill='none', side='bottom', padx=3, pady=2)
        Button(buttonframe, text='Prev', 
               background='#90c0d0', foreground='black',
               command=self.prev,).pack(side='left')
        Button(buttonframe, text='Next', 
               background='#90c0d0', foreground='black',
               command=self.next,).pack(side='left')

    def _configure(self, event):
        self._autostep = 0
        (x1, y1, x2, y2) = self._cframe.scrollregion()
        y2 = event.height - 6
        self._canvas['scrollregion'] = '%d %d %d %d' % (x1,y1,x2,y2)
        self._redraw()

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(parent, background='white', 
                                   #width=525, height=250,
                                   closeenough=10,
                                   border=2, relief='sunken')
        self._cframe.pack(expand=1, fill='both', side='top', pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree or text
        self._tree = None
        self._textwidgets = []
        self._textline = None
    
    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label='Exit', underline=1,
                             command=self.destroy, accelerator='q')
        menubar.add_cascade(label='File', underline=0, menu=filemenu)

        actionmenu = Menu(menubar, tearoff=0)
        actionmenu.add_command(label='Next', underline=0,
                               command=self.next, accelerator='n, Space')
        actionmenu.add_command(label='Previous', underline=0,
                               command=self.prev, accelerator='p, Backspace')
        menubar.add_cascade(label='Action', underline=0, menu=actionmenu)

        optionmenu = Menu(menubar, tearoff=0)
        optionmenu.add_checkbutton(label='Remove Duplicates', underline=0,
                                   variable=self._remove_duplicates, 
                                   command=self._toggle_remove_duplicates,
                                   accelerator='r')
        menubar.add_cascade(label='Options', underline=0, menu=optionmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_radiobutton(label='Tiny', variable=self._size,
                                 underline=0, value=10, command=self.resize)
        viewmenu.add_radiobutton(label='Small', variable=self._size,
                                 underline=0, value=12, command=self.resize)
        viewmenu.add_radiobutton(label='Medium', variable=self._size,
                                 underline=0, value=14, command=self.resize)
        viewmenu.add_radiobutton(label='Large', variable=self._size,
                                 underline=0, value=18, command=self.resize)
        viewmenu.add_radiobutton(label='Huge', variable=self._size,
                                 underline=0, value=24, command=self.resize)
        menubar.add_cascade(label='View', underline=0, menu=viewmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label='About', underline=0,
                             command=self.about)
        menubar.add_cascade(label='Help', underline=0, menu=helpmenu)
        
        parent.config(menu=menubar)
        
    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        canvas = self._canvas
        
        # Delete the old DRS, widgets, etc.
        if self._drsWidget is not None:
            self._drsWidget.clear()

        if(self._drs):
            self._drsWidget = DrsWidget( self._canvas, self._drs )
            self._drsWidget.draw()
            

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def prev(self, *e):
        selection = self._readingList.curselection()
        readingListSize = self._readingList.size()
        
        # there are readings
        if readingListSize > 0:
            # if one reading is currently selected
            if len(selection) == 1: 
                index = int(selection[0])
            
                # if it's on (or before) the first item
                if index <= 0:  
                    newIndex = readingListSize - 1
                else:
                    newIndex = index - 1

            else:
                #select its first reading
                newIndex = 0
                
            self._readingList_store_selection(newIndex)

    def next(self, *e):
        selection = self._readingList.curselection()
        readingListSize = self._readingList.size()
        
        # if there are readings
        if readingListSize > 0:
            # if one reading is currently selected
            if len(selection) == 1: 
                index = int(selection[0])
            
                # if it's on (or past) the last item
                if index >= (readingListSize - 1):
                    # select the first item
                    newIndex = 0
                else:
                    newIndex = index + 1
        
            else:
                #select its first reading
                newIndex = 0
                
            self._readingList_store_selection(newIndex)

    def about(self, *e):
        ABOUT = ("NLTK Discourse Representation Theory (DRT) Glue Semantics Demo\n"+
                 "Written by Daniel H. Garrette")
        TITLE = 'About: NLTK DRT Glue Demo'
        try:
            from tkMessageBox import Message
            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self._top, TITLE, ABOUT)
            
    def help(self, *e):
        self._autostep = 0
        # The default font's not very legible; try using 'fixed' instead. 
        try:
            ShowText(self._top, 'Help: Recursive Descent Parser Demo',
                     (__doc__).strip(), width=75, font='fixed')
        except:
            ShowText(self._top, 'Help: Recursive Descent Parser Demo',
                     (__doc__).strip(), width=75)

    def postscript(self, *e):
        self._autostep = 0
        self._cframe.print_to_file()

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle(): return
        self._top.mainloop(*args, **kwargs)
        
    def resize(self, size=None):
        if size is not None: self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._boldfont.configure(size=-(abs(size)))
        self._sysfont.configure(size=-(abs(size)))
        self._bigfont.configure(size=-(abs(size+2)))
        self._redraw()
        
    def _toggle_remove_duplicates(self):
        self._remove_duplicates = not self._remove_duplicates

        self._exampleList.selection_clear(0, 'end')
        self._readings = []
        self._populate_readingListbox()
        
        self._drs = None
        self._redraw()


    def _exampleList_select(self, event):
        selection = self._exampleList.curselection()
        if len(selection) != 1: return
        self._curExample = int(selection[0])
        example = self._examples[self._curExample]

        if example:
            self._exampleList.selection_clear(0, 'end')
            self._exampleList.selection_set(self._curExample)

            self._readings = drt_glue.parse_to_meaning(example, self._remove_duplicates)
            self._populate_readingListbox()
            
            self._drs = None
            self._redraw()
            
        else:
            # Reset the example selections.
            self._exampleList.selection_clear(0, 'end')

    def _readingList_select(self, event):
        selection = self._readingList.curselection()
        if len(selection) != 1: return
        index = int(selection[0])
        self._readingList_store_selection(index)

    def _readingList_store_selection(self, index):
        reading = self._readings[index]

        if reading:
            self._readingList.selection_clear(0, 'end')
            self._readingList.selection_set(index)

            self._drs = reading.simplify().resolve_anaphora().infixify()
            
            self._redraw()
        else:
            # Reset the reading selections.
            self._readingList.selection_clear(0, 'end')


class DrsWidget(object):
    def __init__(self, canvas, drs, **attribs):
        self._drs = drs
        self._canvas = canvas
        canvas.font = Font(font=canvas.itemcget(canvas.create_text(0, 0, text=''), 'font'))
        canvas._BUFFER = 3
        self.bbox = (0, 0, 0, 0)

    def draw(self):
        bottom_right = self._drs.draw(3, 3, self._canvas);
        self.bbox = (0, 0, bottom_right[0]+1, bottom_right[1]+1) 

    def clear(self):
        self._canvas.create_rectangle(self.bbox, fill="white", width="0" )
    
def demo():
    examples = ['John walks',
                'David sees Mary',
                'David eats a sandwich',
                'every man chases a dog',
                'every man believes a dog yawns',
#                'John gives David a sandwich',
                'John chases himself',
                'John persuades David to order a pizza',
                'John tries to go',
#                'John tries to find a unicorn',
                'John seems to vanish',
                'a unicorn seems to approach',
#                'every big cat leaves',
#                'every gray cat leaves',
                'every big gray cat leaves',
                'a former senator leaves',
                'John likes a cat',
                'John likes every cat',
                'he walks',
                'John walks and he leaves']
    DrtGlueDemo(examples).mainloop()

if __name__ == '__main__': demo()
