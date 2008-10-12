# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2
class MissingClassException(Exception):
    pass

class FactoryBase(object):
    __classes__ = []
    
    def __init__(self):
        self._switch = {}
        if isinstance(self.__classes__, dict):
            self._switch = self.__classes__
        else:
            for cls in self.__classes__:
                for switch in self._get_class_switch(cls):
                    self._switch[switch] = cls
    
    def create(self, *args):
        switch_value = self._get_switch(*args)
        try:
            cls = self._switch[switch_value]
        except KeyError, e:
            self.raise_error(e.args[0])
        return self._create_instance(cls, *args)

    def raise_error(self, switch_name):
        raise MissingClassException, switch_name
    
    def _create_instance(self, cls, *args):
        return cls(*args)

    def _get_class_switch(self, cls):
        raise NotImplementedError
    
    def _get_switch(self, *args):
        raise NotImplementedError
    
    def __iter__(self):
        return iter(set(self._switch.values()))
