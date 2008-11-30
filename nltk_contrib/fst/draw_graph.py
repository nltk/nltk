# Natural Language Toolkit: Graph Visualization
#
# Copyright (C) 2001 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: graph.py,v 1.2 2004/03/18 21:02:36 edloper Exp $

"""
Graphically display a graph.  This module defines two new canvas
widgets: L{GraphEdgeWidget}, and L{GraphWidget}.  Together, these two
widgets can be used to display directed graphs.

C{GraphEdgeWidget} is an arrow, optionally annotated with a 'label',
which can be any canvas widget.  In addition to a source location and
a destination location, it has a 'curve' attribute, which can be used
to define how curved it is (positive values curve one way, and
negative values the other).  This is useful, e.g., if you want to have
two separate graph edges with the same source and the same
destination.  It is also useful for drawing arrows that have the same
source and destination (i.e., loops).

The C{GraphWidget} widget is used to display a single directed graph.
It is a container widget, containing zero or more I{node widgets},
which are connected by zero or more I{edge widgets}.  Any canvas
widget can be used as a node widget.  E.g., a StackWidget containing
an OvalWidget and a LabelWidget could be used to draw a circle with a
label below it.  Edge widgets must be C{GraphEdgeWidgets}.  The
C{GraphWidget} is responsible for adjusting the start and end
positions of edge widgets whenever node widgets move.  Thus, you can
make a node widget draggable, and when the user drags it, the edges
will update automatically.  The C{GraphWidget} also defines a method
C{arrange}, which will automatically choose a layout for the nodes,
attempting to minimize crossing edges.
"""

import math
from nltk.draw import *

class GraphEdgeWidget(CanvasWidget):
    """
    A canvas widget used to display graph edges.

    @todo: Add an 'arrow' attribute, which can be used to control the
           direction and/or shape of the arrow.
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
        (x1, y1) = int(startx), int(starty)
        (x2, y2) = int(endx), int(endy)
        radius1 = 0
        radius2 = 0

        if abs(x1-x2)+abs(y1-y2) < 5:
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
    A canvas widget used to display directed graphs.  This container
    widget contains zero or more 'node widgets', which are connected by
    zero or more C{GraphEdgeWidget}s.  The C{GraphWidget} is responsible
    for updating the edge widgets when nodes move; and for initially
    arranging the nodes.
    """
    def __init__(self, canvas, nodes, edges, **attrs):
        """
        @param edges: A list of tuples (n1, n2, e), where n1 is a
            CanvasWidget in C{nodes}; n2 is a CanvasWidget in
            C{nodes}; and e is a GraphEdgeWidget.
        """
        if len(nodes) == 0:
            # dummy node, since we need to have a bbox.
            nodes = [SpaceWidget(canvas,0,0)]
            
        self._nodes = set(nodes)

        # Management parameters.  I should add attributes for these. 
        self._arrange = 'dfs'
        self._xspace = attrs.pop('xspace', 50)
        
        self._yspace = attrs.pop('yspace', 50)
        self._orientation = attrs.pop('orientation', 'horizontal')

        # Attributes for edges.

        # Out & in edges for a given node
        self._outedges = {}
        self._inedges = {}

        # Start & end nodes for a given edge.
        self._startnode = {}
        self._endnode = {}

        # Keep track of edge widgets.
        self._edgewidgets = {}

        self._initialized = False
        for node in self._nodes:
            self.add_node(node)
        for (start, end, edgewidget) in edges:
            self.add_edge(start, end, edgewidget)
        self._initialized = True
            
        CanvasWidget.__init__(self, canvas, **attrs)

    def add_node(self, node):
        """
        Add a new node to the graph.
        """
        self._add_child_widget(node)
        self._nodes.add(node)

    def add_edge(self, start, end, edgewidget):
        """
        Add a new edge to the graph.
        @param start: The start node
        @type start: C{CanvasWidget}
        @param end: The end node
        @type end: C{CanvasWidget}
        @param edgewidget: The edge
        @type edgewidget: C{GraphEdgeWidget}
        """
        num_edges = (len(self._edgewidgets.get( (start, end), [])) +
                     len(self._edgewidgets.get( (end, start), [])))
        if start is end:
            num_edges = num_edges/2+1
            curve = 0.3 * ((num_edges+1)/2) * (num_edges%2*2-1)
        else:
            curve = 0.4 * ((num_edges+1)/2) * (num_edges%2*2-1)
        edgewidget['curve'] = curve

        # Add the edge to the outedge & inedge dictionaries
        self._outedges.setdefault(start, []).append(edgewidget)
        self._inedges.setdefault(end, []).append(edgewidget)

        self._startnode[edgewidget] = start
        self._endnode[edgewidget] = end
            
        self._edgewidgets.setdefault((start, end),[]).append(edgewidget)
        self._add_child_widget(edgewidget)
        if self._initialized: self._update_edge(edgewidget)

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
            # Moved a node.
            for outedge in self._outedges.get(child, []):
                self._update_edge(outedge)
            for inedge in self._inedges.get(child, []):
                self._update_edge(inedge)

    def _update_edge(self, edge):
        curve = edge['curve']
        # Set the start.
        src_x, src_y = self._node_center(self._endnode[edge])
        x, y = self._node_port(self._startnode[edge], src_x, src_y, curve)
        edge.set_start(x, y)
        # Set the end.
        src_x, src_y = x, y#self._node_center(self._startnode[edge])
        x, y = self._node_port(self._endnode[edge], src_x, src_y, curve)
        edge.set_end(x, y)

    def _node_port(self, node, src_x, src_y, curve):
        x1, y1, x2, y2 = node.bbox()
        x, y = (x1+x2)/2, (y1+y2)/2
        w, h = abs(x2-x1), abs(y2-y1)
        dx, dy = x-src_x, y-src_y

        if dx > abs(dy)/5: return x-w/2, y
        elif dx < -abs(dy)/5: return x+w/2, y
        #if dx > abs(dy): return x-w/2, y
        #elif dx < -abs(dy): return x+w/2, y
        elif dy > 0: return x, y-h/2
        elif dy < 0: return x, y+h/2
        elif curve > 0:
            return x, y+h/2
        else:
            return x, y-h/2

    def _node_center(self, node):
        (x1, y1, x2, y2) = node.bbox()
        return (x1+x2)/2, (y1+y2)/2

    def _manage(self):
        self.arrange()

    ##////////////////////////
    ##  Graph Layout
    ##////////////////////////
    def arrange(self, arrange_algorithm=None, toplevel=None):
        """
        Set the node positions.  This routine should attempt to
        minimize the number of crossing edges, in order to make the
        graph easier to read.
        """
        if arrange_algorithm is not None:
            self._arrange = arrange_algorithm
            
        self._arrange_into_levels(toplevel)
        self._arrange_levels()

        (old_left, old_top) = self.bbox()[:2]
        for node in self._nodes:
            (x1, y1) = node.bbox()[:2]
            node.move(-x1, -y1)

        # Now we want to minimize crossing edges.. how, again? :)
        for i in range(len(self._levels)):
            for j in range(len(self._levels[i])):
                if self._levels[i][j] is not None:
                    node = self._levels[i][j]
                    if self._orientation == 'horizontal':
                        node.move(i*self._xspace, j*self._yspace)
                    else:
                        node.move(j*self._xspace, i*self._yspace)

                    # If there is an edge from a node at the same
                    # position within its level, but whose level is at
                    # least 2 levels prior, then it's likely that that
                    # edge goes through an intervening node; so if its
                    # curve is zero, then increment it.
                    for edge in self._inedges.get(node,[]):
                        from_node = self._startnode[edge]
                        from_levelnum = self._nodelevel[from_node]
                        from_level = self._levels[from_levelnum]
                        if (abs(i-from_levelnum)>1 and
                            len(from_level) > j and
                            from_node == from_level[j] and
                            edge['curve'] == 0):
                            edge['curve'] = -0.25

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
                    if (score > best[2] and level[pos] is None and
                        node in nodes):
                        best = (node, pos, score)
                    elif (score == best[2] and pos<best[1] and
                        level[pos] is None and node in nodes):
                        # Put higher scores at lower level positions
                        best = (node, pos, score)
            nodes.remove(best[0])
            level[best[1]] = best[0]

    def _arrange_into_levels(self, toplevel):
        """
        Assign a level to each node.
        """
        # Mapping from node to level.
        self._nodelevel = {}
        self._levels = []

        # Find any nodes that have no incoming edges; put all of these
        # in level 0.
        if toplevel is None:
            toplevel = []
            for node in self._nodes:
                if len(self._inedges.get(node, [])) == 0:
                    toplevel.append(node)
                    self._nodelevel[node] = 0
        else:
            for node in toplevel:
                self._nodelevel[node] = 0

        # Expand all of their children.
        self._levels = [toplevel]
        self._add_descendants(toplevel, 1)

        # If we didn't get all the nodes, we'll have to start picking
        # nodes that do have incoming transitions.  Pick the ones that
        # have the most reachable nodes.  (n.b., this implementation
        # isn't terribly efficient, but we dont' expect to be
        # displaying huge graphs, so it should be ok)
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



