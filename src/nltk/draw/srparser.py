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
demo window.

On the right side of the demo window is the remaining text.  This is
the portion of the text which has not yet been considered by the parser.

The parser builds up a tree structure for the text using two
operations: 

  - "shift" moves the first token from the remaining text to the top
    of the stack.  In the demo, the top of the stack is its right-hand
    side.
  - "reduce" uses a grammar production to combine the rightmost stack
    elements into a single tree token.

You can control the parser's operation by using the "shift" and
"reduce" button; or you can use the "step" button to let the parser
automatically decide which operation to apply.  The shift reduce
parser uses the following rules to decide which operation to use:

  - Only shift if no reductions are available.
  - If multiple reductions are available, then apply the reduction
    whose CFG production is listed earliest in the grammar.

Currently, there is no way to choose which production to apply;
however, this functionality should be added in the near future.

KEYBOARD SHORTCUTS:
    [space]    Perform the next shift or reduce operation
    [s]        Perform a shift operation
    [r]        Perform a reduction operation
    [delete]   Reset the parser
    [g]        Show/hide grammar
    [ctrl-a]   Toggle animations
    [h]        Help
    [p]        Print
    [q]        Quit
"""

from nltk.draw.tree2 import *
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
        self._num_animation_frames = 5
        self._animating_lock = 0

        # Set up the main window.
        self._top = Tk()
        self._top.title('Shift Reduce Parser Demo')

        # Set up key bindings.
        self._init_bindings()

        # Create the basic frames.
        self._init_grammar(self._top)
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_canvas(self._top)

        # Reset the demo, and set the feedback frame to empty.
        self.reset()
        self._lastoper1['text'] = ''

    def _init_grammar(self, parent):
        # Grammar view.  Don't show it initially.  
        self._prodframe = listframe = Frame(parent)
        listscroll = Scrollbar(self._prodframe, orient='vertical')
        self._prodlist = listbox = Listbox(self._prodframe)
        listbox.config(yscrollcommand = listscroll.set)
        listscroll.config(command=listbox.yview)
        listscroll.pack(side='right', fill='y')
        listbox.pack(side='left', fill='both', expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            listbox.insert('end', production)

        self._show_grammar = 0
        
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
        self._top.bind('<BackSpace>', self.reset)
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
        Button(buttonframe, text='Reset', 
               command=self.reset).pack(side='left')

    def _init_feedback(self, parent):
        feedbackframe = Frame(parent)
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
                                   width=450, closeenough=10)
        self._cframe.pack(expand=1, fill='both', side='top')
        canvas = self._canvas = self._cframe.canvas()

        self._stackwidgets = []
        self._rtextwidgets = []
        self._titlebar = canvas.create_rectangle(0,0,0,0, fill='#c0f0f0',
                                                 outline='black')
        self._exprline = canvas.create_line(0,0,0,0, dash='.')
        self._stacktop = canvas.create_line(0,0,0,0, fill='#408080')
        self._stacklabel = TextWidget(canvas, 'Stack', color='#004040',
                                  font=('helvetica', 16, 'bold'))
        self._rtextlabel = TextWidget(canvas, 'Remaining Text', color='#004040',
                                  font=('helvetica', 16, 'bold'))
        self._cframe.add_widget(self._stacklabel)
        self._cframe.add_widget(self._rtextlabel)

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
            widget.bind_click(self.reduce)
            self._stackwidgets.append(widget)
            self._cframe.add_widget(widget, stackx, y)
            stackx = widget.bbox()[2] + 10

        # Draw the remaining text.
        rtextwidth = 0
        for tok in self._parser.remaining_text():
            widget = TextWidget(self._canvas, tok.type(), color='#000000')
            self._rtextwidgets.append(widget)
            self._cframe.add_widget(widget, rtextwidth, y)
            rtextwidth = widget.bbox()[2] + 10

        # Move the remaining text to the correct location (keep it
        # right-justified, when possible); and move the remaining text
        # label, if necessary.
        stackx = max(stackx, self._stacklabel.width()+25)
        rlabelwidth = self._rtextlabel.width()+10
        if stackx >= cx2-max(rtextwidth, rlabelwidth):
            cx2 = stackx + max(rtextwidth, rlabelwidth)
        for rtextwidget in self._rtextwidgets:
            rtextwidget.move(5+cx2-rtextwidth, 0)
        self._rtextlabel.move(cx2-self._rtextlabel.bbox()[2]-5, 0)

        # Draw the stack top.
        midx = (stackx + cx2-max(rtextwidth, rlabelwidth))/2
        self._canvas.coords(self._stacktop, midx, 0, midx, 5000)
        (x1, y1, x2, y2) = self._stacklabel.bbox()

        # Let them shift by dragging.
        if len(self._rtextwidgets) > 0:
            def drag_shift(widget, midx=midx, self=self):
                if widget.bbox()[0] < midx: self.shift()
                else: self._redraw()
            self._rtextwidgets[0].bind_drag(drag_shift)
            self._rtextwidgets[0].bind_click(self.shift)

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

    def help(self, *e):
        ShowText(self._top, 'Help: Shift Reduce Parser Demo',
                 (__doc__).strip(), width=75)

    def postscript(self, *e):
        self._cframe.print_to_file()

    def toggle_animations(self, *e):
        self._animate = not self._animate
        if self._animate:
            self._lastoper1['text'] = 'Animations On'
        else:
            self._lastoper1['text'] = 'Animations Off'
        self._lastoper2['text'] = ''

    def toggle_grammar(self, *e):
        self._show_grammar = not self._show_grammar
        if self._show_grammar:
            self._prodframe.pack(fill='both', expand='y', side='left',
                                 before=self._buttonframe)
            self._lastoper1['text'] = 'Show Grammar'
        else:
            self._prodframe.pack_forget()
            self._lastoper1['text'] = 'Hide Grammar'
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
        dy = ydist*1.0/self._num_animation_frames
        self._animate_reduce_frame(self._num_animation_frames,
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
        CFGProduction(VP, V, NP, PP),
        CFGProduction(NP, Det, N, PP),
        CFGProduction(PP, P, NP),

        # Lexical Productions
        CFGProduction(NP, 'I'),   CFGProduction(Det, 'the'),
        CFGProduction(Det, 'a'),  CFGProduction(N, 'man'),
        CFGProduction(V, 'saw'),  CFGProduction(P, 'in'),
        CFGProduction(P, 'with'), CFGProduction(N, 'park'),
        CFGProduction(N, 'dog'),  CFGProduction(N, 'telescope'),
        CFGProduction(Det, 'my'),
        )

    grammar = CFG(S, productions)

    sent = 'my dog saw a man in the park'
    print "Sentence:\n", sent

    # tokenize the sentence
    from nltk.token import WSTokenizer
    text = WSTokenizer().tokenize(sent)

    ShiftReduceParserDemo(grammar, text)

if __name__ == '__main__': demo()
        
