# Natural Language Toolkit: Paradigm Visualisation
#
# Copyright (C) 2005 University of Melbourne
# Author: Will Hardy
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Front end to a Python implementation of David
# Penton's paradigm visualisation model.
# Author: 
#
# Run: To run, first load a paradigm using
#      >>> a = paradigm('paradigm.xml')
#      And run the system to produce output
#      >>> a.show('table(one, two, three)')
#
#      Other methods:
#      demo()                   # a quick demonstration
#      a.setFormat('html')      # output is formatted as HTML
#      a.setFormat('text')      # output is formatted as HTML
#      a.setOutput('filename')  # output is sent to filename
#      a.setOutput('term')      # output is sent to terminal

from xml.dom.ext.reader import Sax2
from paradigmquery import ParadigmQuery
import re, os

class Paradigm:
    """
    Paradigm visualisation class

    *Usage*
    
    Simple usage of the system would be:
      >>> from paradigm import Paradigm
      >>> p = Paradigm('german.xml')
      >>> p.show('table(case, gender/number, content)')
    
    Here, a table is generated in HTML format and sent to the file ``output.html``.
    The table can be viewed in a browser, and is updated for every new query. 
    
    A more advanced usage of the system is show below.
    The user simply creates a paradigm p, changes the output format and location, 
    and calls a dedicated prompt to enter the query:
      >>> from paradigm import Paradigm
      >>> p = Paradigm('german.xml')
      >>> p.setFormat('html')
      >>> p.setOutput('test.html')
      >>> p.setCSS('simple.css')
      >>> p.prompt()
      > table(case, gender/number, content)
    
    Please note, however, that plain text tables have not yet been implemented.
    """

    def __init__(self, p_filename):
        """
        Load the given paradigm
        p_filename is a string representing the filename of a paradigm xml file
        """
        # Store input paradigm filename
        self.loadParadigm(p_filename)
        # set default values (text output, to terminal)
        self.format = "html"
        self.output = "output.html"
        self.css = "simple.css"

    def prompt(self):
        """
        Changes to a dedicated prompt
        Type 'exit' or 'quit' to exit
        """
        s = ""
        while s != "exit":
            s = "exit"
            try: s = raw_input(">")
            except EOFError:
                print s
            if s == "exit":
                return
            if s == "quit":
                return
            if s:
                while s[-1] in "!.": s = s[:-1]
                self.show(s)

    def show(self, p_string):
        """
        Process and display the given query
        """

        try:  
          # parse the query
          parse = ParadigmQuery(p_string)
        except:
          print "Could not parse query."
          return

        try:  
          # Fetch the parsed tree and make presentation
          result = Sentence(self, parse.getTree())
          # Check that a presentation actually exists
          if result == None:
            raise Error
        except:
            print "Sorry, no result can be returned"
            return

        try:  
        # Print HTML output if format is set, otherwise plain text
          if self.format == "html":
            output = '<html>\n'
            # Include CSS if we need to
            if self.css <> None:
                output += '<link rel="stylesheet" href="' 
                output += self.css
                output += '" type="text/css" media="screen" />\n'
            output += '<body>'
            output += "<table cellspacing=\"0\" cellpadding=\"0\">"
            output += result.getHTML()
            output += "</table>\n"
            output += '</body></html>\n'
          else:
            output = result.getText()
        except:
            output = None
            print "--no output--"
            return

        # Print to terminal if output is set, otherwise to file
        if self.output == "term":
            print output
        else:
            print "Output written to file:", self.output
            f = open(self.output, 'w')
            f.write(output)

        # Return happily
        return

    def setFormat(self, p_string=None):
        """
        Set the output format: "html" or "text"
        """
        # Default value
        if p_string == None:
            p_string = "text"
        # set to html if requested, otherwise text
        if p_string == "html":
            self.format = "html"
        elif p_string == "text":
            self.format = "text"
        else:
            print "Unknown format:", p_string
            print "Valid formats are: text, html"
            print "Setting format = text"
            self.format = "text"

    def setCSS(self, p_string=None):
        """
        Set the file location for a Cascading Stylesheet: None or filename
        This allows for simple formatting
        """
        if p_string <> None:
            print "Using CSS file:", p_string
        self.output = p_string

    def setOutput(self, p_string=None):
        """
        Set the output location: "term" or filename
        """
        # Default
        if p_string == None:
            p_string = "term"
        # set to term if requested, otherwise filename
        if p_string == "term":
            print "Directing output to terminal"
        else:
            print "Directing output to file:", p_string
        self.output = p_string


    def loadParadigm(self, p_filename ):
        """
        Load the given paradigm (XML file)
        Attributes are stored in self.attributes
        Data are stored in self.data
    
        They can be accessed as follows:
        self.attributes['gender']   # list of genders
        self.data[6]['gender']      # gender for the sixth data object
        self.data[6]['content']     # content for the sixth data object
        """

        from nltk_lite.corpora import get_basedir
        basedir = get_basedir()

        # Look for the file
        try_filename = os.path.join(get_basedir(), "paradigms", p_filename)
        try:
            f = open(try_filename)
            p_filename = try_filename
        except IOError:
            print "Cannot find file"
            return None
        f.close()

        # These variables will be set by this method
        self.attributes = {}  # A new dictionary
        self.data = []        # A new list

        # XML admin: create Reader object, parse document
        reader = Sax2.Reader()
        doc = reader.fromStream(p_filename)

        # Cycle through the given attributes and add them to self.attributes
        # for <name> in <attributes>
        attributes = doc.getElementsByTagName('attributes')[0]
        for name in attributes.getElementsByTagName('name'):

            # Setup a list of attribute values
            tmp_list = []

            # for each value under name, store in list
            for value in name.getElementsByTagName('value'):
                tmp_list.append(value.getAttribute('value'))

            # Store list of values in dictionary
            self.attributes[name.getAttribute('name')] = tmp_list


        # Cycle through data objects and add them to self.data
        # for <form> in <paradigm>
        forms = doc.getElementsByTagName('paradigm')[0]
        for form in forms.getElementsByTagName('form'):
            # Initialise a temporary dictionary
            tmp_dict = {}
            for value in form.getElementsByTagName('attribute'):
                tmp_dict[value.getAttribute('name')] = value.getAttribute('value')
            # Add the new dictionary to the data list
            self.data.append(tmp_dict)

        # Talk to the user
        print "Paradigm information successfully loaded from file:", p_filename
        # State the number and print out a list of attributes
        print " "*4 + str(len(self.attributes)) + " attributes imported:",
        for att in self.attributes:
            print att,
        print
        # State the number of paradigm objects imported
        print " "*4 + str(len(self.data)) + " paradigm objects imported."

        return

class Sentence:
    """
    Manages any operation
    Passes request onto other handlers if necessary
    """

    def __init__(self, p_paradigm, p_tree):
        """
        p_paradigm is the given paradigm (attributes and data)
        p_tree is the query tree
        """
        # store parameters
        self.paradigm = p_paradigm
        self.tree = p_tree
        # discover the type
        self.type = self.getType(self.tree)
        # Handle each possible type
        if self.type == 'O':
            self.item = Sentence(self.paradigm, self.tree[0])
        if self.type == 'D':
            self.item = Domain(self.paradigm, self.tree)
        if self.type == 'H':
            self.item = Hierarchy(self.paradigm, self.tree)
        if self.type == 'T':
            self.item = Table(self.paradigm, self.tree)

    def getList(self):
        """
        Returns values in the form of a list
        """
        if self.tree == None:
            return None
        return self.item.getList()

    def getHTML(self):
        """
        Returns values in html (table) form
        """
        return self.item.getHTML()

    def getHorizontalHTML(self,p_parentSpan=1):
        """
        Returns values in html (table) form
        """
        return self.item.getHorizontalHTML(p_parentSpan)

    def getText(self):
        """
        Returns values in plain text form
        """
        return self.item.getText()

    def getConditions(self):
        """
        Return a list of conditions for each combination (cell)
        """
        return self.item.getConditions()

    def getMaxWidth(self):
        """
        Returns the width in number of characters
        """
        return self.item.getMaxWidth()

    def getSpan(self):
        """
        Returns the span (requred for "rowspan" and "colspan" HTML attributes)
        """
        return self.item.getSpan()

    def getDepth(self):
        """
        Get the depth
        """
        return self.item.getDepth()

    def getType(self, p_tree=None):
        """
        Determine the type of the current node of the tree
        This need not be overridden
        """
        if p_tree == None:
            p_tree = self.tree
        # This is in the second character of the string representation
        return str(p_tree)[1:2]

class Domain(Sentence):
    """
    Manages a domain operation
    
    Provides: Domain(paradigm,tree)
    """
    def __init__(self, p_paradigm, p_tree):
        """
        p_paradigm is the given paradigm (attributes and data)
        p_tree is the query tree
        """
        self.paradigm = p_paradigm
        # Validate that this is a domain
        assert self.getType(p_tree) == 'D'
        # Store the attribute
        self.attribute = p_tree[0]
        self.error = None
        # Check that the requested attribute is available
        try:
            self.paradigm.attributes[self.attribute]
        except KeyError:
            self.error = "I couldn't find this attribute: " + self.attribute
            print self.error

    def __getitem__(self, p_index):
        return self.paradigm.attributes[self.attribute][p_index]

    def getList(self):
        """
        Return the domain in list form
        """
        return self.paradigm.attributes[self.attribute]

    def getHTML(self):
        """
        Return html for this domain
        """
        ret_string = ""
        for item in self.getList():
            ret_string += "<tr><td>" + item + "</td></tr>"
        return ret_string

    def getHorizontalHTML(self,p_parentSpan=1):
        """
        Return a horizontal html table
        """
        ret_string = ""
        for item in self.getList():
            ret_string += "<td>" + item + "</td>"
        return "<tr>" + ret_string*p_parentSpan + "</tr>"


    def getText(self):
        """
        Return text for this domain
        """
        ret_string = ""
        for item in self.getList():
            ret_string += item + "\n"
        return ret_string

    def getConditions(self):
        """
        Return a list of conditions for each combination (cell)
        """
        ret_conds = []
        for item in self.getList():
            new = {self.attribute: item}
            #new[self.attribute] = item
            ret_conds.append(new)
        return ret_conds

    def getMaxWidth(self):
        """
        Get max width (chars) for display purposes
        """
        max_width = 0
        for item in self.getList():
            if max_width < len(item):
                max_width = len(item)
        return max_width

    def getSpan(self):
        """
        Get the span of this domain (number of elements)
        """
        return len(self.getList())

    def getDepth(self):
        """
        Get the depth of this domain (always one!)
        """
        return 1 

class Hierarchy(Sentence):
    """
    Manages a hierarchy operation
    
    Provides: Hierarchy(paradigm,tree)
    """
    def __init__(self, p_paradigm, p_tree):
        """
        p_paradigm is the given paradigm (attributes and data)
        p_tree is the tree representation of this part of the query (Tree)
        """
        self.paradigm = p_paradigm
        self.error = None

        self.tree = p_tree
        # Validate that this is a Hierarchy
        assert self.getType(p_tree) == 'H'
        # Validate that the root is a Domain
        assert self.getType(p_tree[0]) == 'D'
        # Set the root and the leaf 
        self.root = Domain(self.paradigm, p_tree[0])
        self.leaf = Sentence(self.paradigm, p_tree[1])


    def getList(self):
        """
        Return the hierarchy in list form
        """
        # Get child lists
        rootList = self.root.getList()
        leafList = self.leaf.getList()
        
        # Combine lists into an array
        ret_val = []
        for item_root in rootList:
            for item_leaf in leafList:
                ret_val.append([item_root,item_leaf])

        return ret_val

    def getHTML(self):
        """
        Return a html table for this hierarchy
        """
        ret_string = ""
        for index in range(len(self.root.getList())):
            leafCells = self.leaf.getHTML()[4:]
            ret_string += "<tr><td rowspan=\"" + str(self.leaf.getSpan()) + "\">" + self.root[index] \
                             + "</td>" + leafCells
        return ret_string

    def getHorizontalHTML(self,p_parentSpan=1):
        """
        Return a horizontal html table
        """
        ret_string = ""
        # Add a new cell for each root item
        for index in range(len(self.root.getList())):
            ret_string += "<td colspan=\"" + str(self.leaf.getSpan()) + "\">" \
                             + self.root[index] + "</td>" 
        # Recusively get the horizontalHTML from the leaf children
        leafCells = self.leaf.getHorizontalHTML(p_parentSpan*len(self.root.getList()))
        # Return the new row and the leaf cells
        return "<tr>" + ret_string*p_parentSpan + "</tr>" + leafCells 

    def getText(self):
        """
        Return text for this hierarchy
        """
        ret_string = ""
        # Lengths for rendering display
        max_width_root = self.root.getMaxWidth()
        max_width_leaf = self.leaf.getMaxWidth()
        # add root string and call getText() for leaf node
        # (newlines in the leaf node need to have whitespace added)
        for index in range(len(self.root.getList())):
            ret_string += self.root[index].ljust(max_width_root) + " " \
              + self.leaf.getText().ljust(max_width_leaf).replace('\n',"\n" \
              + " "*(max_width_root+1)) + "\n"
        # Remove any blank lines and return the string
        re_blank = re.compile('\n[ ]+\n')
        return re_blank.sub('\n',ret_string)

    def getConditions(self):
        """
        Return a list of conditions for each combination (cell)
        """
        ret_conds = []
        # For each root item
        for item_r in self.root.getList():
            # for each leaf condition
            for cond_l in self.leaf.getConditions():
                # Add the root node's condition
                cond_l[self.root.attribute] = item_r
                # Append this to the return list of conditions 
                ret_conds.append(cond_l)
        # Return our list
        return ret_conds

    def getMaxWidth(self):
        """
        Return the maximum width (in chars) this hierarchy will take up
        """
        return self.root.getMaxWidth() + self.leaf.getMaxWidth() + 1

    def getDepth(self):
        """
        Get the depth of this hierarchy
        """
        return 1 + self.leaf.getDepth() 
        
    def getSpan(self):
        """
        Get the span (for HTML tables) of this hierarchy
        """
        return self.root.getSpan() * self.leaf.getSpan() 

class Table(Sentence):
    """
    Manages a table operation
    
    Provides: Table(paradigm,tree)
    """
    def __init__(self, p_paradigm, p_tree):
        """
        p_paradigm is the given paradigm (attributes and data)
        p_tree is the tree representation of this part of the query (Tree)
        """
        self.paradigm = p_paradigm
        self.error = None

        self.tree = p_tree
        # Validate that this is a Table
        assert self.getType(p_tree) == 'T'
        # Set the table arguments
        self.horizontal = Sentence(self.paradigm, p_tree[0])
        self.vertical = Sentence(self.paradigm, p_tree[1])
        self.cells = Sentence(self.paradigm, p_tree[2])


    def getList(self):
        """
        Return the table (cells) in list form
        """
        ret_val = []
        return ret_val

    def getHTML(self):
        """
        Return a html table for this table operation
        """
        # Start with the dead cell
        dead_cell = "<tr><td colspan=\"" + str(self.vertical.getDepth()) \
                        + "\" rowspan=\"" + str(self.horizontal.getDepth()) \
                        + "\"></td>"
        # Insert horizintal header
        horizontal_header = self.horizontal.getHorizontalHTML()[4:].replace('td','th')
        #horizontal_header = self.horizontal.getHorizontalHTML().replace('td','th')
        # Get the vertical header
        vertical_header = self.vertical.getHTML().replace('td','th')
        str_cells = ""
        # Reset conditions
        conditions = {}
        # get a list of conditions for the row
        conditions_v = self.vertical.getConditions()
        # for each row
        for cond_v in conditions_v:
            str_cells += "<tr>"
            # get a list of conditions for the row
            conditions_h = self.horizontal.getConditions()
            # For each column
            for cond_h in conditions_h:
                # Get the data for this cell, given the hori and vert conditions
                cell_data = self.getData(self.cells.tree, dictJoin(cond_v,cond_h))
                # Add the cell
                str_cells += "<td>" + cell_data + "</td>"
            # End the row
            str_cells += "</tr>"
        
        # VERTICAL HEADER INCLUSION
        # Split rows into a list
        vertical_header_rows = vertical_header.split('</tr>')
        cell_rows = str_cells.replace('<tr>','').split('</tr>')
        # Join two lists
        zipped = zip(vertical_header_rows, cell_rows)
        str_zipped = ""
        for (header,cells) in zipped:
            if header <> '':
                str_zipped += header + cells + "</tr>\n"

        # Return all the elements
        return dead_cell + horizontal_header + str_zipped

    def getHorizontalHTML(self,p_parentSpan=1):
        """
        Return a horizontal html table (?)
        """
        print "?: getHorizontalHTML() called on a table."
        return None

    def getText(self):
        """
        Return text for this table (?)
        """
        print "?: getText() for a table? HAHAHAHAHA"
        print "call setFormat('html') if you want to run queries like that"
        return 
    
    def getConditions(self):
        """
        Return conditions for this table (?)
        """
        print "?: getConditions() called on a table. I don't think so."
        return None

    def getMaxWidth(self):
        """
        Return the maximum width this table could take up. 
        ... I hope you're not trying to nest tables ...
        """
        return self.cells.getMaxWidth() + self.vertical.getMaxWidth() + 1

    def getSpan(self):
        """
        Return span for this table (?)
        """
        print "WTF: getSpan() called on a table."
        return None

    def getData(self, p_return, p_attDict):
        """
        Retrieve data that matches the given list of attributes
        Returns (an HTML) string of values that match.
    
        p_return is a tree pointing to the key of the value to include in the return
        p_attDict is a dictionary of conditions.
        """
        output = []
        return_key = p_return.leaves()[0]

        # For each data object in the paradigm
        for datum in self.paradigm.data:
            inc = True
            # For each given attribute requirement
            for att in p_attDict.keys():
                # If the data object fails the requirement do not include
                if datum[att] != p_attDict[att]:
                    inc = False
                    break
            # If it passed all the tests, include it
            if inc == True:
                output.append(datum[return_key])

        # Return what we found (make sure this is a string)
        if len(output) == 1:
            return output[0]
        else:
            # Hardcoded HTML goodness
            # (Obviously this will have to change for text output)
            ret_str = "<table>"
            for item in output:
                ret_str += "<tr><td>" + item + "</td></tr>"
            ret_str += "</table>"
            return ret_str


def dictJoin(dict1,dict2):
    """
    A handy function to join two dictionaries
    If there is any key overlap, dict1 wins!
    (just make sure this doesn't happen)
    """
    for key in dict1.keys():
        dict2[key] = dict1[key]
    return dict2

def demo():

    # Print the query
    print """
================================================================================
Load: Paradigm(file)
================================================================================
"""
    print
    print ">>> a = Paradigm('german.xml')"
    print 
    a = Paradigm('german.xml')
    print 
    print ">>> a.setOutput('term')"
    print 
    a.setOutput('term')
    print 
    print ">>> a.setFormat('text')"
    print 
    a.setFormat('text')

    # Print a domain
    print """
================================================================================
Domain: case
================================================================================
"""
    print 
    print ">>> a.show('case')"
    print 
    a.show('case')

    # Print a hierarchy
    print """
================================================================================
Hierarchy: case/gender
================================================================================
"""
    print 
    print ">>> a.show('case/gender')"
    print 
    a.show('case/gender')

    # Print a table
    print """
================================================================================
Table: table(case/number,gender,content)
================================================================================
"""
    print 
    print ">>> a.setOutput('demo.html')"
    print 
    a.setOutput('demo.html')
    print 
    print ">>> a.setFormat('html')"
    print 
    a.setFormat('html')
    print 
    print ">>> a.show('table(case/number,gender,content)')"
    print 
    a.show('table(case/number,gender,content)')

    # Some space
    print 

if __name__ == '__main__':
    demo()    
