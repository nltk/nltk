# -*- coding: utf-8 -*-
# Natural Language Toolkit: JSON Encoder/Decoder Helpers
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Register JSON tags, so the nltk data loader knows what module and class to look for.

NLTK uses simple '!' tags to mark the types of objects, but the fully-qualified
"tag:nltk.org,2011:" prefix is also accepted in case anyone ends up
using it.
"""

import json

json_tags = {}

TAG_PREFIX = '!'

def register_tag(cls):
    """
    Decorates a class to register it's json tag.
    """
    json_tags[TAG_PREFIX+getattr(cls, 'json_tag')] = cls
    return cls

class JSONTaggedEncoder(json.JSONEncoder):
    def default(self, obj):
        obj_tag = getattr(obj, 'json_tag', None)
        if obj_tag is None:
            return super(JSONTaggedEncoder, self).default(obj)
        obj_tag = TAG_PREFIX + obj_tag
        obj = obj.encode_json_obj()
        return {obj_tag: obj}

class JSONTaggedDecoder(json.JSONDecoder):
    def decode(self, s):
        return self.decode_obj(super(JSONTaggedDecoder, self).decode(s))

    @staticmethod
    def decode_obj(obj):
        #Check if we have a tagged object.
        if not isinstance(obj, dict) or len(obj) != 1:
            return obj
        obj_tag = next(iter(obj.keys()))
        if not obj_tag.startswith('!'):
            return obj
        if not obj_tag in json_tags:
            raise ValueError('Unknown tag', obj_tag)
        cls = json_tags[obj_tag]
        return cls.decode_json_obj(obj[obj_tag])

__all__ = ['register_tag', 'json_tags',
           'JSONTaggedEncoder', 'JSONTaggedDecoder']
