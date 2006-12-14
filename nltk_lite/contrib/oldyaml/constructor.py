
__all__ = ['BaseConstructor', 'SafeConstructor', 'Constructor',
    'ConstructorError']

from error import *
from nodes import *
from composer import *

try:
    import datetime
    datetime_available = True
except ImportError:
    datetime_available = False

try:
    set
except NameError:
    from sets import Set as set

import binascii, re, sys

class ConstructorError(MarkedYAMLError):
    pass

class BaseConstructor(Composer):

    yaml_constructors = {}
    yaml_multi_constructors = {}

    def __init__(self):
        self.constructed_objects = {}
        self.recursive_objects = {}

    def check_data(self):
        # If there are more documents available?
        return self.check_node()

    def get_data(self):
        # Construct and return the next document.
        if self.check_node():
            return self.construct_document(self.get_node())

    def __iter__(self):
        # Iterator protocol.
        while self.check_node():
            yield self.construct_document(self.get_node())

    def construct_document(self, node):
        data = self.construct_object(node)
        self.constructed_objects = {}
        self.recursive_objects = {}
        return data

    def construct_object(self, node):
        if node in self.constructed_objects:
            return self.constructed_objects[node]
        if node in self.recursive_objects:
            raise ConstructorError(None, None,
                    "found recursive node", node.start_mark)
        self.recursive_objects[node] = None
        constructor = None
        if node.tag in self.yaml_constructors:
            constructor = lambda node: self.yaml_constructors[node.tag](self, node)
        else:
            for tag_prefix in self.yaml_multi_constructors:
                if node.tag.startswith(tag_prefix):
                    tag_suffix = node.tag[len(tag_prefix):]
                    constructor = lambda node:  \
                            self.yaml_multi_constructors[tag_prefix](self, tag_suffix, node)
                    break
            else:
                if None in self.yaml_multi_constructors:
                    constructor = lambda node:  \
                            self.yaml_multi_constructors[None](self, node.tag, node)
                elif None in self.yaml_constructors:
                    constructor = lambda node:  \
                            self.yaml_constructors[None](self, node)
                elif isinstance(node, ScalarNode):
                    constructor = self.construct_scalar
                elif isinstance(node, SequenceNode):
                    constructor = self.construct_sequence
                elif isinstance(node, MappingNode):
                    constructor = self.construct_mapping
                else:
                    print node.tag
        data = constructor(node)
        self.constructed_objects[node] = data
        del self.recursive_objects[node]
        return data

    def construct_scalar(self, node):
        if not isinstance(node, ScalarNode):
            if isinstance(node, MappingNode):
                for key_node in node.value:
                    if key_node.tag == u'tag:yaml.org,2002:value':
                        return self.construct_scalar(node.value[key_node])
            raise ConstructorError(None, None,
                    "expected a scalar node, but found %s" % node.id,
                    node.start_mark)
        return node.value

    def construct_sequence(self, node):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None,
                    "expected a sequence node, but found %s" % node.id,
                    node.start_mark)
        return [self.construct_object(child) for child in node.value]

    def construct_mapping(self, node):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        mapping = {}
        merge = None
        for key_node in node.value:
            if key_node.tag == u'tag:yaml.org,2002:merge':
                if merge is not None:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "found duplicate merge key", key_node.start_mark)
                value_node = node.value[key_node]
                if isinstance(value_node, MappingNode):
                    merge = [self.construct_mapping(value_node)]
                elif isinstance(value_node, SequenceNode):
                    merge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, MappingNode):
                            raise ConstructorError("while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found %s"
                                    % subnode.id, subnode.start_mark)
                        merge.append(self.construct_mapping(subnode))
                    merge.reverse()
                else:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "expected a mapping or list of mappings for merging, but found %s"
                            % value_node.id, value_node.start_mark)
            elif key_node.tag == u'tag:yaml.org,2002:value':
                if '=' in mapping:
                    raise ConstructorError("while construction a mapping", node.start_mark,
                            "found duplicate value key", key_node.start_mark)
                value = self.construct_object(node.value[key_node])
                mapping['='] = value
            else:
                key = self.construct_object(key_node)
                try:
                    duplicate_key = key in mapping
                except TypeError, exc:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "found unacceptable key (%s)" % exc, key_node.start_mark)
                if duplicate_key:
                    raise ConstructorError("while constructing a mapping", node.start_mark,
                            "found duplicate key", key_node.start_mark)
                value = self.construct_object(node.value[key_node])
                mapping[key] = value
        if merge is not None:
            merge.append(mapping)
            mapping = {}
            for submapping in merge:
                mapping.update(submapping)
        return mapping

    def construct_pairs(self, node):
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node in node.value:
            key = self.construct_object(key_node)
            value = self.construct_object(node.value[key_node])
            pairs.append((key, value))
        return pairs

    def add_constructor(cls, tag, constructor):
        if not 'yaml_constructors' in cls.__dict__:
            cls.yaml_constructors = cls.yaml_constructors.copy()
        cls.yaml_constructors[tag] = constructor
    add_constructor = classmethod(add_constructor)

    def add_multi_constructor(cls, tag_prefix, multi_constructor):
        if not 'yaml_multi_constructors' in cls.__dict__:
            cls.yaml_multi_constructors = cls.yaml_multi_constructors.copy()
        cls.yaml_multi_constructors[tag_prefix] = multi_constructor
    add_multi_constructor = classmethod(add_multi_constructor)

class SafeConstructor(BaseConstructor):

    def construct_yaml_null(self, node):
        self.construct_scalar(node)
        return None

    bool_values = {
        u'yes':     True,
        u'no':      False,
        u'true':    True,
        u'false':   False,
        u'on':      True,
        u'off':     False,
    }

    def construct_yaml_bool(self, node):
        value = self.construct_scalar(node)
        return self.bool_values[value.lower()]

    def construct_yaml_int(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value == '0':
            return 0
        elif value.startswith('0b'):
            return sign*int(value[2:], 2)
        elif value.startswith('0x'):
            return sign*int(value[2:], 16)
        elif value[0] == '0':
            return sign*int(value, 8)
        elif ':' in value:
            digits = [int(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return sign*int(value)

    inf_value = 1e300000
    nan_value = inf_value/inf_value

    def construct_yaml_float(self, node):
        value = str(self.construct_scalar(node))
        value = value.replace('_', '')
        sign = +1
        if value[0] == '-':
            sign = -1
        if value[0] in '+-':
            value = value[1:]
        if value.lower() == '.inf':
            return sign*self.inf_value
        elif value.lower() == '.nan':
            return self.nan_value
        elif ':' in value:
            digits = [float(part) for part in value.split(':')]
            digits.reverse()
            base = 1
            value = 0.0
            for digit in digits:
                value += digit*base
                base *= 60
            return sign*value
        else:
            return float(value)

    def construct_yaml_binary(self, node):
        value = self.construct_scalar(node)
        try:
            return str(value).decode('base64')
        except (binascii.Error, UnicodeEncodeError), exc:
            raise ConstructorError(None, None,
                    "failed to decode base64 data: %s" % exc, node.start_mark) 

    timestamp_regexp = re.compile(
            ur'''^(?P<year>[0-9][0-9][0-9][0-9])
                -(?P<month>[0-9][0-9]?)
                -(?P<day>[0-9][0-9]?)
                (?:(?:[Tt]|[ \t]+)
                (?P<hour>[0-9][0-9]?)
                :(?P<minute>[0-9][0-9])
                :(?P<second>[0-9][0-9])
                (?:\.(?P<fraction>[0-9]*))?
                (?:[ \t]*(?:Z|(?P<tz_hour>[-+][0-9][0-9]?)
                (?::(?P<tz_minute>[0-9][0-9])?)?))?)?$''', re.X)

    def construct_yaml_timestamp(self, node):
        value = self.construct_scalar(node)
        match = self.timestamp_regexp.match(node.value)
        values = match.groupdict()
        for key in values:
            if values[key]:
                values[key] = int(values[key])
            else:
                values[key] = 0
        fraction = values['fraction']
        if fraction:
            while 10*fraction < 1000000:
                fraction *= 10
            values['fraction'] = fraction
        stamp = datetime.datetime(values['year'], values['month'], values['day'],
                values['hour'], values['minute'], values['second'], values['fraction'])
        diff = datetime.timedelta(hours=values['tz_hour'], minutes=values['tz_minute'])
        return stamp-diff

    def construct_yaml_omap(self, node):
        # Note: we do not check for duplicate keys, because it's too
        # CPU-expensive.
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing an ordered map", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        omap = []
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing an ordered map", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node = subnode.value.keys()[0]
            key = self.construct_object(key_node)
            value = self.construct_object(subnode.value[key_node])
            omap.append((key, value))
        return omap

    def construct_yaml_pairs(self, node):
        # Note: the same code as `construct_yaml_omap`.
        if not isinstance(node, SequenceNode):
            raise ConstructorError("while constructing pairs", node.start_mark,
                    "expected a sequence, but found %s" % node.id, node.start_mark)
        pairs = []
        for subnode in node.value:
            if not isinstance(subnode, MappingNode):
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a mapping of length 1, but found %s" % subnode.id,
                        subnode.start_mark)
            if len(subnode.value) != 1:
                raise ConstructorError("while constructing pairs", node.start_mark,
                        "expected a single mapping item, but found %d items" % len(subnode.value),
                        subnode.start_mark)
            key_node = subnode.value.keys()[0]
            key = self.construct_object(key_node)
            value = self.construct_object(subnode.value[key_node])
            pairs.append((key, value))
        return pairs

    def construct_yaml_set(self, node):
        value = self.construct_mapping(node)
        return set(value)

    def construct_yaml_str(self, node):
        value = self.construct_scalar(node)
        try:
            return str(value)
        except UnicodeEncodeError:
            return value

    def construct_yaml_seq(self, node):
        return self.construct_sequence(node)

    def construct_yaml_map(self, node):
        return self.construct_mapping(node)

    def construct_yaml_object(self, node, cls):
        state = self.construct_mapping(node)
        data = cls.__new__(cls)
        if hasattr(data, '__setstate__'):
            data.__setstate__(state)
        else:
            data.__dict__.update(state)
        return data

    def construct_undefined(self, node):
        raise ConstructorError(None, None,
                "could not determine a constructor for the tag %r" % node.tag.encode('utf-8'),
                node.start_mark)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:null',
        SafeConstructor.construct_yaml_null)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:bool',
        SafeConstructor.construct_yaml_bool)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:int',
        SafeConstructor.construct_yaml_int)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:float',
        SafeConstructor.construct_yaml_float)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:binary',
        SafeConstructor.construct_yaml_binary)

if datetime_available:
    SafeConstructor.add_constructor(
            u'tag:yaml.org,2002:timestamp',
            SafeConstructor.construct_yaml_timestamp)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:omap',
        SafeConstructor.construct_yaml_omap)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:pairs',
        SafeConstructor.construct_yaml_pairs)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:set',
        SafeConstructor.construct_yaml_set)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:str',
        SafeConstructor.construct_yaml_str)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:seq',
        SafeConstructor.construct_yaml_seq)

SafeConstructor.add_constructor(
        u'tag:yaml.org,2002:map',
        SafeConstructor.construct_yaml_map)

SafeConstructor.add_constructor(None,
        SafeConstructor.construct_undefined)

class Constructor(SafeConstructor):

    def construct_python_str(self, node):
        return self.construct_scalar(node).encode('utf-8')

    def construct_python_unicode(self, node):
        return self.construct_scalar(node)

    def construct_python_long(self, node):
        return long(self.construct_yaml_int(node))

    def construct_python_complex(self, node):
       return complex(self.construct_scalar(node))

    def construct_python_tuple(self, node):
        return tuple(self.construct_yaml_seq(node))

    def find_python_module(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python module", mark,
                    "expected non-empty name appended to the tag", mark)
        try:
            __import__(name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python module", mark,
                    "cannot find module %r (%s)" % (name.encode('utf-8'), exc), mark)
        return sys.modules[name]

    def find_python_name(self, name, mark):
        if not name:
            raise ConstructorError("while constructing a Python object", mark,
                    "expected non-empty name appended to the tag", mark)
        if u'.' in name:
            # Python 2.4 only
            #module_name, object_name = name.rsplit('.', 1)
            items = name.split('.')
            object_name = items.pop()
            module_name = '.'.join(items)
        else:
            module_name = '__builtin__'
            object_name = name
        try:
            __import__(module_name)
        except ImportError, exc:
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find module %r (%s)" % (module_name.encode('utf-8'), exc), mark)
        module = sys.modules[module_name]
        if not hasattr(module, object_name):
            raise ConstructorError("while constructing a Python object", mark,
                    "cannot find %r in the module %r" % (object_name.encode('utf-8'),
                        module.__name__), mark)
        return getattr(module, object_name)

    def construct_python_name(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python name", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_name(suffix, node.start_mark)

    def construct_python_module(self, suffix, node):
        value = self.construct_scalar(node)
        if value:
            raise ConstructorError("while constructing a Python module", node.start_mark,
                    "expected the empty value, but found %r" % value.encode('utf-8'),
                    node.start_mark)
        return self.find_python_module(suffix, node.start_mark)

    class classobj: pass

    def make_python_instance(self, suffix, node,
            args=None, kwds=None, newobj=False):
        if not args:
            args = []
        if not kwds:
            kwds = {}
        cls = self.find_python_name(suffix, node.start_mark)
        if newobj and isinstance(cls, type(self.classobj))  \
                and not args and not kwds:
            instance = self.classobj()
            instance.__class__ = cls
            return instance
        elif newobj and isinstance(cls, type):
            return cls.__new__(cls, *args, **kwds)
        else:
            return cls(*args, **kwds)

    def set_python_instance_state(self, instance, state):
        if hasattr(instance, '__setstate__'):
            instance.__setstate__(state)
        else:
            slotstate = {}
            if isinstance(state, tuple) and len(state) == 2:
                state, slotstate = state
            if hasattr(instance, '__dict__'):
                instance.__dict__.update(state)
            elif state:
                slotstate.update(state)
            for key, value in slotstate.items():
                setattr(object, key, value)

    def construct_python_object(self, suffix, node):
        # Format:
        #   !!python/object:module.name { ... state ... }
        instance = self.make_python_instance(suffix, node, newobj=True)
        state = self.construct_mapping(node)
        self.set_python_instance_state(instance, state)
        return instance

    def construct_python_object_apply(self, suffix, node, newobj=False):
        # Format:
        #   !!python/object/apply       # (or !!python/object/new)
        #   args: [ ... arguments ... ]
        #   kwds: { ... keywords ... }
        #   state: ... state ...
        #   listitems: [ ... listitems ... ]
        #   dictitems: { ... dictitems ... }
        # or short format:
        #   !!python/object/apply [ ... arguments ... ]
        # The difference between !!python/object/apply and !!python/object/new
        # is how an object is created, check make_python_instance for details.
        if isinstance(node, SequenceNode):
            args = self.construct_sequence(node)
            kwds = {}
            state = {}
            listitems = []
            dictitems = {}
        else:
            value = self.construct_mapping(node)
            args = value.get('args', [])
            kwds = value.get('kwds', {})
            state = value.get('state', {})
            listitems = value.get('listitems', [])
            dictitems = value.get('dictitems', {})
        instance = self.make_python_instance(suffix, node, args, kwds, newobj)
        if state:
            self.set_python_instance_state(instance, state)
        if listitems:
            instance.extend(listitems)
        if dictitems:
            for key in dictitems:
                instance[key] = dictitems[key]
        return instance

    def construct_python_object_new(self, suffix, node):
        return self.construct_python_object_apply(suffix, node, newobj=True)


Constructor.add_constructor(
    u'tag:yaml.org,2002:python/none',
    Constructor.construct_yaml_null)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/bool',
    Constructor.construct_yaml_bool)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/str',
    Constructor.construct_python_str)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/unicode',
    Constructor.construct_python_unicode)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/int',
    Constructor.construct_yaml_int)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/long',
    Constructor.construct_python_long)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/float',
    Constructor.construct_yaml_float)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/complex',
    Constructor.construct_python_complex)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/list',
    Constructor.construct_yaml_seq)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/tuple',
    Constructor.construct_python_tuple)

Constructor.add_constructor(
    u'tag:yaml.org,2002:python/dict',
    Constructor.construct_yaml_map)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/name:',
    Constructor.construct_python_name)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/module:',
    Constructor.construct_python_module)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object:',
    Constructor.construct_python_object)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/apply:',
    Constructor.construct_python_object_apply)

Constructor.add_multi_constructor(
    u'tag:yaml.org,2002:python/object/new:',
    Constructor.construct_python_object_new)

