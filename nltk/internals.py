# Natural Language Toolkit: Internal utility functions
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import subprocess
import os
import os.path
import re
import warnings
import textwrap
import types
import sys
import stat

from nltk import __file__

# Use the c version of ElementTree, which is faster, if possible:
try: from xml.etree import cElementTree as ElementTree
except ImportError: from nltk.etree import ElementTree

######################################################################
# Regular Expression Processing
######################################################################

def convert_regexp_to_nongrouping(pattern):
    """
    Convert all grouping parenthases in the given regexp pattern to
    non-grouping parenthases, and return the result.  E.g.:

        >>> convert_regexp_to_nongrouping('ab(c(x+)(z*))?d')
        'ab(?:c(?:x+)(?:z*))?d'

    @type pattern: C{str}
    @rtype: C{str}
    """
    # Sanity check: back-references are not allowed!
    for s in re.findall(r'\\.|\(\?P=', pattern):
        if s[1] in '0123456789' or s == '(?P=':
            raise ValueError('Regular expressions with back-references '
                             'are not supported: %r' % pattern)
    
    # This regexp substitution function replaces the string '('
    # with the string '(?:', but otherwise makes no changes.
    def subfunc(m):
        return re.sub('^\((\?P<[^>]*>)?$', '(?:', m.group())

    # Scan through the regular expression.  If we see any backslashed
    # characters, ignore them.  If we see a named group, then
    # replace it with "(?:".  If we see any open parens that are part
    # of an extension group, ignore those too.  But if we see
    # any other open paren, replace it with "(?:")
    return re.sub(r'''(?x)
        \\.           |  # Backslashed character
        \(\?P<[^>]*>  |  # Named group
        \(\?          |  # Extension group
        \(               # Grouping parenthasis''', subfunc, pattern)


##########################################################################
# Java Via Command-Line
##########################################################################

_java_bin = None
_java_options = []
# [xx] add classpath option to config_java?
def config_java(bin=None, options=None):
    """
    Configure nltk's java interface, by letting nltk know where it can
    find the C{java} binary, and what extra options (if any) should be
    passed to java when it is run.

    @param bin: The full path to the C{java} binary.  If not specified,
        then nltk will search the system for a C{java} binary; and if
        one is not found, it will raise a C{LookupError} exception.
    @type bin: C{string}
    @param options: A list of options that should be passed to the
        C{java} binary when it is called.  A common value is
        C{['-Xmx512m']}, which tells the C{java} binary to increase
        the maximum heap size to 512 megabytes.  If no options are
        specified, then do not modify the options list.
    @type options: C{list} of C{string}
    """
    global _java_bin, _java_options
    _java_bin = find_binary('java', bin, env_vars=['JAVAHOME', 'JAVA_HOME'])
        
    if options is not None:
        if isinstance(options, basestring):
            options = options.split()
        _java_options = list(options)

def java(cmd, classpath=None, stdin=None, stdout=None, stderr=None,
         blocking=True):
    """
    Execute the given java command, by opening a subprocess that calls
    C{java}.  If java has not yet been configured, it will be configured
    by calling L{config_java()} with no arguments.

    @param cmd: The java command that should be called, formatted as
        a list of strings.  Typically, the first string will be the name
        of the java class; and the remaining strings will be arguments
        for that java class.
    @type cmd: C{list} of C{string}

    @param classpath: A C{':'} separated list of directories, JAR
        archives, and ZIP archives to search for class files.
    @type classpath: C{string}

    @param stdin, stdout, stderr: Specify the executed programs'
        standard input, standard output and standard error file
        handles, respectively.  Valid values are C{subprocess.PIPE},
        an existing file descriptor (a positive integer), an existing
        file object, and C{None}.  C{subprocess.PIPE} indicates that a
        new pipe to the child should be created.  With C{None}, no
        redirection will occur; the child's file handles will be
        inherited from the parent.  Additionally, stderr can be
        C{subprocess.STDOUT}, which indicates that the stderr data
        from the applications should be captured into the same file
        handle as for stdout.

    @param blocking: If C{false}, then return immediately after
        spawning the subprocess.  In this case, the return value is
        the C{Popen} object, and not a C{(stdout, stderr)} tuple.

    @return: If C{blocking=True}, then return a tuple C{(stdout,
        stderr)}, containing the stdout and stderr outputs generated
        by the java command if the C{stdout} and C{stderr} parameters
        were set to C{subprocess.PIPE}; or C{None} otherwise.  If
        C{blocking=False}, then return a C{subprocess.Popen} object.

    @raise OSError: If the java command returns a nonzero return code.
    """
    if stdin == 'pipe': stdin = subprocess.PIPE
    if stdout == 'pipe': stdout = subprocess.PIPE
    if stderr == 'pipe': stderr = subprocess.PIPE
    if isinstance(cmd, basestring):
        raise TypeError('cmd should be a list of strings')

    # Make sure we know where a java binary is.
    if _java_bin is None:
        config_java()

    # Set up the classpath.
    if classpath is None:
        classpath = NLTK_JAR
    else:
        classpath += ':' + NLTK_JAR

    # Construct the full command string.
    cmd = list(cmd)
    cmd = ['-cp', classpath] + cmd
    cmd = [_java_bin] + _java_options + cmd

    # Call java via a subprocess
    p = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
    if not blocking: return p
    (stdout, stderr) = p.communicate()

    # Check the return code.
    if p.returncode != 0:
        print stderr
        raise OSError('Java command failed!')

    return (stdout, stderr)

#: The location of the NLTK jar file, which is used to communicate
#: with external Java packages (such as Mallet) that do not have
#: a sufficiently powerful native command-line interface.
NLTK_JAR = os.path.abspath(os.path.join(os.path.split(__file__)[0],
                                        'nltk.jar'))

if 0:
    #config_java(options='-Xmx512m')
    # Write:
    #java('weka.classifiers.bayes.NaiveBayes',
    #     ['-d', '/tmp/names.model', '-t', '/tmp/train.arff'],
    #     classpath='/Users/edloper/Desktop/weka/weka.jar')
    # Read:
    (a,b) = java(['weka.classifiers.bayes.NaiveBayes',
                  '-l', '/tmp/names.model', '-T', '/tmp/test.arff',
                  '-p', '0'],#, '-distribution'],
                 classpath='/Users/edloper/Desktop/weka/weka.jar')


######################################################################
# Parsing
######################################################################

class ParseError(ValueError):
    """
    Exception raised by parse_* functions when they fail.
    @param position: The index in the input string where an error occured.
    @param expected: What was expected when an error occured.
    """
    def __init__(self, expected, position):
        ValueError.__init__(self, expected, position)
        self.expected = expected
        self.position = position
    def __str__(self):
        return 'Expected %s at %s' % (self.expected, self.position)

_STRING_START_RE = re.compile(r"[uU]?[rR]?(\"\"\"|\'\'\'|\"|\')")
def parse_str(s, start_position):
    """
    If a Python string literal begins at the specified position in the
    given string, then return a tuple C{(val, end_position)}
    containing the value of the string literal and the position where
    it ends.  Otherwise, raise a L{ParseError}.
    """
    # Read the open quote, and any modifiers.
    m = _STRING_START_RE.match(s, start_position)
    if not m: raise ParseError('open quote', start_position)
    quotemark = m.group(1)

    # Find the close quote.
    _STRING_END_RE = re.compile(r'\\|%s' % quotemark)
    position = m.end()
    while True:
        match = _STRING_END_RE.search(s, position)
        if not match: raise ParseError('close quote', position)
        if match.group(0) == '\\': position = match.end()+1
        else: break

    # Parse it, using eval.  Strings with invalid escape sequences
    # might raise ValueEerror.
    try:
        return eval(s[start_position:match.end()]), match.end()
    except ValueError, e:
        raise ParseError('valid string (%s)' % e, start)

_PARSE_INT_RE = re.compile(r'-?\d+')
def parse_int(s, start_position):
    """
    If an integer begins at the specified position in the given
    string, then return a tuple C{(val, end_position)} containing the
    value of the integer and the position where it ends.  Otherwise,
    raise a L{ParseError}.
    """
    m = _PARSE_INT_RE.match(s, start_position)
    if not m: raise ParseError('integer', start_position)
    return int(m.group()), m.end()

_PARSE_NUMBER_VALUE = re.compile(r'-?(\d*)([.]?\d*)?')
def parse_number(s, start_position):
    """
    If an integer or float begins at the specified position in the
    given string, then return a tuple C{(val, end_position)}
    containing the value of the number and the position where it ends.
    Otherwise, raise a L{ParseError}.
    """
    m = _PARSE_NUMBER_VALUE.match(s, start_position)
    if not m or not (m.group(1) or m.group(2)):
        raise ParseError('number', start_position)
    if m.group(2): return float(m.group()), m.end()
    else: return int(m.group()), m.end()
    


######################################################################
# Check if a method has been overridden
######################################################################

def overridden(method):
    """
    @return: True if C{method} overrides some method with the same
    name in a base class.  This is typically used when defining
    abstract base classes or interfaces, to allow subclasses to define
    either of two related methods:

        >>> class EaterI:
        ...     '''Subclass must define eat() or batch_eat().'''
        ...     def eat(self, food):
        ...         if overridden(self.batch_eat):
        ...             return self.batch_eat([food])[0]
        ...         else:
        ...             raise NotImplementedError()
        ...     def batch_eat(self, foods):
        ...         return [self.eat(food) for food in foods]

    @type method: instance method
    """
    # [xx] breaks on classic classes!
    if isinstance(method, types.MethodType) and method.im_class is not None:
        name = method.__name__
        funcs = [cls.__dict__[name]
                 for cls in _mro(method.im_class)
                 if name in cls.__dict__]
        return len(funcs) > 1
    else:
        raise TypeError('Expected an instance method.')

def _mro(cls):
    """
    Return the I{method resolution order} for C{cls} -- i.e., a list
    containing C{cls} and all its base classes, in the order in which
    they would be checked by C{getattr}.  For new-style classes, this
    is just cls.__mro__.  For classic classes, this can be obtained by
    a depth-first left-to-right traversal of C{__bases__}.
    """
    if isinstance(cls, type):
        return cls.__mro__
    else:
        mro = [cls]
        for base in cls.__bases__: mro.extend(_mro(base))
        return mro

######################################################################
# Deprecation decorator & base class
######################################################################
# [xx] dedent msg first if it comes from  a docstring.

def _add_epytext_field(obj, field, message):
    """Add an epytext @field to a given object's docstring."""
    indent = ''
    # If we already have a docstring, then add a blank line to separate
    # it from the new field, and check its indentation.
    if obj.__doc__:
        obj.__doc__ = obj.__doc__.rstrip()+'\n\n'
        indents = re.findall(r'(?<=\n)[ ]+(?!\s)', obj.__doc__.expandtabs())
        if indents: indent = min(indents)
    # If we don't have a docstring, add an empty one.
    else:
        obj.__doc__ = ''

    obj.__doc__ += textwrap.fill('@%s: %s' % (field, message),
                                 initial_indent=indent,
                                 subsequent_indent=indent+'    ')

def deprecated(message):
    """
    A decorator used to mark functions as deprecated.  This will cause
    a warning to be printed the when the function is used.  Usage:

      >>> @deprecated('Use foo() instead')
      >>> def bar(x):
      ...     print x/10
    """
    def decorator(func):
        msg = ("Function %s() has been deprecated.  %s"
               % (func.__name__, message))
        msg = '\n' + textwrap.fill(msg, initial_indent='  ',
                                   subsequent_indent='  ')
        def newFunc(*args, **kwargs):
            warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
            
        # Copy the old function's name, docstring, & dict
        newFunc.__dict__.update(func.__dict__)
        newFunc.__name__ = func.__name__
        newFunc.__doc__ = func.__doc__
        newFunc.__deprecated__ = True
        # Add a @deprecated field to the docstring.
        _add_epytext_field(newFunc, 'deprecated', message)
        return newFunc
    return decorator

class Deprecated(object):
    """
    A base class used to mark deprecated classes.  A typical usage is to
    alert users that the name of a class has changed:

        >>> class OldClassName(Deprecated, NewClassName):
        ...     "Use NewClassName instead."

    The docstring of the deprecated class will be used in the
    deprecation warning message.
    """
    def __new__(cls, *args, **kwargs):
        # Figure out which class is the deprecated one.
        dep_cls = None
        for base in _mro(cls):
            if Deprecated in base.__bases__:
                dep_cls = base; break
        assert dep_cls, 'Unable to determine which base is deprecated.'

        # Construct an appropriate warning.
        doc = dep_cls.__doc__ or ''.strip()
        # If there's a @deprecated field, strip off the field marker.
        doc = re.sub(r'\A\s*@deprecated:', r'', doc)
        # Strip off any indentation.
        doc = re.sub(r'(?m)^\s*', '', doc)
        # Construct a 'name' string.
        name = 'Class %s' % dep_cls.__name__
        if cls != dep_cls:
            name += ' (base class for %s)' % cls.__name__
        # Put it all together.
        msg = '%s has been deprecated.  %s' % (name, doc)
        # Wrap it.
        msg = '\n' + textwrap.fill(msg, initial_indent='    ',
                                   subsequent_indent='    ')
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        # Do the actual work of __new__.
        return object.__new__(cls, *args, **kwargs)

##########################################################################
# COUNTER, FOR UNIQUE NAMING
##########################################################################

class Counter:
    """
    A counter that auto-increments each time its value is read.
    """
    def __init__(self, initial_value=0):
        self._value = initial_value
    def get(self):
        self._value += 1
        return self._value

##########################################################################
# Search for binaries
##########################################################################

def find_binary(name, path_to_bin=None, env_vars=(), 
                searchpath=(), binary_names=None, url=None,
                verbose=True):
    """
    Search for the binary for a program that is used by nltk.

    @param name: The name of the program
    @param path_to_bin: The user-supplied binary location, or None.
    @param env_vars: A list of environment variable names to check
    @param binary_names: A list of alternative binary names to check.
    @param searchpath: List of directories to search.
    """
    if binary_names is None: binary_names = [name]
    assert isinstance(name, basestring)
    assert not isinstance(binary_names, basestring)
    assert not isinstance(searchpath, basestring)
    if isinstance(env_vars, basestring):
        env_vars = env_vars.split()
    
    # If an explicit bin was given, then check it, and return it if
    # it's present; otherwise, complain.
    if path_to_bin is not None:
        if os.path.isfile(path_to_bin):
            return path_to_bin
        for bin in binary_names:
            if os.path.isfile(os.path.join(path_to_bin, bin)):
                return os.path.join(path_to_bin, bin)
            if os.path.isfile(os.path.join(path_to_bin, 'bin', bin)):
                return os.path.join(path_to_bin, 'bin', bin)
        raise ValueError('Could not find %s binary at %s' %
                         (name, path_to_bin))
    
    # Check environment variables
    for env_var in env_vars:
        if env_var in os.environ:
            path_to_bin = os.environ[env_var]
            if os.path.isfile(path_to_bin):
                if verbose: print '[Found %s: %s]' % (name, path_to_bin)
                return os.environ[env_var]
            else:
                for bin_name in binary_names:
                    path_to_bin = os.path.join(os.environ[env_var], bin_name)
                    if os.path.isfile(path_to_bin):
                        if verbose: print '[Found %s: %s]'%(name, path_to_bin)
                        return path_to_bin
                    path_to_bin = os.path.join(os.environ[env_var], 'bin',
                                               bin_name)
                    if os.path.isfile(path_to_bin):
                        if verbose: print '[Found %s: %s]'%(name, path_to_bin)
                        return path_to_bin

    # Check the path list.
    for directory in searchpath:
        for bin in binary_names:
            path_to_bin = os.path.join(directory, bin)
            if os.path.isfile(path_to_bin):
                return path_to_bin
        

    # If we're on a POSIX system, then try using the 'which' command
    # to find the binary.
    if os.name == 'posix':
        for bin in binary_names:
            try:
                p = subprocess.Popen(['which', bin], stdout=subprocess.PIPE)
                stdout, stderr = p.communicate()
                path = stdout.strip()
                if path.endswith(bin) and os.path.exists(path):
                    if verbose: print '[Found %s: %s]' % (name, path)
                    return path
            except KeyboardInterrupt, SystemExit:
                raise
            except:
                pass

    msg = ("NLTK was unable to find the %s executable!  Use "
           "config_%s()" % (name, name))
    if env_vars: msg += ' or set the %s environment variable' % env_vars[0]
    msg = textwrap.fill(msg+'.', initial_indent='  ',
                        subsequent_indent='  ')
    msg += "\n\n    >>> config_%s('/path/to/%s')" % (name, name)
    if searchpath:
        msg += '\n\n  Searched in:'
        msg += ''.join('\n    - %s' % d for d in searchpath)
    if url: msg += ('\n\n  For more information, on %s, see:\n    <%s>' %
                    (name, url))
    div = '='*75
    raise LookupError('\n\n%s\n%s\n%s' % (div, msg, div))

##########################################################################
# Import Stdlib Module
##########################################################################

def import_from_stdlib(module):
    """
    When python is run from within the nltk/ directory tree, the
    current directory is included at the beginning of the search path.
    Unfortunately, that means that modules within nltk can sometimes
    shadow standard library modules.  As an example, the stdlib
    'inspect' module will attempt to import the stdlib 'tokenzie'
    module, but will instead end up importing NLTK's 'tokenize' module
    instead (causing the import to fail).
    """
    old_path = sys.path
    sys.path = [d for d in sys.path if d not in ('', '.')]
    m = __import__(module)
    sys.path = old_path
    return m

##########################################################################
# Abstract declaration
##########################################################################

def abstract(func):
    """
    A decorator used to mark methods as abstract.  I.e., methods that
    are marked by this decorator must be overridden by subclasses.  If
    an abstract method is called (either in the base class or in a
    subclass that does not override the base class method), it will
    raise C{NotImplementedError}.
    """
    # Avoid problems caused by nltk.tokenize shadowing the stdlib tokenize:
    inspect = import_from_stdlib('inspect')

    # Read the function's signature.
    args, varargs, varkw, defaults = inspect.getargspec(func)

    # Create a new function with the same signature (minus defaults)
    # that raises NotImplementedError.
    msg = '%s is an abstract method.' % func.__name__
    signature = inspect.formatargspec(args, varargs, varkw, ())
    exec ('def newfunc%s: raise NotImplementedError(%r)' % (signature, msg))

    # Substitute in the defaults after-the-fact, since eval(repr(val))
    # may not work for some default values.
    newfunc.func_defaults = func.func_defaults
    
    # Copy the name and docstring
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__abstract__ = True
    _add_epytext_field(newfunc, "note", "This method is abstract.")

    # Return the function.
    return newfunc

##########################################################################
# Wrapper for ElementTree Elements
##########################################################################

class ElementWrapper(object):
    """
    A wrapper around ElementTree Element objects whose main purpose is
    to provide nicer __repr__ and __str__ methods.  In addition, any
    of the wrapped Element's methods that return other Element objects
    are overridden to wrap those values before returning them.

    This makes Elements more convenient to work with in
    interactive sessions and doctests, at the expense of some
    efficiency.
    """
    
    # Prevent double-wrapping:
    def __new__(cls, etree):
        """
        Create and return a wrapper around a given Element object.
        If C{etree} is an C{ElementWrapper}, then C{etree} is
        returned as-is.
        """
        if isinstance(etree, ElementWrapper):
            return etree
        else:
            return object.__new__(ElementWrapper, etree)

    def __init__(self, etree):
        """
        Initialize a new Element wrapper for C{etree}.  If
        C{etree} is a string, then it will be converted to an
        Element object using C{ElementTree.fromstring()} first.
        """
        if isinstance(etree, basestring):
            etree = ElementTree.fromstring(etree)
        self.__dict__['_etree'] = etree

    def unwrap(self):
        """
        Return the Element object wrapped by this wrapper.
        """
        return self._etree

    ##////////////////////////////////////////////////////////////
    #{ String Representation
    ##////////////////////////////////////////////////////////////
    
    def __repr__(self):
        s = ElementTree.tostring(self._etree)
        if len(s) > 60:
            e = s.rfind('<')
            if (len(s)-e) > 30: e = -20
            s = '%s...%s' % (s[:30], s[e:])
        return '<Element %r>' % s

    def __str__(self):
        """
        @return: the result of applying C{ElementTree.tostring()} to
        the wrapped Element object.
        """
        return ElementTree.tostring(self._etree).rstrip()

    ##////////////////////////////////////////////////////////////
    #{ Element interface Delegation (pass-through)
    ##////////////////////////////////////////////////////////////
    
    def __getattr__(self, attrib):
        return getattr(self._etree, attrib)
    
    def __setattr__(self, attr, value):
        return setattr(self._etree, attr, value)
    
    def __delattr__(self, attr):
        return delattr(self._etree, attr)

    def __setitem__(self, index, element):
        self._etree[index] = element

    def __delitem__(self, index):
        del self._etree[index]

    def __setslice__(self, start, stop, elements):
        self._etree[start:stop] = elements

    def __delslice__(self, start, stop):
        del self._etree[start:stop]

    def __len__(self):
        return len(self._etree)

    ##////////////////////////////////////////////////////////////
    #{ Element interface Delegation (wrap result)
    ##////////////////////////////////////////////////////////////
    
    def __getitem__(self, index):
        return ElementWrapper(self._etree[index])

    def __getslice__(self, start, stop):
        return [ElementWrapper(elt) for elt in self._etree[start:stop]]

    def getchildren(self):
        return [ElementWrapper(elt) for elt in self._etree]

    def getiterator(self, tag=None):
        return (ElementWrapper(elt)
                for elt in self._etree.getiterator(tag))

    def makeelement(self, tag, attrib):
        return ElementWrapper(self._etree.makeelement(tag, attrib))

    def find(self, path):
        elt = self._etree.find(path)
        if elt is None: return elt
        else: return ElementWrapper(elt)

    def findall(self, path):
        return [ElementWrapper(elt) for elt in self._etree.findall(path)]

######################################################################
# Helper for Handling Slicing 
######################################################################

def slice_bounds(sequence, slice_obj, allow_step=False):
    """
    Given a slice, return the corresponding (start, stop) bounds,
    taking into account None indices and negative indices.  The
    following guarantees are made for the returned start and stop values:

      - 0 <= start <= len(sequence)
      - 0 <= stop <= len(sequence)
      - start <= stop

    @raise ValueError: If C{slice_obj.step} is not C{None}.
    @param allow_step: If true, then the slice object may have a
        non-None step.  If it does, then return a tuple
        (start, stop, step).
    """
    start, stop = (slice_obj.start, slice_obj.stop)

    # If allow_step is true, then include the step in our return
    # value tuple.  
    if allow_step:
        if slice_obj.step is None: slice_obj.step = 1
        # Use a recursive call without allow_step to find the slice
        # bounds.  If step is negative, then the roles of start and
        # stop (in terms of default values, etc), are swapped.
        if slice_obj.step < 0:
            start, stop = slice_bounds(sequence, slice(stop, start))
        else:
            start, stop = slice_bounds(sequence, slice(start, stop))
        return start, stop, slice_obj.step

    # Otherwise, make sure that no non-default step value is used.
    elif slice_obj.step not in (None, 1):
        raise ValueError('slices with steps are not supported by %s' %
                         sequence.__class__.__name__)

    # Supply default offsets.
    if start is None: start = 0
    if stop is None: stop = len(sequence)
    
    # Handle negative indices.
    if start < 0: start = max(0, len(sequence)+start)
    if stop < 0: stop = max(0, len(sequence)+stop)

    # Make sure stop doesn't go past the end of the list.  Note that
    # we avoid calculating len(sequence) if possible, because for lazy
    # sequences, calculating the length of a sequence can be expensive.
    if stop > 0:
        try: sequence[stop-1]
        except IndexError: stop = len(sequence)
    
    # Make sure start isn't past stop.
    start = min(start, stop)

    # That's all folks!
    return start, stop    

######################################################################
# Permission Checking
######################################################################

def is_writable(path):
    # Ensure that it exists.
    if not os.path.exists(path):
        return False

    # If we're on a posix system, check its permissions.
    if hasattr(os, 'getuid'):
        statdata = os.stat(path)
        perm = stat.S_IMODE(statdata.st_mode)
        # is it world-writable?
        if (perm & 0002):
            return True
        # do we own it?
        elif statdata.st_uid == os.getuid() and (perm & 0200):
            return True
        # are we in a group that can write to it?
        elif statdata.st_gid == os.getgid() and (perm & 0020):
            return True
        # otherwise, we can't write to it.
        else:
            return False

    # Otherwise, we'll assume it's writable.
    # [xx] should we do other checks on other platforms?
    return True
