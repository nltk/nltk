# Natural Language Toolkit: Feature Structure Visualization
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Graphically display a feature structure.
"""

# DEBUG
import nltk.draw.graph; reload(nltk.draw.graph)

from nltk.draw import *
from nltk.draw.graph import GraphWidget, GraphEdgeWidget
from nltk.featurestruct import *

##//////////////////////////////////////////////////////
##  FVMWidget
##//////////////////////////////////////////////////////

class FVM(AbstractContainerWidget):
    def __init__(self, canvas, fstruct, **attribs):
        self._canvas = canvas
        self._fstruct = fstruct
        self._valwidgets = {}
        self._namewidgets = {}
        self._idwidgets = {}

        # Determine which structures are reentrant.
        # [XX] This breaks an abstraction barrier.
        self._reentrances = fstruct._find_reentrances({})
        
        self._reentrance_ids = {}
        self._child = self._init(fstruct)
        AbstractContainerWidget.__init__(self, canvas,
                                         self._child, **attribs)

        # Maintain a selection.
        self._selection = None
    
    def _init(self, fstruct):
        c = self._canvas
        if self._reentrances[id(fstruct)]:
            self._reentrance_ids[fstruct] = `len(self._reentrance_ids)+1`
    
        if len(fstruct._features) == 0:
            if self._reentrances[id(fstruct)]:
                identifier = '(%s)' % self._reentrance_ids[fstruct]
                idwidget = TextWidget(c, identifier)
                self._idwidgets[fstruct] = idwidget
                return SequenceWidget(c, idwidget, BracketWidget(c))
            else:
                return BracketWidget(c)
    
        fwidgets = []
        for fname in fstruct.feature_names():
            namewidget = TextWidget(c, '%s' % fname)
            self._namewidgets[fstruct,fname] = namewidget
            fval = fstruct[fname]
            if not isinstance(fval, FeatureStructure):
                opwidget = TextWidget(c,'=')
                valwidget = TextWidget(c,repr(fval))
                # BUT: single value repeated??
                self._valwidgets[fval] = valwidget
            elif self._reentrance_ids.has_key(fval):
                opwidget = SymbolWidget(c,'rightarrow')
                valwidget = TextWidget(c,'(%s)' % self._reentrance_ids[fval])
            else:
                opwidget = TextWidget(c,'=')
                valwidget = self._init(fval)
            fwidget = SequenceWidget(c, namewidget, opwidget, valwidget)
            fwidgets.append(fwidget)

        w = BracketWidget(c,StackWidget(c, align='left', *fwidgets))
        self._valwidgets[fstruct] = w
        if self._reentrances[id(fstruct)]:
            ident = self._reentrance_ids[fstruct]
            idwidget = TextWidget(c, '(%s)' % ident)
            self._idwidgets[fstruct] = idwidget
            w = SequenceWidget(c, idwidget, w)
        return w

    def mark(self, featurepath):
        """
        Mark the given feature.  Feature values may be either basic
        values or feature structures.
        """
        # Mark the path.
        fstruct = self._fstruct
        for fname in featurepath:
            self._valwidgets[fstruct]['color'] = '#000080'
            self._valwidgets[fstruct]['width'] = 2
            self._namewidgets[fstruct,fname]['color'] = '#000080'
            self._namewidgets[fstruct,fname]['font'] = 'bold'
            fstruct = fstruct[fname]
            if self._idwidgets.has_key(fstruct):
                self._idwidgets[fstruct]['color'] = '#000080'
                self._idwidgets[fstruct]['font'] = 'bold'

        # Mark the value.
        fstruct = self._fstruct[featurepath]
        widget = self._valwidgets[fstruct]

        # Get the parent of the value we want to mark
        parent = widget.parent()

        # Find the index of the value in its parent's children
        siblings = parent.child_widgets()
        i = siblings.index(widget)

        # Remove the value from the parent
        parent.remove_child(widget)

        # Wrap the value in a box
        box = BoxWidget(self._canvas, widget, fill='#d0e8ff', outline='')

        # Add the box as a child of the parent
        parent.insert_child(i, box)
        parent.update(box)

        # Highlight the brackets for feature values.
        #if isinstance(widget, BracketWidget): widget['width'] = 2

    def _tags(self): return []
    def __repr__(self): return '[FVM: %r]' % self._topwidget
        
    

##//////////////////////////////////////////////////////
##  FeatureStructureGraph
##//////////////////////////////////////////////////////

def feature_struct_graph(canvas, fstruct):
    nodes = {}
    edges = []
    _feature_struct_graph(canvas, fstruct, nodes, edges)
    for node in nodes.values():
        node['draggable'] = 1
    graph = GraphWidget(canvas, nodes.values(), edges, draggable=1)
    return graph

def _feature_struct_graph(canvas, fstruct, nodes, edges):
    nodes[fstruct] = OvalWidget(canvas, SpaceWidget(canvas, 12, 12),
                                fill='green3', margin=0)
    for fname in fstruct.feature_names():
        fval = fstruct[fname]

        # Build the subnode for the value.
        if not nodes.has_key(fval):
            if isinstance(fval, FeatureStructure):
                _feature_struct_graph(canvas, fval, nodes, edges)
            else:
                nodes[fval] = TextWidget(canvas, repr(fval))
                
        # Connect an edge to the subnode
        subnode = nodes[fval]
        label = TextWidget(canvas, fname, color='black')
        edge = GraphEdgeWidget(canvas, 0,0,0,0, label, color='cyan4')
        edges.append( (nodes[fstruct], subnode, edge) )

    return nodes[fstruct]
        
##//////////////////////////////////////////////////////
##  Demo
##//////////////////////////////////////////////////////

def demo():
    # Define a feature structure.
    fstruct = FeatureStructure.parse('[a=(1)[b=2,c=(2)hi],d->(1),e=[f=22],'+
                                  'g=[h->(1)]]')
    #fstruct = FeatureStructure.parse('[a=[b=1,c=[d=x],e=?x],f=12,g=13]')
    #fstruct = FeatureStructure.parse('[a=12]')

    # Create the canvas frame.
    cf = CanvasFrame(width=300, height=300)

    # Create a FVM view of the feature structure
    fvm = FVM(cf.canvas(), fstruct, draggable=1)
    fvm.mark(['g','h'])
    cf.add_widget(fvm)

    # Create a digraph view of the feature structure.
    graph = feature_struct_graph(cf.canvas(), fstruct)
    cf.add_widget(graph)
    
    cf.mainloop()

if __name__ == '__main__':
    demo()
