# Natural Language Toolkit: Shift/Reduce Parser Demo
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A graphical tool for exploring the shift/reduce parser.

This tool allows you to explore algorithm used by the shift/reduce
parser.  The shift/reduce parser maintains a stack, which records the
structure of the portion of the text that has been parsed.  The stack
is initially empty.  Its contents are shown on the left side of the
main canvas.

On the right side of the main canvas is the remaining text.  This is
the portion of the text which has not yet been considered by the
parser.

The parser builds up a tree structure for the text using two
operations: 

  - "shift" moves the first token from the remaining text to the top
    of the stack.  In the demo, the top of the stack is its right-hand
    side.
  - "reduce" uses a grammar production to combine the rightmost stack
    elements into a single tree token.

You can control the parser's operation by using the "shift" and
"reduce" buttons; or you can use the "step" button to let the parser
automatically decide which operation to apply.  The parser uses the
following rules to decide which operation to apply:

  - Only shift if no reductions are available.
  - If multiple reductions are available, then apply the reduction
    whose CFG production is listed earliest in the grammar.

The "reduce" button applies the reduction whose CFG production is
listed earliest in the grammar.  There are two ways to manually choose
which reduction to apply:

  - Select a CFG production from the list of available reductions, on
    the left side of the main window.  The reduction based on that
    production will be applied to the top of the stack.
  - Click on one of the stack elements.  A popup window will appear, 
    containing all available reductions.  Select one, and it will be
    applied to the top of the stack.

Note that reductions can only be applied to the top of the stack.

Keyboard Shortcuts::
      [Space]\t Perform the next shift or reduce operation
      [s]\t Perform a shift operation
      [r]\t Perform a reduction operation
      [Ctrl-z]\t Undo most recent operation
      [Delete]\t Reset the parser
      [g]\t Show/hide available production list
      [Ctrl-a]\t Toggle animations
      [h]\t Help
      [p]\t Print
      [q]\t Quit
"""

"""
Possible future improvements:
  - button/window to change and/or select text.  Just pop up a window
    with an entry, and let them modify the text; and then retokenize
    it?  Maybe give a warning if it contains tokens whose types are
    not in the grammar.
  - button/window to change and/or select grammar.  Select from
    several alternative grammars?  Or actually change the grammar?  If
    the later, then I'd want to define nltk.draw.cfg, which would be
    responsible for that.
"""

from nltk.draw.tree import *
from nltk.draw import *
from nltk.parser import *
        
class ShiftReduceParserDemo:
    """
    A graphical tool for exploring the shift/reduce parser.  The tool
    displays the parser's stack and the remaining text, and allows the
    user to control the parser's operation.  In particular, the user
    can shift tokens onto the stack, and can perform reductions on the
    top elements of the stack.  A "step" button simply steps through
    the parsing process, performing the operations that
    C{ShiftReduceParser} would use.
    """
    def __init__(self, grammar, text, trace=0):
        self._text = text
        self._parser = SteppingShiftReduceParser(grammar, trace)

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animate = 1
        self._num_animation_frames = 10
        self._animating_lock = 0

        # Set up the main window.
        self._top = Tk()
        self._top.title('Shift Reduce Parser Demo')

        # Set up key bindings.
        self._init_bindings()

        # Create the basic frames.
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

        # A popup menu for reducing.
        self._reduce_menu = Menu(self._canvas, tearoff=0)

        # Reset the demo, and set the feedback frame to empty.
        self.reset()
        self._lastoper1['text'] = ''

    #########################################
    ##  Initialization Helpers
    #########################################

    def _init_grammar(self, parent):
        # Grammar view.
        self._show_grammar = 1
        self._prodframe = listframe = Frame(parent)
        self._prodframe.pack(fill='both', side='left', padx=2)
        Label(self._prodframe, text='Available Reductions',
              font=('helvetica', 14, 'bold')).pack()
        self._prodlist = Listbox(self._prodframe, selectmode='single',
                                 relief='groove', background='white',
                                 foreground='#909090',
                                 selectforeground='#004040',
                                 selectbackground='#c0f0c0')

        self._prodlist.pack(side='right', fill='both', expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert('end', (' %s' % production))
        self._prodlist.config(height=min(len(self._productions), 25))

        # Add a scrollbar if there are more than 25 productions.
        if len(self._productions) > 25:
            listscroll = Scrollbar(self._prodframe,
                                   orient='vertical')
            self._prodlist.config(yscrollcommand = listscroll.set)
            listscroll.config(command=self._prodlist.yview)
            listscroll.pack(side='left', fill='y')

        # If they select a production, apply it.
        self._prodlist.bind('<<ListboxSelect>>', self._prodlist_select)

        # When they hover over a production, highlight it.
        self._hover = -1
        self._prodlist.bind('<Motion>', self._highlight_hover)
        self._prodlist.bind('<Leave>', self._clear_hover)

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind('<q>', self.destroy)
        self._top.bind('<Escape>', self.destroy)
        self._top.bind('<space>', self.step)
        self._top.bind('<s>', self.shift)
        self._top.bind('<Alt-s>', self.shift)
        self._top.bind('<Control-s>', self.shift)
        self._top.bind('<r>', self.reduce)
        self._top.bind('<Alt-r>', self.reduce)
        self._top.bind('<Control-r>', self.reduce)
        self._top.bind('<Delete>', self.reset)
        self._top.bind('<u>', self.undo)
        self._top.bind('<Alt-u>', self.undo)
        self._top.bind('<Control-u>', self.undo)
        self._top.bind('<Control-z>', self.undo)
        self._top.bind('<BackSpace>', self.undo)
        self._top.bind('<p>', self.postscript)
        self._top.bind('<Alt-p>', self.postscript)
        self._top.bind('<Control-p>', self.postscript)
        self._top.bind('<h>', self.help)
        self._top.bind('<Alt-h>', self.help)
        self._top.bind('<Control-h>', self.help)
        self._top.bind('<F1>', self.help)
        self._top.bind('<Control-a>', self.toggle_animations)
        self._top.bind('<g>', self.toggle_grammar)
        self._top.bind('<Alt-g>', self.toggle_grammar)
        self._top.bind('<Control-g>', self.toggle_grammar)

    def _init_buttons(self, parent):
        # Set up the frames.
        self._buttonframe = buttonframe = Frame(parent)
        buttonframe.pack(fill='x', side='bottom')
        Button(buttonframe, text='Quit', underline=0,
               command=self.destroy).pack(side='right')
        Button(buttonframe, text='Print', underline=0,
               command=self.postscript).pack(side='right')
        Button(buttonframe, text='Help', underline=0,
               command=self.help).pack(side='right')
        Button(buttonframe, text='Step', 
               command=self.step,).pack(side='left')
        Button(buttonframe, text='Shift', underline=0,
               command=self.shift).pack(side='left')
        Button(buttonframe, text='Reduce', underline=0,
               command=self.reduce).pack(side='left')
        Button(buttonframe, text='Undo', underline=0,
               command=self.undo).pack(side='left')
        Button(buttonframe, text='Reset', 
               command=self.reset).pack(side='left')

    def _init_feedback(self, parent):
        self._feedbackframe = feedbackframe = Frame(parent)
        feedbackframe.pack(fill='x', side='bottom')
        Label(feedbackframe, text='Last Operation:').pack(side='left')
        lastoperframe = Frame(feedbackframe, relief='groove', border=2)
        lastoperframe.pack(fill='x', side='right', padx=5, expand=1)
        self._lastoper1 = Label(lastoperframe, foreground='#007070')
        self._lastoper2 = Label(lastoperframe, anchor='w', width=30,
                                foreground='#004040')
        self._lastoper1.pack(side='left')
        self._lastoper2.pack(side='left', fill='x', expand=1)

    def _init_canvas(self, parent):
        self._cframe = CanvasFrame(parent, background='white', 
                                   width=525, closeenough=10,
                                   border=2, relief='sunken')
        self._cframe.pack(expand=1, fill='both', side='top', pady=2)
        canvas = self._canvas = self._cframe.canvas()

        self._stackwidgets = []
        self._rtextwidgets = []
        self._titlebar = canvas.create_rectangle(0,0,0,0, fill='#c0f0f0',
                                                 outline='black')
        self._exprline = canvas.create_line(0,0,0,0, dash='.')
        self._stacktop = canvas.create_line(0,0,0,0, fill='#408080')
        self._stacklabel = TextWidget(canvas, 'Stack', color='#004040',
                                  font=('helvetica', 16, 'bold'))
        self._rtextlabel = TextWidget(canvas, 'Remaining Text',
                                      color='#004040',
                                      font=('helvetica', 16, 'bold'))
        self._cframe.add_widget(self._stacklabel)
        self._cframe.add_widget(self._rtextlabel)

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        scrollregion = self._canvas['scrollregion'].split()
        (cx1, cy1, cx2, cy2) = [int(c) for c in scrollregion]

        # Delete the old stack & rtext widgets.
        for stackwidget in self._stackwidgets:
            self._cframe.destroy_widget(stackwidget)
        self._stackwidgets = []
        for rtextwidget in self._rtextwidgets:
            self._cframe.destroy_widget(rtextwidget)
        self._rtextwidgets = []

        # Position the titlebar & exprline
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        y = y2-y1+10
        self._canvas.coords(self._titlebar, -10, 0, 5000, y-4)
        self._canvas.coords(self._exprline, 0, y*2-10, 5000, y*2-10)

        # Position the titlebar labels..
        (x1, y1, x2, y2) = self._stacklabel.bbox()
        self._stacklabel.move(5-x1, 3-y1)
        (x1, y1, x2, y2) = self._rtextlabel.bbox()
        self._rtextlabel.move(cx2-x2-5, 3-y1)

        # Draw the stack.
        stackx = 5
        bold = ('helvetica', 12, 'bold')
        for tok in self._parser.stack():
            if isinstance(tok, TreeToken):
                attribs = {'tree_color': '#4080a0', 'tree_width': 2,
                           'node_font': bold, 'node_color': '#006060',
                           'leaf_color': '#006060'}
                widget = tree_to_treesegment(self._canvas, tok.type(),
                                             **attribs)
                widget.node()['color'] = '#000000'
            else:
                widget = TextWidget(self._canvas, tok.type())
                widget['color'] = '#000000'
            widget.bind_click(self._popup_reduce)
            self._stackwidgets.append(widget)
            self._cframe.add_widget(widget, stackx, y)
            stackx = widget.bbox()[2] + 10

        # Draw the remaining text.
        rtextwidth = 0
        for tok in self._parser.remaining_text():
            widget = TextWidget(self._canvas, tok.type(), color='#000000')
            self._rtextwidgets.append(widget)
            self._cframe.add_widget(widget, rtextwidth, y)
            rtextwidth = widget.bbox()[2] + 4

        # Allow enough room to shift the next token (for animations)
        if len(self._rtextwidgets) > 0:
            stackx += self._rtextwidgets[0].width()
               
        # Move the remaining text to the correct location (keep it
        # right-justified, when possible); and move the remaining text
        # label, if necessary.
        stackx = max(stackx, self._stacklabel.width()+25)
        rlabelwidth = self._rtextlabel.width()+10
        if stackx >= cx2-max(rtextwidth, rlabelwidth):
            cx2 = stackx + max(rtextwidth, rlabelwidth)
        for rtextwidget in self._rtextwidgets:
            rtextwidget.move(4+cx2-rtextwidth, 0)
        self._rtextlabel.move(cx2-self._rtextlabel.bbox()[2]-5, 0)

        # Draw the stack top.
        midx = (stackx + cx2-max(rtextwidth, rlabelwidth))/2
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)
        (x1, y1, x2, y2) = self._stacklabel.bbox()

        # Set up binding to allow them to shift a token by dragging it.
        if len(self._rtextwidgets) > 0:
            def drag_shift(widget, midx=midx, self=self):
                if widget.bbox()[0] < midx: self.shift()
                else: self._redraw()
            self._rtextwidgets[0].bind_drag(drag_shift)
            self._rtextwidgets[0].bind_click(self.shift)

        # Highlight the productions that can be reduced.
        self._prodlist.selection_clear(0, 'end')
        for prod in self._parser.reducible_productions():
            index = self._productions.index(prod)
            self._prodlist.selection_set(index)

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._parser.initialize(self._text)
        self._lastoper1['text'] = 'Reset Demo'
        self._lastoper2['text'] = ''
        self._redraw()

    def step(self, *e):
        if self.reduce(): return 1
        elif self.shift(): return 1
        else: 
            if len(self._parser.parses()) > 0:
                self._lastoper1['text'] = 'Finised:'
                self._lastoper2['text'] = 'Success'
            else:
                self._lastoper1['text'] = 'Finised:'
                self._lastoper2['text'] = 'Failure'

    def shift(self, *e):
        if self._animating_lock: return
        if self._parser.shift():
            tok = self._parser.stack()[-1]
            self._lastoper1['text'] = 'Shift:'
            self._lastoper2['text'] = '%r' % tok.type()
            if self._animate:
                self._animate_shift()
            else:
                self._redraw()
            return 1
        return 0

    def reduce(self, *e):
        if self._animating_lock: return
        production = self._parser.reduce()
        if production:
            self._lastoper1['text'] = 'Reduce:'
            self._lastoper2['text'] = '%s' % production
            if self._animate:
                self._animate_reduce()
            else:
                self._redraw()
        return production

    def undo(self, *e):
        if self._animating_lock: return
        if self._parser.undo():
            self._redraw()

    def help(self, *e):
        # The default font's not very legible; try using 'fixed' instead. 
        try:
            ShowText(self._top, 'Help: Shift Reduce Parser Demo',
                     (__doc__).strip(), width=75, font='fixed')
        except:
            ShowText(self._top, 'Help: Shift Reduce Parser Demo',
                     (__doc__).strip(), width=75)

    def postscript(self, *e):
        self._cframe.print_to_file()

    def mainloop(self, *args, **varargs):
        self._top.mainloop(*args, **varargs)

    #########################################
    ##  Reduce Production Selection
    #########################################

    def toggle_grammar(self, *e):
        self._show_grammar = not self._show_grammar
        if self._show_grammar:
            self._prodframe.pack(fill='both', expand='y', side='left',
                                 after=self._feedbackframe)
            self._lastoper1['text'] = 'Show Grammar'
        else:
            self._prodframe.pack_forget()
            self._lastoper1['text'] = 'Hide Grammar'
        self._lastoper2['text'] = ''

    def _prodlist_select(self, event):
        selection = self._prodlist.curselection()
        if len(selection) != 1: return
        index = int(selection[0])
        production = self._parser.reduce(self._productions[index])
        if production:
            self._lastoper1['text'] = 'Reduce:'
            self._lastoper2['text'] = '%s' % production
            if self._animate:
                self._animate_reduce()
            else:
                self._redraw()
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, 'end')
            for prod in self._parser.reducible_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    def _popup_reduce(self, widget):
        # Remove old commands.
        productions = self._parser.reducible_productions()
        if len(productions) == 0: return
        
        self._reduce_menu.delete(0, 'end')
        for production in productions:
            self._reduce_menu.add_command(label=str(production),
                                          command=self.reduce)
        self._reduce_menu.post(self._canvas.winfo_pointerx(),
                               self._canvas.winfo_pointery())

    #########################################
    ##  Animations
    #########################################

    def toggle_animations(self, *e):
        if self._animate:
            if self._num_animation_frames > 10:
                self._animate = 1
                self._num_animation_frames = 10
                self._lastoper1['text'] = 'Normal Animations'
            elif self._num_animation_frames > 4:
                self._animate = 1
                self._num_animation_frames = 4
                self._lastoper1['text'] = 'Fast Animations'
            else:
                self._animate = 0
                self._lastoper1['text'] = 'Animations Off'
        else:
            self._animate = 1
            self._num_animation_frames = 20
            self._lastoper1['text'] = 'Slow Animations'
        self._lastoper2['text'] = ''

    def _animate_shift(self):
        # What widget are we shifting?
        widget = self._rtextwidgets[0]

        # Where are we shifting from & to?
        right = widget.bbox()[0]
        if len(self._stackwidgets) == 0: left = 5
        else: left = self._stackwidgets[-1].bbox()[2]+10

        # Start animating.
        dx = (left-right)*1.0/self._num_animation_frames
        frame = self._num_animation_frames
        self._animate_shift_frame(self._num_animation_frames,
                                  widget, dx)

    def _animate_shift_frame(self, frame, widget, dx):
        if frame > 0:
            self._animating_lock = 1
            widget.move(dx, 0)
            self._top.after(10, self._animate_shift_frame,
                            frame-1, widget, dx)
        else:
            self._redraw()
            self._animating_lock = 0

    def _animate_reduce(self):
        # What widgets are we shifting?
        numwidgets = len(self._parser.stack()[-1].children())
        widgets = self._stackwidgets[-numwidgets:]

        # How far are we moving?
        if isinstance(widgets[0], TreeSegmentWidget):
            ydist = 15 + widgets[0].node().height()
        else:
            ydist = 15 + widgets[0].height()

        # Start animating.
        dy = ydist*2.0/self._num_animation_frames
        self._animate_reduce_frame(self._num_animation_frames/2,
                                   widgets, dy)

    def _animate_reduce_frame(self, frame, widgets, dy):
        if frame > 0:
            self._animating_lock = 1
            for widget in widgets: widget.move(0, dy)
            self._top.after(10, self._animate_reduce_frame,
                            frame-1, widgets, dy)
        else:
            self._redraw()
            self._animating_lock = 0

    #########################################
    ##  Hovering.
    #########################################

    def _highlight_hover(self, event):
        # What production are we hovering over?
        index = self._prodlist.nearest(event.y)
        if self._hover == index: return

        # Clear any previous hover highlighting.
        self._clear_hover()

        # If the production corresponds to an available reduction,
        # highlight the stack.
        selection = [int(s) for s in self._prodlist.curselection()]
        if index in selection:
            rhslen = len(self._productions[index].rhs())
            for stackwidget in self._stackwidgets[-rhslen:]:
                if isinstance(stackwidget, TreeSegmentWidget):
                    stackwidget.node()['color'] = '#00a000'
                else:
                    stackwidget['color'] = '#00a000'

        # Remember what production we're hovering over.
        self._hover = index
                    
    def _clear_hover(self, *event):
        # Clear any previous hover highlighting.
        if self._hover == -1: return
        self._hover = -1
        for stackwidget in self._stackwidgets:
            if isinstance(stackwidget, TreeSegmentWidget):
                stackwidget.node()['color'] = 'black'
            else:
                stackwidget['color'] = 'black'
        
    
def demo():
    """
    Create a shift reduce parser demo, using a simple grammar and
    text. 
    """
    
    from nltk.cfg import Nonterminal, CFGProduction, CFG
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    productions = (
        # Syntactic Productions
        CFGProduction(S, NP, VP),
        CFGProduction(NP, Det, N),
        CFGProduction(NP, NP, PP),
        CFGProduction(VP, VP, PP),
        CFGProduction(VP, V, NP, PP),
        CFGProduction(VP, V, NP),
        CFGProduction(PP, P, NP),

        # Lexical Productions
        CFGProduction(NP, 'I'),   CFGProduction(Det, 'the'),
        CFGProduction(Det, 'a'),  CFGProduction(N, 'man'),
        CFGProduction(V, 'saw'),  CFGProduction(P, 'in'),
        CFGProduction(P, 'with'), CFGProduction(N, 'park'),
        CFGProduction(N, 'dog'),  CFGProduction(N, 'statue'),
        CFGProduction(Det, 'my'),
        )

    grammar = CFG(S, productions)

    # tokenize the sentence
    sent = 'my dog saw a man in the park with a statue'
    from nltk.token import WSTokenizer
    text = WSTokenizer().tokenize(sent)

    ShiftReduceParserDemo(grammar, text).mainloop()

if __name__ == '__main__': demo()
        
