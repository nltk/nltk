# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Tools for graphically displaying and interacting with the objects and
processing classes defined by the Toolkit.  These tools are primarily
intended to help students visualize the objects that they create.
Each drawable object has a X{draw method}; calling this method on the
object will create a new window, containing a graphical representation
of the object.  In addition, this window can be used to print the
object's graphical representation to a postscript file.

Methods in the draw package should not be used directly; instead, call 
the C{draw()} member function on any drawable object.  This will
automatically dispatch to the correct method in the draw package.
"""

##//////////////////////////////////////////////////////
##  CanvasWidget
##//////////////////////////////////////////////////////

class CanvasWidgetI:
    """
    A collection of graphical elements and bindings used to display a
    complex object in a Tkinter C{Canvas}.  A canvas widget is
    responsible for managing the C{Canvas} tags and callback bindings
    necessary to display and interact with the object.

    Each canvas widget is bound to a single C{Canvas}.  This C{Canvas}
    should be specified as the first argument to the C{CanvasWidget}'s
    constructor.

    Each canvas widget is characterized by a X{bounding box}.  The
    bounding box is a tuple of four coordinates, M{(xmin, ymin, xmax,
    ymax)}, for a rectangle which encloses all of the canvas widget's
    graphical elements.  Bounding box coordinates are specified with
    respect to the C{Canvas's} coordinate space.

    Canvas widgets can be either X{hidden} or X{shown}.  Their
    graphical elements are only displayed in their C{Canvas} when they
    are shown.  By default, canvas widgets are shown when they are
    first created; but if the constructor is given the keyword
    argument "hidden" with a true value, they will be hidden when they
    are created.

    Many canvas widgets have a X{location}, which specifies M{x} and
    {y} coordinates for the displayed object.  In particular, a canvas
    widget's location specifies the position of the canvas widget's
    X{anchor}; and the location of each graphical element is defined
    with respect to this X{anchor}.  Typically, all of the graphical
    elements will be in close proximity to the anchor, and at least
    one graphical element will overlap with the anchor.  Location
    coordinates are specified with respect to the C{Canvas}'s
    coordinate space.  

    Canvas widgets that have locations should implement the methods
    C{location} and C{move}.  But note that not all canvas widgets
    have locations.  For example, C{CanvasEdge}s, which connect two
    C{CanvasNode}s, do not have locations of their own; so it would
    not make sense to try to "move" them.

    Attributes
    ==========
    Each C{CanvasWidget} can support a variety of X{attributes},
    which control how the canvas widget is displayed.  Some typical
    examples attributes are C{nodecolor}, C{labelcolor}, {leafcolor},
    C{labelfont}, and C{noderadius}.  Each attribute has a default
    value.  This default value can be overridden in the constructor,
    using keyword arguments of the form C{attribute=value}:
    
        >>> cn = CanvasNode(c, x, y, label, nodecolor='red', labelfont='blue')

    Attribute values can also be changed after a canvas widget has
    been constructed, using the C{__setitem__} operator:

        >>> cn['noderadius'] = 8

    The current value of an attribute value can be queried using the
    C{__getitem__} operator:

        >>> cn['noderadius']
        8

    Callbacks
    =========
    Some C{CanvasWidget}s support X{callback functions}, which are
    called in response to specific types of user interaction.  These
    callback functions are registered and deregisterd with X{callback
    binding methods} and X{callback unbinding methods}.  Each callback
    binding method takes a callback function, registers it, and
    returns a callback identifier.  Each callback unbinding method
    takes a callback identifier, and deregisters the corresponding
    callback.  Some common callback binding/unbinding methods are:

      - C{bind_click(cb)}: registers a callback function C{cb} that
        will be called with no arguments whenever the user clicks on
        the canvas widget.
      - C{bind_drag(cb)}: registers a callback function C{cb} that
        will be called with a location whenver the user drags the
        canvas widget to that location.
    """
    def bbox(self):
        """
        @return: A bounding box for this C{CanvasWidget}. The bounding
            box is a tuple of four coordinates, M{(xmin, ymin, xmax,
            ymax)}, for a rectangle which encloses all of the canvas
            widget's graphical elements.  Bounding box coordinates are
            specified with respect to the C{Canvas's} coordinate
            space.

            The C{bbox} method should only be called when the canvas
            widget is shown.
            
        @rtype: C{4-tuple} of C{int}s    
        """
        raise AssertionError()
        
    def hide(self):
        """
        Remove the graphical elements for this C{CanvasWidget} from
        its C{Canvas}.
        
        @rtype: C{None}
        """
        raise AssertionError()

    def show(self):
        """
        Display this C{CanvasWidget}'s graphical elements on its
        C{Canvas}.
        
        @rtype: C{None}
        """
        raise AssertionError()

    def hidden(self):
        """
        @return: true if this C{CanvasWidget} is currently hidden.
        @rtype: C{boolean}
        """
        raise AssertionError()

    def __setitem__(self, attr, value):
        """
        Set the value of the attribute C{attr} to C{value}.

        @rtype: C{None}
        """
        raise AssertionError()

    def __getitem__(self, attr):
        """
        @return: the value of the attribute C{attr}.
        @rtype: (any)
        """
        raise AssertionError()

    def redraw(self):
        """
        Check that this canvas widget is correctly displayed; and if
        it is not, then update it.  This method should be called after
        any of the objects that this canvas widget's graphical
        representation depends on are changed.
        """
        raise AssertionError()

    # [Optional Method]
    def location(self):
        """
        @return: The coordinates for this C{CanvasWidget}'s anchor, 
            as a pair of the form C{(x,y)}.
        @rtype: C{2-tuple} of C{int}
        """
        raise NotImplementedError()

    # [Optional Method]
    def move(self, newx, newy):
        """
        Move this canvas widget to the specified location.  In
        particular, move this canvas widget such that its anchor's
        location is C{(newx, newy)}.

        @rtype: C{None}
        """
        raise NotImplementedError()

##//////////////////////////////////////////////////////
##  Helpers.
##//////////////////////////////////////////////////////

def merge_bbox(bbox1, bbox2):
    """
    Given two bounding boxes, of the form C{(xmin, ymin, xmax, ymax)},
    return a new bounding box which encloses both bounding boxes.

    @return: a new bounding box that encloses C{bbox1} and C{bbox2}.
    @rtype: C{4-tuple} of C{int}
    """
    return (min(int(bbox1[0]), int(bbox2[0])),
            min(int(bbox1[1]), int(bbox2[1])),
            max(int(bbox1[2]), int(bbox2[2])),
            max(int(bbox1[3]), int(bbox2[3])))

def adjust_scrollregion(canvas, bbox):
    """
    Given a canvas and a bounding box, adjust the scrollregion of the
    canvas to include the bounding box.
    """
    scrollregion = [int(n) for n in canvas['scrollregion'].split()]
    if len(scrollregion) != 4: return
    if (bbox[0] < scrollregion[0] or bbox[1] < scrollregion[1] or
        bbox[2] > scrollregion[2] or bbox[3] > scrollregion[3]):
        scrollregion = ('%d %d %d %d' % 
                        (min(bbox[0], scrollregion[0]),
                         min(bbox[1], scrollregion[1]),
                         max(bbox[2], scrollregion[2]),
                         max(bbox[3], scrollregion[3])))
        canvas['scrollregion'] = scrollregion
