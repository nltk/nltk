# Natural Language Toolkit: A Tree Editor
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
A simple tree-editing tool.  This tool is not yet fully functional.

This tool will most likely be re-written to use the new canvas widget
framework (TreeSegmentWidgets in particular).
"""

"""
I may want to get rid of the interactive scrollregion.
I like the way it just keeps 0,0 as the left boundary.  Otherwise,
it looks a little choppy

NOTE: FIX DESTROY AND QUIT

"""


# The next few lines all deal with importing the proper modules

from Tkinter import *
import os
import sys


twoBack = os.pardir+os.sep+os.pardir

if not twoBack in sys.path:
    sys.path.append(twoBack)



import nltk.tree; reload(nltk.tree) 
from nltk.tree import Tree 
from nltk.tree import TreeToken 
from nltk.token import Token 
from nltk.token import Location 
from tkFileDialog import *
import string


HIGHLIGHT = '#CCCCFF'
HIGHLIGHT2 = '#FFFF99'

X_SPACING = 10
Y_SPACING = 50
FONT_SIZE = 10 # default value


RATIO = 1.0

class Text:
    """
    Text class:  The Text class is little more than a slightly more complicated
    version of the Canvas_Text class.  It only consists of two components--the
    text itself and a rectangle behind the text which is only there for the
    purpose of hightlighting and unhighlighting the text.  If you do not want
    the highlight to be there, this class is unnecessary.
    """
    
    def __init__(self, canvas, xloc, yloc, font_dict, **attr):
        text = attr['text']
        color= attr['fill']
        style = attr['style']

        size = font_dict['size']
        if 'size' in attr.keys():
            size = attr['size']
        #print size
        family = font_dict['family']
        
        
        # create the text at the xloc(ation) and yloc(ation)
        self.tag = tag = canvas.create_text(xloc, yloc,
                                            text=text,
                                            fill=color,
                                            font = (family,
                                                    size,
                                                    style))

        # since we are highlighting only the area around the text, first
        # determine what that area is with canvas.bbox(item)
        bbox = canvas.bbox(self.tag)

        self.height = bbox[3]-bbox[1]
        self.width = bbox[2]-bbox[0]
        
        # set that area to rectangle and lower it behind the text
        self.rectangle = rectangle = canvas.create_rectangle(bbox, outline='')
        canvas.lower(self.rectangle)
        
        # highlight/unhighlight changes the fill color of the rectangle
        def highlight(event, self=self, canvas=canvas, rectangle=rectangle, style=style):
            if style is 'normal':
                canvas.itemconfig(rectangle, fill='light grey')
            else:
                canvas.itemconfig(rectangle, fill=HIGHLIGHT)
        def unhighlight(event, canvas=canvas, rectangle=rectangle):
            canvas.itemconfig(rectangle, fill='')

        # bind highlight and unhighlight to when the mouse enters and leaves
        # (respectively) the area of the text
        canvas.tag_bind(rectangle, '<Enter>', highlight)
        canvas.tag_bind(tag, '<Enter>', highlight)
        canvas.tag_bind(rectangle, '<Leave>', unhighlight)
        canvas.tag_bind(tag, '<Leave>', unhighlight)

        def print_tag(event, tag=tag, rectangle=rectangle):
            print tag,rectangle

        canvas.tag_bind(rectangle, '<Button-3>', print_tag)
        canvas.tag_bind(tag, '<Button-3>', print_tag)

    def move(self, canvas, dx, dy):
        """
        move the text and the rectangle dx and dy distance on the
        canvas.
        """
        canvas.move(self.tag, dx, dy)
        canvas.move(self.rectangle, dx, dy)

    def delete(self, canvas):
        canvas.delete(self.tag)
        canvas.delete(self.rectangle)
    
class Draw_Node:
    """
    Draw_Node class: this is a structural class which stores all the
    important attributes and methods necessary to manipulate and print out
    the nodes of the tree.  Ideally it is little more than a wrapper for
    the Tree and Tree_Token classes.  More elegant code may have been able
    to do the tree drawing without having to declare new classes. 

    B{NOTE:  This will be explained further in the tree_draw method of
    window, so for now, just basically consider the x value in the
    above two methods as what should be the leftmost boundary for
    where you can draw the node and anything below it}
    """
    
    def __init__(self, node):
        """
        __init__ -> takes in a node from the original tree and, depending on
        whether it is a Tree node or a Tree_Token node, adjusts the attributes
        accordingly
        """

        self.children = []
        self.width = None
        
        # self.collapsed keeps track of whether the node has been collapsed
        # into a single node.  To begin with, it should be uncollapsed
        self.collapsed = 0

        
        if isinstance(node,Tree):
            self.node = node.node()
            self.type = 'Normal'
        else:
            self.node = str((node.type()).node())
            self.type = 'Tree Token'
            # tree_tokens have these two extra pieces of data which we
            # need to keep track of
            self.loc = node.loc()
            #self.span = None
            

        # the label attribute will store the text that is drawn to canvas
        self.label = None

        # the location of the node.  This can be stored to facilitate
        # collapsing the node and (given time) methods like moving the node
        self.xloc = None
        self.yloc = None

        # a list for all the arrows going from the node to all the children
        self.arrow_list = []

        # the next two are only used if the node is collapsed
        # but its easier and more streamlined to include them
        # in this class than it would be to make another class
        self.collapsed_string = None
        self.triangle = None

    def string(self):
        """
        returns the string representing the collapsed node
        """
        
        string = ''

        # go through all the children and recursively determine determine
        # their collapsed strings
        for child in self.children:
            if isinstance(child, Draw_Node):
                string += child.string() + ' '
            else:
                string += (child.data) + ' '
                
        string = string[:-1]  #to get rid of that last whitespace
        return string

    def display_collapsed(self, canvas, x, depth, font_dict, app_dict):
        """
        draws the collapsed version of the node to the canvas
        """
        
        # get the attributes of the collapsed node
        text_color = app_dict['text']
        line_color = app_dict['lines']
        triangle_color = app_dict['shapes']

        shift = int(Y_SPACING*font_dict['ratio'])
        
        ghost = Text(canvas, 0, 0,
                     font_dict,
                     text='Al^|qp',
                     fill=app_dict['bg'], style='bold')
        height = ghost.height
        ghost.delete(canvas)

        # if your node is of type Tree originally, all you need to draw
        # is the label of the node (i.e. 'ip', 'np', etc.), the triangle below
        # it, and the collapsed string below that
        if self.type == 'Normal':
            self.label = label = Text(canvas, x, depth*shift,
                                      font_dict,
                                      text=self.node,
                                      fill=text_color,
                                      style='bold')
            self.collapsed_string = Text(canvas, x, (depth+1)*shift,
                                         font_dict,
                                         text=self.string(),
                                         fill=text_color,
                                         style='normal')

            # get the bbox of the collapsed string so we know how wide
            # to draw the base of the triangle
            bbox = canvas.bbox(self.collapsed_string.tag)
            self.triangle = canvas.create_polygon(x, (depth*shift)+height,
                                                  bbox[0], bbox[1]-(height/2),
                                                  bbox[2], bbox[1]-(height/2),
                                                  outline=line_color,
                                                  fill=triangle_color)
            
        # if the node is of type Tree_Token, you need to draw the label, the
        # triangle below it, the collapsed string below that, and the span of
        # the node, in total (for a description of span, see the Tree_Token
        # class)
        else:
            self.label = label = Text(canvas, x, depth*shift,
                                      font_dict,
                                      text=self.node,
                                      fill=text_color,
                                      style='bold')
            self.collapsed_string = Text(canvas, x, (depth+1)*shift,
                                         font_dict,
                                         text=self.string(),
                                         fill=text_color,
                                         style='normal')
            if self.loc is None:
                self.span = Text(canvas, x, ((depth+1)*shift)+height,
                                 font_dict,
                                 text='None',
                                 fill=text_color,
                                 style='normal')
            else:
                text = '['+str(self.loc.start())+','+str(self.loc.end())+']'
                self.span = Text(canvas, x, ((depth+1)*shift)+height,
                                 font_dict,
                                 text=text,
                                 fill=text_color,
                                 style='normal')

            # since we do not know which is wider, the collapsed string or
            # the span, we get the bbox of both at the same time
            bbox = canvas.bbox(self.collapsed_string.tag, self.span.tag)
            self.triangle = canvas.create_polygon(x, (depth*shift)+height,
                                                  bbox[0], bbox[1]-(height/2),
                                                  bbox[2], bbox[1]-(height/2),
                                                  outline=line_color,
                                                  fill=triangle_color)

        def highlight_triangle (event, self=self, canvas=canvas):
            canvas.itemconfig(self.triangle, fill=HIGHLIGHT2)

        def unhighlight_triangle(event, self=self, canvas=canvas):
            canvas.itemconfig(self.triangle, fill=HIGHLIGHT)

        canvas.tag_bind(self.triangle, '<Enter>', highlight_triangle)
        canvas.tag_bind(self.triangle, '<Leave>', unhighlight_triangle)

        self.xloc = x
        self.yloc = depth*shift
        return {'label':self.label,
                'new_x':self.xloc+(self.width/2),
                'triangle':self.triangle}
    
        
    def display_node(self, canvas, x, depth, font_dict, app_dict):
        """
        draws the node to the canvas.  Basically this can be done in one of two
        senarios.  If we already have the xloc and yloc of the node (i.e. it
        has already been drawn) then just draw the node there, ignoring the
        arguments passed to you.  If however, one is drawing the nodes anew
        (for example, for the first time) then we draw the node at the x
        position and at 50*the depth (which is basically a variable relating
        to what level in the tree it is at)
        """
        
        text_color = app_dict['text']

        if 1 < 0:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      font_dict,
                                      text=self.node,
                                      fill=text_color,
                                      style='bold')
        else:
            shift = int(Y_SPACING*font_dict['ratio'])
            self.label = label = Text(canvas, x, depth*shift,
                                      font_dict,
                                      text=self.node,
                                      fill=text_color,
                                      style='bold')
            # now that it has been drawn, save the xloc and yloc
            self.xloc = x
            self.yloc = depth*shift

        """
        if not self.width:
            bbox = canvas.bbox(label.tag, self.dependancies())
            self.width = bbox[2]-bbox[0]
        """
        
        return label

    def move(self, canvas, dx, dy):
        """
        move the node and all of the members of the tree below it
        dx places in the x direction and dy in the y direction
        """
        # if it is collaped, just move the label, the triangle, and the
        # collapsed string
        if self.collapsed == 1:
            self.label.move(canvas, dx, dy)
            self.collapsed_string.move(canvas, dx, dy)
            canvas.move(self.triangle, dx, dy)

        # else, go through the children and recursively call move on them, then
        # move all the arrows the requisite amount as well.
        else: 
            for child in self.children:
                child.move(canvas, dx, dy)

            self.label.move(canvas, dx, dy)

            for arrow in self.arrow_list:
                canvas.move(arrow, dx, dy)

        # update the xloc and yloc of the node
        self.xloc += dx
        self.yloc += dy
        
    def dependancies(self):
        """
        return a list of all the descendants of the node.  Reursive.
        """
        
        list = []
        for child in self.children:
            if isinstance(child, Draw_Node):
                l = child.dependancies()
                list = list + l
                list.append(child.label.tag)
            else:
                list.append(child.label.tag)
                if isinstance(child, Draw_Token):
                    list.append(child.span.tag)
        return list

    def depth(self):
        d = 0
        for child in self.children:
            x = child.depth()+1
            if x > d:
                d = x
        return d
   

class Draw_Leaf:
    """
    Draw_Leaf class: a purely structural class, Draw_Leaf stores all
    important information for the leaves that are to be displayed.  Leaves can
    be of any type that can be represented as a string, so it can be a string,
    a number, etc.
    """
    
    def __init__(self, data):
        self.data = str(data) # the actual value of the leaf
        self.label = None     # the drawn version of the leaf
        self.xloc = None
        self.yloc = None
        

    def display(self, canvas, x, depth, font_dict, app_dict):
        """
        draws the leaf to the canvas.  Like Draw_Node, if it already has an
        xloc (and hence a yloc) then it will be drawn there.  Otherwise draw
        it at the x distance and 50*depth
        """

        text_color = app_dict['text']
        if 1 < 0:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      font_dict,
                                      text=self.data,
                                      fill=text_color,
                                      style='normal')
        else:
            shift = int(Y_SPACING * font_dict['ratio'])
            self.label = label = Text(canvas, x, depth*shift,
                                      font_dict,
                                      text=self.data,
                                      fill=text_color,
                                      style='normal')

            # now that it is drawn, see whether the text itself breaches the
            # leftmost boundary that it is given (the vertical line at x).
            # if so, move it over until it does not
            bbox = canvas.bbox(label.tag)
            self.xloc = x
            self.yloc = depth*shift
            if bbox[0] < x:       # bbox[0] is the left boundary of the text
                self.move(canvas, x-bbox[0], 0)
        return label

    def move(self, canvas, dx, dy):
        """
        move the leaf dx horizontally and dy vertically
        """
        
        self.label.move(canvas, dx, dy)
        self.xloc += dx
        self.yloc += dy

    def depth(self):
        return 1

class Draw_Token:
    """
    Draw_Token class: a purely structural class, Draw_Token stores all important information
    for the leaves that are to be displayed
    """
    
    def __init__(self, token):
        self.data = str(token.type())
        
        loc = token.loc()     # thus, loc is of type Location
        
        if loc is None:
            self.loc = 'None'
        else:
            start = str(loc.start())
            end = str(loc.end())
            self.loc = '['+start+','+end+']'  # save the sorrect location ifo for the token
            
        self.label = None #will store the tag for the printed text
        self.span = None # will store the tag for the span text
        self.xloc = 0
        self.yloc = 0
        

    def display(self, canvas, x, depth, font_dict, app_dict):
        """
        display will actually print out the token to the provided canvas.
        """
        
        text_color = app_dict['text']
        
        if 1 < 0:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      font_dict,
                                      text=self.data,
                                      fill=text_color,
                                      style='normal')
            self.span = span = Text(canvas, self.xloc, self.yloc+15,
                                    font_dict,
                                    text=self.loc,
                                    fill=text_color,
                                    style='normal')
        else:
            ghost_text = Text(canvas, 0, 0,
                              font_dict,
                              text='Al^|qp',
                              fill=app_dict['bg'],
                              style='bold',
                              size=font_dict['size'])
            text_height = ghost_text.height
            ghost_text.delete(canvas)
            
            shift = int (Y_SPACING * font_dict['ratio'])
            self.label = label = Text(canvas, x, depth*shift,
                                      font_dict,
                                      text=self.data,
                                      fill=text_color,
                                      style='normal')
            self.span = span = Text(canvas, x, (depth*shift)+text_height,
                                    font_dict,
                                    text=self.loc,
                                    fill=text_color,
                                    style='normal')
            
            # now that it is drawn, see whether the text itself breaches the
            # leftmost boundary that it is given (the vertical line at x).
            # if so, move it over until it does not
            bbox = canvas.bbox(label.tag, span.tag)
            self.xloc = x
            self.yloc = depth*shift
            if bbox[0] < x:       # bbox[0] is the left boundary of the text
                self.move(canvas, x-bbox[0], 0)
        return {'label':self.label, 'span':self.span}





    def move(self, canvas, dx, dy):
        self.label.move(canvas, dx, dy)
        self.span.move(canvas, dx, dy)
        self.xloc += dx
        self.yloc += dy

    def depth (self):
        return 1

class Window:
    """
    Window class: this is the overarching class in the program.  It contains
    all the things which control the actual window in which everything is
    drawn.
    """
    
    ftypes = [('Postscript files', '.ps'),
              ('All files', '*')
              ]
    def __init__(self, tree):

        # default window setup

        self.appearance_dict = {'text':'black',
                                'bg':'white',
                                'lines':'black',
                                'shapes':HIGHLIGHT}
        self.font_dict = {'size':10,
                          'family':'helvetica',
                          'ratio':1.0
                          }
        
        self.top = top = Tk()

        self.bottom = bottom = Frame(top) # will hold the shortcut buttons
        self.window = window = Frame(top) # will hold the canvas and the scrollbars
        bottom.pack(fill=X, side=BOTTOM)
        window.pack(fill=BOTH, expand=YES)
        self.right = Frame(window) # will hold the vertical scrollbar
        self.left = Frame(window) # will hold the canvas and the horizontal scrollbar
        self.right.pack(side=RIGHT, fill=Y)
        self.left.pack(side=LEFT, fill=BOTH, expand=Y)
        self.topleft = Frame(self.left) # will hold the canvas
        self.bottomleft = Frame(self.left) # will hold the horizontal scrollbar
        self.bottomleft.pack(side=BOTTOM, fill=X)
        self.topleft.pack(expand=Y, fill=BOTH)
        

        self.c = c = Canvas(self.topleft, height=300, width=200,
                            bg=self.appearance_dict['bg'])
        c.pack(fill=BOTH, expand=YES)
                
        self.v_scroll= Scrollbar(self.right)
        self.v_scroll.pack(expand=Y, fill=Y)
        self.v_scroll.config(command = self.c.yview)
        self.c.config(yscrollcommand=self.v_scroll.set)
        
        self.h_scroll = Scrollbar(self.bottomleft, orient=HORIZONTAL)
        self.h_scroll.pack(fill=X)
        self.h_scroll.config(command = self.c.xview)
        self.c.config(xscrollcommand=self.h_scroll.set)


        # quit destroys the window
        def quit(self=self):
            self.top.quit()
            #self.destroy() 
            
        # expand all the nodes, delete the tree, then draw it
        def expand(self=self):
            self.expand_all(self.tree)
            self.c.delete(ALL)
            self.display()

        # save the postscript of the canvas
        def onSavePS(self=self, forcefile=None):
            # asksaveasfilename is imported in the beginning.  It handles displaying your directory
            # structure so you know what to save the name of the ps as
            foo = asksaveasfilename(filetypes=self.ftypes,
                                    defaultextension='.ps')
            if foo:
                self.c.postscript(file=foo)
                
            
        # worthless function which just prints the x and y coordinate of the button click
        def myprint(event, self=self):
            print event.x, event.y

        c.bind('<Button-2>', myprint)
        Button(bottom, text='+', command=self.zoom_in).pack(side=LEFT)
        Button(bottom, text='-', command=self.zoom_out).pack(side=LEFT)
        
        Button(bottom, text='Done',
               command=quit).pack(side=RIGHT)
        Button(bottom, text='PS', command=onSavePS).pack(side=RIGHT)
        Button(bottom, text='Expand All',
               command=expand).pack()
        
        def destroy(event, self=self):
            if self.top:
                self.top.destroy()
                self.top = None
                
        self.top.bind('q', destroy)
        
        # make the menu bar at the top.  It should have the structure:
        #  -File            -Functions         -Appearance
        # ------------------------------------------------
        #  *Save PS...      *Expand All        *BG Color
        #  *Exit                               *Text Color
        #                                      *Line Color
        
        menubar=Menu(self.top)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label='Save PS...', command=onSavePS)
        filemenu.add_command(label='Exit', command=quit)
        menubar.add_cascade(label='File', menu=filemenu)

        funcmenu = Menu(menubar, tearoff=0)
        funcmenu.add_command(label='Expand All', command=expand)
        funcmenu.add_command(label='Zoom-In', command=self.zoom_in)
        funcmenu.add_command(label='Zoom-Out', command=self.zoom_out)
        menubar.add_cascade(label='Functions', menu=funcmenu)


        colormenu = Menu(menubar, tearoff=0)

        bgcolorlist = Menu(colormenu, tearoff=0)
        bgcolorlist.add_command(label='White',
                                command=(lambda x='white', y=self:
                                         y.change_bg(x)))
        bgcolorlist.add_command(label='Blue',
                                command=(lambda x='blue', y=self:
                                         y.change_bg(x)))
        bgcolorlist.add_command(label='Grey',
                                command=(lambda x='grey', y=self:
                                         y.change_bg(x)))
        bgcolorlist.add_command(label='Black',
                                command=(lambda x='black', y=self:
                                         y.change_bg(x)))


        textcolorlist = Menu(colormenu, tearoff=0)
        textcolorlist.add_command(label='White',
                                  command=(lambda x='white', y=self:
                                           y.change_text(x)))
        textcolorlist.add_command(label='Green',
                                  command=(lambda x='green', y=self:
                                           y.change_text(x)))
        textcolorlist.add_command(label='Black',
                                  command=(lambda x='black', y=self:
                                           y.change_text(x)))
        
        
        linecolorlist = Menu(colormenu, tearoff=0)
        linecolorlist.add_command(label='Black',
                                  command=(lambda x='black', y=self:
                                           y.change_line(x)))
        linecolorlist.add_command(label='Green',
                                  command=(lambda x='green', y=self:
                                           y.change_line(x)))
        linecolorlist.add_command(label='White',
                                  command=(lambda x='white', y=self:
                                           y.change_line(x)))
        
        colormenu.add_cascade(label='BG color', menu=bgcolorlist)
        colormenu.add_cascade(label='Text color', menu=textcolorlist)
        colormenu.add_cascade(label='Line color', menu=linecolorlist) 

        menubar.add_cascade(label='Appearance', menu=colormenu)

        self.top.config(menu=menubar)


        # This is the key step, in which you take the tree you are given (in Tree or Tree_Token form)
        # and convert it to Draw_Node/Draw_Leaf/Draw_Token form
        self.tree = convert_tree(tree)
        self.width = 0

        ### NEW STUFF ###
        self.altered = 0
        #self.c.bind('<Button-3>', self.set_point)
        
        
        ########################################################
        
        self.display()
        #self.top.mainloop()
        
    # The following three methods are pretty self-explanatory
    
    def change_bg(self, color):
        self.appearance_dict['bg'] = color
        self.c.config(bg=color)

    def change_text(self, color):
        self.appearance_dict['text'] = color
        self.display()
        
    def change_line(self, line_color):
        self.appearance_dict['lines'] = line_color
        self.display()


    def display(self):
        """
        Effectively, this is like an update function.  Clear the
        screen, draw it, then set the scrollable region to include
        everything.
        """
        
        self.c.delete(ALL)

        # call drawtree on the root of the tree
        right = self.drawtree(self.tree, PADDING)

        bbox = self.c.bbox(ALL)
        print bbox
        self.c['scrollregion']=(bbox[0]-PADDING, bbox[1]-50,
                                bbox[2]+PADDING, bbox[3]+50)
        self.c['width'] = min(bbox[2]-bbox[0]+(2*PADDING), 800)
        self.c['height'] = min(bbox[3]-bbox[1], 300)
        
    def drawtree(self, node, left=0, depth=1):
        """
        This is the main tree-drawing function.  It takes in a node, a
        leftmost boundary, and the depth of the node.  Basically, you
        work your way down the tree drawing each substructure at a
        time, starting from the left.  When you have all of the
        children of a node drawn, you can draw the node.  So let's say
        you have a tree like this::

                   n1
                   |
               ----------
              |          |
              n2         n3
              |          |
            -----      -----
           |     |    |     |
           n4    n5   n6    n7
                            |
                          -----
                         |     |
                         n8    n9

        It will be drawn in the following order::
        
                   9
                   |
               ----------
              |          |
              3          8
              |          |
            -----      -----
           |     |    |     |
           1     2    4     7
                            |
                          -----
                         |     |
                         5     6


        It draws the node such that the text never an imaginary
        rectangle surrounding everything on the same level or below to
        the left of it.

        drawtree works under one key assumption--that a collapsed node
        is never wider than an uncollaped one.  This is not such a bad
        assumtion, given that in an uncollapsed one, there is a
        distance between each leaf that is wider than the spaces
        between the words in the collapsed node.

        It returns the rightmost boundary of whatever is being drawn
        """
        
        x = left
        

        # callback function--calls toggle
        def cb(event, node=node, self=self):
            self.toggle(node)

        if node.collapsed == 1:
            # Draw a collapsed node
            parentx = x + (node.width/2)
            
            result = node.display_collapsed(self.c, parentx, depth,
                                            self.font_dict,
                                            self.appearance_dict)

            # you use these tags here in order to apply the expand/collapse method toggle to the
            # label and to the triangle drawn
            text2 = result['label']
            triangle = result['triangle']
            x = result['new_x'] # the new rightmost axis
            self.c.tag_bind(text2.tag, '<Button-1>', cb)
            self.c.tag_bind(triangle, '<Button-1>', cb)


        else:
            for child in node.children:
                if isinstance(child, Draw_Node):
                    # draw that child at the next lowest depth
                    newx = self.drawtree(child, x, depth+1)

                    # now update your rightmost boundary 
                    x = newx

                else:
                    if isinstance(child, Draw_Leaf):
                        # draw the leaf node.
                        text = child.display(self.c,
                                             x, depth+1,
                                             self.font_dict,
                                             self.appearance_dict)
                        bbox = self.c.bbox(text.tag)
                        #x = bbox[2]
                    else :
                        result = child.display(self.c,
                                               x, depth+1,
                                               self.font_dict,
                                               self.appearance_dict)
                        label = result['label']
                        span = result['span']
                        bbox = self.c.bbox(label.tag, span.tag)
                    x = bbox[2]+int (X_SPACING*self.font_dict['ratio'])

            # Now, you can draw the parent.  Note that we couldn't calculate parentx until
            # now, since we didn't know how big the children were going to be.

            # the following bit of code just ensures that if you have an odd number of children,
            # you draw the node over the middle one.  Otherwise, you draw it in between the two
            # middle children
            
            number = len(node.children)  
            if (number % 2) == 0 :  
                l = number/2 - 1  
                r = l + 1  
                parentx = ((node.children[l].xloc)+(node.children[r].xloc))/2  
            else:  
                parentx = node.children[number/2 ].xloc 
           
            # draw the node and bind the text to the callback function
            text = node.display_node(self.c,
                                     parentx, depth,
                                     self.font_dict,
                                     self.appearance_dict)
            self.c.tag_bind(text.tag, '<Button-1>', cb)

            # go through all the children, drawing arrows from the parent to the children
            text_height = self._get_text_height(self.font_dict['size'])
            
            for child in node.children:
                arrow =  self.c.create_line(node.xloc, node.yloc+(text_height/2),
                                            child.xloc, child.yloc-(text_height/2),
                                            fill=self.appearance_dict['lines'])
                node.arrow_list.append(arrow)
                
            # Check whether the node tag is wider than its children
            # if so, move all of it's descendants and arrows that distance

            bbox = self.c.bbox(text.tag)
            x = max(bbox[2], x)
            if (bbox[0] < left) :
                diff = left-bbox[0]
                node.move(self.c, diff, 0)
                x += diff
                
            node.width=x - left

        #print "for node %s, x is %d" % (node.node, x)
        return x + int (X_SPACING*self.font_dict['ratio']) # for padding


    def toggle(self, node):
        """
        This function changes the status of the node that was clicked, then calls the
        window to redraw the whole thing
        """

        # what this checks is that if you only have one child and a depth of 1 or less, then
        # collapsing the node is worthless
        
        if len(node.children) == 1 and node.depth() <= 1:
            pass
        else:
            node.collapsed = not node.collapsed

            self.c.delete(ALL)

            self.display()

    def expand_all(self, node):
        """
        sets the collapsed attribute of all nodes to 0
        """
        if isinstance(node, Draw_Node):
            for child in node.children:
                self.expand_all(child)
                node.collapsed = 0
        else:
            pass


    def _get_text_height(self, size):
        t = Text(self.c, 0, 0,
                 self.font_dict,
                 text='Al^|qp',
                 fill=self.appearance_dict['bg'],
                 style='bold',
                 size=size)
        height = t.height
        t.delete(self.c)
        #self.c.delete(t.tag)
        return height
    
    def zoom_in(self):
        old_size = self.font_dict['size']
        old = self._get_text_height(old_size)
        new_size = old_size
        new = self._get_text_height(new_size)
        
        while new == old:
            new_size += 2
            new = self._get_text_height(new_size)
        self.c.delete(ALL)
        self.font_dict['size']=new_size
        self.font_dict['ratio'] = float(new)/float(self._get_text_height(FONT_SIZE))
        print self.font_dict['ratio']
        self.display()

    def zoom_out(self):
        old_size = self.font_dict['size']
        if old_size == 6 : return
        else :
            old = self._get_text_height(old_size)
            new_size = old_size
            new = self._get_text_height(new_size)
        
            while new == old and new_size > 6:
                new_size -= 2
                new = self._get_text_height(new_size)
            self.c.delete(ALL)
            self.font_dict['size']=new_size
            self.font_dict['ratio'] = float(new)/float(self._get_text_height(FONT_SIZE))
            print self.font_dict['ratio']
            self.display()
 
    def make_new_tree(self):
        self.altered = 1
        
    
PADDING = 20
MAXWIDTH = 600
MAXHEIGHT = 600

def convert_tree(tree):
    """
    this function will recursively go through a Tree and return a tree
    in Draw_Node/Draw_Leaf/Draw_Token form
    """
    if isinstance(tree, Tree) or isinstance(tree, TreeToken):
        root = Draw_Node(tree)
        for child in tree:
            root.children.append(convert_tree(child))
    elif isinstance(tree, Token):
        root = Draw_Token(tree)
    else: 
        root = Draw_Leaf(tree)  
 
    return root

def drawtree(tree):
    """
    display the given tree
    """
    
    w = Window(tree)
    
def drawtreetoken(tree):
    """
    display the given tree_token tree
    """
    
    w = Window(tree)
    


if __name__ == '__main__':


    from random import randint
    def randomtree(depth=0, bf=None):
        if bf == None: bf = randint(1,2)
        if randint(0,7-depth) == 0 and depth>1:
            return 'L%d' % randint(0, 10)
        else:
            numchildren = randint(1,bf)
            children = [randomtree(depth+1, bf) for x in range(numchildren)]
            return Tree('Node %d' % randint(0,10000), *children)

    def randomtreetok(depth=0, left=0, bf=None):
        if bf == None: bf = randint(1,2)
        if randint(0,7-depth) == 0 and depth>1:
            len = randint(1,5)
            return Token('L%d' % randint(0, 10), left, left+len)
        else:
            numchildren = randint(1,bf)
            children = []
            for x in range(numchildren):
                children.append(randomtreetok(depth+1, left, bf))
                left = children[-1].loc().end()
            return TreeToken('Node %d' % randint(0,10000), *children)

    if randint(1,1) ==0:
        t = randomtree()
        while not (5 < len(t.leaves()) < 25):
            t = randomtree()
    else:
        t = randomtreetok()
        while not (5 < len(t.leaves()) < 25):
            t = randomtreetok()





    d = Tree('ip', 'none','foo')

    w = Window(t)
    w.display()

