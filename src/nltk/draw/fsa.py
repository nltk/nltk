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

class GraphEdgeWidget(CanvasWidget):
    """
    Display an edge of a graph.
    """
    def __init__(self, canvas, x1, y1, x2, y2, label=None, **attribs):
        self._curve = 0
        coords = self._line_coords((x1, y1), (x2, y2))
        self._line = canvas.create_line(arrow='last', smooth=1, *coords)
        canvas.lower(self._line)
        self._label = label
        if label is not None:
            self._add_child_widget(label)

        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == 'curve':
            self._curve = value
            coords = self._line_coords(self.start(), self.end())
            self.canvas().coords(self._line, *coords)
        elif attr == 'color':
            self.canvas().itemconfig(self._line, fill=value)
        elif attr == 'width':
            self.canvas().itemconfig(self._line, width=value)
        else:
            CanvasWidget.__setitem__(self, attr, value)
        
    def __getitem__(self, attr):
        if attr == 'curve':
            return self._curve
        elif attr == 'color':
            return self.canvas().itemcget(self._line, fill)
        elif attr == 'width':
            return self.canvas().itemcget(self._line, width)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return [self._line]

    def __repr__(self):
        return '[GraphEdge: %r %r->%r]' % (self._label, self.start(),
                                           self.end())

    def start(self):
        return self.canvas().coords(self._line)[:2]
    
    def end(self):
        return self.canvas().coords(self._line)[-2:]

    def set_start(self, x, y):
        coords = self._line_coords((x, y), self.end())
        self.canvas().coords(self._line, *coords)
        self.update(self._label)

    def set_end(self, x, y):
        coords = self._line_coords(self.start(), (x, y))
        self.canvas().coords(self._line, *coords)
        self.update(self._label)

    def _update(self, child):
        # The label moved?
        (x1, y1, x2, y2) = child.bbox()
        (x, y) = self._label_coords()
        child.move(x-(x1+x2)/2, y-(y1+y2)/2)

    def _manage(self):
        if self._label is not None:
            self._update(self._label)

    def _label_coords(self):
        line_coords = self.canvas().coords(self._line)
        (x1, y1) = line_coords[:2]
        (x2, y2) = line_coords[-2:]
        if (x1, y1) == (x2, y2):
            # Self-loops.  Emperically, this formula seems about
            # right, but it wasn't derived mathmatically.
            radius = 0
            return (x1, y1 + 0.81*(150*self._curve+radius) + 10)
        elif self._curve >= 0:
            # Normal edges.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
            labelx = (x1+x2)*0.5 + (y2-y1)*(self._curve*.6)
            labely = (y1+y2)*0.5 - (x2-x1)*(self._curve*.6)
            return (int(labelx), int(labely))
        else:
            # Normal edges.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
            labelx = (x1+x2)*0.5 + (y2-y1)*(self._curve/2 + 8/r)
            labely = (y1+y2)*0.5 - (x2-x1)*(self._curve/2 + 8/r)
            return (int(labelx), int(labely))
    
    def _line_coords(self, (startx, starty), (endx, endy)):
        (x1, y1) = (startx, starty)
        (x2, y2) = (endx, endy)
        radius1 = 0
        radius2 = 0
        
        if (x1, y1) == (x2, y2):
            # Self-loops
            x3 = x1 - 70*self._curve - radius1
            y3 = y1 + 70*self._curve + radius1
            x4 = x1
            y4 = y1 + 140*self._curve + radius1
            x5 = x1 + 70*self._curve + radius1
            y5 = y1 + 70*self._curve + radius1
            return (int(x1), int(y1), int(x3), int(y3), int(x4),
                    int(y4), int(x5), int(y5), int(x1), int(y1))
        else:
            # Normal edges.
            x3 = (x1+x2)*0.5 + (y2-y1)*self._curve
            y3 = (y1+y2)*0.5 - (x2-x1)*self._curve
            # Adjust endpoints so they end at the node parimeter.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 0.001)
            (dx, dy) = (x2-x1, y2-y1)
            x1 += dx/r * radius1
            y1 += dy/r * radius1
            x2 -= dx/r * radius2
            y2 -= dy/r * radius2
            return (int(x1), int(y1), int(x3), int(y3), int(x2), int(y2))
        
class GraphWidget(CanvasWidget):
    """
    Connect nodes and GraphEdgeWidgets into a graph.
    """
    def __init__(self, canvas, nodes, edges, **attrs):
        """
        @param edges: A list of tuples (n1, n2, e), where n1 is a
            CanvasWidget in C{nodes}; n2 is a CanvasWidget in
            C{nodes}; and e is a GraphEdgeWidget.
        """
        self._nodes = nodes

        # Management parameters.  I should add attributes for these. 
        self._arrange = 'bfs'
        self._xspace = 50
        self._yspace = 50
        self._orientation = 'horizontal'

        # Attributes for edges.

        # Out & in edges for a given node
        self._outedges = {}
        self._inedges = {}

        # Start & end nodes for a given edge.
        self._startnode = {}
        self._endnode = {}

        # Keep track of edge widgets.
        self._edgewidgets = {}

        for node in self._nodes:
            self.add_node(node)
        for (start, end, edgewidget) in edges:
            self.add_edge(start, end, edgewidget)
            
        CanvasWidget.__init__(self, canvas, **attrs)

    def add_node(self, node):
        """
        Add a new node to the graph.
        """
        self._add_child_widget(node)

    def add_edge(self, start, end, edgewidget):
        """
        Add a new edge to the graph.
        @param edges: A tuple (n1, n2, e), where n1 is a
            CanvasWidget in C{nodes}; n2 is a CanvasWidget in
            C{nodes}; and e is a GraphEdgeWidget.
        """
        curve = 0.2 * (1+len(self._edgewidgets.get( (start, end), [])))
        edgewidget['curve'] = curve

        # Add the edge to the outedge & inedge dictionaries
        self._outedges.setdefault(start, []).append(edgewidget)
        self._inedges.setdefault(end, []).append(edgewidget)

        self._startnode[edgewidget] = start
        self._endnode[edgewidget] = end
            
        self._edgewidgets.setdefault((start, end),[]).append(edgewidget)
        self._add_child_widget(edgewidget)
        

    def remove_edge(self, edge):
        """
        Remove an edge from the graph (but don't destroy it).
        @type edge: L{GraphEdgeWidget}
        """
        print 'remove', edge
        # Get the edge's start & end nodes.
        start, end = self._startnode[edge], self._endnode[edge]

        # Remove the edge from the node->edge maps
        self._outedges[start].remove(edge)
        self._inedges[end].remove(edge)
        
        # Remove the edge from the edge->node maps.
        del self._startnode[edge]
        del self._endnode[edge]
        
        # Remove the edge from the list of edge widgets that connect 2
        # nodes.  (Recompute curves?)
        self._edgewidgets[start, end].remove(edge)

        # Remove the edge from our list of child widgets.
        self._remove_child_widget(edge)

    def remove_node(self, node):
        """
        Remove a node from the graph (but don't destroy it).
        @type node: L{CanvasWidget}
        @return: A list of widgets that were removed from the
            graph.  Note that this will include any edges that
            connected to C{node}.
        """
        # Remove all edges that connect to this node.
        removed_edges = []
        for edge in self._outedges.get(node, [])[:]:
            self.remove_edge(edge)
            removed_edges.append(edge)
        for edge in self._inedges.get(node, [])[:]:
            self.remove_edge(edge)
            removed_edges.append(edge)

        # Remove the node from the node->edges map
        try: del self._outedges[node]
        except KeyError: pass
        try: del self._inedges[node]
        except KeyError: pass

        # Remove the node from our list of nodes
        self._nodes.remove(node)

        # Remove the node from our list of child widgets.
        self._remove_child_widget(node)

        # Return the list of removed widgets
        return removed_edges + [node]

    def destroy_edge(self, edge):
        """
        Remove an edge from the graph, and destroy the edge.
        """
        self.remove_edge(edge)
        edge.destroy()

    def destroy_node(self, node):
        """
        Remove a node from the graph, and destroy the node.
        """
        print 'removing', node
        for widget in self.remove_node(node):
            print 'destroying', widget
            widget.destroy()

    def _tags(self): return []

    def _update(self, child):
        """
        Make sure all edges/nodes are connected correctly.
        """
        if isinstance(child, GraphEdgeWidget):
            # Moved an edge.
            pass
        else:
            (x1, y1, x2, y2) = child.bbox()
            x = (x1+x2)/2
            y = (y1+y2)/2
            
            # Moved a node.
            for outedge in self._outedges.get(child, []):
                outedge.set_start(x, y)
            for inedge in self._inedges.get(child, []):
                inedge.set_end(x, y)

    def _manage(self):
        self.arrange()

    ##////////////////////////
    ##  Graph Layout
    ##////////////////////////
    def arrange(self, arrange_algorithm=None):
        """
        Set the node positions.  This routine should attempt to
        minimize the number of crossing edges, in order to make the
        graph easier to read.
        """
        if arrange_algorithm is not None:
            self._arrange = arrange_algorithm
            
        self._arrange_into_levels()
        self._arrange_levels()

        (old_left, old_top) = self.bbox()[:2]
        for node in self._nodes:
            (x1, y1) = node.bbox()[:2]
            node.move(-x1, -y1)

        # Now we want to minimize crossing edges.. how, again? :)
        for i in range(len(self._levels)):
            for j in range(len(self._levels[i])):
                if self._levels[i][j] is not None:
                    if self._orientation == 'horizontal':
                        self._levels[i][j].move(i*self._xspace,
                                                j*self._yspace)
                    else:
                        self._levels[i][j].move(j*self._xspace,
                                                i*self._yspace)

        (left, top) = self.bbox()[:2]
        self.move(int(old_left-left), int(old_top-top))

    def _arrange_levels(self):
        """
        Re-arrange each level to (locally) minimize the number of
        crossing edges.
        """
        # For now, put nodes with more incoming edges further down.
        for levelnum in range(len(self._levels)):
            self._arrange_level(levelnum)
        #for level in self._levels:
        #    level.sort(lambda n1,n2:cmp(len(n1.incoming()), len(n2.incoming())))

    def _arrange_level(self, levelnum):
        """
        Arrange a given level..  This algorithm is simple and pretty
        heuristic..
        """
        if levelnum == 0: return

        # For each position where we might want to put a node, create
        # a scores dictionary, mapping candidate nodes to scores.  We
        # will then use these scores to distribute nodes to level positions.
        scores = [{} for i in range(max(len(self._levels[levelnum]),
                                       len(self._levels[levelnum-1])))]
        for node in self._levels[levelnum]:
            # All else being equal, put nodes with more incoming
            # connections towards the end (=bottom) of the level.
            for pos in range(len(scores)):
                scores[pos][node] = 1.0/len(self._inedges.get(node, []))
                
            # Try to put a node at level position x if nodes
            # in previous levels at position x point to it.
            for edge in self._inedges.get(node, []):
                from_node = self._startnode[edge]
                from_levelnum = self._nodelevel[from_node]
                if from_levelnum < levelnum:
                    from_pos = self._levels[from_levelnum].index(from_node)
                    score = (scores[from_pos].get(node, 0) + 1.0 /
                             (levelnum - from_levelnum))
                    scores[from_pos][node] = score

        # Get the list of nodes that we need to fill in, and empty the
        # level.
        nodes = self._levels[levelnum]
        self._levels[levelnum] = [None] * len(scores)
        level = self._levels[levelnum]

        # Fill in nodes, picking the best first..
        while len(nodes) > 0:
            best = (None, None, -1) # node, position, score.
            for pos in range(len(scores)):
                for (node, score) in scores[pos].items():
                    if score > best[2] and level[pos] is None and node in nodes:
                        best = (node, pos, score)
                    elif (score == best[2] and pos<best[1] and
                        level[pos] is None and node in nodes):
                        # Put higher scores at lower level positions
                        best = (node, pos, score)
            nodes.remove(best[0])
            level[best[1]] = best[0]

    def _arrange_into_levels(self):
        """
        Assign a level to each node.
        """
        # Mapping from node to level.
        self._nodelevel = {}
        self._levels = []

        # Find any nodes that have no incoming edges; put all of these
        # in level 0.
        toplevel = []
        for node in self._nodes:
            if len(self._inedges.get(node, [])) == 0:
                toplevel.append(node)
                self._nodelevel[node] = 0

        # Expand all of their children.
        self._levels = [toplevel]
        self._add_descendants(toplevel, 1)

        # If we didn't get all the nodes, we'll have to start picking
        # nodes that do have incoming transitions.  Pick the ones that
        # have the most reachable nodes.  (n.b., this implementation
        # isn't terribly efficient, but we dont' expect to be
        # displaying huge FSAs, so it should be ok)
        while len(self._nodelevel) < len(self._nodes):
            expand_node = None
            max_reachable = -1

            for node in self._nodes:
                reachable = self._reachable(node)
                if reachable >= max_reachable:
                    max_reachable = reachable
                    expand_node = node
            
            # Expand the new node's children.
            self._levels[0].append(expand_node)
            self._nodelevel[expand_node] = 0
            self._add_descendants(toplevel, 1)
    
    def _reachable(self, node, reached=None):
        """
        How many *unexpanded* nodes can be reached from the given node?
        """
        if self._nodelevel.has_key(node): return 0
        if reached is None: reached = {}
        if not reached.has_key(node):
            reached[node] = 1
            for edge in self._outedges.get(node, []):
                self._reachable(self._endnode[edge], reached)
        return len(reached)

    def _add_descendants(self, parent_level, levelnum):
        """
        Add all the descendants of the nodes in the list parent_level
        to the structures self._level and self._nodelevel.
        """
        if self._arrange == 'bfs':
            self._add_descendants_bfs(parent_level, levelnum)
        elif self._arrange == 'dfs':
            self._add_descendants_dfs(parent_level, levelnum)
        else:
            # Default to dfs
            self._add_descendants_dfs(parent_level, levelnum)

    def _add_descendants_dfs(self, parent_level, levelnum):
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            # Add the parent node
            if not self._nodelevel.has_key(parent_node):
                self._levels[levelnum-1].append(parent_node)
                self._nodelevel[parent_node] = levelnum-1

            # Recurse to its children
            child_nodes = [self._endnode[edge]
                           for edge in self._outedges.get(parent_node, [])
                           if not self._nodelevel.has_key(self._endnode[edge])]
            if len(child_nodes) > 0:
                self._add_descendants_dfs(child_nodes, levelnum+1)

    def _add_descendants_bfs(self, parent_level, levelnum):
        frontier_nodes = []
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            child_nodes = [self._endnode[edge]
                           for edge in self._outedges.get(parent_node, [])]
            for node in child_nodes:
                if not self._nodelevel.has_key(node):
                    self._levels[levelnum].append(node)
                    self._nodelevel[node] = levelnum
                    frontier_nodes.append(node)
        if len(frontier_nodes) > 0:
            self._add_descendants_bfs(frontier_nodes, levelnum+1)

    def _add_descendants_bfs2(self, parent_level, levelnum):
        frontier_nodes = []
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            child_nodes = [self._endnode[edge]
                           for edge in self._outedges.get(parent_node, [])]
            child_nodes += [self._startnode[edge]
                           for edge in self._inedges.get(parent_node, [])]
            for node in child_nodes:
                if not self._nodelevel.has_key(node):
                    self._levels[levelnum].append(node)
                    self._nodelevel[node] = levelnum
                    frontier_nodes.append(node)
        if len(frontier_nodes) > 0:
            self._add_descendants_bfs2(frontier_nodes, levelnum+1)



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

    return nodes, graph

# Test
import nltk.fsa
def demo():
    import time, random
    t = time.time()
    regexps = [#'(ab(c*)c)*dea(b+)e',
               #'((ab(c*))?(edc))*dea(b*)e',
               #'(((ab(c*))?(edc))+dea(b+)eabba)*',
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
    nodemap, graph = fsawindow(dfa)

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

if __name__ == '__main__':
    demo()
