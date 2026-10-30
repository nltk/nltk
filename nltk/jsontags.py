# -*- coding: utf-8 -*-
# Natural Language Toolkit: JSON Encoder/Decoder Helpers
#
# Copyright (C) 2001-2019 NLTK Project
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
    json_tags[TAG_PREFIX + getattr(cls, 'json_tag')] = cls
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

    @classmethod
    def decode_obj(cls, obj):
        # Decode nested objects first.
        if isinstance(obj, dict):
            obj = dict((key, cls.decode_obj(val)) for (key, val) in obj.items())
        elif isinstance(obj, list):
            obj = list(cls.decode_obj(val) for val in obj)
        # Check if we have a tagged object.
        if not isinstance(obj, dict) or len(obj) != 1:
            return obj
        obj_tag = next(iter(obj.keys()))
        if not obj_tag.startswith('!'):
            return obj
        if obj_tag not in json_tags:
            raise ValueError('Unknown tag', obj_tag)
        obj_cls = json_tags[obj_tag]
        return obj_cls.decode_json_obj(obj[obj_tag])


__all__ = ['register_tag', 'json_tags', 'JSONTaggedEncoder', 'JSONTaggedDecoder']


######################################################################
# Bounded loaders (the 3.10 line's safe_json_load / safe_yaml_load)
######################################################################

#: Deepest nesting a JSON document may have: the recursive decoder would
#: otherwise overflow the stack on a crafted document (CWE-674).
JSON_MAX_DEPTH = 100
#: Largest JSON or YAML body read from a stream (CWE-400).
JSON_MAX_BYTES = 200 * 1024 * 1024
YAML_MAX_BYTES = 1 * 1024 * 1024


def _read_bounded(fp, limit, context):
    data = fp.read(limit + 1)
    if len(data) > limit:
        raise ValueError("%s: document exceeds %d bytes" % (context, limit))
    return data


def _check_json_depth(text, limit, context):
    depth = 0
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            depth += 1
            if depth > limit:
                raise ValueError("%s: JSON nested deeper than %d levels" % (context, limit))
        elif ch in "]}":
            depth -= 1


def safe_json_loads(data, max_depth=JSON_MAX_DEPTH, context="NLTK JSON"):
    """``json.loads`` after refusing a document nested deeper than
    *max_depth* (CWE-674). *data* is text or UTF-8 bytes."""
    import json

    if isinstance(data, bytes) and not isinstance(data, str):
        data = data.decode("utf-8")
    _check_json_depth(data, max_depth, context)
    return json.loads(data)


def safe_json_load(fp, max_depth=JSON_MAX_DEPTH, max_bytes=JSON_MAX_BYTES, context="NLTK JSON"):
    """Read a JSON document from a file-like object under the same bounds."""
    return safe_json_loads(_read_bounded(fp, max_bytes, context), max_depth, context)


def safe_yaml_loads(data, context="NLTK YAML"):
    """``yaml.safe_load``: plain data only, no python/object tags (CWE-502)."""
    import yaml

    return yaml.safe_load(data)


def safe_yaml_load(fp, max_bytes=YAML_MAX_BYTES, context="NLTK YAML"):
    """Read a YAML document from a file-like object, bounded, with the safe loader."""
    return safe_yaml_loads(_read_bounded(fp, max_bytes, context), context)
