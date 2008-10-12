# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
import logging

__all__ = ("element_handler", "IterParseHandler", "ET")

has_lxml = False
has_schema = False

try:
    import sys
    import lxml.etree as ET
    # lxml 1.3.4 is broken on win32, crashes on large inputs.
    if sys.platform == "win32" and ET.__version__ == "1.3.4":
        del ET
        raise ImportError
    has_lxml = True
    has_schema = ET.LXML_VERSION[:3] >= (2, 0, 3)
    import lxml._elementpath as DONTUSE # py2exe workaround
    del DONTUSE
except ImportError:
    import xml.etree.ElementTree # py2exe workaround
    import xml.etree.cElementTree as ET

HANDLER_ATTRIBUTE_NAME = "_handled"

def element_handler(tag, event = "end"):
    assert event in ("start", "end")
    def _inner_element_handler(method):
        setattr(method, HANDLER_ATTRIBUTE_NAME, (event, tag))
        return method
    return _inner_element_handler


class IterParseType(type):
    def __new__(mcs, classname, bases, class_dict):
        class_dict["__x_handlers__"] = handlers = {}
        for attr in class_dict.itervalues():
            if callable(attr) and hasattr(attr, HANDLER_ATTRIBUTE_NAME):
                handlers[getattr(attr, HANDLER_ATTRIBUTE_NAME)] = attr
                
        return type.__new__(mcs, classname, bases, class_dict)


class IterParseHandler(object):
    DELETE_BRANCH = True
    
    __metaclass__ = IterParseType
    
    __x_handlers__ = {}
    
    def __init__(self, schema = None):
        self._schema = None
        
        if schema:
            if has_lxml:
                if has_schema:
                    self._schema = ET.XMLSchema(ET.parse(schema))
                else:
                    logging.warning(
                        "XML schema validation is only supported with lxml 2.0.3 and higher.")
            else:
                logging.warning("Validation requested, but lxml is not installed, deactivating!")
           
    def _parse(self, filename):
        """Parses the XML file `filename`."""
        events = ("start", "end")
            
        if has_schema:
            event_source = ET.iterparse(filename, events,  schema=self._schema)
        else:
            event_source = ET.iterparse(filename, events)
        
        context = iter(event_source)
        
        event, root = context.next()
        self._handle_root(root)
        
        for event, elem in context:
            try:
                handler = self.__x_handlers__[(event, elem.tag)]
            except KeyError:
                continue
            result = handler(self, elem)
            if result == self.DELETE_BRANCH and event == "end":
                elem.clear()
        
    def _handle_root(self, elem):
        """Called with the root element before any other processing is done.
        
        Only the attributes of the `elem` may be accessed at this time, children
        might be present as a side-effect, but may not be used.
        
        The default implementation does nothing, should be overridden by subclasses.
        """
        pass
