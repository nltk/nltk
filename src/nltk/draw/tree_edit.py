"""
Tree.py is a simple tree-drawing program.  The tree must be in
Tree (label, child1, child2, ...) form, for this to work.
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


class Text:
    """
    Text class:  The Text class is little more than a slightly more complicated
    version of the Canvas_Text class.  It only consists of two components--the
    text itself and a rectangle behind the text which is only there for the
    purpose of hightlighting and unhighlighting the text.  If you do not want
    the highlight to be there, this class is unnecessary.

    * move (self, canvas, dx, dy) -> move the text and the rectangle dx and dy
    distance on the canvas.
    """
    
    def __init__(self, canvas, xloc, yloc, **attr):
        text = attr['text']
        color= attr['fill']
        # create the text at the xloc(ation) and yloc(ation)
        self.tag = tag = canvas.create_text(xloc, yloc, text=text, fill=color)

        # since we are highlighting only the area around the text, first
        # determine what that area is with canvas.bbox(item)
        bbox = canvas.bbox(self.tag)

        # set that area to rectangle and lower it behind the text
        self.rectangle = rectangle = canvas.create_rectangle(bbox, outline='')
        canvas.lower(self.rectangle)

        # highlight/unhighlight changes the fill color of the rectangle
        def highlight(event, canvas=canvas, rectangle=rectangle):
            canvas.itemconfig(rectangle, fill='lightblue')
        def unhighlight(event, canvas=canvas, rectangle=rectangle):
            canvas.itemconfig(rectangle, fill='')

        # bind highlight and unhighlight to when the mouse enters and leaves
        # (respectively) the area of the text
        canvas.tag_bind(rectangle, '<Enter>', highlight)
        canvas.tag_bind(tag, '<Enter>', highlight)
        canvas.tag_bind(rectangle, '<Leave>', unhighlight)
        canvas.tag_bind(tag, '<Leave>', unhighlight)

    def move(self, canvas, dx, dy):
        canvas.move(self.tag, dx, dy)
        canvas.move(self.rectangle, dx, dy)
    
class Draw_Node:
    """
    Draw_Node class: this is a structural class which stores all the
    important attributes and methods necessary to manipulate and print out
    the nodes of the tree.  Ideally it is little more than a wrapper for
    the Tree and Tree_Token classes.  More elegant code may have been able
    to do the tree drawing without having to declare new classes. 

    * string (self) -> returns the string that corresponds to the collapsed
    string of the node
    
    * display_collapsed (self, canvas, x, depth, options) -> draws the
    collapsed form of the node 

    * display_node (self, canvas, x, depth, options)  -> draws the node to
    the canvas

    -- NOTE:  This will be explained further in the tree_draw method of --
    -- window, so for now, just basically consider the x value in the   --
    -- above two methods as what should be the leftmost boundary for    --
    -- where you can draw the node and anything below it                --

    * move (self, canvas, dx, dy) -> move the node (and anything below it) dx
    and dy

    * dependancies (self) -> returns a list of all the descendants of the node
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

    def display_collapsed(self, canvas, dict):
        """
        draws the collapsed version of the node to the canvas
        """
        
        # get the attributes of the collapsed node
        text_color = dict['text']
        line_color = dict['lines']
        triangle_color = dict['shapes']

        # if your node is of type Tree originally, all you need to draw
        # is the label of the node (i.e. 'ip', 'np', etc.), the triangle below
        # it, and the collapsed string below that
        if self.type == 'Normal':
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      text=self.node,
                                      fill=text_color)
            self.collapsed_string = Text(canvas, self.xloc, self.yloc+50,
                                         text=self.string(),
                                         fill=text_color)

            # get the bbox of the collapsed string so we know how wide
            # to draw the base of the triangle
            bbox = canvas.bbox(self.collapsed_string.tag)
            self.triangle = canvas.create_polygon(self.xloc, self.yloc+10,
                                                  bbox[0], bbox[1]-10,
                                                  bbox[2], bbox[1]-10,
                                                  outline=line_color,
                                                  fill=triangle_color)

        # if the node is of type Tree_Token, you need to draw the label, the
        # triangle below it, the collapsed string below that, and the span of
        # the node, in total (for a description of span, see the Tree_Token
        # class)
        else:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      text=self.node,
                                      fill=text_color)
            self.collapsed_string = Text(canvas, self.xloc, self.yloc+50,
                                         text=self.string(),
                                         fill=text_color)
            if self.loc is None:
                self.span = Text(canvas, self.xloc, self.yloc+65,
                                 text='None',
                                 fill=text_color)
            else:
                text = '['+str(self.loc.start())+','+str(self.loc.end())+']'
                self.span = Text(canvas, self.xloc, self.yloc+65, 
                                 text=text,
                                 fill=text_color)

            # since we do not know which is wider, the collapsed string or
            # the span, we get the bbox of both at the same time
            bbox = canvas.bbox(self.collapsed_string.tag, self.span.tag)
            self.triangle = canvas.create_polygon(self.xloc, self.yloc+10,
                                                  bbox[0], bbox[1]-10,
                                                  bbox[2], bbox[1]-10,
                                                  outline=line_color,
                                                  fill=triangle_color)

        """
        # width basically determines the width of the uncollapsed node by
        # taking the bbox of the node label and all of the descendants of that
        # node
        def width(self=self, canvas=canvas):
            bbox = canvas.bbox(self.label.tag, self.dependancies())
            return bbox[2]-bbox[0]
        """

        return {'label':self.label,
                'new_x':self.xloc+(self.width/2),
                'triangle':self.triangle}
    
        
    def display_node(self, canvas, x, depth, dict):
        """
        draws the node to the canvas.  Basically this can be done in one of two
        senarios.  If we already have the xloc and yloc of the node (i.e. it
        has already been drawn) then just draw the node there, ignoring the
        arguments passed to you.  If however, one is drawing the nodes anew
        (for example, for the first time) then we draw the node at the x
        position and at 50*the depth (which is basically a variable relating
        to what level in the tree it is at)
        """
        
        text_color = dict['text']

        if self.xloc:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      text=self.node,
                                      fill=text_color)
        else:
            self.label = label = Text(canvas, x, depth*50,
                                      text=self.node,
                                      fill=text_color)
            # now that it has been drawn, save the xloc and yloc
            self.xloc = x
            self.yloc = depth*50

        if not self.width:
            bbox = canvas.bbox(label.tag, self.dependancies)
            self.width = bbox[2]-bbox[0]
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
                if instance(child, Draw_Token):
                    list.append(child.span.tag)
        return list

class Draw_Leaf:
    """
    Draw_Leaf class: a purely structural class, Draw_Leaf stores all
    important information for the leaves that are to be displayed.  Leaves can
    be of any type that can be represented as a string, so it can be a string,
    a number, etc.

    * display (self, canvas, x, depth, options) -> draw the leaf on the canvas

    * move (self, canvas, dx, dy) -> move the leaf dx and dy on the canvas
    """
    
    def __init__(self, data):
        self.data = str(data) # the actual value of the leaf
        self.label = None     # the drawn version of the leaf
        self.xloc = None
        self.yloc = None
        

    def display(self, canvas, x, depth, dict):
        """
        draws the leaf to the canvas.  Like Draw_Node, if it already has an
        xloc (and hence a yloc) then it will be drawn there.  Otherwise draw
        it at the x distance and 50*depth
        """

        text_color = dict['text']
        if self.xloc:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      text=self.data,
                                      fill=text_color)
        else:
            self.label = label = Text(canvas, x, depth*50,
                                      text=self.data,
                                      fill=text_color)

            # now that it is drawn, see whether the text itself breaches the
            # leftmost boundary that it is given (the vertical line at x).
            # if so, move it over until it does not
            bbox = canvas.bbox(label.tag)
            self.xloc = x
            self.yloc = depth*50
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


class Draw_Token:
    """
    Draw_Token class: a purely structural class, Draw_Token stores all important information
    for the leaves that are to be displayed

    * display(self, canvas, x, depth, options) -> draw the token on the canvas
    
    * move(self, canvas, dx, dy) -> move the token dx and dy on the canvas
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
        

    def display(self, canvas, x, depth, dict):
        """
        display will actually print out the token to the provided canvas.
        """
        
        text_color = dict['text']
        
        if self.xloc:
            self.label = label = Text(canvas, self.xloc, self.yloc,
                                      text=self.data,
                                      fill=text_color)
            self.span = span = Text(canvas, self.xloc, self.yloc+15,
                                    text=self.loc,
                                    fill=text_color)
        else:
            self.label = label = Text(canvas, x, depth*50,
                                      text=self.data,
                                      fill=text_color)
            self.span = span = Text(canvas, x, (depth*50)+15,
                                    text=self.loc,
                                    fill=text_color)
            
            # now that it is drawn, see whether the text itself breaches the
            # leftmost boundary that it is given (the vertical line at x).
            # if so, move it over until it does not
            bbox = canvas.bbox(label.tag, span.tag)
            self.xloc = x
            self.yloc = depth*50
            if bbox[0] < x:       # bbox[0] is the left boundary of the text
                self.move(canvas, x-bbox[0], 0)
        return {'label':self.label, 'span':self.span}





        """
        if self.
        self.tag = tag = Text(canvas, x, depth*50, text=self.data)
        self.span = span = canvas.create_text(x, (depth*50)+15, text=self.loc)
        
        bbox = canvas.bbox(tag,span)
        j = bbox[2]
        
        if bbox[0] < x :
            diff = x - bbox[0]
            canvas.move(tag, diff, 0)
            canvas.move(span, diff, 0)
            j += diff
        self.xloc = (j+x)/2
        self.yloc = depth*50
        #return tag
        return {'tag':self.tag, 'span':self.span, 'new_x':j}
        """
    def move(self, canvas, dx, dy):
        self.label.move(canvas, dx, dy)
        self.span.move(canvas, dx, dy)
        self.xloc += dx
        self.yloc += dy





class Window:
    """
    Window class: this is the overarching class in the program.  It contains
    all the things which control the actual window in which everything is
    drawn.

    * display (self) -> draw the tree

    * drawtree (self, node, left, depth) -> recursively draw the node and all its descendants (if
    there are any).  Returns the rightmost boundary of that node/descendants tree structure

    * several appearance-changing methods:
      - change_bg
      - change_text
      - change_line
    """
    
    ftypes = [('Postscript files', '.ps'),
              ('All files', '*')
              ]
    def __init__(self, tree):

        # default window setup

        self.appearance_dict = {'text':'black',
                                'bg':'white',
                                'lines':'black',
                                'shapes':'lightblue'}
        
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
        #self.c.bind('<Configure>', self.reconfigure)


        self.v_scroll= Scrollbar(self.right)
        self.v_scroll.pack(expand=Y, fill=Y)
        self.v_scroll.config(command = self.c.yview)
        self.c.config(yscrollcommand=self.v_scroll.set)
        
        self.h_scroll = Scrollbar(self.bottomleft, orient=HORIZONTAL)
        self.h_scroll.pack(fill=X)
        self.h_scroll.config(command = self.c.xview)
        self.c.config(xscrollcommand=self.h_scroll.set)


        # quit destroys the window
        def quit(self=self):self.top.destroy() 

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
                self.c.postscript(foo)

        # worthless function which just prints the x and y coordinate of the button click
        def myprint(event, self=self):
            print event.x, event.y

        c.bind('<Button-2>', myprint)
        Button(bottom, text='Save PS', command=onSavePS).pack(side=LEFT)
        Button(bottom, text='Expand All',
               command=expand).pack(side=LEFT)
        Button(bottom, text='Quit',
               command=quit).pack(side=RIGHT)


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
        funcmenu.add_command(label='Zoom-In') # these two not implemented yet
        funcmenu.add_command(label='Zoom-Out')
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
                                  command=(lambda x='black', y='lightblue', z=self:
                                         z.change_line(x,y)))
        linecolorlist.add_command(label='Green',
                                  command=(lambda x='green', y='#00FFCC', z=self:
                                           z.change_line(x,y)))
        linecolorlist.add_command(label='White',
                                  command=(lambda x='white', y='grey', z=self:
                                         z.change_line(x,y)))
        
        colormenu.add_cascade(label='BG color', menu=bgcolorlist)
        colormenu.add_cascade(label='Text color', menu=textcolorlist)
        colormenu.add_cascade(label='Line color', menu=linecolorlist) 

        menubar.add_cascade(label='Appearance', menu=colormenu)

        self.top.config(menu=menubar)


        # This is the key step, in which you take the tree you are given (in Tree or Tree_Token form)
        # and convert it to Draw_Node/Draw_Leaf/Draw_Token form
        self.tree = convert_tree(tree)
        self.width = 0


    # The following three methods are pretty self-explanatory
    
    def change_bg(self, color):
        self.appearance_dict['bg'] = color
        self.c.config(bg=color)

    def change_text(self, color):
        self.appearance_dict['text'] = color
        self.display()
        
    def change_line(self, line_color, triangle_color):
        self.appearance_dict['lines'] = line_color
        self.appearance_dict['shapes'] = triangle_color
        self.display()


    def display(self):
        """
        Effectively, this is like an update function.  Clear the screen, draw it, then set the
        scrollable region to include everything.
        """
        
        self.c.delete(ALL)

        # call drawtree on the root of the tree
        right = self.drawtree(self.tree, PADDING)
        bbox = self.c.bbox(ALL)
        self.c['scrollregion']=(0,0,bbox[2]+PADDING, bbox[3]+50)
        
    def drawtree(self, node, left=0, depth=1):
        """
        This is the main tree-drawing function.  It takes in a node,
        a leftmost boundary, and the depth of the node.  Basically, you work your way down the tree
        drawing each substructure at a time, starting from the left.  When you have all of the
        children of a node drawn, you can draw the node.  So let's say you have a tree like this:

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

        It will be drawn in the following order:
        
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


        It draws the node such that the text never an imaginary rectangle surrounding everything
        on the same level or below to the left of it.

        draw_tree works under one key assumption--that a collapsed node is never wider than an
        uncollaped one.  This is not such a bad assumtion, given that in an uncollapsed one, there
        is a distance between each leaf that is wider than the spaces between the words in the
        collapsed node.

        It returns the rightmost boundary of whatever is being drawn
        """
        
        x = left
        

        # callback function--calls toggle
        def cb(event, node=node, self=self):
            self.toggle(node)

        if node.collapsed == 1:
            # Draw a collapsed node
            
            result = node.display_collapsed(self.c, self.appearance_dict)

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
                                             self.appearance_dict)
                        bbox = self.c.bbox(text.tag)
                        x = bbox[2]      # bbox[2] returns the farthest right boundary
                                         # of the canvas text
                    else :
                        result = child.display(self.c,
                                               x, depth+1,
                                               self.appearance_dict)
                        label = result['label']
                        span = result['span']
                        bbox = self.c.bbox(label.tag, span.tag)
                        x = bbox[2]

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
                                     self.appearance_dict)
            self.c.tag_bind(text.tag, '<Button-1>', cb)

            # go through all the children, drawing arrows from the parent to the children
            for child in node.children:
                arrow =  self.c.create_line(node.xloc, node.yloc+10,
                                            child.xloc, child.yloc-10,
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

        return x + 8 # for padding


    def toggle(self, node):
        """
        This function changes the status of the node that was clicked, then calls the
        window to redraw the whole thing
        """

        # what this checks is that if you only have one child, collapsing the node is worthless
        if len(node.children) == 1:
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
    w.display()

def drawtreetoken(tree):
    """
    display the given tree_token tree
    """
    
    w = Window(tree)
    w.display()



if __name__ == '__main__':

    t=Tree('ip',
           Tree('dnfgojrhslkjghrlkjghdrlghp',
                Tree('d', 'a'),
                Tree('n', 'cat')),
           Tree('vbeqkjhfdkjahdkjwa',
                Tree('v', 'saw'),
                Tree('dp',
                     Tree('dp',
                          Tree('srghldsgldrkjgldksjgd', 'a'),
                          Tree('adj', 'blue'),
                          Tree('akj', 'convicted'),
                          ),
                     Tree('n', 'dog')
                     )
                )
           )

    d = TreeToken('ip',Token('a',1),Token('cat',2))

    d2=TreeToken('ip',
                 TreeToken('dp',
                           TreeToken('d', Token('a',1)),
                           TreeToken('n', Token('cat',2))),
                 TreeToken('vp',
                           TreeToken('v', Token('saw',3)),
                           TreeToken('dp',
                                     TreeToken('d', Token('a',4)),
                                     TreeToken('n', Token('dog',5)))))

    d3 = TreeToken('ip', Token('a'), Token('cat'))
    #drawtree(t)
    w = Window(d2)
    w.display()
