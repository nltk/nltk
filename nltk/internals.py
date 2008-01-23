# Natural Language Toolkit: Internal utility functions
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import subprocess, os.path, re, warnings, textwrap
import types

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
    if bin is not None:
        if not os.path.exists(bin):
            raise ValueError('Could not find java binary at %r' % bin)
        _java_bin = bin
    if options is not None:
        if isinstance(options, basestring):
            options = options.split()
        _java_options = list(options)

    # Check the JAVAHOME environment variable.
    for env_var in ['JAVAHOME', 'JAVA_HOME']:
        if _java_bin is None and env_var in os.environ:
            paths = [os.path.join(os.environ[env_var], 'java'),
                     os.path.join(os.environ[env_var], 'bin', 'java')]
            for path in paths:
                if os.path.exists(path):
                    _java_bin = path
                    print '[Found java: %s]' % path

    # If we're on a POSIX system, try using the 'which' command to
    # find a java binary.
    if _java_bin is None and os.name == 'posix':
        try:
            p = subprocess.Popen(['which', 'java'], stdout=subprocess.PIPE)
            stdout, stderr = p.communicate()
            path = stdout.strip()
            if path.endswith('java') and os.path.exists(path):
                _java_bin = path
                print '[Found java: %s]' % path
        except:
            pass

    if _java_bin is None:
        raise LookupError('Unable to find java!  Use config_java() '
                          'or set the JAVAHOME environment variable.')

def java(cmd, classpath=None, stdin=None, stdout=None, stderr=None):
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

    @return: A tuple C{(stdout, stderr)}, containing the stdout and
        stderr outputs generated by the java command if the C{stdout}
        and C{stderr} parameters were set to C{subprocess.PIPE}; or
        C{None} otherwise.

    @raise OSError: If the java command returns a nonzero return code.
    """
    if isinstance(cmd, basestring):
        raise TypeError('cmd should be a list of strings')

    # Make sure we know where a java binary is.
    if _java_bin is None:
        config_java()
        
    # Construct the full command string.
    cmd = list(cmd)
    if classpath is not None:
        cmd = ['-cp', classpath] + cmd
    cmd = [_java_bin] + _java_options + cmd

    # Call java via a subprocess
    p = subprocess.Popen(cmd, stdin=stdin, stdout=stdout, stderr=stderr)
    (stdout, stderr) = p.communicate()

    # Check the return code.
    if p.returncode != 0:
        print stderr
        raise OSError('Java command failed!')

    return (stdout, stderr)

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

def _add_deprecated_field(obj, message):
    """Add a @deprecated field to a given object's docstring."""
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

    obj.__doc__ += textwrap.fill('@deprecated: %s' % message,
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
        _add_deprecated_field(newFunc, message)
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


