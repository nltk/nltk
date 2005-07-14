# Natural Language Toolkit: graphical representations package
#
# Copyright (C) 2001-2005 University of Pennsylvania
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
documentation for L{CanvasWidget} for more information.

The C{nltk.draw} module defines the abstract C{CanvasWidget} base
class, and a number of simple canvas widgets.  The remaining canvas
widgets are defined by submodules, such as L{nltk.draw.tree}.

The C{nltk.draw} module also defines L{CanvasFrame}, which
encapsulates a C{Canvas} and its scrollbars.  It uses a
L{ScrollWatcherWidget} to ensure that all canvas widgets contained on
its canvas are within the scroll region.

Acknowledgements: Many of the ideas behind the canvas widget system
are derived from C{CLIG}, a Tk-based grapher for linguistic data
structures.  For more information, see U{the CLIG
homepage<http://www.ags.uni-sb.de/~konrad/clig.html>}.

@group Graphical Demonstrations: rdparser, srparser, chart
@group Widgets: tree, cfg, fsa, plot, tree_edit
@group Abstract Widget Superclasses: CanvasWidget, AbstractContainerWidget
@sort: CanvasWidget, AbstractContainerWidget
@group Canvas Widgets: BoxWidget, BracketWidget, OvalWidget, ParenWidget,
    ScrollWatcherWidget, SequenceWidget, SpaceWidget, StackWidget,
    SymbolWidget, TextWidget
@sort: TextWidget, SymbolWidget, BoxWidget, OvalWidget, ParenWidget,
    BracketWidget, SequenceWidget, StackWidget, SpaceWidget,
    ScrollWatcherWidget
@group Tkinter Widgets: CanvasFrame, EntryDialog, ShowText
"""
from Tkinter import *

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
        if self.__class__ == CanvasWidget:
            raise TypeError, 'CanvasWidget is an abstract base class'
        
        if not isinstance(canvas, Canvas):
            raise TypeError('Expected a canvas!')
        
        self.__canvas = canvas
        self.__parent = parent

        # If the subclass constructor called _add_child_widget, then
        # self.__children will already exist.
        if not hasattr(self, '_CanvasWidget__children'): self.__children = []

        # Is this widget hidden?
        self.__hidden = 0

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
        if self.__hidden: return (0,0,0,0)
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

    def moveto(self, x, y, anchor='NW'):
        """
        Move this canvas widget to the given location.  In particular,
        shift the canvas widget such that the corner or side of the
        bounding box specified by C{anchor} is at location (C{x},
        C{y}).

        @param x,y: The location that the canvas widget should be moved
            to.
        @param anchor: The corner or side of the canvas widget that
            should be moved to the specified location.  C{'N'}
            specifies the top center; C{'NE'} specifies the top right
            corner; etc.
        """
        x1,y1,x2,y2 = self.bbox()
        if anchor == 'NW': self.move(x-x1,        y-y1)
        if anchor == 'N':  self.move(x-x1/2-x2/2, y-y1)
        if anchor == 'NE': self.move(x-x2,        y-y1)
        if anchor == 'E':  self.move(x-x2,        y-y1/2-y2/2)
        if anchor == 'SE': self.move(x-x2,        y-y2)
        if anchor == 'S':  self.move(x-x1/2-x2/2, y-y2)
        if anchor == 'SW': self.move(x-x1,        y-y2)
        if anchor == 'W':  self.move(x-x1,        y-y1/2-y2/2)

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
        if self.__hidden or child.__hidden: return
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
        if self.__hidden: return
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

    def hide(self):
        """
        Temporarily hide this canvas widget.

        @rtype: C{None}
        """
        self.__hidden = 1
        for tag in self.tags():
            self.__canvas.itemconfig(tag, state='hidden')

    def show(self):
        """
        Show a hidden canvas widget.

        @rtype: C{None}
        """
        self.__hidden = 0
        for tag in self.tags():
            self.__canvas.itemconfig(tag, state='normal')

    def hidden(self):
        """
        @return: True if this canvas widget is hidden.
        @rtype: C{boolean}
        """
        return self.__hidden

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
        self._tag = canvas.create_text(1, 1, text=text)
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
        return self.canvas().itemcget(self._tag, 'TEXT')
    
    def set_text(self, text):
        """
        Change the text that is displayed by this text widget.

        @type text: C{string}
        @param text: The string of text to display.
        @rtype: C{None}
        """
        self.canvas().itemconfig(self._tag, text=text)
        if self.parent() is not None:
            self.parent().update(self)

    def __repr__(self):
        return '[Text: %r]' % self._text

class SymbolWidget(TextWidget):
    """
    A canvas widget that displays special symbols, such as the
    negation sign and the exists operator.  Symbols are specified by
    name.  Currently, the following symbol names are defined: C{neg},
    C{disj}, C{conj}, C{lambda}, C{merge}, C{forall}, C{exists},
    C{subseteq}, C{subset}, C{notsubset}, C{emptyset}, C{imp},
    C{rightarrow}, C{equal}, C{notequal}, C{epsilon}.
        
    Attributes:
      - C{color}: the color of the text.
      - C{draggable}: whether the text can be dragged by the user.
      
    @cvar SYMBOLS: A dictionary mapping from symbols to the character
        in the C{symbol} font used to render them.
    """
    SYMBOLS = {'neg':'\330', 'disj':'\332', 'conj': '\331',
               'lambda': '\154', 'merge': '\304',
               'forall': '\042', 'exists': '\044',
               'subseteq': '\315', 'subset': '\314',
               'notsubset': '\313', 'emptyset': '\306',
               'imp': '\336', 'rightarrow': chr(222), #'\256',
               'equal': '\75', 'notequal': '\271',
               'intersection': '\307', 'union': '\310',
               'epsilon': 'e',
               }
    
    def __init__(self, canvas, symbol, **attribs):
        """
        Create a new symbol widget.

        @type canvas: C{Tkinter.Canvas}
        @param canvas: This canvas widget's canvas.
        @type symbol: C{string}
        @param symbol: The name of the symbol to display.
        @param attribs: The new canvas widget's attributes.
        """
        attribs['font'] = 'symbol'
        TextWidget.__init__(self, canvas, '', **attribs)
        self.set_symbol(symbol)

    def symbol(self):
        """
        @return: the name of the symbol that is displayed by this
            symbol widget.
        @rtype: C{string}
        """
        return self._symbol

    def set_symbol(self, symbol):
        """
        Change the symbol that is displayed by this symbol widget.

        @type symbol: C{string}
        @param symbol: The name of the symbol to display.
        """
        if not SymbolWidget.SYMBOLS.has_key(symbol):
            raise ValueError('Unknown symbol: %s' % symbol)
        self._symbol = symbol
        self.set_text(SymbolWidget.SYMBOLS[symbol])

    def __repr__(self):
        return '[Symbol: %r]' % self._symbol

    # A staticmethod that displays all symbols.
    def symbolsheet(size=20):
        """
        Open a new Tkinter window that displays the entire alphabet
        for the symbol font.  This is useful for constructing the
        L{SymbolWidget.SYMBOLS} dictionary.
        """
        top = Tk()
        def destroy(e, top=top): top.destroy()
        top.bind('q', destroy)
        Button(top, text='Quit', command=top.destroy).pack(side='bottom')
        text = Text(top, font=('helvetica', -size), width=20, height=30)
        text.pack(side='left')
        sb=Scrollbar(top, command=text.yview)
        text['yscrollcommand']=sb.set
        sb.pack(side='right', fill='y')
        text.tag_config('symbol', font=('symbol', -size))
        for i in range(256):
            if i in (0,10): continue # null and newline
            for k,v in SymbolWidget.SYMBOLS.items():
                if v == chr(i):
                    text.insert('end', '%-10s\t' % k)
                    break
            else:
                text.insert('end', '%-10d  \t' % i)
            text.insert('end', '[%s]\n' % chr(i), 'symbol')
        top.mainloop()
    symbolsheet = staticmethod(symbolsheet)


class AbstractContainerWidget(CanvasWidget):
    """
    An abstract class for canvas widgets that contain a single child,
    such as C{BoxWidget} and C{OvalWidget}.  Subclasses must define
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
        self._box = canvas.create_rectangle(1,1,1,1)
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
        self._oval = canvas.create_oval(1,1,1,1)
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
        left = int(( x1*(1+R) + x2*(1-R) ) / 2 - margin)
        right = left + int((x2-x1)*R)
        top = int(( y1*(1+R) + y2*(1-R) ) / 2 - margin)
        bot = top + int((y2-y1)*R)
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
        self._oparen = canvas.create_arc(1,1,1,1, style='arc',
                                         start=90, extent=180)
        self._cparen = canvas.create_arc(1,1,1,1, style='arc',
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
        self._obrack = canvas.create_line(1,1,1,1,1,1,1,1)
        self._cbrack = canvas.create_line(1,1,1,1,1,1,1,1)
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
      - C{ordered}: If true, then keep the children in their
        original order.
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
        self._ordered = False
        self._children = list(children)
        for child in children: self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == 'align':
            if value not in ('top', 'bottom', 'center'):
                raise ValueError('Bad alignment: %r' % value)
            self._align = value
        elif attr == 'space': self._space = value
        elif attr == 'ordered': self._ordered = value
        else: CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'align': return value
        elif attr == 'space': return self._space
        elif attr == 'ordered': return self._ordered
        else: return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return []

    def _yalign(self, top, bot):
        if self._align == 'top': return top
        if self._align == 'bottom': return bot
        if self._align == 'center': return (top+bot)/2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        y = self._yalign(top, bot)
        for c in self._children:
            (x1, y1, x2, y2) = c.bbox()
            c.move(0, y-self._yalign(y1,y2))

        if self._ordered and len(self._children) > 1:
            index = self._children.index(child)

            x = right + self._space
            for i in range(index+1, len(self._children)):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if x > x1:
                    self._children[i].move(x-x1, 0)
                    x += x2-x1 + self._space

            x = left - self._space
            for i in range(index-1, -1, -1):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if x < x2:
                    self._children[i].move(x-x2, 0)
                    x -= x2-x1 + self._space

    def _manage(self):
        if len(self._children) == 0: return
        child = self._children[0]

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
        
    def __repr__(self):
        return '[Sequence: ' + `self._children`[1:-1]+']'

    # Provide an alias for the child_widgets() member.
    children = CanvasWidget.child_widgets
    
    def replace_child(self, oldchild, newchild):
        """
        Replace the child canvas widget C{oldchild} with C{newchild}.
        C{newchild} must not have a parent.  C{oldchild}'s parent will
        be set to C{None}.

        @type oldchild: C{CanvasWidget}
        @param oldchild: The child canvas widget to remove.
        @type newchild: C{CanvasWidget}
        @param newchild: The canvas widget that should replace
            C{oldchild}.
        """
        index = self._children.index(oldchild)
        self._children[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        """
        Remove the given child canvas widget.  C{child}'s parent will
        be set ot None.

        @type child: C{CanvasWidget}
        @param child: The child canvas widget to remove.
        """
        index = self._children.index(child)
        del self._children[index]
        self._remove_child_widget(child)
        if len(self._children) > 0:
            self.update(self._children[0])

    def insert_child(self, index, child):
        """
        Insert a child canvas widget before a given index.

        @type child: C{CanvasWidget}
        @param child: The canvas widget that should be inserted.
        @type index: C{int}
        @param index: The index where the child widget should be
            inserted.  In particular, the index of C{child} will be
            C{index}; and the index of any children whose indices were
            greater than equal to C{index} before C{child} was
            inserted will be incremented by one.
        """
        self._children.insert(index, child)
        self._add_child_widget(child)
    
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
      - C{ordered}: If true, then keep the children in their
        original order.
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
        self._ordered = False
        self._children = list(children)
        for child in children: self._add_child_widget(child)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr == 'align':
            if value not in ('left', 'right', 'center'):
                raise ValueError('Bad alignment: %r' % value)
            self._align = value
        elif attr == 'space': self._space = value
        elif attr == 'ordered': self._ordered = value
        else: CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'align': return value
        elif attr == 'space': return self._space
        elif attr == 'ordered': return self._ordered
        else: return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return []

    def _xalign(self, left, right):
        if self._align == 'left': return left
        if self._align == 'right': return right
        if self._align == 'center': return (left+right)/2

    def _update(self, child):
        # Align all children with child.
        (left, top, right, bot) = child.bbox()
        x = self._xalign(left, right)
        for c in self._children:
            (x1, y1, x2, y2) = c.bbox()
            c.move(x-self._xalign(x1,x2), 0)

        if self._ordered and len(self._children) > 1:
            index = self._children.index(child)

            y = bot + self._space
            for i in range(index+1, len(self._children)):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if y > y1:
                    self._children[i].move(0, y-y1)
                    y += y2-y1 + self._space
        
            y = top - self._space
            for i in range(index-1, -1, -1):
                (x1, y1, x2, y2) = self._children[i].bbox()
                if y < y2:
                    self._children[i].move(0, y-y2)
                    y -= y2-y1 + self._space
        
    def _manage(self):
        if len(self._children) == 0: return
        child = self._children[0]
        
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

    def __repr__(self):
        return '[Stack: ' + `self._children`[1:-1]+']'

    # Provide an alias for the child_widgets() member.
    children = CanvasWidget.child_widgets
    
    def replace_child(self, oldchild, newchild):
        """
        Replace the child canvas widget C{oldchild} with C{newchild}.
        C{newchild} must not have a parent.  C{oldchild}'s parent will
        be set to C{None}.

        @type oldchild: C{CanvasWidget}
        @param oldchild: The child canvas widget to remove.
        @type newchild: C{CanvasWidget}
        @param newchild: The canvas widget that should replace
            C{oldchild}.
        """
        index = self._children.index(oldchild)
        self._children[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        """
        Remove the given child canvas widget.  C{child}'s parent will
        be set ot None.

        @type child: C{CanvasWidget}
        @param child: The child canvas widget to remove.
        """
        index = self._children.index(child)
        del self._children[index]
        self._remove_child_widget(child)
        if len(self._children) > 0:
            self.update(self._children[0])

    def insert_child(self, index, child):
        """
        Insert a child canvas widget before a given index.

        @type child: C{CanvasWidget}
        @param child: The canvas widget that should be inserted.
        @type index: C{int}
        @param index: The index where the child widget should be
            inserted.  In particular, the index of C{child} will be
            C{index}; and the index of any children whose indices were
            greater than equal to C{index} before C{child} was
            inserted will be incremented by one.
        """
        self._children.insert(index, child)
        self._add_child_widget(child)
    
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
        # For some reason, 
        if width > 4: width -= 4
        if height > 4: height -= 4
        self._tag = canvas.create_line(1, 1, width, height, fill='')
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
            self._parent.bind('<Control-p>', self.print_to_file)
            self._parent.bind('<Control-x>', self.destroy)
            self._parent.bind('<Control-q>', self.destroy)
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

        # If no parent was given, pack the frame, and add a menu.
        if parent is None:
            self.pack(expand=1, fill='both')
            self._init_menubar()

    def _init_menubar(self):
        menubar = Menu(self._parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label='Print to Postscript', underline=0,
                             command=self.print_to_file, accelerator='Ctrl-p')
        filemenu.add_command(label='Exit', underline=1,
                             command=self.destroy, accelerator='Ctrl-x')
        menubar.add_cascade(label='File', underline=0, menu=filemenu)

        self._parent.config(menu=menubar)

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
        (x0, y0, w, h) = self.scrollregion()
        self._canvas.postscript(file=filename, x=x0, y=y0,
                                width=w+2, height=h+2)

    def scrollregion(self):
        """
        @return: The current scroll region for the canvas managed by
            this C{CanvasFrame}.
        @rtype: 4-tuple of C{int}
        """
        (x1, y1, x2, y2) = self._canvas['scrollregion'].split()
        return (int(x1), int(y1), int(x2), int(y2))
        
    def canvas(self):
        """
        @return: The canvas managed by this C{CanvasFrame}.
        @rtype: C{Tkinter.Canvas}
        """
        return self._canvas

    def add_widget(self, canvaswidget, x=None, y=None):
        """
        Register a canvas widget with this C{CanvasFrame}.  The
        C{CanvasFrame} will ensure that this canvas widget is always
        within the C{Canvas}'s scrollregion.  If no coordinates are
        given for the canvas widget, then the C{CanvasFrame} will
        attempt to find a clear area of the canvas for it.

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
        if x is None or y is None:
            (x, y) = self._find_room(canvaswidget)
        
        # Move to (x,y)
        (x1,y1,x2,y2) = canvaswidget.bbox()
        canvaswidget.move(x-x1,y-y1)

        # Register with scrollwatcher.
        self._scrollwatcher.add_child(canvaswidget)

    def _find_room(self, widget):
        """
        Try to find a space for a given widget.
        """
        (left, top, right, bot) = self.scrollregion()
        w = widget.width()
        h = widget.height()

        if w >= (right-left): return (0,0)
        if h >= (bot-top): return (0,0)

        # Move the widget out of the way, for now.
        (x1,y1,x2,y2) = widget.bbox()
        widget.move(left-x2-50, top-y2-50)

        for y in range(top, bot-h, (bot-top-h)/10):
            for x in range(left, right-w, (right-left-w)/10):
                if not self._canvas.find_overlapping(x-5, y-5, x+w+5, y+h+5):
                    return (x,y)
        return (0,0)
        
    def destroy_widget(self, canvaswidget):
        """
        Remove a canvas widget from this C{CanvasFrame}.  This
        deregisters the canvas widget, and destroys it.
        """
        self.remove_widget(canvaswidget)
        canvaswidget.destroy()

    def remove_widget(self, canvaswidget):
        # Deregister with scrollwatcher.
        self._scrollwatcher.remove_child(canvaswidget)
        
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

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this frame is created from a non-interactive program (e.g.
        from a secript); otherwise, the frame will close as soon as
        the script completes.
        """
        if in_idle(): return
        self._parent.mainloop(*args, **kwargs)

##//////////////////////////////////////////////////////
##  Text display
##//////////////////////////////////////////////////////

class ShowText:
    """
    A C{Tkinter} window used to display a text.  C{ShowText} is
    typically used by graphical tools to display help text, or similar
    information.
    """
    def __init__(self, root, title, text, width=None, height=None,
                 **textbox_options):
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
        textbox = Text(tbf, wrap='word', width=width, 
                       height=height, **textbox_options)
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

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this window is created from a non-interactive program (e.g.
        from a secript); otherwise, the window will close as soon as
        the script completes.
        """
        if in_idle(): return
        self._top.mainloop(*args, **kwargs)

##//////////////////////////////////////////////////////
##  Entry dialog
##//////////////////////////////////////////////////////

class EntryDialog:
    """
    A dialog box for entering 
    """
    def __init__(self, parent, original_text='', instructions='',
                 set_callback=None, title=None):
        self._parent = parent
        self._original_text = original_text
        self._set_callback = set_callback

        width = max(30, len(original_text)*3/2)
        self._top = Toplevel(parent)

        if title: self._top.title(title)

        # The text entry box.
        entryframe = Frame(self._top)
        entryframe.pack(expand=1, fill='both', padx=5, pady=5,ipady=10)
        if instructions:
            l=Label(entryframe, text=instructions)
            l.pack(side='top', anchor='w', padx=30)
        self._entry = Entry(entryframe, width=width)
        self._entry.pack(expand=1, fill='x', padx=30)
        self._entry.insert(0, original_text)

        # A divider
        divider = Frame(self._top, borderwidth=1, relief='sunken')
        divider.pack(fill='x', ipady=1, padx=10)

        # The buttons.
        buttons = Frame(self._top)
        buttons.pack(expand=0, fill='x', padx=5, pady=5)
        b = Button(buttons, text='Cancel', command=self._cancel, width=8)
        b.pack(side='right', padx=5)
        b = Button(buttons, text='Ok', command=self._ok,
                   width=8, default='active')
        b.pack(side='left', padx=5)
        b = Button(buttons, text='Apply', command=self._apply, width=8)
        b.pack(side='left')
        
        self._top.bind('<Return>', self._ok)
        self._top.bind('<Control-q>', self._cancel)
        self._top.bind('<Escape>', self._cancel)

        self._entry.focus()

    def _reset(self, *e):
        self._entry.delete(0,'end')
        self._entry.insert(0, self._original_text)
        if self._set_callback:
            self._set_callback(self._original_text)
        
    def _cancel(self, *e):
        try: self._reset()
        except: pass
        self._destroy()

    def _ok(self, *e):
        self._apply()
        self._destroy()

    def _apply(self, *e):
        if self._set_callback:
            self._set_callback(self._entry.get())
        
    def _destroy(self, *e):
        if self._top is None: return
        self._top.destroy()
        self._top = None

##//////////////////////////////////////////////////////
##  Colorized List
##//////////////////////////////////////////////////////

class ColorizedList:
    """
    An abstract base class for displaying a colorized list of items.
    Subclasses should define:
      - L{_init_colortags}, which sets up Text color tags that
        will be used by the list.
      - L{_item_repr}, which returns a list of (text,colortag)
        tuples that make up the colorized representation of the
        item.
    @note: Typically, you will want to register a callback for
        C{'select'} that calls L{mark} on the given item.
    """
    def __init__(self, parent, items=[], **options):
        """
        Construct a new list.

        @param parent: The Tk widget that contains the colorized list
        @param items: The initial contents of the colorized list.
        @param options: 
        """
        self._parent = parent
        self._callbacks = {}

        # Which items are marked?
        self._marks = {}

        # Initialize the Tkinter frames.
        self._init_itemframe(options.copy())

        # Set up key & mouse bindings.
        self._textwidget.bind('<KeyPress>', self._keypress)
        self._textwidget.bind('<ButtonPress>', self._buttonpress)

        # Fill in the given CFG's items.
        self._items = None
        self.set(items)

    #////////////////////////////////////////////////////////////
    # Abstract methods
    #////////////////////////////////////////////////////////////

    def _init_colortags(self, textwidget, options):
        """
        Set up any colortags that will be used by this colorized list.
        E.g.:
            >>> textwidget.tag_config('terminal', foreground='black')
        """
        raise AssertionError, 'Abstract base class'

    def _item_repr(self, item):
        """
        Return a list of (text, colortag) tuples that make up the
        colorized representation of the item.  Colorized
        representations may not span multiple lines.  I.e., the text
        strings returned may not contain newline characters.
        """
        raise AssertionError, 'Abstract base class'

    #////////////////////////////////////////////////////////////
    # Item Access
    #////////////////////////////////////////////////////////////

    def get(self, index=None):
        """
        @return: A list of the items contained by this list.
        """
        if index is None:
            return self._items[:]
        else:
            return self._items[index]

    def set(self, items):
        """
        Modify the list of items contained by this list.
        """
        items = list(items)
        if self._items == items: return
        self._items = list(items)
        
        self._textwidget['state'] = 'normal'
        self._textwidget.delete('1.0', 'end')
        for item in items:
            for (text, colortag) in self._item_repr(item):
                assert '\n' not in text, 'item repr may not contain newline'
                self._textwidget.insert('end', text, colortag)
            self._textwidget.insert('end', '\n')
        # Remove the final newline
        self._textwidget.delete('end-1char', 'end')
        self._textwidget.mark_set('insert', '1.0')
        self._textwidget['state'] = 'disabled'
        # Clear all marks
        self._marks.clear()

    def unmark(self, item=None):
        """
        Remove highlighting from the given item; or from every item,
        if no item is given.
        @raise ValueError: If C{item} is not contained in the list.
        @raise KeyError: If C{item} is not marked.
        """
        if item is None:
            self._marks.clear()
            self._textwidget.tag_remove('highlight', '1.0', 'end+1char')
        else:
            index = self._items.index(item)
            del self._marks[item]
            (start, end) = ('%d.0' % (index+1), '%d.0' % (index+2))
            self._textwidget.tag_remove('highlight', start, end)

    def mark(self, item):
        """
        Highlight the given item.
        @raise ValueError: If C{item} is not contained in the list.
        """
        self._marks[item] = 1
        index = self._items.index(item)
        (start, end) = ('%d.0' % (index+1), '%d.0' % (index+2))
        self._textwidget.tag_add('highlight', start, end)

    def markonly(self, item):
        """
        Remove any current highlighting, and mark the given item.
        @raise ValueError: If C{item} is not contained in the list.
        """
        self.unmark()
        self.mark(item)

    def view(self, item):
        """
        Adjust the view such that the given item is visible.  If
        the item is already visible, then do nothing.
        """
        index = self._items.index(item)
        self._textwidget.see('%d.0' % (index+1))

    #////////////////////////////////////////////////////////////
    # Callbacks
    #////////////////////////////////////////////////////////////

    def add_callback(self, event, func):
        """
        Register a callback function with the list.  This function
        will be called whenever the given event occurs.
        
        @param event: The event that will trigger the callback
            function.  Valid events are: click1, click2, click3,
            space, return, select, up, down, next, prior, move
        @param func: The function that should be called when
            the event occurs.  C{func} will be called with a
            single item as its argument.  (The item selected
            or the item moved to).
        """
        if event == 'select': events = ['click1', 'space', 'return']
        elif event == 'move': events = ['up', 'down', 'next', 'prior']
        else: events = [event]

        for e in events:
            self._callbacks.setdefault(e,{})[func] = 1

    def remove_callback(self, event, func=None):
        """
        Deregister a callback function.  If C{func} is none, then
        all callbacks are removed for the given event.
        """
        if event is None: events = self._callbacks.keys()
        elif event == 'select': events = ['click1', 'space', 'return']
        elif event == 'move': events = ['up', 'down', 'next', 'prior']
        else: events = [event]

        for e in events:
            if func is None: del self._callbacks[e]
            else:
                try: del self._callbacks[e][func]
                except: pass

    #////////////////////////////////////////////////////////////
    # Tkinter Methods
    #////////////////////////////////////////////////////////////

    def pack(self, cnf={}, **kw):
#        "@include: Tkinter.Pack.pack"
        self._itemframe.pack(cnf, **kw)
        
    def grid(self, cnf={}, **kw):
#        "@include: Tkinter.Grid.grid"
        self._itemframe.grid(cnf, *kw)
        
    def focus(self):
#        "@include: Tkinter.Widget.focus"
        self._textwidget.focus()
        
    #////////////////////////////////////////////////////////////
    # Internal Methods
    #////////////////////////////////////////////////////////////

    def _init_itemframe(self, options):
        self._itemframe = Frame(self._parent)

        # Create the basic Text widget & scrollbar.
        options.setdefault('background', '#e0e0e0')
        self._textwidget = Text(self._itemframe, **options)
        self._textscroll = Scrollbar(self._itemframe, takefocus=0,
                                     orient='vertical')
        self._textwidget.config(yscrollcommand = self._textscroll.set)
        self._textscroll.config(command=self._textwidget.yview)
        self._textscroll.pack(side='right', fill='y')
        self._textwidget.pack(expand=1, fill='both', side='left')
        
        # Initialize the colorization tags
        self._textwidget.tag_config('highlight', background='#e0ffff',
                                    border='1', relief='raised')
        self._init_colortags(self._textwidget, options)

        # How do I want to mark keyboard selection?
        self._textwidget.tag_config('sel', foreground='')
        self._textwidget.tag_config('sel', foreground='', background='',
                                    border='', underline=1)
        self._textwidget.tag_lower('highlight', 'sel')

    def _fire_callback(self, event, itemnum):
        if not self._callbacks.has_key(event): return
        if 0 <= itemnum < len(self._items):
            item = self._items[itemnum]
        else:
            item = None
        for cb_func in self._callbacks[event].keys():
            cb_func(item)

    def _buttonpress(self, event):
        clickloc = '@%d,%d' % (event.x,event.y)
        insert_point = self._textwidget.index(clickloc)
        itemnum = int(insert_point.split('.')[0])-1
        self._fire_callback('click%d' % event.num, itemnum)
        
    def _keypress(self, event):
        if event.keysym == 'Return' or event.keysym == 'space':
            insert_point = self._textwidget.index('insert')
            itemnum = int(insert_point.split('.')[0])-1
            self._fire_callback(event.keysym.lower(), itemnum)
            return
        elif event.keysym == 'Down': delta='+1line'
        elif event.keysym == 'Up': delta='-1line'
        elif event.keysym == 'Next': delta='+10lines'
        elif event.keysym == 'Prior': delta='-10lines'
        else: return 'continue'
        
        self._textwidget.mark_set('insert', 'insert'+delta)
        self._textwidget.see('insert')
        self._textwidget.tag_remove('sel', '1.0', 'end+1char')
        self._textwidget.tag_add('sel', 'insert linestart', 'insert lineend')

        insert_point = self._textwidget.index('insert')
        itemnum = int(insert_point.split('.')[0])-1
        self._fire_callback(event.keysym.lower(), itemnum)
        
        return 'break'
    
##//////////////////////////////////////////////////////
##  Improved OptionMenu
##//////////////////////////////////////////////////////

class MutableOptionMenu(Menubutton):
    def __init__(self, master, values, **options):
        self._callback = options.get('command')
        if 'command' in options: del options['command']
        
        # Create a variable
        self._variable = variable = StringVar()
        if len(values) > 0:
            variable.set(values[0])

        kw = {"borderwidth": 2, "textvariable": variable,
              "indicatoron": 1, "relief": RAISED, "anchor": "c",
              "highlightthickness": 2}
        kw.update(options)
        Widget.__init__(self, master, "menubutton", kw)
        self.widgetName = 'tk_optionMenu'
        self._menu = Menu(self, name="menu", tearoff=0,)
        self.menuname = self._menu._w

        self._values = []
        for value in values: self.add(value)

        self["menu"] = self._menu

    def add(self, value):
        if value in self._values: return
        def set(value=value): self.set(value)
        self._menu.add_command(label=value, command=set)
        self._values.append(value)

    def set(self, value):
        self._variable.set(value)
        if self._callback:
            self._callback(value)

    def remove(self, value):
        # Might raise indexerror: pass to parent.
        i = self._values.index(value)
        del self._values[i]
        self._menu.delete(i, i)

    def __getitem__(self, name):
        if name == 'menu':
            return self.__menu
        return Widget.__getitem__(self, name)

    def destroy(self):
        """Destroy this widget and the associated menu."""
        Menubutton.destroy(self)
        self._menu = None

##//////////////////////////////////////////////////////
##  Helpers
##//////////////////////////////////////////////////////

def in_idle():
    """
    @rtype: C{boolean}
    @return: true if this function is run within idle.  Tkinter
    programs that are run in idle should never call L{Tk.mainloop}; so
    this function should be used to gate all calls to C{Tk.mainloop}.

    @warning: This function works by checking C{sys.stdin}.  If the
    user has modified C{sys.stdin}, then it may return incorrect
    results.
    """
    import sys, types
    return (type(sys.stdin) == types.InstanceType and \
            sys.stdin.__class__.__name__ == 'PyShell')

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
    c = cf.canvas()
    ct3 = TextWidget(c, 'hiya there', draggable=1)
    ct2 = TextWidget(c, 'o  o\n||\n___\n  U', draggable=1, justify='center')
    co = OvalWidget(c, ct2, outline='red')
    ct = TextWidget(c, 'o  o\n||\n\\___/', draggable=1, justify='center')
    cp = ParenWidget(c, ct, color='red')
    cb = BoxWidget(c, cp, fill='cyan', draggable=1, width=3, margin=10)
    equation = SequenceWidget(c,
                              SymbolWidget(c, 'forall'), TextWidget(c, 'x'),
                              SymbolWidget(c, 'exists'), TextWidget(c, 'y: '),
                              TextWidget(c, 'x'), SymbolWidget(c, 'notequal'),
                              TextWidget(c, 'y'))
    space = SpaceWidget(c, 0, 30)
    cstack = StackWidget(c, cb, ct3, space, co, equation, align='center')
    foo = TextWidget(c, 'try clicking\nand dragging',
                     draggable=1, justify='center')
    cs = SequenceWidget(c, cstack, foo)
    zz = BracketWidget(c, cs, color='green4', width=3)
    cf.add_widget(zz, 60, 30)

    cb.bind_click(fill)
    ct.bind_click(color)
    co.bind_click(fill)
    ct2.bind_click(color)
    ct3.bind_click(color)

    #ShowText(None, 'title', ((('this is text'*150)+'\n')*5))

if __name__ == '__main__':
    demo()
