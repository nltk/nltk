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

The graphical tools are typically built using X{canvas widgets}, each
of which encapsulates the graphical elements and bindings used to
display a complex object on a Tkinter C{Canvas}.  For example, NLTK
defines canvas widgets for displaying trees and directed graphs, as
well as a number of simpler widgets.  These canvas widgets make it
easier to build new graphical tools and demos.  See the class
documentation for C{CanvasWidget} for more information.

The C{nltk.draw} module defines the abstract C{CanvasWidget} base
class, and a number of simple canvas widgets.  The remaining canvas
widgets are defined by submodules, such as C{nltk.draw.tree}.

The C{nltk.draw} module also defines C{CanvasFrame}, which
encapsulates a C{Canvas} and its scrollbars.  It uses a
C{ScrollWatcherWidget} to ensure that all canvas widgets contained on
its canvas are within the scroll region.

Acknowledgements: Many of the ideas behind the canvas widget system
are derived from C{CLIG}, a Tk-based grapher for linguistic data
structures.  For more information, see the CLIG homepage at::

    http://www.ags.uni-sb.de/~konrad/clig.html

"""

from Tkinter import *

__all__ = (
    'CanvasFrame', 'CanvasWidget',
    
    'TextWidget', 'BoxWidget', 'OvalWidget',
    'ParenWidget', 'BracketWidget',
    'SequenceWidget', 'StackWidget', 'SpaceWidget',
    'ScrollWatcherWidget', 'AbstractContainerWidget',
    )

##//////////////////////////////////////////////////////
##  CanvasWidget
##//////////////////////////////////////////////////////

class CanvasWidget:
    """
    A collection of graphical elements and bindings used to display a
    complex object on a Tkinter C{Canvas}.  A canvas widget is
    responsible for managing the C{Canvas} tags and callback bindings
    necessary to display and interact with the object.  Canvas widgets
    are often organized into hierarchies, where parent canvas widgets
    control aspects of their child widgets.

    Each canvas widget is bound to a single C{Canvas}.  This C{Canvas}
    is specified as the first argument to the C{CanvasWidget}'s
    constructor.

    Attributes
    ==========
    Each canvas widget can support a variety of X{attributes}, which
    control how the canvas widget is displayed.  Some typical examples
    attributes are C{color}, C{font}, and C{radius}.  Each attribute
    has a default value.  This default value can be overridden in the
    constructor, using keyword arguments of the form
    C{attribute=value}:
    
        >>> cn = CanvasText(c, 'test', color='red')

    Attribute values can also be changed after a canvas widget has
    been constructed, using the C{__setitem__} operator:

        >>> cn['font'] = 'times'

    The current value of an attribute value can be queried using the
    C{__getitem__} operator:

        >>> cn['color']
        red

    For a list of the attributes supported by a type of canvas widget,
    see its class documentation.
    
    Interaction
    ===========
    The attribute C{'draggable'} controls whether the user can drag a
    canvas widget around the canvas.  By default, canvas widgets
    are not draggable.
    
    C{CanvasWidget} provides callback support for two types of user
    interaction: clicking and dragging.  The method C{bind_click}
    registers a callback function that is called whenever the canvas
    widget is clicked.  The method C{bind_drag} registers a callback
    function that is called after the canvas widget is dragged.  If
    the user clicks or drags a canvas widget with no registered
    callback function, then the interaction event will propagate to
    its parent.  For each canvas widget, only one callback function
    may be registered for an interaction event.  Callback functions
    can be deregistered with the C{unbind_click} and C{unbind_drag}
    methods. 

    Subclassing
    ===========
    C{CanvasWidget} is an abstract class.  Subclasses are required to
    implement the following methods:

      - C{__init__}: Builds a new canvas widget.  It must perform the
        following three tasks (in order):
          - Create any new graphical elements.
          - Call C{_add_child_widget} on each child widget.
          - Call the C{CanvasWidget} constructor.
      - C{_tags}: Returns a list of the canvas tags for all graphical
        elements managed by this canvas widget, not including
        graphical elements managed by its child widgets.
      - C{_manage}: Arranges the child widgets of this canvas widget.
        This is typically only called when the canvas widget is
        created.
      - C{_update}: Update this canvas widget in response to a
        change in a single child.

    For C{CanvasWidget}s with no child widgets, the default
    definitions for C{_manage} and C{_update} may be used.

    If a subclass defines any attributes, then it should implement
    C{__getitem__} and C{__setitem__}.  If either of these methods is
    called with an unknown attribute, then they should propagate the
    request to C{CanvasWidget}.

    Most subclasses implement a number of additional methods that
    modify the C{CanvasWidget} in some way.  These methods must call
    C{parent.update(self)} after making any changes to the canvas
    widget's graphical elements.  The canvas widget must also call
    C{parent.update(self)} after changing any attribute value that
    affects the shape or position of the canvas widget's graphical
    elements.

    @type __canvas: C{Tkinter.Canvas}
    @ivar __canvas: This C{CanvasWidget}'s canvas.

    @type __parent: C{CanvasWidget} or C{None}
    @ivar __parent: This C{CanvasWidget}'s hierarchical parent widget.
    @type __children: C{list} of C{CanvasWidget}
    @ivar __children: This C{CanvasWidget}'s hierarchical child widgets.

    @type __updating: C{boolean}
    @ivar __updating: Is this canvas widget currently performing an
        update?  If it is, then it will ignore any new update requests
        from child widgets.

    @type __draggable: C{boolean}
    @ivar __draggable: Is this canvas widget draggable?
    @type __press: C{event}
    @ivar __press: The ButtonPress event that we're currently handling.
    @type __drag_x: C{int}
    @ivar __drag_x: Where it's been moved to (to find dx)
    @type __drag_y: C{int}
    @ivar __drag_y: Where it's been moved to (to find dy)
    @type __callbacks: C{dictionary}
    @ivar __callbacks: Registered callbacks.  Currently, four keys are
        used: C{1}, C{2}, C{3}, and C{'drag'}.  The values are
        callback functions.  Each callback function takes a single
        argument, which is the C{CanvasWidget} that triggered the
        callback. 
    """
    def __init__(self, canvas, parent=None, **attribs):
        """
        Create a new canvas widget.  This constructor should only be
        called by subclass constructors; and it should be called only
        X{after} the subclass has constructed all graphical canvas
        objects and registered all child widgets.

        @param canvas: This canvas widget's canvas.
        @type canvas: C{Tkinter.Canvas}
        @param parent: This canvas widget's hierarchical parent.
        @type parent: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self.__canvas = canvas
        self.__parent = parent
        if not hasattr(self, '_CanvasWidget__children'): self.__children = []

        # Update control (prevents infinite loops)
        self.__updating = 0

        # Button-press and drag callback handling.
        self.__press = None
        self.__drag_x = self.__drag_y = 0
        self.__callbacks = {}
        self.__draggable = 0

        # Set up attributes.
        for (attr, value) in attribs.items(): self[attr] = value

        # Manage this canvas widget
        self._manage()

        # Register any new bindings
        for tag in self._tags():
            self.__canvas.tag_bind(tag, '<ButtonPress-1>',
                                   self.__press_cb)
            self.__canvas.tag_bind(tag, '<ButtonPress-2>',
                                   self.__press_cb)
            self.__canvas.tag_bind(tag, '<ButtonPress-3>',
                                   self.__press_cb)

    ##//////////////////////////////////////////////////////
    ##  Inherited methods.
    ##//////////////////////////////////////////////////////

    def bbox(self):
        """
        @return: A bounding box for this C{CanvasWidget}. The bounding
            box is a tuple of four coordinates, M{(xmin, ymin, xmax,
            ymax)}, for a rectangle which encloses all of the canvas
            widget's graphical elements.  Bounding box coordinates are
            specified with respect to the C{Canvas}'s coordinate
            space.
        @rtype: C{4-tuple} of C{int}s    
        """
        if len(self.tags()) == 0: raise ValueError('No tags')
        return self.__canvas.bbox(*self.tags())

    def width(self):
        """
        @return: The width of this canvas widget's bounding box, in
            its C{Canvas}'s coordinate space.
        @rtype: C{int}
        """
        if len(self.tags()) == 0: raise ValueError('No tags')
        bbox = self.__canvas.bbox(*self.tags())
        return bbox[2]-bbox[0]

    def height(self):
        """
        @return: The height of this canvas widget's bounding box, in
            its C{Canvas}'s coordinate space.
        @rtype: C{int}
        """
        if len(self.tags()) == 0: raise ValueError('No tags')
        bbox = self.__canvas.bbox(*self.tags())
        return bbox[3]-bbox[1]
        
    def parent(self):
        """
        @return: The hierarchical parent of this canvas widget.  
            C{self} is considered a subpart of its parent for
            purposes of user interaction.
        @rtype: C{CanvasWidget} or C{None}
        """
        return self.__parent

    def child_widgets(self):
        """
        @return: A list of the hierarchical children of this canvas
            widget.  These children are considered part of C{self}
            for purposes of user interaction.
        @rtype: C{list} of C{CanvasWidget}
        """
        return self.__children

    def canvas(self):
        """
        @return: The canvas that this canvas widget is bound to.
        @rtype: C{Tkinter.Canvas}
        """
        return self.__canvas

    def move(self, dx, dy):
        """
        Move this canvas widget by a given distance.  In particular,
        shift the canvas widget right by C{dx} pixels, and down by
        C{dy} pixels.  Both C{dx} and C{dy} may be negative, resulting
        in leftward or upward movement.

        @type dx: C{int}
        @param dx: The number of pixels to move this canvas widget
            rightwards.
        @type dy: C{int}
        @param dy: The number of pixels to move this canvas widget
            downwards.
        @rtype: C{None}
        """
        if dx == dy == 0: return
        for tag in self.tags():
            self.__canvas.move(tag, dx, dy)
        if self.__parent: self.__parent.update(self)

    def destroy(self):
        """
        Remove this C{CanvasWidget} from its C{Canvas}.  After a
        C{CanvasWidget} has been destroyed, it should not be accessed.

        Note that you only need to destroy a top-level
        C{CanvasWidget}; its child widgets will be destroyed
        automatically.  If you destroy a non-top-level
        C{CanvasWidget}, then the entire top-level widget will be
        destroyed.

        @raise ValueError: if this C{CanvasWidget} has a parent.
        @rtype: C{None}
        """
        if self.__parent is not None:
            self.__parent.destroy()
            return
        
        for tag in self.tags():
            self.__canvas.tag_unbind(tag, '<ButtonPress-1>')
            self.__canvas.tag_unbind(tag, '<ButtonPress-2>')
            self.__canvas.tag_unbind(tag, '<ButtonPress-3>')
        self.__canvas.delete(*self.tags())
        self.__canvas = None

    def update(self, child):
        """
        Update the graphical display of this canvas widget, and all of
        its ancestors, in response to a change in one of this canvas
        widget's children.

        @param child: The child widget that changed.
        @type child: C{CanvasWidget}
        """
        # If we're already updating, then do nothing.  This prevents
        # infinite loops when _update modifies its children.
        if self.__updating: return
        self.__updating = 1

        # Update this CanvasWidget.
        self._update(child)

        # Propagate update request to the parent.
        if self.__parent: self.__parent.update(self)

        # We're done updating.
        self.__updating = 0

    def manage(self):
        """
        Arrange this canvas widget and all of its descendants.
        
        @rtype: C{None}
        """
        for child in self.__children: child.manage()
        self._manage()

    def tags(self):
        """
        @return: a list of the canvas tags for all graphical
            elements managed by this canvas widget, including
            graphical elements managed by its child widgets.
        @rtype: C{list} of C{int}
        """
        if self.__canvas is None:
            raise ValueError('Attempt to access a destroyed canvas widget')
        tags = []
        tags += self._tags()
        for child in self.__children:
            tags += child.tags()
        return tags

    def __setitem__(self, attr, value):
        """
        Set the value of the attribute C{attr} to C{value}.  See the
        class documentation for a list of attributes supported by this
        canvas widget.

        @rtype: C{None}
        """
        if attr == 'draggable':
            self.__draggable = value
        else:
            raise ValueError('Unknown attribute %r' % attr)

    def __getitem__(self, attr):
        """
        @return: the value of the attribute C{attr}.  See the class
            documentation for a list of attributes supported by this
            canvas widget.
        @rtype: (any)
        """
        if attr == 'draggable':
            return self.__draggable
        else:
            raise ValueError('Unknown attribute %r' % attr)

    def __repr__(self):
        """
        @return: a string representation of this canvas widget.
        @rtype: C{string}
        """
        return '<%s>' % self.__class__.__name__

    ##//////////////////////////////////////////////////////
    ##  Callback interface
    ##//////////////////////////////////////////////////////

    def bind_click(self, callback, button=1):
        """
        Register a new callback that will be called whenever this
        C{CanvasWidget} is clicked on.

        @type callback: C{function}
        @param callback: The callback function that will be called
            whenever this C{CanvasWidget} is clicked.  This function
            will be called with this C{CanvasWidget} as its argument.
        @type button: C{int}
        @param button: Which button the user should use to click on
            this C{CanvasWidget}.  Typically, this should be 1 (left
            button), 3 (right button), or 2 (middle button).
        """
        self.__callbacks[button] = callback
        
    def bind_drag(self, callback):
        """
        Register a new callback that will be called after this
        C{CanvasWidget} is dragged.  This implicitly makes this
        C{CanvasWidget} draggable.

        @type callback: C{function}
        @param callback: The callback function that will be called
            whenever this C{CanvasWidget} is clicked.  This function
            will be called with this C{CanvasWidget} as its argument.
        """
        self.__draggable = 1
        self.__callbacks['drag'] = callback

    def unbind_click(self, button=1):
        """
        Remove a callback that was registered with C{bind_click}.

        @type button: C{int}
        @param button: Which button the user should use to click on
            this C{CanvasWidget}.  Typically, this should be 1 (left
            button), 3 (right button), or 2 (middle button).
        """
        try: del self.__callbacks[button]
        except: pass

    def unbind_drag(self):
        """
        Remove a callback that was registered with C{bind_drag}.
        """
        try: del self.__callbacks['drag']
        except: pass
        
    ##//////////////////////////////////////////////////////
    ##  Callback internals
    ##//////////////////////////////////////////////////////

    def __press_cb(self, event):
        """
        Handle a button-press event:
          - record the button press event in C{self.__press}
          - register a button-release callback.
          - if this CanvasWidget or any of its ancestors are
            draggable, then register the appropriate motion callback.
        """
        # If we're already waiting for a button release, then ignore
        # this new button press.
        if (self.__canvas.bind('<ButtonRelease-1>') or
            self.__canvas.bind('<ButtonRelease-2>') or
            self.__canvas.bind('<ButtonRelease-3>')):
            return

        # Unbind motion (just in case; this shouldn't be necessary)
        self.__canvas.unbind('<Motion>')

        # Record the button press event.
        self.__press = event

        # If any ancestor is draggable, set up a motion callback.
        # (Only if they pressed button number 1)
        if event.num == 1:
            widget = self
            while widget is not None:
                if widget['draggable']:
                    widget.__start_drag(event)
                    break
                widget = widget.parent()

        # Set up the button release callback.
        self.__canvas.bind('<ButtonRelease-%d>' % event.num,
                          self.__release_cb)

    def __start_drag(self, event):
        """
        Begin dragging this object:
          - register a motion callback
          - record the drag coordinates
        """
        self.__canvas.bind('<Motion>', self.__motion_cb)
        self.__drag_x = event.x
        self.__drag_y = event.y
        
    def __motion_cb(self, event):
        """
        Handle a motion event:
          - move this object to the new location
          - record the new drag coordinates
        """
        self.move(event.x-self.__drag_x, event.y-self.__drag_y)
        self.__drag_x = event.x
        self.__drag_y = event.y

    def __release_cb(self, event):
        """
        Handle a release callback:
          - unregister motion & button release callbacks.
          - decide whether they clicked, dragged, or cancelled
          - call the appropriate handler.
        """
        # Unbind the button release & motion callbacks.
        self.__canvas.unbind('<ButtonRelease-%d>' % event.num)
        self.__canvas.unbind('<Motion>')
        
        # Is it a click or a drag?
        if (event.time - self.__press.time < 100 and
            abs(event.x-self.__press.x) + abs(event.y-self.__press.y) < 5):
            # Move it back, if we were dragging.
            if self.__draggable and event.num == 1:
                self.move(self.__press.x - self.__drag_x,
                          self.__press.y - self.__drag_y)
            self.__click(event.num)
        elif event.num == 1:
            self.__drag()

        self.__press = None

    def __drag(self):
        """
        If this C{CanvasWidget} has a drag callback, then call it;
        otherwise, find the closest ancestor with a drag callback, and
        call it.  If no ancestors have a drag callback, do nothing.
        """
        if self.__draggable:
            if self.__callbacks.has_key('drag'):
                cb = self.__callbacks['drag']
                try:
                    cb(self)
                except:
                    print 'Error in drag callback for %r' % self
        elif self.__parent is not None:
            self.__parent.__drag()

    def __click(self, button):
        """
        If this C{CanvasWidget} has a drag callback, then call it;
        otherwise, find the closest ancestor with a click callback, and
        call it.  If no ancestors have a click callback, do nothing.
        """
        if self.__callbacks.has_key(button):
            cb = self.__callbacks[button]
            #try:
            cb(self)
            #except:
            #    print 'Error in click callback for %r' % self
            #    raise
        elif self.__parent is not None:
            self.__parent.__click(button)
            
    ##//////////////////////////////////////////////////////
    ##  Child/parent Handling
    ##//////////////////////////////////////////////////////

    def _add_child_widget(self, child):
        """
        Register a hierarchical child widget.  The child will be
        considered part of this canvas widget for purposes of user
        interaction.  C{_add_child_widget} has two direct effects:
          - It sets C{child}'s parent to this canvas widget.
          - It adds C{child} to the list of canvas widgets returned by
            the C{child_widgets} member function.

        @param child: The new child widget.  C{child} must not already
            have a parent.
        @type child: C{CanvasWidget}
        """
        if not hasattr(self, '_CanvasWidget__children'): self.__children = []
        if child.__parent is not None:
            raise ValueError('%s already has a parent', child)
        child.__parent = self
        self.__children.append(child)
        
    def _remove_child_widget(self, child):
        """
        Remove a hierarchical child widget.  This child will no longer
        be considered part of this canvas widget for purposes of user
        interaction.  C{_add_child_widget} has two direct effects:
          - It sets C{child}'s parent to C{None}.
          - It removes C{child} from the list of canvas widgets
            returned by the C{child_widgets} member function.

        @param child: The child widget to remove.  C{child} must be a
            child of this canvas widget.
        @type child: C{CanvasWidget}
        """
        self.__children.remove(child)
        child.__parent = None

    ##//////////////////////////////////////////////////////
    ##  Defined by subclass
    ##//////////////////////////////////////////////////////

    def _tags(self):
        """
        @return: a list of canvas tags for all graphical elements
            managed by this canvas widget, not including graphical
            elements managed by its child widgets.
        @rtype: C{list} of C{int}
        """
        raise AssertionError()

    def _manage(self):
        """
        Arrange the child widgets of this canvas widget.  This method
        is called when the canvas widget is initially created.  It is
        also called if the user calls the C{manage} method on this
        canvas widget or any of its ancestors.
        
        @rtype: C{None}
        """
        pass
        
    def _update(self, child):
        """
        Update this canvas widget in response to a change in one of
        its children.

        @param child: The child that changed.
        @type child: C{CanvasWidget}
        @rtype: C{None}
        """
        pass

##//////////////////////////////////////////////////////
##  Basic widgets.
##//////////////////////////////////////////////////////

class TextWidget(CanvasWidget):
    """
    A canvas widget that displays a single string of text.

    Attributes:
      - C{color}: the color of the text.
      - C{font}: the font used to display the text.
      - C{justify}: justification for multi-line texts.  Valid values
        are C{left}, C{center}, and C{right}.
      - C{width}: the width of the text.  If the text is wider than
        this width, it will be line-wrapped at whitespace.
      - C{draggable}: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, text, **attribs):
        """
        Create a new text widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @type text: C{string}
        @param text: The string of text to display.
        @param attribs: The new canvas widget's attributes.
        """
        self._text = text
        self._tag = canvas.create_text(0, 0, text=text)
        CanvasWidget.__init__(self, canvas, **attribs)
            
    def __setitem__(self, attr, value):
        if attr in ('color', 'font', 'justify', 'width'):
            if attr == 'color': attr = 'fill'
            self.canvas().itemconfig(self._tag, {attr:value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'width':
            return int(self.canvas().itemcget(self._tag, attr))
        elif attr in ('color', 'font', 'justify'):
            if attr == 'color': attr = 'fill'
            return self.canvas().itemcget(self._tag, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return [self._tag]

    def text(self):
        """
        @return: The text displayed by this text widget.
        @rtype: C{string}
        """
        return self.canvas().itemcget(self._tag, 'text')
    
    def set_text(self, text):
        """
        Change the text that is displayed by this text widget.

        @type text: C{string}
        @param text: The string of text to display.
        @rtype: C{None}
        """
        self.canvas().itemconfig(self._tag, text=text)
        self.parent().update(self)

    def __repr__(self):
        return '[Text: %r]' % self._text

class AbstractContainerWidget(CanvasWidget):
    """
    An abstract class for canvas widgets that contain a single child,
    such as C{CanvasBox} and C{CanvasOval}.  Subclasses must define
    a constructor, which should create any new graphical elements and
    then call the C{AbstractCanvasContainer} constructor.  Subclasses
    must also define the C{_update} method and the C{_tags} method;
    and any subclasses that define attributes should define
    C{__setitem__} and C{__getitem__}.
    """
    def __init__(self, canvas, child, **attribs):
        """
        Create a new container widget.  This constructor should only
        be called by subclass constructors.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param child: The container's child widget.  C{child} must not
            have a parent.
        @type child: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def _manage(self):
        self._update(self._child)

    def child(self):
        """
        @return: The child widget contained by this container widget.
        @rtype: C{CanvasWidget}
        """
        return self._child

    def set_child(self, child):
        """
        Change the child widget contained by this container widget.

        @param child: The new child widget.  C{child} must not have a
            parent.  
        @type child: C{CanvasWidget}
        @rtype: C{None}
        """
        self._remove_child_widget(self._child)
        self._add_child_widget(child)
        self._child = child
        self.update(child)

    def __repr__(self):
        name = self.__class__.__name__
        if name[-6:] == 'Widget': name = name[:-6]
        return '[%s: %r]' % (name, self._child)
    
class BoxWidget(AbstractContainerWidget):
    """
    A canvas widget that places a box around a child widget.

    Attributes:
      - C{fill}: The color used to fill the interior of the box.
      - C{outline}: The color used to draw the outline of the box.
      - C{width}: The width of the outline of the box.
      - C{margin}: The number of pixels space left between the child
        and the box.
      - C{draggable}: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, child, **attribs):
        """
        Create a new box widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param child: The child widget.  C{child} must not have a
            parent. 
        @type child: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._margin = 1
        self._box = canvas.create_rectangle(0,0,0,0)
        canvas.tag_lower(self._box)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)
        
    def __setitem__(self, attr, value):
        if attr == 'margin': self._margin = value
        elif attr in ('outline', 'fill', 'width'):
            self.canvas().itemconfig(self._box, {attr:value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'margin': return self._margin
        elif attr == 'width':
            return float(self.canvas().itemcget(self._box, attr))
        elif attr in ('outline', 'fill', 'width'):
            return self.canvas().itemcget(self._box, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        margin = self._margin + self['width']/2
        self.canvas().coords(self._box, x1-margin, y1-margin,
                             x2+margin, y2+margin)

    def _tags(self): return [self._box]

class OvalWidget(AbstractContainerWidget):
    """
    A canvas widget that places a oval around a child widget.

    Attributes:
      - C{fill}: The color used to fill the interior of the oval.
      - C{outline}: The color used to draw the outline of the oval.
      - C{width}: The width of the outline of the oval.
      - C{margin}: The number of pixels space left between the child
        and the oval.
      - C{draggable}: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, child, **attribs):
        """
        Create a new oval widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param child: The child widget.  C{child} must not have a
            parent. 
        @type child: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._margin = 1
        self._oval = canvas.create_oval(0,0,0,0)
        canvas.tag_lower(self._oval)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)
        
    def __setitem__(self, attr, value):
        if attr == 'margin': self._margin = value
        elif attr in ('outline', 'fill', 'width'):
            self.canvas().itemconfig(self._oval, {attr:value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'margin': return self._margin
        elif attr == 'width':
            return float(self.canvas().itemcget(self._oval, attr))
        elif attr in ('outline', 'fill', 'width'):
            return self.canvas().itemcget(self._oval, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    # The ratio between inscribed & circumscribed ovals
    RATIO = 1.4142135623730949
    
    def _update(self, child):
        R = OvalWidget.RATIO
        (x1, y1, x2, y2) = child.bbox()
        margin = self._margin + self['width']/2
        left = ( x1*(1+R) + x2*(1-R) ) / 2 - margin
        right = ( x1*(1-R) + x2*(1+R) ) / 2 + margin
        top = ( y1*(1+R) + y2*(1-R) ) / 2 - margin
        bot = ( y1*(1-R) + y2*(1+R) ) / 2 + margin
        self.canvas().coords(self._oval, left, top, right, bot)

    def _tags(self): return [self._oval]

class ParenWidget(AbstractContainerWidget):
    """
    A canvas widget that places a pair of parenthases around a child
    widget. 

    Attributes:
      - C{color}: The color used to draw the parenthases.
      - C{width}: The width of the parenthases.
      - C{draggable}: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, child, **attribs):
        """
        Create a new parenthasis widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param child: The child widget.  C{child} must not have a
            parent. 
        @type child: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._oparen = canvas.create_arc(0,0,0,0, style='arc',
                                         start=90, extent=180)
        self._cparen = canvas.create_arc(0,0,0,0, style='arc',
                                         start=-90, extent=180)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)
        
    def __setitem__(self, attr, value):
        if attr == 'color':
            self.canvas().itemconfig(self._oparen, outline=value)
            self.canvas().itemconfig(self._cparen, outline=value)
        elif attr == 'width':
            self.canvas().itemconfig(self._oparen, width=value)
            self.canvas().itemconfig(self._cparen, width=value)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'color':
            return self.canvas().itemcget(self._oparen, 'outline')
        elif attr == 'width':
            return self.canvas().itemcget(self._oparen, 'width')
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        width = max((y2-y1)/6, 4)
        self.canvas().coords(self._oparen, x1-width, y1, x1+width, y2)
        self.canvas().coords(self._cparen, x2-width, y1, x2+width, y2)

    def _tags(self): return [self._oparen, self._cparen]

class BracketWidget(AbstractContainerWidget):
    """
    A canvas widget that places a pair of brackets around a child
    widget. 

    Attributes:
      - C{color}: The color used to draw the brackets.
      - C{width}: The width of the brackets.
      - C{draggable}: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, child, **attribs):
        """
        Create a new bracket widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param child: The child widget.  C{child} must not have a
            parent. 
        @type child: C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._child = child
        self._obrack = canvas.create_line(0,0,0,0,0,0,0,0)
        self._cbrack = canvas.create_line(0,0,0,0,0,0,0,0)
        AbstractContainerWidget.__init__(self, canvas, child, **attribs)
        
    def __setitem__(self, attr, value):
        if attr == 'color':
            self.canvas().itemconfig(self._obrack, fill=value)
            self.canvas().itemconfig(self._cbrack, fill=value)
        elif attr == 'width':
            self.canvas().itemconfig(self._obrack, width=value)
            self.canvas().itemconfig(self._cbrack, width=value)
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'color':
            return self.canvas().itemcget(self._obrack, 'outline')
        elif attr == 'width':
            return self.canvas().itemcget(self._obrack, 'width')
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _update(self, child):
        (x1, y1, x2, y2) = child.bbox()
        width = max((y2-y1)/8, 2)
        self.canvas().coords(self._obrack, x1, y1, x1-width, y1,
                             x1-width, y2, x1, y2)
        self.canvas().coords(self._cbrack, x2, y1, x2+width, y1,
                             x2+width, y2, x2, y2)

    def _tags(self): return [self._obrack, self._cbrack]

class SequenceWidget(CanvasWidget):
    """
    A canvas widget that keeps a list of canvas widgets in a
    horizontal line.

    Attributes:
      - C{align}: The vertical alignment of the children.  Possible
        values are C{'top'}, C{'center'}, and C{'bottom'}.  By
        default, children are center-aligned.
      - C{space}: The amount of horizontal space to place between
        children.  By default, one pixel of space is used.
    """
    def __init__(self, canvas, *children, **attribs):
        """
        Create a new sequence widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param children: The widgets that should be aligned
            horizontally.  Each child must not have a parent.
        @type children: C{list} of C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._align = 'center'
        self._space = 1
        self._children = list(children)
        for child in children: self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == 'align':
            if value not in ('top', 'bottom', 'center'):
                raise ValueError('Bad alignment: %r' % value)
            self._align = value
        elif attr == 'space': self._space = value
        else: CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'align': return value
        elif attr == 'space': return self._space
        else: return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return []

    def _manage(self):
        if len(self._children) == 0: return
        self._update(self._children[0])

    def _yalign(self, top, bot):
        if self._align == 'top': return top
        if self._align == 'bottom': return bot
        if self._align == 'center': return (top+bot)/2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        y = self._yalign(top, bot)

        index = self._children.index(child)

        # Line up children to the right of child.
        x = right + self._space
        for i in range(index+1, len(self._children)):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x-x1, y-self._yalign(y1,y2))
            x += x2-x1 + self._space
        
        # Line up children to the left of child.
        x = left - self._space
        for i in range(index-1, -1, -1):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x-x2, y-self._yalign(y1,y2))
            x -= x2-x1 + self._space
        
class StackWidget(CanvasWidget):
    """
    A canvas widget that keeps a list of canvas widgets in a vertical
    line.

    Attributes:
      - C{align}: The horizontal alignment of the children.  Possible
        values are C{'left'}, C{'center'}, and C{'right'}.  By
        default, children are center-aligned.
      - C{space}: The amount of vertical space to place between
        children.  By default, one pixel of space is used.
    """
    def __init__(self, canvas, *children, **attribs):
        """
        Create a new stack widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @param children: The widgets that should be aligned
            vertically.  Each child must not have a parent.
        @type children: C{list} of C{CanvasWidget}
        @param attribs: The new canvas widget's attributes.
        """
        self._align = 'center'
        self._space = 1
        self._children = list(children)
        for child in children: self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == 'align':
            if value not in ('left', 'right', 'center'):
                raise ValueError('Bad alignment: %r' % value)
            self._align = value
        elif attr == 'space': self._space = value
        else: CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'align': return value
        elif attr == 'space': return self._space
        else: return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return []

    def _manage(self):
        if len(self._children) == 0: return
        self._update(self._children[0])

    def _xalign(self, left, right):
        if self._align == 'left': return left
        if self._align == 'right': return right
        if self._align == 'center': return (left+right)/2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        x = self._xalign(left, right)

        index = self._children.index(child)

        # Line up children below the child.
        y = bot + self._space
        for i in range(index+1, len(self._children)):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x-self._xalign(x1,x2), y-y1)
            y += y2-y1 + self._space
        
        # Line up children above the child.
        y = top - self._space
        for i in range(index-1, -1, -1):
            (x1, y1, x2, y2) = self._children[i].bbox()
            self._children[i].move(x-self._xalign(x1,x2), y-y2)
            y -= y2-y1 + self._space

class SpaceWidget(CanvasWidget):
    """
    A canvas widget that takes up space but does not display
    anything.  C{SpaceWidget}s can be used to add space between
    elements.  Each space widget is characterized by a width and a
    height.  If you wish to only create horizontal space, then use a
    height of zero; and if you wish to only create vertical space, use
    a width of zero.
    """
    def __init__(self, canvas, width, height, **attribs):
        """
        Create a new space widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @type width: C{int}
        @param width: The width of the new space widget.
        @type height: C{int}
        @param height: The height of the new space widget.
        @param attribs: The new canvas widget's attributes.
        """
        self._tag = canvas.create_line(0, 0, width, height, fill='')
        CanvasWidget.__init__(self, canvas, **attribs)

    # note: width() and height() are already defined by CanvasWidget.
    def set_width(self, width):
        """
        Change the width of this space widget.

        @param width: The new width.
        @type width: C{int}
        @rtype: C{None}
        """
        [x1, y1, x2, y2] = self._tag.bbox()
        self._canvas.coords(self._tag, x1, y1, x1+width, y2)

    def set_height(self, height):
        """
        Change the height of this space widget.

        @param height: The new height.
        @type height: C{int}
        @rtype: C{None}
        """
        [x1, y1, x2, y2] = self._tag.bbox()
        self._canvas.coords(self._tag, x1, y1, x2, y1+height)
        
    def _tags(self): return [self._tag]
    
    def __repr__(self): return '[Space]'

class ScrollWatcherWidget(CanvasWidget):
    """
    A special canvas widget that adjusts its C{Canvas}'s scrollregion
    to always include the bounding boxes of all of its children.  The
    scroll-watcher widget will only increase the size of the
    C{Canvas}'s scrollregion; it will never decrease it.
    """
    def __init__(self, canvas, *children, **attribs):
        """
        Create a new scroll-watcher widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @type children: C{list} of C{CanvasWidget}
        @param children: The canvas widgets watched by the
            scroll-watcher.  The scroll-watcher will ensure that these
            canvas widgets are always contained in their canvas's
            scrollregion.
        @param attribs: The new canvas widget's attributes.
        """
        for child in children: self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def add_child(self, canvaswidget):
        """
        Add a new canvas widget to the scroll-watcher.  The
        scroll-watcher will ensure that the new canvas widget is
        always contained in its canvas's scrollregion.

        @param canvaswidget: The new canvas widget.
        @type canvaswidget: C{CanvasWidget}
        @rtype: C{None}
        """
        self._add_child_widget(canvaswidget)
        self.update(canvaswidget)

    def remove_child(self, canvaswidget):
        """
        Remove a canvas widget from the scroll-watcher.  The
        scroll-watcher will no longer ensure that the new canvas
        widget is always contained in its canvas's scrollregion.
        
        @param canvaswidget: The canvas widget to remove.
        @type canvaswidget: C{CanvasWidget}
        @rtype: C{None}
        """
        self._remove_child_widget(canvaswidget)

    def _tags(self): return []

    def _update(self, child):
        self._adjust_scrollregion()

    def _adjust_scrollregion(self):
        """
        Adjust the scrollregion of this scroll-watcher's C{Canvas} to
        include the bounding boxes of all of its children.
        """
        bbox = self.bbox()
        canvas = self.canvas()
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
        
##//////////////////////////////////////////////////////
##  Canvas Frame
##//////////////////////////////////////////////////////

class CanvasFrame:
    """
    A C{Tkinter} frame containing a canvas and scrollbars.
    C{CanvasFrame} uses a C{ScrollWatcherWidget} to ensure that all of
    the canvas widgets contained on its canvas are within its
    scrollregion.  In order for C{CanvasFrame} to make these checks,
    all canvas widgets must be registered with C{add_widget} when they
    are added to the canvas; and destroyed with C{destroy_widget} when
    they are no longer needed.

    If a C{CanvasFrame} is created with no parent, then it will create
    its own main window, including a "Done" button and a "Print"
    button.
    """
    def __init__(self, parent=None, **kw):
        """
        Create a new C{CanvasFrame}.

        @type parent: C{Tkinter.BaseWidget} or C{Tkinter.Tk}
        @param parent: The parent C{Tkinter} widget.  If no parent is 
            specified, then C{CanvasFrame} will create a new main
            window.
        @param kw: Keyword arguments for the new C{Canvas}.  See the
            documentation for C{Tkinter.Canvas} for more information.
        """
        # If no parent was given, set up a top-level window.
        if parent is None:
            self._parent = Tk()
            self._parent.title('NLTK')
            self._parent.bind('q', self.destroy)
        else:
            self._parent = parent

        # Create a frame for the canvas & scrollbars
        self._frame = frame = Frame(self._parent)
        self._canvas = canvas = Canvas(frame, **kw)
        xscrollbar = Scrollbar(self._frame, orient='horizontal')
        yscrollbar = Scrollbar(self._frame, orient='vertical')
        xscrollbar['command'] = canvas.xview
        yscrollbar['command'] = canvas.yview
        canvas['xscrollcommand'] = xscrollbar.set
        canvas['yscrollcommand'] = yscrollbar.set
        yscrollbar.pack(fill='y', side='right')
        xscrollbar.pack(fill='x', side='bottom')
        canvas.pack(expand=1, fill='both', side='left')

        # Set initial scroll region.
        scrollregion = '0 0 %s %s' % (canvas['width'], canvas['height'])
        canvas['scrollregion'] = scrollregion
        
        self._scrollwatcher = ScrollWatcherWidget(canvas)

        # If no parent was given, pack the frame.
        if parent is None:
            self.pack(expand=1, fill='both')

            # Done button.
            buttonframe = Frame(self._parent)
            buttonframe.pack(fill='x', side='bottom')
            ok = Button(buttonframe, text='Done', command=self.destroy)
            ok.pack(side='right')
            ps = Button(buttonframe, text='Print',
                        command=self.print_to_file)
            ps.pack(side='left')
            #help = Button(buttonframe, text='Help')
            #help.pack(side='right')

    def print_to_file(self, filename=None):
        """
        Print the contents of this C{CanvasFrame} to a postscript
        file.  If no filename is given, then prompt the user for one.

        @param filename: The name of the file to print the tree to.
        @type filename: C{string}
        @rtype: C{None}
        """
        if filename is None:
            from tkFileDialog import asksaveasfilename
            ftypes = [('Postscript files', '.ps'),
                      ('All files', '*')]
            filename = asksaveasfilename(filetypes=ftypes,
                                         defaultextension='.ps')
            if not filename: return
        (x0, y0, w, h) = self._canvas['scrollregion'].split()
        self._canvas.postscript(file=filename, x=x0, y=y0,
                                width=int(w)+2, height=int(h)+2)

    def canvas(self):
        """
        @return: The canvas managed by this C{CanvasFrame}.
        @rtype: C{Tkinter.Canvas}
        """
        return self._canvas

    def add_widget(self, canvaswidget, x=0, y=0):
        """
        Register a canvas widget with this C{CanvasFrame}.  The
        C{CanvasFrame} will ensure that this canvas widget is always
        within the C{Canvas}'s scrollregion.

        @type canvaswidget: C{CanvasWidget}
        @param canvaswidget: The new canvas widget.  C{canvaswidget}
            must have been created on this C{CanvasFrame}'s canvas.
        @type x: C{int}
        @param x: The initial x coordinate for the upper left hand
            corner of C{canvaswidget}, in the canvas's coordinate
            space. 
        @type y: C{int}
        @param y: The initial y coordinate for the upper left hand
            corner of C{canvaswidget}, in the canvas's coordinate
            space. 
        """
        # Move to (x,y)
        (x1,y1,x2,y2) = canvaswidget.bbox()
        canvaswidget.move(x-x1,y-y1)

        # Register with scrollwatcher.
        self._scrollwatcher.add_child(canvaswidget)
        
    def destroy_widget(self, canvaswidget):
        """
        Remove a canvas widget from this C{CanvasFrame}.  This
        deregisters the canvas widget, and destroys it.
        """
        # Deregister with scrollwatcher.
        self._scrollwatcher.remove_child(canvaswidget)
        canvaswidget.destroy()
        
    def pack(self, cnf={}, **kw):
        """
        Pack this C{CanvasFrame}.  See the documentation for
        C{Tkinter.Pack} for more information.
        """
        self._frame.pack(cnf, **kw)
        # Adjust to be big enough for kids?

    def destroy(self, *e):
        """
        Destroy this C{CanvasFrame}.  If this C{CanvasFrame} created a
        top-level window, then this will close that window.
        """
        if self._parent is None: return
        self._parent.destroy()
        self._parent = None

class ShowText:
    """
    A C{Tkinter} window used to display a text.  C{ShowText} is
    typically used by graphical tools to display help text, or similar
    information.
    """
    def __init__(self, root, title, text, width=None, height=None):
        if width is None or height is None:
            (width, height) = self.find_dimentions(text, width, height)
        
        # Create the main window.
        if root is None:
            self._top = top = Tk()
        else:
            self._top = top = Toplevel(root)
        top.title(title)

        b = Button(top, text='Ok', command=self.destroy)
        b.pack(side='bottom')

        tbf = Frame(top)
        tbf.pack(expand=1, fill='both')
        scrollbar = Scrollbar(tbf, orient='vertical')
        scrollbar.pack(side='right', fill='y')
        textbox = Text(tbf, wrap='word',
                               width=width, height=height)
        textbox.insert('end', text)
        textbox['state'] = 'disabled'
        textbox.pack(side='left', expand=1, fill='both')
        scrollbar['command'] = textbox.yview
        textbox['yscrollcommand'] = scrollbar.set

        # Make it easy to close the window.
        top.bind('q', self.destroy)
        top.bind('x', self.destroy)
        top.bind('c', self.destroy)
        top.bind('<Return>', self.destroy)
        top.bind('<Escape>', self.destroy)

        # Focus the scrollbar, so they can use up/down, etc.
        scrollbar.focus()

    def find_dimentions(self, text, width, height):
        lines = text.split('\n')
        if width is None:
            maxwidth = max([len(line) for line in lines])
            width = min(maxwidth, 80)

        # Now, find height.
        height = 0
        for line in lines:
            while len(line) > width:
                brk = line[:width].rfind(' ')
                line = line[brk:]
                height += 1
            height += 1
        height = min(height, 25)

        return (width, height)

    def destroy(self, *e):
        if self._top is None: return
        self._top.destroy()
        self._top = None

    def mainloop(self):
        self._top.mainloop()

##//////////////////////////////////////////////////////
##  Test code.
##//////////////////////////////////////////////////////

def demo():
    """
    A simple demonstration showing how to use canvas widgets.
    """
    def fill(cw):
        from random import randint
        cw['fill'] = '#00%04d' % randint(0,9999)
    def color(cw):
        from random import randint
        cw['color'] = '#ff%04d' % randint(0,9999)
    
    cf = CanvasFrame(closeenough=10, width=300, height=300)
    ct3 = TextWidget(cf.canvas(), 'hiya there', draggable=1)
    ct2 = TextWidget(cf.canvas(), 'o  o\n||\n___\n|   |',
                 draggable=1, justify='center')
    co = OvalWidget(cf.canvas(), ct2, outline='red')
    ct = TextWidget(cf.canvas(), 'o  o\n||\n\\___/',
                draggable=1, justify='center')
    cp = ParenWidget(cf.canvas(), ct, color='red')
    cb = BoxWidget(cf.canvas(), cp, fill='cyan', draggable=1,
               width=3, margin=10)
    space = SpaceWidget(cf.canvas(), 0, 30)
    cstack = StackWidget(cf.canvas(), cb, space, co, ct3, align='center')
    foo = TextWidget(cf.canvas(), 'try clicking\nand dragging',
                     draggable=1, justify='center')
    cs = SequenceWidget(cf.canvas(), cstack, foo)
    zz = BracketWidget(cf.canvas(), cs, color='green4', width=3)
    cf.add_widget(zz, 60, 30)

    cb.bind_click(fill)
    ct.bind_click(color)
    co.bind_click(fill)
    ct2.bind_click(color)
    ct3.bind_click(color)

    #ShowText(None, 'title', ((('this is text'*150)+'\n')*5))

if __name__ == '__main__':
    demo()
