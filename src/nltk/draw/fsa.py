# Natural Language Toolkit: Finite Statue Automota Visualization
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Draw a finite state automoton

  - CanvasNode: a node, displayed on a canvas.
  - CanvasEdge: an edge, displayed on a canvas.
  - CanvasFSA: an FSA, displayed on a canvas.
  - FSAView: A widget showing an FSA

"""

import Tkinter, math, nltk.fsa
from nltk.draw import CanvasWidgetI, adjust_scrollregion, merge_bbox

##//////////////////////////////////////////////////////
##  Configuration constants
##//////////////////////////////////////////////////////
# These may get moved to class params eventually.

# How much extra space should we add around the FSA, to make it
# viewable.  If this were zero, then all nodes at the edges would be
# only half-visible.
VIEWBORDER = 60

# How much extra scroll-space should we provide, to let the user move
# nodes around?  This also gives a little extra room, in case some of
# the edges curve way out away from the nodes.  This is in addition to
# the view border.
SCROLLBORDER = 20

# What's the spacing between nodes, for the level-based layout?
XSPACING = 100
YSPACING = 100

# What algorithm should we use to arrange nodes into layers?  Current
# options are dfs and bfs.  I find dfs easier to read, but it can get
# long-and-narrow; bfs will tend to give shallower trees.
DEFAULT_ARRANGE = 'bfs'

# Orientation for layering: HORIZONTAL or VERTICAL
ORIENTATION = 'HORIZONTAL'


    

##//////////////////////////////////////////////////////
##  CanvasNode & CanvasEdge
##//////////////////////////////////////////////////////
# Note: CanvasNode and CanvasEdge are currently circularly dependant.

class CanvasNode(CanvasWidgetI):
    """
    A canvas widget for displaying a node in a graph.  A C{CanvasNode}
    is drawn as a labeled circle.  Each C{CanvasNode} has a location,
    a label, a set of incoming edges, and a set of outgoing edges:

      - The location specifies the coordinates of the center of the
        C{CanvasNode}'s circle.
      - The label is a C{string} that is displayed adjacent to the
        C{CanvasNode}'s circle.
      - The incoming edges is a C{list} of all C{CanvasEdge}s whose
        destination node is this C{CanvasNode}.
      - The outoing edges is a C{list} of all C{CanvasEdge}s whose
        source node is this C{CanvasNode}.

    Attributes:
      - C{nodecolor}: The fill color used to draw the node's circle
      - C{noderadius}: The radius of the node's circle
      - C{labelcolor}: The text color used to draw the node's label
      - C{labelfont}: The font used to draw the node's label
      - C{labelposition}: The position at which the node's text is
        displayed.  Valid values are 'n', 's', 'e', 'w', and 'c' (for
        north, south, east, west, and centered).
      - C{draggable}: Should the node be draggable?
    """
    # Most method docstrings are inherited from
    # nltk.draw.CanvasWidgetI. 
    def __init__(self, canvas, x, y, label, **attrs):
        """
        Construct a new C{CanvasNode}.  C{x} and C{y} specify the
        C{CanvasNode}'s location; and C{label} specifies the label to
        annotate the node with (or C{None} fo no label).
        """
        # Basic attributes
        if label is None: label = ''
        self._canvas = canvas
        self._loc = (x,y)
        self._label = label

        # Incoming and outgoing edges
        self._incoming = []
        self._outgoing = []

        # Canvas tags and tag_bind callback identifiers
        self._labeltag = None
        self._nodetag = None
        self._press_bind = None
        self._move_bind = None
        self._release_bind = None

        # Default attribute values.
        self._noderadius = 12
        self._nodecolor = None
        self._labelcolor = None
        self._labelfont = ('helvetica', 12, 'bold')
        self._labelpos = 'c'
        self._draggable = 1

        # Overridden attribute values
        for (attr, val) in attrs.items(): self[attr]=val

        # Show ourself.
        if not attrs.get('hidden', None): self.show()

    def __setitem__(self, attr, value):
        attr = attr.lower().strip()
        c = self._canvas
        if attr == 'nodecolor': self._nodecolor = value
        elif attr == 'noderadius': self._noderadius = int(value)
        elif attr == 'labelcolor': self._labelcolor = value
        elif attr == 'labelfont': self._labelfont = value
        elif attr == 'labelposition':
            if value not in 'nsewcNSEWC':
                raise ValueError('Bad labelposotion %r' % value)
            self._labelpos = value.lower()
        elif attr == 'draggable': self._draggable = value
        elif attr == 'hidden': pass
        else: raise ValueError('Unknown attribute %r' % attr)
        if not self.hidden():
            self.hide()
            self.show()

    def redraw(self): pass

    def __getitem__(self, attr):
        if attr == 'nodecolor': return self._nodecolor
        elif attr == 'noderadius': return self._noderadius
        elif attr == 'labelcolor': return self._labelcolor
        elif attr == 'labelfont': return self._labelfont
        elif attr == 'labelposition': return self._labelposition
        elif attr == 'draggable': return self._draggable
        else: raise ValueError('Unknown attribute %r' % attr)

    def bbox(self):
        if self.hidden(): return (0,0,0,0)
        bbox1 = self._canvas.bbox(self._nodetag)
        bbox2 = self._canvas.bbox(self._labeltag)
        return merge_bbox(bbox1, bbox2)

    def hidden(self):
        return self._nodetag is None
        
    def show(self):
        if not self.hidden(): return
        
        # Draw the node's circle.
        c = self._canvas
        (x, y) = self._loc
        radius = self._noderadius
        self._nodetag = c.create_oval(x-radius, y-radius,
                                      x+radius, y+radius,
                                      fill=self._nodecolor)

        # Draw the node's label.
        p = self._labelpos
        anchor = {'s':'n','n':'s','e':'w','w':'e','c':'c'}[p]
        dx = {'s':0, 'n':0, 'e':radius, 'w':-radius, 'c':0}[p]
        dy = {'s':radius, 'n':-radius, 'e':0, 'w':0, 'c':0}[p]
        justify = {'s':'c', 'n':'c', 'e':'l', 'w':'r', 'c':'c'}[p]
        self._labeltag = c.create_text(x+dx, y+dy, text=self._label,
                                       anchor=anchor, justify=justify,
                                       font=self._labelfont,
                                       fill=self._labelcolor)

        # Set up a callback for dragging nodes.
        if self._draggable:
            self._press_bind = [
                c.tag_bind(self._nodetag, '<ButtonPress-1>', self._press_cb),
                c.tag_bind(self._labeltag,'<ButtonPress-1>', self._press_cb)]

    def hide(self):
        if self.hidden(): return

        # Deregister callbacks
        if self._press_bind is not None:
            self._canvas.tag_unbind(self._nodetag, '<ButtonPress-1>',
                                    self._press_bind[0])
            self._canvas.tag_unbind(self._labeltag, '<ButtonPress-1>',
                                    self._press_bind[1])
        if self._release_bind is not None:
            self._canvas.unbind('<ButtonRelease-1>', self._release_bind)
        if self._move_bind is not None:
            self._canvas.unbind('<Motion>', self._move_bind)
        self._press_bind = self._release_bind = self._move_bind = None

        # Destroy canvas items
        self._canvas.delete(self._labeltag, self._nodetag)
        self._labeltag = self._nodetag = None

    def location(self): return self._loc
    def label(self): return self._label
    def incoming(self): return self._incoming
    def outgoing(self): return self._outgoing
    def add_incoming(self, edge): self._incoming.append(edge)
    def add_outgoing(self, edge): self._outgoing.append(edge)
    
    def move(self, newx, newy):
        if not self.hidden():
            (x,y) = self._loc
            self._canvas.move(self._nodetag, (newx-x), (newy-y))
            self._canvas.move(self._labeltag, (newx-x), (newy-y))
        self._loc = (newx, newy)
        for edge in self._incoming + self._outgoing:
            edge.redraw()

        # Make sure the node is visible.
        if not self.hidden():
            adjust_scrollregion(self._canvas, self.bbox())
            
    def _press_cb(self, event):
        self._move_bind = self._canvas.bind('<Motion>', self._motion_cb)
        self._release_bind = self._canvas.bind('<ButtonRelease-1>',
                                               self._release_cb)

        # Use the node oval's width to indicate which node we're dragging.
        self._canvas.itemconfig(self._nodetag, width=2)
        
    def _motion_cb(self, event):
        x = self._canvas.canvasx(event.x)
        y = self._canvas.canvasy(event.y)
        self.move(x, y)

    def _release_cb(self, event):
        # Deregister callback bindings.
        if self._release_bind is not None:
            self._canvas.unbind('<ButtonRelease-1>', self._release_bind)
        if self._move_bind is not None:
            self._canvas.unbind('<Motion>', self._move_bind)
        self._release_bind = self._move_bind = None
        
        # Restore the node's oval width.
        self._canvas.itemconfig(self._nodetag, width=1)

    def __repr__(self):
        return '<Node %s @%sx%s>' % (self._label, self._x, self._y)
    def __str__(self):
        return '<Node %s>' % (self._label)

class CanvasEdge(CanvasWidgetI):
    """
    Attributes:
      - C{curvature}
      - C{edgecolor}
      - C{labelcolor}
      - C{labelfont}
    """
    def __init__(self, canvas, from_node, to_node, label, **attrs):
        # Basic attributes
        self._from_node = from_node
        self._to_node = to_node
        self._label = label
        self._canvas = canvas

        # Canvas tags
        self._edgetag = None
        self._labeltag = None
        self._collapse_edges = 0

        # Default attribute values.
        self._edgecolor = None
        self._labelcolor = None
        self._labelfont = None

        # Default attribute value: curvature (??)
        other_edges = 1
        for edge in from_node.outgoing():
            if edge.to_node() is to_node: other_edges += 1
        self._curve = 0.2 * other_edges

        # Overridden attribute values
        for (attr, val) in attrs.items(): self[attr]=val

        # Show ourself.
        if not attrs.get('hidden', None): self.show()

    def hidden(self):
        return self._edgetag is None
        
    def bbox(self):
        if self.hidden(): return (0,0,0,0)
        bbox1 = self._canvas.bbox(self._edgetag)
        bbox2 = self._canvas.bbox(self._labeltag)
        return merge_bbox(bbox1, bbox2)

    def __setitem__(self, attr, value):
        attr = attr.lower().strip()
        c = self._canvas
        if attr == 'edgecolor': self._edgecolor = value
        elif attr == 'curvature': self._curve = value
        elif attr == 'labelcolor': self._labelcolor = value
        elif attr == 'labelfont': self._labelfont = value
        elif attr == 'hidden': pass
        else: raise ValueError('Unknown attribute %r' % attr)
        if not self.hidden():
            self.hide()
            self.show()

    def __getitem__(self, attr):
        if attr == 'edgecolor': return self._edgecolor
        elif attr == 'curvature': return self._curve
        elif attr == 'labelcolor': return self._labelcolor
        elif attr == 'labelfont': return self._labelfont
        else: raise ValueError('Unknown attribute %r' % attr)

    def show(self):
        if not self.hidden(): return

        kw = {'arrow':'last', 'fill':self._edgecolor, 'smooth':1}
        t = self._canvas.create_line(*self._line_coords(), **kw)
        self._edgetag = t

        (textx, texty) = self._text_coords()
        t = self._canvas.create_text(textx, texty, text=self._label,
                                     anchor='c', font=self._labelfont,
                                     fill=self._labelcolor)
        self._labeltag = t

        # Lower the edge, so the tag_binds of nodes take precedence
        self._canvas.tag_lower(self._labeltag)
        self._canvas.tag_lower(self._edgetag)

    def hide(self):
        if self.hidden(): return
        self._canvas.delete(self._edgetag, self._labeltag)
        self._edgetag = self._labeltag = None

    def _text_coords(self):
        (x1, y1) = self._from_node.location()
        (x2, y2) = self._to_node.location()
        if self._from_node is self._to_node:
            # Self-loops.  Emperically, this formula seems about
            # right, but it wasn't derived mathmatically.
            radius = self._from_node['noderadius']
            return (x1, y1 + 0.81*(150*self._curve+radius) + 10)
        else:
            # Normal edges.
            r = max(math.sqrt((x1-x2)**2 + (y1-y2)**2), 1)
            textx = (x1+x2)*0.5 + (y2-y1)*(self._curve/2 + 8/r)
            texty = (y1+y2)*0.5 - (x2-x1)*(self._curve/2 + 8/r)
                     
            return (textx, texty)
    
    def _line_coords(self):
        (x1, y1) = self._from_node.location()
        (x2, y2) = self._to_node.location()
        radius1 = self._from_node['noderadius']
        radius2 = self._to_node['noderadius']
        
        if self._from_node is self._to_node:
            # Self-loops
            x3 = x1 - 70*self._curve - radius1
            y3 = y1 + 70*self._curve + radius1
            x4 = x1
            y4 = y1 + 140*self._curve + radius1
            x5 = x1 + 70*self._curve + radius1
            y5 = y1 + 70*self._curve + radius1
            return (x1, y1, x3, y3, x4, y4, x5, y5, x1, y1)
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
            return (x1, y1, x3, y3, x2, y2)

    def from_node(self): return self._from_node
    def to_node(self): return self._to_node
    def label(self): return self._label
    def set_label(self, newlabel): self._label = newlabel
    def redraw(self):
        """
        Respond to node movement.
        """
        if self.hidden(): return
        self._canvas.coords(self._edgetag, *self._line_coords())
        self._canvas.coords(self._labeltag, *self._text_coords())
    
        # Make sure the edge is visible. 
        adjust_scrollregion(self._canvas, self.bbox())
            
    def __repr__(self):
        return '%s-->%s' % (self._from_node, self._to_node)

##//////////////////////////////////////////////////////
##  Canvas FSA
##//////////////////////////////////////////////////////
    
class CanvasFSA:
    def __init__(self, canvas, fsa, collapsed_edges = 0,
                 arrange=DEFAULT_ARRANGE):
        """
        @param collapse_edges: Should multiple edges between the same
            2 nodes be displayed as a single comma-separated edge?
        @param arrange: What arrangement algorithm should we use?
            Current options are 'dfs' and 'bfs'.
        """
        self._fsa = fsa
        self._canvas = canvas
        self._arrange = arrange.lower()

        nodes = self._nodes = {}
        edges = self._edges = []

        # Create the CanvasNodes and CanvasEdges for the FSA's states
        # and transitions.
        self._create_nodes(fsa)
        if collapsed_edges:
            self._create_collapsed_edges(fsa)
        else:
            self._create_expanded_edges(fsa)

        # Decide where to put each node.
        self.arrange()

    def _create_nodes(self, fsa):
        """
        Create CanvasNodes for each state in the given fsa.
        """
        nodes = self._nodes
        for state in fsa.states():
            node = nodes[state] = CanvasNode(self._canvas, 0, 0,
                                             str(state), hidden=1)
            if state in self._fsa._finals:
                node['nodecolor'] = 'red'
            else:
                node['nodecolor'] = 'green3'

    def _create_collapsed_edges(self, fsa):
        """
        Create CanvasEdges for each transition in the given fsa; and
        add the edges to incoming/outgoing lists for the appropriate
        edges.  This version collapses multiple edges between the same
        2 nodes into a single edge, with labels separated by commas.
        """
        edges = self._edges
        nodes = self._nodes
        for (s1, labels, s2) in fsa.transitions():
            for label in labels.elements():
                for edge in nodes[s1].outgoing():
                    if edge.to_node() is nodes[s2]:
                        edge.set_label(edge.label()+', '+label)
                        break
                else:
                    edges.append(self._make_edge(nodes[s1], nodes[s2], label))

    def _create_expanded_edges(self, fsa):
        """
        Create CanvasEdges for each transition in the given fsa; and
        add the edges to incoming/outgoing lists for the appropriate
        edges.
        """
        edges = self._edges
        nodes = self._nodes
        for (s1, labels, s2) in fsa.transitions():
            for label in labels.elements():
                edges.append(self._make_edge(nodes[s1], nodes[s2], label))

    def show(self):
        """
        Display ourself!
        """
        for node in self._nodes.values(): node.show()
        for edge in self._edges: edge.show()

    def hide(self):
        "Hide ourself"
        for node in self._nodes.values(): node.hide()
        for edge in edges: edge.hide()
        
    def _make_edge(self, node1, node2, label):
        # Handle epsilon transitions
        if label != nltk.fsa.epsilon:
            edge = CanvasEdge(self._canvas, node1, node2, label,
                              hidden=1)
            edge['edgecolor'] = 'cyan4'
            edge['labelcolor'] = 'blue4'
        else:
            edge = CanvasEdge(self._canvas, node1, node2, 'e',
                              hidden=1)
            edge['labelfont'] = ('symbol', 12)
            edge['edgecolor'] = 'gray50'
            edge['labelcolor'] = 'gray40'

        # Tell the nodes about it the edge.
        node1.add_outgoing(edge)
        node2.add_incoming(edge)
        
        return edge

    def _resize_canvas(self):
        # Adjust the canvas size...
        minx = miny = maxx = maxy = 0
        for node in self._nodes.values():
            (x, y) = node.location()
            minx = min(x, minx)
            miny = min(y, miny)
            maxx = max(x, maxx)
            maxy = max(y, maxy)

        minx -= VIEWBORDER
        miny -= VIEWBORDER
        maxx += VIEWBORDER
        maxy += VIEWBORDER
        canvas = self._canvas
        canvas['scrollregion'] = (minx-SCROLLBORDER, miny-SCROLLBORDER,
                                  maxx+SCROLLBORDER, maxy+SCROLLBORDER)
        canvas.xview('moveto', (SCROLLBORDER / (2.0 * SCROLLBORDER +
                                                maxx-minx)))
        canvas.yview('moveto', (SCROLLBORDER / (2.0 * SCROLLBORDER +
                                                maxy-miny)))
        
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

        # Now we want to minimize crossing edges.. how, again? :)
        for i in range(len(self._levels)):
            for j in range(len(self._levels[i])):
                if self._levels[i][j] is not None:
                    if ORIENTATION == 'HORIZONTAL':
                        self._levels[i][j].move(i*XSPACING, j*YSPACING)
                    elif ORIENTATION == 'VERTICAL':
                        self._levels[i][j].move(j*XSPACING, i*YSPACING)
                    else:
                        # Default to horizontal
                        self._levels[i][j].move(i*XSPACING, j*YSPACING)

        # Finally, set the canvas size appropriately
        self._resize_canvas()

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
        Arrange a given level..  This algorithm is simple and pretty heuristic.. 
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
                scores[pos][node] = 1.0/len(node.incoming())
                
            # Try to put a node at level position x if nodes
            # in previous levels at position x point to it.
            for edge in node.incoming():
                from_node = edge.from_node()
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

        nodelist = self._nodes.values()
        
        # Find any nodes that have no incoming edges; put all of these
        # in level 0.
        toplevel = []
        for node in nodelist:
            if len(node.incoming()) == 0:
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

            for node in nodelist:
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
            for edge in node.outgoing():
                self._reachable(edge.to_node(), reached)
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
            child_nodes = [edge.to_node() for edge in parent_node.outgoing()
                           if not self._nodelevel.has_key(edge.to_node())]
            if len(child_nodes) > 0:
                self._add_descendants_dfs(child_nodes, levelnum+1)

    def _add_descendants_bfs(self, parent_level, levelnum):
        frontier_nodes = []
        if levelnum >= len(self._levels): self._levels.append([])
        for parent_node in parent_level:
            child_nodes = [edge.to_node() for edge in parent_node.outgoing()]
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
            child_nodes = [edge.to_node() for edge in parent_node.outgoing()]
            child_nodes += [edge.from_node() for edge in parent_node.incoming()]
            for node in child_nodes:
                if not self._nodelevel.has_key(node):
                    self._levels[levelnum].append(node)
                    self._nodelevel[node] = levelnum
                    frontier_nodes.append(node)
        if len(frontier_nodes) > 0:
            self._add_descendants_bfs2(frontier_nodes, levelnum+1)

##//////////////////////////////////////////////////////
##  Canvas FSA Container Classes
##//////////////////////////////////////////////////////
    
class FSAFrame:
    "Widget to view FSA's."

    MINX = MINY = 60
    MAXX = 700
    MAXY = 400
    
    def __init__(self, parent, fsa, **kw):
        self._parent = parent
        self._fsa = fsa

        self._frame = frame = Tkinter.Frame(parent)
        self._canvas = canvas = Tkinter.Canvas(frame, closeenough='10.0', **kw)
        xscrollbar = Tkinter.Scrollbar(parent, orient='horizontal')
        yscrollbar = Tkinter.Scrollbar(parent, orient='vertical')
        xscrollbar['command'] = canvas.xview
        yscrollbar['command'] = canvas.yview
        canvas['xscrollcommand'] = xscrollbar.set
        canvas['yscrollcommand'] = yscrollbar.set
        
        canvas.pack(expand=1, fill='both', side='left')
        yscrollbar.pack(fill='y', side='right')
        xscrollbar.pack(fill='x', side='bottom')

        # Try using dfs; if its' big, try using bfs instead.
        self._canvas_fsa = CanvasFSA(canvas, fsa, 1, 'dfs')
        self._canvas_fsa.show()
        (x1,y1,x2,y2) = [int(n) for n in canvas['scrollregion'].split()]
        if x2-x1 > FSAFrame.MAXX:
            self._canvas_fsa.arrange('bfs')

    def pack(self, cnf={}, **kw):
        self._frame.pack(cnf, **kw)
        (minx, miny, maxx, maxy) = self._canvas['scrollregion'].split()
        self._canvas['width'] = max(FSAFrame.MINX, min(FSAFrame.MAXX,
                                            int(maxx)-int(minx)-2*SCROLLBORDER))
        self._canvas['height'] = max(FSAFrame.MINY, min(FSAFrame.MAXY,
                                             int(maxy)-int(miny)-2*SCROLLBORDER))

class FSAWindow:
    "Window to view FSA's."
    def __init__(self, fsa):
        self._top = Tkinter.Tk()
        self._top.bind('q', self.destroy)

        # Ok button.
        buttonframe = Tkinter.Frame(self._top)
        buttonframe.pack(fill='x', side='bottom')
        ok = Tkinter.Button(buttonframe, text='Done', command=self.destroy)
        ok.pack(side='left')
        help = Tkinter.Button(buttonframe, text='Help')
        help.pack(side='right')

        # FSAFrame.
        fsaframe = FSAFrame(self._top, fsa, background='white')
        fsaframe.pack(side='bottom', expand=1, fill='both')

    def destroy(self, *e):
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def mainloop(self, n=0):
        if self._top is None: return
        self._top.mainloop(n)

    def title(self, title):
        if self._top is None: return
        self._top.title(title)

# Test
if __name__ == '__main__':
    import time, random
    t = time.time()
    regexps = ['(ab(c*)c)*dea(b+)e',
               '((ab(c*))?(edc))*dea(b*)e',
               #'(((ab(c*))?(edc))+dea(b+)eabba)*',
               '(ab(c*)c)*']

    #regexps = ['(b?a)*']
    #regexps = ['ab((cdb)*)e']
    #regexps = ['(((ab(c*))?(edc))dea(b+)e)+']
    #regexps = ['((ab(c*))?(edc))*dea(b*)e']
    
    # Pick a random regexp, and draw it.
    regexp = random.choice(regexps)
    print 'trying', regexp
    fsa = nltk.fsa.FSA("abcdef")
    fsa.empty()
    nltk.fsa.re2nfa(fsa, regexp)

    # Show the NFA's FSA.
    w1 = FSAWindow(fsa)
    w1.title("FSA for: %s" % regexp)

    # Show the DFA
    dfa = fsa.dfa()
    #w2 = FSAWindow(dfa)
    #w2.title("Unpruned DFA for: %s" % regexp)
    dfa.prune()
    w3 = FSAWindow(dfa)
    w3.title("Pruned DFA for: %s" % regexp)

    # n.b., this is optional, as long as you're running this from an
    # interactive Python shell..
    Tkinter.mainloop()
