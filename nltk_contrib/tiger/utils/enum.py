# -*- coding: utf-8 -*-
# Copyright © 2007-2008 Stockholm TreeAligner Project
# Author: Torsten Marek <shlomme@gmx.net>
# Licensed under the GNU GPLv2

__all__ = ["Enum", "enum_member"]

# this class was heavily inspired by http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/521879

class _EnumMember(object):
    def __init__(self, fields):
        self.fields = fields

    def __get__(self, obj, type_):
        return type_.__members__[self._name]


def enum_member(*args):
    return _EnumMember(args)


class _EnumType(type):
    def __new__(mcs, class_name, bases, dct):
        dct.setdefault("__fields__", ())
        dct["__slots__"] = ("__value__", "__name__")
        dct["__members__"] = members = {}
        
        for name, obj in dct.iteritems():
            if isinstance(obj, _EnumMember):
                members[name] = obj.fields
                obj._name = name
        
        for idx, fname in enumerate(dct["__fields__"]):
            dct[fname] = property(lambda self, i = idx: self.__value__[i])

        return type.__new__(mcs, class_name, bases, dct)
    
    def __init__(mcs, name, bases, dct):
        type.__init__(mcs, name, bases, dct)

        decl = type.__getattribute__(mcs, '__members__')
        
        members = {}
        
        field_count = len(type.__getattribute__(mcs, "__fields__"))
        
        for member_name, field_values in decl.iteritems():
            members[member_name] = mcs()
            if len(field_values) != field_count:
                raise TypeError, (
                    "Wrong number of fields for enum member '%s'. Expected %i, got %i instead." % (
                    member_name, field_count, len(field_values)))
            else:
                object.__setattr__(members[member_name], "__value__", field_values)
            object.__setattr__(members[member_name], '__name__', member_name)
                
        type.__setattr__(mcs, "__members__", members)

    def __setattr__(mcs, name, value):
        raise TypeError, "enum types cannot be modified"
     
    def __delattr__(mcs, name):
        raise TypeError, "enum types cannot be modified"
    
    def names(mcs):
        return type.__getattribute__(mcs, '__members__').keys()
    
    def __len__(mcs):
        return len(type.__getattribute__(mcs, '__members__'))
    
    def __iter__(mcs):
        return type.__getattribute__(mcs, '__members__').itervalues()
    
    def __contains__(mcs, name):
        return name in type.__getattribute__(mcs, '__members__')
    
    def __repr__(mcs): # pragma: nocover
        return "<EnumType '%s.%s'>" % (mcs.__module__, mcs.__name__)

    
class Enum(object):
    __metaclass__ = _EnumType

    # assigned by metaclass
    __value__ = ()
    __name__ = ""
    
    def __repr__(self):
        return "%s.%s" % (self.__class__.__name__,  self.__name__)
    
    def __getstate__(self):
        return self.__name__
    
    def __setstate__(self, name):
        self.__name__ = name
        self.__value__ = getattr(self.__class__, name).__value__
    
    def __eq__(self, other):
        return self is other or type(self) is type(other) and self.__name__ == other.__name__
    
    def __ne__(self, other):
        return not (self == other)

    def elem_set(self):
        return set([self])

    @classmethod
    def enum_set(cls):
        return set(iter(cls))
