# Natural Language Toolkit: CFG visualization
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Visualization tools for CFGs

listbox of productions..
  - edit in place?
  - hmm..
  - color code terminals/nonterminals
  - draw terminals as C{'foo'} (i.e., with quotes)
  - click on a rule to edit it.

Can I do this with listbox? might have to use a canvas.. :-/

1. canvas displaying rules; click to select
2. entry for editing selected rule
3. 'set' button, or some such
4. (optional) picture of corresponding partial tree
# +-----------------+------------------+
# | S  -> NP VP    ^|                  |
# | NP -> Det N    #|       VP         |
# |[VP -> V PP    ]:|      / \         |
# | N  -> 'dog'    v|     V   PP       |
# +-----------------+                  |
# |[VP -> V PP][Set]|                  |
# +-----------------+------------------+




"""

from nltk.draw import *
from nltk.cfg import *
from Tkinter import *
        
class CFGEditor:
    def __init__(self, parent, cfg):
        # If no parent was given, set up a top-level window.
        if parent is None:
            self._parent = Tk()
            self._parent.title('NLTK')
            self._parent.bind('q', self.destroy)
        else:
            self._parent = parent

        self._cfg = cfg

        self._prodlist_canvas = self._init_prodlist_canvas(cfg.productions())

    def _init_prodlist_canvas(self, productions):
        cframe = CanvasFrame(self._parent, background='white')
        c = cframe.canvas()

        # Create a stack for the production widgets.
        prod_widgets = []
        for production in productions:
            lhs = TextWidget(c, str(production.lhs()), color='#026')
            elt_widgets = [lhs, SymbolWidget(c, 'rightarrow')]
            for elt in production.rhs():
                if isinstance(elt, Nonterminal):
                    elt_widgets.append(TextWidget(c, str(elt), color='#026'))
                else:
                    elt_widgets.append(TextWidget(c, repr(elt), color='#062'))
            prod_widgets.append(SequenceWidget(c, *elt_widgets))
        prod_stack = StackWidget(c, align='left', *prod_widgets)

        # Bind clicks..
        for prod_widget in prod_widgets:
            prod_widget.bind_click(self.select)
                                
        # Add to the cframe
        cframe.add_widget(prod_stack)
        cframe.pack(expand=1, fill='both')
        return c

    def select(self, prod_widget):
        prod_widget._children[1]['color'] = 'red'
        
    def destroy(self, *e):
        if self._parent is None: return
        self._parent.destroy()
        self._parent = None

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

    CFGEditor(None, grammar)

if __name__ == '__main__': demo()
        

        

