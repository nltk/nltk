# Natural Language Toolkit: Shift/Reduce Parser Demo
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A graphical tool for exploring the recursive descent parser.
"""

import nltk.parser.rdparser2; reload(nltk.parser.rdparser2)
from nltk.draw.tree import *
from nltk.draw import *
from nltk.parser import *
        
class RecursiveDescentParserDemo:
    def __init__(self, grammar, text, trace=0):
        self._text = text
        self._parser = SteppingRecursiveDescentParser(grammar, trace)

        # Set up the main window.
        self._top = Tk()
        self._top.title('Recursive Descent Parser Demo')

        # Set up key bindings.
        self._init_bindings()

        # Animations.  animating_lock is a lock to prevent the demo
        # from performing new operations while it's animating.
        self._animate = 1
        self._num_animation_frames = 3
        self._animating_lock = 0
        self._autostep = 0
        
        # Create the basic frames.
        self._init_buttons(self._top)
        self._init_feedback(self._top)
        self._init_grammar(self._top)
        self._init_canvas(self._top)

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
        Label(self._prodframe, text='Available Expansions',
              font=('helvetica', 14, 'bold')).pack()
        self._prodlist = Listbox(self._prodframe, selectmode='single',
                                 relief='groove', background='white',
                                 foreground='#909090',
                                 selectforeground='#004040',
                                 selectbackground='#c0f0c0')

        self._prodlist.pack(side='right', fill='both', expand=1)

        self._productions = list(self._parser.grammar().productions())
        for production in self._productions:
            self._prodlist.insert('end', ('  %s' % production))
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

    def _init_bindings(self):
        # Key bindings are a good thing.
        self._top.bind('<q>', self.destroy)
        self._top.bind('<Escape>', self.destroy)
        self._top.bind('<a>', self.autostep)
        self._top.bind('<Control-a>', self.autostep)
        self._top.bind('<Control-space>', self.autostep)
        self._top.bind('<Control-c>', self.cancel_autostep)
        self._top.bind('<space>', self.step)
        self._top.bind('<Delete>', self.reset)
        self._top.bind('<u>', self.backtrack)
        self._top.bind('<Alt-b>', self.backtrack)
        self._top.bind('<Control-b>', self.backtrack)
        self._top.bind('<Control-z>', self.backtrack)
        self._top.bind('<BackSpace>', self.backtrack)
        self._top.bind('<Control-p>', self.postscript)
        self._top.bind('<h>', self.help)
        self._top.bind('<Alt-h>', self.help)
        self._top.bind('<Control-h>', self.help)
        self._top.bind('<F1>', self.help)
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
        Button(buttonframe, text='Expand', underline=0,
               command=self.expand).pack(side='left')
        Button(buttonframe, text='Match', underline=0,
               command=self.match).pack(side='left')
        Button(buttonframe, text='Backtrack', underline=0,
               command=self.backtrack).pack(side='left')
        self._autostep_button = Button(buttonframe, text='Autostep',
                                       underline=0, command=self.autostep)
        self._autostep_button.pack(side='left')
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
                                   width=525, height=250,
                                   closeenough=10,
                                   border=2, relief='sunken')
        self._cframe.pack(expand=1, fill='both', side='top', pady=2)
        canvas = self._canvas = self._cframe.canvas()

        # Initially, there's no tree.
        self._tree = None

        # Text widgets (for the text we're parsing)
        bottom = self._cframe.scrollregion()[3]
        y = bottom
        self._textwidgets = [TextWidget(canvas, tok.type())
                             for tok in self._text]
        for twidget in self._textwidgets:
            self._cframe.add_widget(twidget, 0, 0)
            twidget.move(0, bottom-twidget.bbox()[3]-5)
            y = min(y, twidget.bbox()[1])
        
        self._textline = canvas.create_line(-5000, y-5, 5000, y-5, dash='.')
    
    #########################################
    ##  Helper
    #########################################

    def _get(self, widget, treeloc):
        for i in treeloc: widget = widget.subtrees()[i]
        if isinstance(widget, TreeSegmentWidget):
            widget = widget.node()
        return widget

    #########################################
    ##  Main draw procedure
    #########################################

    def _redraw(self):
        # Delete the old stack & rtext widgets.
        if self._tree is not None:
            self._cframe.destroy_widget(self._tree)

        # Draw the tree.
        bold = ('helvetica', -12, 'bold')
        attribs = {'tree_color': '#000000', 'tree_width': 2,
                   'node_font': bold,}
        tree = self._parser.tree().type()
        self._tree = tree_to_treesegment(self._canvas, tree, **attribs)
        self._cframe.add_widget(self._tree, 30, 5)

        self._highlight_nodes()
        self._highlight_prodlist()
        self._position_text()

    def _redraw_quick(self):
        # This should be more-or-less sufficient after an animation. 
        self._highlight_nodes()
        self._highlight_prodlist()
        self._position_text()

    def _highlight_nodes(self):
        # Highlight the list of nodes to be checked.
        bold = ('helvetica', -12, 'bold')
        for treeloc in self._parser.frontier()[:1]:
            self._get(self._tree, treeloc)['color'] = '#20a050'
            self._get(self._tree, treeloc)['font'] = bold
        for treeloc in self._parser.frontier()[1:]:
            self._get(self._tree, treeloc)['color'] = '#008080'

    def _highlight_prodlist(self):
        # Highlight the productions that can be expanded.
        # Boy, too bad tkinter doesn't implement Listbox.itemconfig;
        # that would be pretty useful here.
        self._prodlist.delete(0, 'end')
        expandable = self._parser.expandable_productions()
        untried = self._parser.untried_expandable_productions()
        productions = self._productions
        for index in range(len(productions)):
            if productions[index] in expandable:
                if productions[index] in untried:
                    self._prodlist.insert(index, ' %s' % productions[index])
                else:
                    self._prodlist.insert(index, ' %s (TRIED)' %
                                          productions[index])
                self._prodlist.selection_set(index)
            else:
                self._prodlist.insert(index, ' %s' % productions[index])

    def _position_text(self):
        # Line up the text, as best we can..
        self._text_index = 0
        self._text_x = self._tree.bbox()[0]
        self._position_tree_text(self._tree)

        # If we have a complete parse, make everything green :)
        if self._parser.currently_complete():
            for twidget in self._textwidgets:
                twidget['color'] = '#00a000'
        
        while self._text_index < len(self._text):
            widget = self._textwidgets[self._text_index]
            widget.move(self._text_x - widget.bbox()[0], 0)
            self._text_x += widget.width() + 10
            self._text_index += 1
            widget['color'] = '#a0a0a0'

        # Make sure the text is at the bottom of the scrollregion.
        bottom = self._cframe.scrollregion()[3]
        #bottom = max(bottom, self._canvas.winfo_height()-5)
        y = bottom
        for twidget in self._textwidgets:
            twidget.move(0, bottom-twidget.bbox()[3]-5)
            y = min(y, twidget.bbox()[1])
        self._canvas.coords(self._textline, -5000, y-5, 5000, y-5)

    def _position_tree_text(self, tree):
        if self._text_index == len(self._textwidgets): return
        if isinstance(tree, TreeSegmentWidget):
            for subtree in tree.subtrees():
                self._position_tree_text(subtree)
        elif tree['color'] not in ('#008080', '#20a050'):
            widget = self._textwidgets[self._text_index]
            widget['color'] = '#006040'
            tree['color'] = '#006040'
            widget.move(tree.bbox()[0] - widget.bbox()[0], 0)
            self._text_x = widget.bbox()[2] + 10
            self._text_index += 1
            dy = widget.bbox()[1] - tree.bbox()[3] - 10.0
            tree.move(0, dy)

    #########################################
    ##  Button Callbacks
    #########################################

    def destroy(self, *e):
        self._autostep = 0
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def reset(self, *e):
        self._autostep = 0
        self._parser.initialize(self._text)
        self._lastoper1['text'] = 'Reset Demo'
        self._lastoper2['text'] = ''
        self._redraw()

    def autostep(self, *e):
        if self._autostep:
            self._autostep = 0
        else:
            self._autostep = 1
            self._step()

    def cancel_autostep(self, *e):
        self._autostep_button['text'] = 'Autostep'
        self._autostep = 0

    # Make sure to stop auto-stepping if we get any user input. 
    def step(self, *e): self._autostep = 0; self._step()
    def match(self, *e): self._autostep = 0; self._match()
    def expand(self, *e): self._autostep = 0; self._expand()
    def backtrack(self, *e): self._autostep = 0; self._backtrack()
    
    def _step(self):
        if self._animating_lock: return

        # Try expanding, matching, and backtracking (in that order)
        if self._expand(): pass
        elif self._parser.untried_match() and self._match(): pass
        elif self._backtrack(): pass
        else:
            self._lastoper1['text'] = 'Finished'
            self._lastoper2['text'] = ''
            self._autostep = 0

        # Check if we just completed a parse.
        if self._parser.currently_complete():
            self._autostep = 0
            self._lastoper2['text'] += '    [COMPLETE PARSE]'

    def _expand(self, *e):
        if self._animating_lock: return
        old_frontier = self._parser.frontier()
        rv = self._parser.expand()
        if rv:
            self._lastoper1['text'] = 'Expand:'
            self._lastoper2['text'] = rv
            self._prodlist.selection_clear(0, 'end')
            index = self._productions.index(rv)
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
            return 1
        else:
            self._lastoper1['text'] = 'Expand:'
            self._lastoper2['text'] = '(all expansions tried)'
            return 0

    def _match(self, *e):
        if self._animating_lock: return
        old_frontier = self._parser.frontier()
        rv = self._parser.match()
        if rv:
            self._lastoper1['text'] = 'Match:'
            self._lastoper2['text'] = rv
            self._animate_match(old_frontier[0])
            return 1
        else:
            self._lastoper1['text'] = 'Match:'
            self._lastoper2['text'] = '(failed)'
            return 0

    def _backtrack(self, *e):
        if self._animating_lock: return
        if self._parser.backtrack():
            elt = self._parser.tree()
            for i in self._parser.frontier()[0]: elt = elt[i]
            if isinstance(elt, TreeToken):
                self._lastoper1['text'] = 'Backtrack'
                self._lastoper2['text'] = 'Expand'
                self._animate_backtrack(self._parser.frontier()[0])
                return 1
            else:
                self._lastoper1['text'] = 'Backtrack'
                self._lastoper2['text'] = 'Match'
                self._animate_match_backtrack(self._parser.frontier()[0])
                return 1
        else:
            self._autostep = 0
            self._lastoper1['text'] = 'Finished'
            self._lastoper2['text'] = ''
            return 0

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

    def mainloop(self, *args, **varargs):
        self._top.mainloop(*args, **varargs)

    #########################################
    ##  Expand Production Selection
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
        old_frontier = self._parser.frontier()
        production = self._parser.expand(self._productions[index])

        if production:
            self._lastoper1['text'] = 'Expand:'
            self._lastoper2['text'] = production
            self._prodlist.selection_clear(0, 'end')
            self._prodlist.selection_set(index)
            self._animate_expand(old_frontier[0])
        else:
            # Reset the production selections.
            self._prodlist.selection_clear(0, 'end')
            for prod in self._parser.expandable_productions():
                index = self._productions.index(prod)
                self._prodlist.selection_set(index)

    #########################################
    ##  Attempt at animation...
    #########################################

    def _animate_expand(self, treeloc):
        oldwidget = self._get(self._tree, treeloc)
        oldtree = oldwidget.parent()
        top = not isinstance(oldtree.parent(), TreeSegmentWidget)

        tree = self._parser.tree()
        for i in treeloc:
            tree = tree.children()[i]

        bold = ('helvetica', -12, 'bold')
        widget = tree_to_treesegment(self._canvas, tree.type(),
                                     node_font=bold, leaf_color='white',
                                     tree_width=2, tree_color='white',
                                     node_color='white')
        widget.node()['color'] = '#20a050'
                                     
        (oldx, oldy) = oldtree.node().bbox()[:2]
        (newx, newy) = widget.node().bbox()[:2]
        widget.move(oldx-newx, oldy-newy)

        if top:
            self._cframe.add_widget(widget, 0, 5)
            widget.move(30-widget.node().bbox()[0], 0)
            self._tree = widget
        else:
            oldtree.parent().replace_child(oldtree, widget)

        # Move the children over so they don't overlap.
        # Line the children up in a strange way.
        if widget.subtrees():
            dx = (oldx + widget.node().width()/2 -
                  widget.subtrees()[0].bbox()[0]/2 -
                  widget.subtrees()[0].bbox()[2]/2)
            for subtree in widget.subtrees(): subtree.move(dx, 0)

        self._makeroom(widget)

        if top:
            self._cframe.destroy_widget(oldtree)
        else:
            oldtree.destroy()

        colors = ['gray%d' % (10*int(10*x/self._num_animation_frames))
                  for x in range(self._num_animation_frames,0,-1)]

        # Move the text string down, if necessary.
        dy = widget.bbox()[3] + 30 - self._canvas.coords(self._textline)[1]
        if dy > 0:
            for twidget in self._textwidgets: twidget.move(0, dy)
            self._canvas.move(self._textline, 0, dy)
        
        self._animate_expand_frame(widget, colors)

    def _makeroom(self, treeseg):
        """
        Make sure that no sibling tree bbox's overlap.
        """
        parent = treeseg.parent()
        if not isinstance(parent, TreeSegmentWidget): return

        index = parent.subtrees().index(treeseg)

        # Handle siblings to the right
        rsiblings = parent.subtrees()[index+1:]
        if rsiblings:
            dx = treeseg.bbox()[2] - rsiblings[0].bbox()[0] + 10
            for sibling in rsiblings: sibling.move(dx, 0)

        # Handle siblings to the left
        if index > 0:
            lsibling = parent.subtrees()[index-1]
            dx = max(0, lsibling.bbox()[2] - treeseg.bbox()[0] + 10)
            treeseg.move(dx, 0)
            
        # Keep working up the tree.
        self._makeroom(parent)
        
    def _animate_expand_frame(self, widget, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            widget['color'] = colors[0]
            for subtree in widget.subtrees():
                if isinstance(subtree, TreeSegmentWidget):
                    subtree.node()['color'] = colors[0]
                else:
                    subtree['color'] = colors[0]
            self._top.after(50, self._animate_expand_frame,
                            widget, colors[1:])
        else:
            self._redraw_quick()
            widget.node()['color'] = 'black'
            self._animating_lock = 0
            if self._autostep: self._step()
            
    def _animate_backtrack(self, treeloc):
        # Flash red first.
        colors = ['#a00000', '#000000', '#a00000']
        colors += ['gray%d' % (10*int(10*x/(self._num_animation_frames)))
                   for x in range(1, self._num_animation_frames+1)]

        widgets = [self._get(self._tree, treeloc).parent()]
        for subtree in widgets[0].subtrees():
            if isinstance(subtree, TreeSegmentWidget):
                widgets.append(subtree.node())
            else:
                widgets.append(subtree)
        
        self._animate_backtrack_frame(widgets, colors)

    def _animate_backtrack_frame(self, widgets, colors):
        if len(colors) > 0:
            self._animating_lock = 1
            for widget in widgets: widget['color'] = colors[0]
            self._top.after(50, self._animate_backtrack_frame,
                            widgets, colors[1:])
        else:
            self._redraw_quick()
            for subtree in widgets[0].subtrees():
                widgets[0].remove_child(subtree)
                subtree.destroy()
            self._animating_lock = 0
            if self._autostep: self._step()

    def _animate_match_backtrack(self, treeloc):
        widget = self._get(self._tree, treeloc)
        node = widget.parent().node()
        dy = (1.0 * (node.bbox()[3] - widget.bbox()[1] + 14) /
              self._num_animation_frames)
        self._animate_match_frame(self._num_animation_frames, widget, dy)

    def _animate_match(self, treeloc):
        widget = self._get(self._tree, treeloc)
        
        dy = ((self._textwidgets[0].bbox()[1] - widget.bbox()[3] - 10.0) /
              self._num_animation_frames)
        self._animate_match_frame(self._num_animation_frames, widget, dy)

    def _animate_match_frame(self, frame, widget, dy):
        if frame > 0:
            self._animating_lock = 1
            widget.move(0, dy)
            self._top.after(10, self._animate_match_frame,
                            frame-1, widget, dy)
        else:
            widget['color'] = '#006040'
            self._redraw_quick()
            self._animating_lock = 0
            if self._autostep: self._step()


def demo():
    """
    Create a recursive descent parser demo, using a simple grammar and
    text.
    """
    
    from nltk.cfg import Nonterminal, CFGProduction, CFG
    nonterminals = 'S VP NP PP P N Name V Det'
    (S, VP, NP, PP, P, N, Name, V, Det) = [Nonterminal(s)
                                           for s in nonterminals.split()]
    
    productions = (
        # Syntactic Rules
        CFGProduction(S, NP, VP),
        CFGProduction(NP, Det, N),
        CFGProduction(NP, Det, N, PP),
        CFGProduction(VP, V, NP, PP),
        CFGProduction(VP, V, NP),
        CFGProduction(VP, V),
        CFGProduction(PP, P, NP),
        # CFGProduction(PP), # Try an epsilon rule?

        # Lexical Rules
        CFGProduction(NP, 'I'),   CFGProduction(Det, 'the'),
        CFGProduction(Det, 'a'),  CFGProduction(N, 'man'),
        CFGProduction(V, 'saw'),  CFGProduction(P, 'in'),
        CFGProduction(N, 'park'), CFGProduction(P, 'with'),
        CFGProduction(N, 'dog'),  CFGProduction(N, 'telescope'),
        )

    grammar = CFG(S, productions)

    sent = 'the dog saw a man in the park'
    from nltk.token import WSTokenizer
    text = WSTokenizer().tokenize(sent)

    RecursiveDescentParserDemo(grammar, text)#.mainloop()

if __name__ == '__main__': demo()
        
