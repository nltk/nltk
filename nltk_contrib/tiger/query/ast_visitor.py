# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
"""Defines a class for traversing Abstract Syntax Trees as defined in `nltk_contrib.tiger.query.ast`.
"""

__all__ = ["node_handler", "post_child_handler", "AstVisitor"]

def node_handler(*node_types):
    """Sets a method as a handler for all AST node types list in `node_types`."""
    def _set_node_type(fun):
        """Stores the node types on the method to be used by the metaclass."""
        fun.node_types = node_types
        return fun
    return _set_node_type


def post_child_handler(node_type):
    """Sets a method as a handler for that is invoked for every child of an
    AST node of type `node_type`.
    
    The handler is invoked after the whole branch of a child has been processed."""
    def _set_post_child_handler(fun):
        """Stores the node type on the method to be used as a handler for further processing."""
        fun.post_child = node_type
        return fun
    return _set_post_child_handler


class AstVisitorType(type):
    """The meta class for AST visitors.
    
    During class creation, the meta class will look for methods annotated as node handlers
    and store them in a dictionary. The handler for node can be retrieved using the method
    `switch`.
    """
    def __new__(mcs, classname, bases, class_dict):
        switch = {}
        post_switch = {}
        for obj in class_dict.itervalues():
            for n in getattr(obj, "node_types", []):
                switch[n] = obj
            
            if hasattr(obj, "post_child"):
                post_switch[getattr(obj, "post_child")] = obj

        class_dict["switch"] = switch.get
        class_dict["post_switch"] = post_switch.get
        return type.__new__(mcs, classname, bases, class_dict)
    
    
class AstVisitor(object):
    """
    The base class for AST visitors.
    
    Example:
    >>> class SomeVisitor(AstVisitor):
    ...    @node_handler(ast.Negation):
    ...    def show_negations(self, node):
    ...        print node
    ...        return self.CONTINUE(node)
    
    This visitor will simply print all negation nodes and do nothing else.
    
    A handler can have the following return values defined on `AstVisitor`:
      `STOP`
        stops traversal for all nodes under the currently visited one
      `CONTINUE(n)`
       continues the traversal, uses `n` to get the child nodes. Usually, this will
       be the visitied node
      `REPLACE(n)`
       continues the traversal using `n`, but also replaces the visited node by `n`.
    
       
    The traversal will never visit the root node via a method annotated with `@node_handler`. The 
    root node of the tree cannot be replaced [#]_, and only the methods `setup` and `result` have 
    access to it.
    
    .. [#] Changing the visitor code to allow this is easy, but the use case has not come up yet.
    """
    __metaclass__ = AstVisitorType

    STOP = (0, None)
    CONTINUE = lambda s, n: (1, n)
    REPLACE = lambda s, n: (2, n)
    
    def switch(self, ast_node_type, default_handler): # reassigned by meta-class 
        """Returns the handler for `ast_node_type`, or the `default_handler`."""
        pass
    
    def post_switch(self, ast_node_type, default_handler): # reassigned by meta-class
        """Returns the handler for `ast_node_type`, or the `default_handler`."""
        pass
    
    def default(self, child_node):
        """The default handler.
        
        Returns `STOP` for leaf nodes, and `CONTINUE(child_node)` for everything else.
        
        May be reimplemented by clients.
        """
        return self.STOP if child_node.is_leaf() else self.CONTINUE(child_node)
    
    def post_default(self, parent_node, child_name):
        """The default post-handler.
        
        Does nothing by default, may be reimplemented by clients.
        """
        pass
    
    def setup(self, query, *args, **kwargs):
        """Setup method, called before the tree is traversed.
        
        Any arguments passed into the `run` method will be passed to this method as well.
        
        Does nothing by default, can be implemented by clients.
        """
        pass
    
    def result(self, query, *args, **kwargs):
        """Teardown/result processing methods, called after the tree is traversed.

        Any arguments passed into the `run` method will be passed to this method as well.
        
        The return value of the `result` method is also the return value of `run`.

        Does nothing by default, can be implemented by clients.
        """
        pass
    
    def call_handler(self, node):
        """Calls the handler method for `node`.
        
        Convenience method to be used by subclasses.
        """
        r = self.switch(node.TYPE, self.__class__.default)(self, node)
        assert len(r) == 2, "Wrong return value '%s' from %s handler." % (r, node.TYPE, )
        return r
    
    def _process(self, node, child_name, child_node):
        """Processes the node `child_node`.
        
        Calls the type handler and acts on the result.
        """
        action, new_child = self.call_handler(child_node)
        
        if action == 2:
            node.set_child(child_name, new_child)
            self._process(node, child_name, new_child)
        elif action == 1:
            self._traverse(new_child)
        
        self.post_switch(node.TYPE, self.__class__.post_default)(self, node, child_name)

    def _traverse(self, branch):
        """Calls `_process` for all child nodes of a given node."""
        for child_name, child_node in branch.named_iter():
            self._process(branch, child_name, child_node)
            
    def run(self, query, *args, **kwargs):
        """Visits the tree rooted at `query`.
        
        All arguments will be passed to `setup` and `result`.
        
        Returns the value returned by `result`.
        """
        self.setup(query, *args, **kwargs)
        self._traverse(query)        
        return self.result(query, *args, **kwargs)
