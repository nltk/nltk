# Natural Language Toolkit: Finite State Automota Visualization
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Graphically display a finite state automaton.

This module may be renamed to nltk.draw.graph at some point in the
future, since it actually supports arbitrary graphs.
"""

import math
from nltk.draw import *
from nltk.draw.graph import *

##//////////////////////////////////////////////////////
##  Test code.
##//////////////////////////////////////////////////////

def fsawindow(fsa):
    import random
    def manage(cw): cw.manage()
    def changetext(cw):
        from random import randint
        cw.set_text(5*('%d' % randint(0,999999)))
    
    cf = CanvasFrame(width=300, height=300)
    c = cf.canvas()

    nodes = {}
    for state in fsa.states():
        if state in fsa.finals(): color = 'red3'
        else: color='green3'
        nodes[state] = StackWidget(c, TextWidget(c, `state`),
                                   OvalWidget(c, SpaceWidget(c, 12, 12),
                                              fill=color, margin=0))

    edges = []
    for (s1, tlabels, s2) in fsa.transitions():
        for tlabel in tlabels.elements():
            if tlabel is None:
                label = SymbolWidget(c, 'epsilon', color='gray40')
                edge = GraphEdgeWidget(c, 0,0,0,0, label, color='gray50')
            else:
                label = TextWidget(c, str(tlabel), color='blue4')
                edge = GraphEdgeWidget(c, 0,0,0,0, label, color='cyan4')
            edges.append( (nodes[s1], nodes[s2], edge) )

    for node in nodes.values():
        node['draggable'] = 1

    graph = GraphWidget(c, nodes.values(), edges, draggable=1)
    graph.bind_click(manage)
    cf.add_widget(graph, 20, 20)

    return nodes, graph, cf

# Test
def demo():
    import nltk.fsa
    import time, random
    t = time.time()
    regexps = ['(ab(c*)c)*dea(b+)e',
               '((ab(c*))?(edc))*dea(b*)e',
               '(((ab(c*))?(edc))+dea(b+)eabba)*',
               '(ab(c*)c)*']

    # Pick a random regexp, and draw it.
    regexp = random.choice(regexps)
    print 'trying', regexp
    fsa = nltk.fsa.FSA("abcdef")
    fsa.empty()
    nltk.fsa.re2nfa(fsa, regexp)

    # Show the DFA
    dfa = fsa.dfa()
    dfa.prune()
    nodemap, graph, cf = fsawindow(dfa)

    if 0:
        # Now, step through a text.
        text = []
        state = [dfa.start()]
        def reset(widget, text=text, state=state, dfa=dfa, nodemap=nodemap):
            nodemap[state[0]].child_widgets()[1]['fill'] = 'green3'
            text[:] = list('abcababc')
            text.reverse()
            state[0] = dfa.start()
            nodemap[state[0]].child_widgets()[1]['fill'] = 'red'
            
        def step(widget, text=text, dfa=dfa, state=state, nodemap=nodemap):
            nodemap[state[0]].child_widgets()[1]['fill'] = 'green3'
            if len(text) == 0: return
            nextstates = dfa.next(state[0], text.pop())
            if not nextstates: return
            state[0] = nextstates[0]
            nodemap[state[0]].child_widgets()[1]['fill'] = 'red'

        reset(0)
        graph.bind_click(step)
        graph.bind_click(reset, 3)

    cf.mainloop()

if __name__ == '__main__':
    print ('nltk.fsa has been temporarily removed; '+
           'so nltk.draw.fsa is disabled.')
    #demo()
