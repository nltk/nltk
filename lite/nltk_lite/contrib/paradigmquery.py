# Natural Language Toolkit: Paradigm Visualisation
#
# Copyright (C) 2005 University of Melbourne
# Author: Will Hardy
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# Parses a paradigm query and produces an XML representation of
# that query. This is part of a Python implementation of David
# Penton's paradigm visualisation model.

#This is the query XML version of "table(person, number, content)"
#
#<?xml version="1.0"?>
#<document>
#  <parse-tree>
#    <operator opcode="table" instruction="1">
#      <operand type="domain"
#        arg="horizontal">person</operand>
#      <operand type="domain"
#        arg="vertical">number</operand>
#      <operand type="domain"
#        arg="cell">content</operand>
#    </operator>
#  </parse-tree>
#</document>

from nltk_lite import tokenize
from nltk_lite import parse
from nltk_lite.parse import cfg
from re import *

class ParadigmQuery(object):
    """
    Class to read and parse a paradigm visualisation query
    """

    def __init__(self, p_string=None):
        """
        Construct a query.
        Setup various attributes and parse given string
        """
        self.nltktree = None
        self.string = p_string
        self.parseList = None
        self.nltkTree = None
        self.parseTree = None
        self.xml = None

        # If p_string was given, parse it
        if p_string <> None:
            self.parse(p_string)

    def parse(self, p_string):
        """
        Parses a string and stores the resulting hierarchy of "domains"
        "hierarchies" and "tables"

        For the sake of NLP I've parsed the string using the nltk_lite 
        context free grammar library.

        A query is a "sentence" and can either be a domain, hierarchy or a table.
        A domain is simply a word.
        A hierarchy is expressed as "domain/domain"
        A table is exressed as "table(sentence, sentence, sentence)"

        Internally the query is represented as a nltk_lite.parse.tree

        Process:
          1. string is tokenized
          2. develop a context free grammar
          3. parse
          4. convert to a tree representation
        """
        self.nltktree = None

        # Store the query string
        self.string = p_string

        """
        1. Tokenize
        ------------------------------------------------------------------------
        """

        # Tokenize the query string, allowing only strings, parentheses,
        # forward slashes and commas.
        re_all = r'table[(]|\,|[)]|[/]|\w+'
        data_tokens = tokenize.regexp(self.string, re_all)

        """
        2. Develop a context free grammar
        ------------------------------------------------------------------------
        """

        # Develop a context free grammar
        # S = sentence, T = table, H = hierarchy, D = domain
        O, T, H, D = cfg.nonterminals('O, T, H, D')

        # Specify the grammar
        productions = (
            # A sentence can be either a table, hierarchy or domain
            cfg.Production(O, [D]), cfg.Production(O, [H]), cfg.Production(O, [T]),
            
            # A table must be the following sequence:
            # "table(", sentence, comma, sentence, comma, sentence, ")" 
            cfg.Production(T, ['table(', O, ',', O, ',', O, ')']),

            # A hierarchy must be the following sequence:
            # domain, forward slash, domain
            cfg.Production(H, [D, '/', D]),
            # domain, forward slash, another operator
            cfg.Production(H, [D, '/', O])
        )

        # Add domains to the cfg productions
        # A domain is a token that is entirely word chars
        re_domain = compile(r'^\w+$') 
        # Try every token and add if it matches the above regular expression
        for tok in data_tokens:
            if re_domain.match(tok):
                prod = cfg.Production(D,[tok]),
                productions = productions + prod

        # Make a grammar out of our productions
        grammar = cfg.Grammar(O, productions)
        rd_parser = parse.RecursiveDescent(grammar)
       
        # Tokens need to be redefined. 
        # It disappears after first use, and I don't know why.
        tokens = tokenize.regexp(self.string, re_all)
        toklist = list(tokens)

        """
        3. Parse using the context free grammar
        ------------------------------------------------------------------------
        """
        # Store the parsing. 
        # Only the first one, as the grammar should be completely nonambiguous.
        try:
            self.parseList = rd_parser.get_parse_list(toklist)[0]
        except IndexError: 
            print "Could not parse query."
            return


        """
        4. Refine and convert to a Tree representation
        ------------------------------------------------------------------------
        """
        # Set the nltk_lite.parse.tree tree for this query to the global sentence
        string = str(self.parseList)
        string2 = string.replace(":","").replace("')'","").replace("table(","").replace("','","").replace("'","").replace("/","")
        self.nltktree = parse.tree.bracket_parse(string2)
        
        # Store the resulting nltk_lite.parse.tree tree
        self.parseTree = QuerySentence(self.nltktree)
        self.xml = self.parseTree.toXML()


    def getTree(self):
        """
        Returns the results from the CFG parsing
        """
        if self.string == None:
            print "No string has been parsed. Please use parse(string)."
            return None
        return self.nltktree

    def getXML(self):
        """
        This XML is written without the use of SAX or DOM, it is a straight
        translation of the parsed string. This may be slightly dangerous, but
        the document is very simple. If I have time, this may be reimplemented.
        """
        if self.string == None:
            print "No string has been parsed. Please use parse(string)."
            return None
        return '<?xml version="1.0"?>\n<document><parse-tree>' + self.xml \
                  + "</parse-tree></document>"



# Additional Classes for handling The various types of recursive operations

class QuerySentence(object):
    """
    Handles the XML export of sentences
    """
    def __init__(self, tree):
        self.tree = tree
        type = str(tree[0])[1:2]
        # Move on, nothing to see here
        if type == "O":
            self.child = QuerySentence(tree[0])
            self.content = self.child.content
        # Get the child and replicate the data
        elif type == "D":
            self.child = QueryDomain(tree[0])
            self.content = self.child.content
        elif type == "H":
            self.child = QueryHierarchy(tree[0])
            self.root = self.child.root
            self.leaf = self.child.leaf
        elif type == "T":
            self.child = QueryTable(tree[0])
            self.horizontal = self.child.horizontal
            self.vertical = self.child.vertical
        # Otherwise, must simply be a domain...
        else:
            self.child = QueryDomain(tree[0])
            self.content = self.child.content
        self.type = self.child.type


    def __str__(self):
        return str(self.tree[0])

    def toXML(self):
        """
        Export this class to an xml string
        """
        return self.child.toXML()


class QueryDomain(object):
    """
    Handles the XML export of the domain operation
    """
    def __init__(self, tree):
        self.type = 'domain'
        self.content = tree[0]

    def __str__(self):
        return tree[0]

    def toXML(self):
        """
        Export this class to an xml string
        """
        return self.content


class QueryHierarchy(object):
    """
    Handles the XML export of the hierarchy operation
    """
    def __init__(self, tree):
        self.type = 'hierarchy'
        # First argument must be a Domain
        self.root = QueryDomain(tree[0]) 
        # Second argument can conceivably be anything
        self.leaf = QuerySentence(tree[1]) 

    def __str__(self):
        return tree[0]

    def toXML(self):
        """
        Export this class to an xml string
        """
        return '<operator opcode="hierarchy">' \
               + '<operand type="' + self.root.type + '" arg="root">' \
               + self.root.toXML() + "</operand>" \
               + '<operand type="' + self.leaf.type + '" arg="leaf">' \
               + self.leaf.toXML() + "</operand>" \
               + '</operator>'


class QueryTable(object):
    """
    Handles the XML export of the hierarchy operation
    """
    def __init__(self, tree):
        """
        Simply stores attributes, passing off handling of attributes to the
        QuerySentence class
        """
        self.type = 'table'
        self.horizontal = QuerySentence(tree[0])
        self.vertical = QuerySentence(tree[1])
        self.content = QuerySentence(tree[2])

    def __str__(self):
        return tree[0]

    def toXML(self):
        """
        Export this class to an xml string
        """
        return '<operator opcode="table">' \
               + '<operand type="' + self.horizontal.type + '" arg="horizontal">' \
               + self.horizontal.toXML() + "</operand>" \
               + '<operand type="' + self.vertical.type + '" arg="vertical">' \
               + self.vertical.toXML() + "</operand>" \
               + '<operand type="' + self.content.type + '" arg="cell">' \
               + self.content.toXML() + "</operand>" \
               + '</operator>'


def demo():
    """
    A demonstration of the use of this class
    """
    query = r'table(one/two/three, four, five)'

    # Print the query
    print """
================================================================================
Query: ParadigmQuery(query)
================================================================================
"""
    a = ParadigmQuery(query)
    print query

    # Print the Tree representation
    print """
================================================================================
Tree: getTree()
  O is an operator
  T is a table
  H is a hierarchy
  D is a domain
================================================================================
"""
    print a.getTree()

    # Print the XML representation
    print """
================================================================================
XML: getXML()
================================================================================
"""
    print a.getXML()

    # Some space
    print 


if __name__ == '__main__':
    demo()    
