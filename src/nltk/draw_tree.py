from Tkinter import *

import tree; reload(tree) 
from tree import Tree 
from tree import TreeToken 
from token import Token 
from token import Location 

"""
from tree import Tree
from tree import TreeToken
from token import Token
from token import Location
"""

class Draw_Node:
    """
    this is a structural class which stores all the important attributes
    and methods necessary to manipulate and print out the nodes of the tree
    """
    def __init__(self, node):
        self.children = []
        self.collapsed = 0
        self.node = str(node)
        self.tag = None
        self.xloc = 0
        self.yloc = 0
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
        for child in self.children:
            if isinstance(child, Draw_Node):
                string += child.string() + ' '
            else:
                string += (child.data) + ' '
        string = string[:-1]  #to get rid of that last whitespace
        return string

    def display_collapsed(self, canvas, x, depth, left):
        """
        prints the collapsed version of the node to screen
        """

        self.collapsed_string = canvas.create_text(x, (depth+1)*50,
                                                   text=self.string(),
                                                   anchor='w')
        bbox = canvas.bbox(self.collapsed_string)
        j = bbox[2] + 4
        parentx = (j+left)/2
        self.tag = canvas.create_text(parentx, (depth*50), text=self.node)
        self.xloc = parentx
        self.yloc = depth*50
        self.triangle = canvas.create_polygon(parentx, depth*50+10,
                                              bbox[0], (depth+1)*50-10,
                                              bbox[2], (depth+1)*50-10,
                                              outline='black',
                                              fill='lightblue')
        # Check if the node label is bigger than its string
        # if so, shift everything over
        
        bbox2 = canvas.bbox(self.tag)
        x2 = bbox2[2] + 4
        if x2 > j:
            diff = x2 - j
            self.move(canvas, diff-1, 0)
            j = x2 + diff
        return {'tag':self.tag, 'new_x':j, 'triangle':self.triangle}
    
        
    def display_node(self, canvas, x, depth):
        """
        prints the node to window
        """
        self.tag = tag = canvas.create_text(x, depth*50,
                                            text=self.node,
                                            anchor='c')
        self.xloc = x
        self.yloc = depth*50
        bbox = canvas.bbox(self.tag)
        width = bbox[2]-bbox[0]
        return tag

    def move(self, canvas, dx, dy):
        """
        move the node and all of the members of the tree below it
        dx places in the x direction and dy in the y direction
        """
        if self.collapsed == 1:
            canvas.move(self.tag, dx, dy)
            canvas.move(self.collapsed_string, dx, dy)
            canvas.move(self.triangle, dx, dy)
        else: 
            for child in self.children:
                child.move(canvas, dx, dy)

            canvas.move(self.tag, dx, dy)

            for arrow in self.arrow_list:
                canvas.move(arrow, dx, 0)

        # update the xloc and yloc of the node
        self.xloc += dx
        self.yloc += dy

    def tree_depth(self, i):
        """
        returns the max depth at a specific node relative to the number i
        in most cases, on its first call, it will
        """
        children_depths = []
        for child in self.children:
            j = child.tree_depth(i+1)
            children_depths.append(j)
        return max(children_depths)
        



class Draw_Leaf:
    """
    a purely structural class, Draw_Leaf stores all important information
    for the leaves that are to be displayed
    """
    
    def __init__(self, data):
        self.data = str(data)
        self.tag = None #will store the tag for the printed text
        self.xloc = 0
        self.yloc = 0
        
    def tree_depth(self, i):
        return i  

    def display(self, canvas, x, depth):
        """
        display will actually print out the leaf to the provided canvas.
        it returns the tag of the printed text
        """
        self.tag = tag = canvas.create_text(x, depth*50,
                                            text=self.data,
                                            anchor='w')
        bbox = canvas.bbox(tag)
        self.xloc = (bbox[2]+bbox[0])/2
        self.yloc = depth*50
        return tag

    def move(self, canvas, dx, dy):
        canvas.move(self.tag, dx, dy)
        self.xloc += dx
        self.yloc += dy



###################################################################
#                          split                                  #
###################################################################


PADDING = 20
MAXWIDTH = 600
MAXHEIGHT = 600

def convert_tree(tree):
    """
    this function will recursively go through a Tree and return a tree
    in Draw_Node/Draw_Leaf/Draw_Token form
    """
    if isinstance(tree, Tree):
        root = Draw_Node(tree.node())
        for child in tree:
            root.children.append(convert_tree(child))

    else: 
        root = Draw_Leaf(tree)  
 
    return root

class Window:
    
    def __init__(self, tree):

        """
        Top level class.  Window contains in it all the necessary methods
        and attributes to handle managing the window itself.
          - display -> sets the window width and height at every redraw
                       calls the main drawing function drawtree
          - drawtree -> in a depth-first manner, determines the status of
                        a node, then calls the appropriate display command.
                        Then determines how much of the nodes themselves
                        lie outside the bounding box of the subordinate tree
                        and shifts that whole tree accordingly
        """
        
        # default window setup
        self.top = top = Tk()
        self.v_scroll = v_scroll= Scrollbar(top)
        v_scroll.pack(side=RIGHT, fill=Y)
        self.h_scroll= h_scroll = Scrollbar(top, orient='horizontal')
        h_scroll.pack(side=BOTTOM, fill=X)

        def f(self=self): self.top.destroy()


        def expand(self=self):
            """
            this function will expand all the nodes in the tree,
            and then redraw it
            """
            self.expand_all(self.tree)
            self.c.delete(ALL)
            self.display()
        self.menu_top = Frame(top)
        self.menu_bar = menu = Frame(self.menu_top)
        self.close = Button(menu, width=6, text='close', command=f)
        self.close.pack(side=LEFT, padx=2, pady=2)
        self.expand = Button(menu, width=6, text='expand', command=expand)
        self.expand.pack(side=LEFT, padx=2, pady=2)
        self.printer = Button(menu, width=6, text='print', command=expand)
        self.printer.pack(side=LEFT, padx=2, pady=2)
        self.zoom_in = Button(menu, width=6, text='zoom-in', command=f)
        self.zoom_in.pack(side=LEFT, padx=2, pady=2)
        self.zoom_out = Button(menu, width=6, text='zoom-out', command=f)
        self.zoom_out.pack(side=LEFT, padx=2, pady=2)
        
        self.menu_bar.pack()
        self.menu_top.pack(side=TOP, fill=X)

        self.c = c = Canvas(top, width=300, height=300,
                            yscrollcommand=v_scroll.set,
                            xscrollcommand=h_scroll.set)
                            

        c.pack(side=LEFT, expand='1', fill='both')
        v_scroll.config (command=c.yview)
        h_scroll.config (command=c.xview)


        

        self.tree = convert_tree(tree)
        self.width = 0


    def display(self):
        """
        draw the tree, then change the width and height
        of the window itself accordingly
        """
        w = int(self.c.cget('width'))
        right = self.drawtree(self.tree, PADDING)
        bottom = self.tree.tree_depth(0)

        self.c['scrollregion']=(0,0,right+PADDING,min(250,(bottom+2)*50))
        
        #self.c['width'] = right+PADDING
        #
        #if (bottom+2)*50 <= 250:
        #    self.c['height'] = 250
        #else:
        #    self.c['height'] = (bottom+2)*50
            



    def drawtree(self, node, left=0, depth=1):
        """
        This is the main tree-drawing function.  It takes in a node,
        a leftmost boundary, and the depth of the node.
        Basically, it works by drawing the leaf nodes at the place marked
        by the left axis.  All nodes are drawn in the center of a
        region marked by the left axis and the farthest right axis of
        its children.  It returns the rightmost boundary of whatever
        is being drawn
        """
        
        x = left
        

        # callback function--calls toggle
        def cb(event, node=node, self=self):
            self.toggle(node)

        if node.collapsed == 1:
            # Draw a collapsed node
            
            #x += 4
            result = node.display_collapsed(self.c, x, depth, left)
            text2 = result['tag']
            triangle = result['triangle']
            x = result['new_x'] # the new rightmost axis
            #x += 4
            self.c.tag_bind(text2, '<Button-1>', cb)
            self.c.tag_bind(triangle, '<Button-1>', cb)


        else:
            for child in node.children:
                if isinstance(child, Draw_Node):
                    # Draw an uncollapsed node.
                    #x += 4
                    newx = self.drawtree(child, x, depth+1)
                    
                    x = newx# + 4
                else:
                    # Draw the leaf node.
                    #x += 4
                    text = child.display(self.c, x, depth+1)
                    bbox = self.c.bbox(text)
                    x = bbox[2]# + 4  # bbox[2] returns the farthest right
                                     # boundary of the canvas text

            # Draw the parent.  Note that we couldn't calculate parentx until
            # now, since we didn't know how big the children were going to be.

                       
            number = len(node.children)  
            if (number % 2) == 0 :  
                l = number/2 - 1  
                r = l + 1  
                parentx = ((node.children[l].xloc)+(node.children[r].xloc))/2  
            else:  
                parentx = node.children[number/2 ].xloc 
           

            text = node.display_node(self.c, parentx, depth)
            self.c.tag_bind(text, '<Button-1>', cb)

            for child in node.children:
                arrow =  self.c.create_line(node.xloc, node.yloc+10,
                                            child.xloc, child.yloc-10)
                node.arrow_list.append(arrow)
            # Check whether the node tag is wider than its children
            # if so, move everything that is within the area beneath it

            bbox = self.c.bbox(text)
            x = max(bbox[2], x)
            if (bbox[0] < left) :
                diff = left-bbox[0]
                node.move(self.c, diff, 0)
                x += diff
        return x + 8 # for padding

    def toggle(self, node):
        """
        This function changes the status of the node that was clicked, then
        calls the window to redraw the whole thing
        """
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

   

    w = Window(t)
    w.display()
