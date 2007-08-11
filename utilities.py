# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import subprocess, os.path, locale, re, warnings, textwrap

##########################################################################
# PRETTY PRINTING
##########################################################################

def pr(data, start=0, end=None):
    """
    Pretty print a sequence of data items

    @param data: the data stream to print
    @type data: C{sequence} or C{iterator}
    @param start: the start position
    @type start: C{int}
    @param end: the end position
    @type end: C{int}
    """
    from pprint import pprint
    from itertools import islice
    pprint(list(islice(data, start, end)))

def print_string(s, width=70):
    """
    Pretty print a string, breaking lines on whitespace

    @param s: the string to print, consisting of words and spaces
    @type s: C{string}
    @param width: the display width
    @type width: C{int}
    """
    while s:
        s = s.strip()
        try:
            i = s[:width].rindex(' ')
        except ValueError:
            print s
            return
        print s[:i]
        s = s[i:]

class SortedDict(dict):
    """
    A very rudamentary sorted dictionary, whose main purpose is to
    allow dictionaries to be displayed in a consistent order in
    regression tests.  keys(), items(), values(), iter*(), and
    __repr__ all sort their return values before returning them.
    (note that the sort order for values() does *not* correspond to
    the sort order for keys().  I.e., zip(d.keys(), d.values()) is not
    necessarily equal to d.items().
    """
    def keys(self): return sorted(dict.keys(self))
    def items(self): return sorted(dict.items(self))
    def values(self): return sorted(dict.values(self))
    def iterkeys(self): return iter(sorted(dict.keys(self)))
    def iteritems(self): return iter(sorted(dict.items(self)))
    def itervalues(self): return iter(sorted(dict.values(self)))
    def __iter__(self): return iter(sorted(dict.keys(self)))
    def repr(self):
        items = ['%s=%s' % t for t in sorted(self.items())]
        return '{%s}' % ', '.join(items)
    
# OrderedDict: Written Doug Winter
# http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/438823

class OrderedDict(dict):
    """
    This implementation of a dictionary keeps track of the order
    in which keys were inserted.
    """

    def __init__(self, d={}):
        self._keys = d.keys()
        dict.__init__(self, d)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        dict.__setitem__(self, key, item)
        # a peculiar sharp edge from copy.deepcopy
        # we'll have our set item called without __init__
        if not hasattr(self, '_keys'):
            self._keys = [key,]
        if key not in self._keys:
            self._keys.append(key)

    def clear(self):
        dict.clear(self)
        self._keys = []

    def items(self):
        for i in self._keys:
            yield i, self[i]

    def keys(self):
        return self._keys

    def popitem(self):
        if len(self._keys) == 0:
            raise KeyError('dictionary is empty')
        else:
            key = self._keys[-1]
            val = self[key]
            del self[key]
            return key, val

    def setdefault(self, key, failobj = None):
        dict.setdefault(self, key, failobj)
        if key not in self._keys:
            self._keys.append(key)

    def update(self, d):
        for key in d.keys():
            if key not in self:
                self._keys.append(key)
        dict.update(self, d)

    def values(self):
        for i in self._keys:
            yield self[i]

    def move(self, key, index):

        """ Move the specified to key to *before* the specified index. """

        try:
            cur = self._keys.index(key)
        except ValueError:
            raise KeyError(key)
        self._keys.insert(index, key)
        # this may have shifted the position of cur, if it is after index
        if cur >= index: cur = cur + 1
        del self._keys[cur]

    def index(self, key):
        if key not in self:
            raise KeyError(key)
        return self._keys.index(key)


##########################################################################
# EDIT DISTANCE (LEVENSHTEIN)
##########################################################################

def _edit_dist_init(len1, len2):
    lev = []
    for i in range(len1):
        lev.append([0] * len2)  # initialize 2-D array to zero
    for i in range(len1):
        lev[i][0] = i           # column 0: 0,1,2,3,4,...
    for j in range(len2):
        lev[0][j] = j           # row 0: 0,1,2,3,4,...
    return lev

def _edit_dist_step(lev, i, j, c1, c2):
    a = lev[i-1][j  ] + 1            # skipping s1[i]
    b = lev[i-1][j-1] + (c1 != c2)   # matching s1[i] with s2[j]
    c = lev[i  ][j-1] + 1            # skipping s2[j]
    lev[i][j] = min(a,b,c)           # pick the cheapest

def edit_dist(s1, s2):
    """
    Calculate the Levenshtein edit-distance between two strings.
    The edit distance is the number of characters that need to be
    substituted, inserted, or deleted, to transform s1 into s2.  For
    example, transforming "rain" to "shine" requires three steps,
    consisting of two substitutions and one insertion:
    "rain" -> "sain" -> "shin" -> "shine".  These operations could have
    been done in other orders, but at least three steps are needed.

    @param s1, s2: The strings to be analysed
    @type s1, s2: C{string}
    @rtype C{int}
    """
    # set up a 2-D array
    len1 = len(s1); len2 = len(s2)
    lev = _edit_dist_init(len1+1, len2+1)

    # iterate over the array
    for i in range(len1):
        for j in range (len2):
            _edit_dist_step(lev, i+1, j+1, s1[i], s2[j])
    return lev[len1][len2]


##########################################################################
# MINIMAL SETS
##########################################################################

class MinimalSet(object):
    """
    Find contexts where more than one possible target value can
    appear.  E.g. if targets are word-initial letters, and contexts
    are the remainders of words, then we would like to find cases like
    "fat" vs "cat", and "training" vs "draining".  If targets are
    parts-of-speech and contexts are words, then we would like to find
    cases like wind (noun) 'air in rapid motion', vs wind (verb)
    'coil, wrap'.
    """
    def __init__(self, parameters=None):
        """
        Create a new minimal set.

        @param parameters: The (context, target, display) tuples for the item
        @type parameters: C{list} of C{tuple} of C{string}
        """
        self._targets = set()  # the contrastive information
        self._contexts = set() # what we are controlling for
        self._seen = {}        # to record what we have seen
        self._displays = {}    # what we will display

        if parameters:
            for context, target, display in parameters:
                self.add(context, target, display)

    def add(self, context, target, display):
        """
        Add a new item to the minimal set, having the specified
        context, target, and display form.

        @param context: The context in which the item of interest appears
        @type context: C{string}
        @param target: The item of interest
        @type target: C{string}
        @param display: The information to be reported for each item
        @type display: C{string}
        """
        # Store the set of targets that occurred in this context
        if context not in self._seen:
           self._seen[context] = set()
        self._seen[context].add(target)

        # Keep track of which contexts and targets we have seen
        self._contexts.add(context)
        self._targets.add(target)

        # For a given context and target, store the display form
        self._displays[(context, target)] = display

    def contexts(self, minimum=2):
        """
        Determine which contexts occurred with enough distinct targets.

        @param minimum: the minimum number of distinct target forms
        @type minimum: C{int}
        @rtype C{list}
        """
        return [c for c in self._contexts if len(self._seen[c]) >= minimum]

    def display(self, context, target, default=""):
        if (context, target) not in self._displays:
            return self._displays[(context, target)]
        else:
            return default

    def display_all(self, context):
        result = []
        for target in self._targets:
            x = self.display(context, target)
            if x: result.append(x)
        return result

    def targets(self):
        return self._targets


######################################################################
## Regexp display (thanks to David Mertz)
######################################################################

def re_show(regexp, string, left="{", right="}"):
    """
    Search C{string} for substrings matching C{regexp} and wrap
    the matches with braces.  This is convenient for learning about
    regular expressions.

    @param regexp: The regular expression.
    @type param: C{string}
    @param string: The string being matched.
    @type string: C{string}
    @param left: The left delimiter (printed before the matched substring), default "{"
    @type left: C{string}
    @param right: The right delimiter (printed after the matched substring), default "}"
    @type right: C{string}
    @rtype: C{string}
    @return: A string with markers surrounding the matched substrings.
    """
    print re.compile(regexp, re.M).sub(left + r"\g<0>" + right, string.rstrip())


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
# READ FROM FILE OR STRING
##########################################################################

# recipe from David Mertz
def filestring(f):
    if hasattr(f, 'read'):
        return f.read()
    elif isinstance(f, basestring):
        return open(f).read()
    else:
        raise ValueError, "Must be called with a filename or file-like object"

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
# TRIES
##########################################################################

# Trie structure, by James Tauber and Leonardo Maffi (V. 1.2, July 18 2006)
# Extended by Steven Bird

class Trie:
    """A Trie is like a dictionary in that it maps keys to
    values. However, because of the way keys are stored, it allows
    look up based on the longest prefix that matches.  Keys must be
    strings.
    """

    def __init__(self, trie=None):
        if trie is None:
            self._root = [None, {}, 0]
        else:
            self._root = trie

    def clear(self):
        self._root = [None, {}, 0]

    def isleaf(self, key):
        """Return True if the key is present and it's a leaf of the
        Trie, False otherwise."""

        curr_node = self._root
        for char in key:
            curr_node_1 = curr_node[1]
            if char in curr_node_1:
                curr_node = curr_node_1[char]
            else:
                return False
        return curr_node[0] is not None

    def find_prefix(self, key):
        """Find as much of the key as one can, by using the longest
        prefix that has a value.  Return (value, remainder) where
        remainder is the rest of the given string."""

        curr_node = self._root
        remainder = key
        for char in key:
            if char in curr_node[1]:
                curr_node = curr_node[1][char]
            else:
                return curr_node[0], remainder
            remainder = remainder[1:]
        return curr_node[0], remainder

    def subtrie(self, key):
        curr_node = self._root
        for char in key:
            curr_node = curr_node[1][char]
        return Trie(trie=curr_node)

    def __len__(self):
        return self._root[2]

    def __eq__(self, other):
        return self._root == other._root

    def __setitem__(self, key, value):
        curr_node = self._root
        for char in key:
            curr_node[2] += 1
            curr_node = curr_node[1].setdefault(char, [None, {}, 0])
        curr_node[0] = value
        curr_node[2] += 1

    def __getitem__(self, key):
        """Return the value for the given key if it is present, raises
        a KeyError if key not found, and return None if it is present
        a key2 that starts with key."""

        curr_node = self._root
        for char in key:
            curr_node = curr_node[1][char]
        return curr_node[0]

    def __contains__(self, key):
        """Return True if the key is present or if it is present a
        key2 string that starts with key."""

        curr_node = self._root
        for char in key:
            curr_node_1 = curr_node[1]
            if char in curr_node_1:
                curr_node = curr_node_1[char]
            else:
                return False
        return True

    def __str__(self):
        return str(self._root)

    def __repr__(self):
        return "Trie(%r)" % self._root

##########################################################################
# Breadth-First Search
##########################################################################

# Adapted from a Python cookbook entry; original version by David Eppstein
def breadth_first(tree, children=iter, depth=-1):
    """Traverse the nodes of a tree in breadth-first order.
    The first argument should be the tree root; children
    should be a function taking as argument a tree node and
    returning an iterator of the node's children.
    """
    yield tree
    last = tree
    if depth != 0:
        for node in breadth_first(tree, children, depth-1):
            for child in children(node):
                yield child
                last = child
            if last == node:
                return

##########################################################################
# Guess Character Encoding
##########################################################################

# adapted from io.py in the docutils extension module (http://docutils.sourceforge.net)
# http://www.pyzine.com/Issue008/Section_Articles/article_Encodings.html

def guess_encoding(data):
    """
    Given a byte string, attempt to decode it.
    Tries the standard 'UTF8' and 'latin-1' encodings,
    Plus several gathered from locale information.

    The calling program *must* first call 
        locale.setlocale(locale.LC_ALL, '')

    If successful it returns 
        (decoded_unicode, successful_encoding)
    If unsuccessful it raises a ``UnicodeError``
    """
    successful_encoding = None
    # we make 'utf-8' the first encoding
    encodings = ['utf-8']
    #
    # next we add anything we can learn from the locale
    try:
        encodings.append(locale.nl_langinfo(locale.CODESET))
    except AttributeError:
        pass
    try:
        encodings.append(locale.getlocale()[1])
    except (AttributeError, IndexError):
        pass
    try:
        encodings.append(locale.getdefaultlocale()[1])
    except (AttributeError, IndexError):
        pass
    #
    # we try 'latin-1' last
    encodings.append('latin-1')
    for enc in encodings:
        # some of the locale calls 
        # may have returned None
        if not enc:
            continue
        try:
            decoded = unicode(data, enc)
            successful_encoding = enc

        except (UnicodeError, LookupError):
            pass
        else:
            break
    if not successful_encoding:
         raise UnicodeError(
        'Unable to decode input data.  Tried the following encodings: %s.'
        % ', '.join([repr(enc) for enc in encodings if enc]))
    else:
         return (decoded, successful_encoding)


##########################################################################
# Invert a dictionary
##########################################################################

def invert_dict(d):
    from nltk import defaultdict
    inverted_dict = defaultdict(list)
    for key in d:
        for term in d[key]:
            inverted_dict[term].append(key)
    return inverted_dict


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
        if not os.path.exists(_java_bin):
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

##########################################################################
# HTML Cleaning
##########################################################################

from HTMLParser import HTMLParser
skip = ['script', 'style']   # non-nesting tags to skip

class HTMLCleaner(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
        self._flag = True
    def handle_data(self, d):
        if self._flag:
            self.fed.append(d)
    def handle_starttag(self, tag, attrs):
        if tag in skip:
            self._flag = False
    def handle_endtag(self, tag):
        if tag in skip:
            self._flag = True
    def clean_text(self):
        return ''.join(self.fed)

def clean_html(html):
    """
    Remove HTML markup from the given string.

    @param html: the HTML string to be cleaned
    @type html: C{string}
    @rtype: C{string}
    """
    
    cleaner = HTMLCleaner()
    cleaner.feed(html)
    return cleaner.clean_text()


##########################################################################
# Windowdiff
# Pevzner, L., and Hearst, M., A Critique and Improvement of an Evaluation Metric for Text Segmentation,
# Computational Linguistics,, 28 (1), March 2002, pp. 19-36
##########################################################################

def windowdiff(seg1, seg2, k, boundary="1"):
    """
    Compute the windowdiff score for a pair of segmentations.  A segmentation is any sequence
    over a vocabulary of two items (e.g. "0", "1"), where the specified boundary value is used
    to mark the edge of a segmentation.

    @param seg1: a segmentation
    @type seg1: C{string} or C{list}
    @param seg2: a segmentation
    @type seg2: C{string} or C{list}
    @param k: window width
    @type k: C{int}
    @param boundary: boundary value
    @type boundary: C{string} or C{int} or C{bool}
    @rtype: C{int}
    """

    if len(seg1) != len(seg2):
        raise ValueError, "Segmentations have unequal length"
    wd = 0
    for i in range(len(seg1) - k):
        wd += abs(seg1[i:i+k+1].count(boundary) - seg2[i:i+k+1].count(boundary))
    return wd

######################################################################
# Deprecation decorator & base class
######################################################################

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
        newFunc.__name__ = func.__name__
        newFunc.__doc__ = func.__doc__
        newFunc.__dict__.update(func.__dict__)
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
        import warnings, textwrap, re
        # Figure out which class is the deprecated one.
        dep_cls = None
        for base in cls.__mro__:
            if Deprecated in base.__bases__:
                dep_cls = base
        assert dep_cls, 'Unable to determine which base is deprecated.'

        # Construct an appropriate warning.
        doc = re.sub(r'\A\s*@deprecated:', '', dep_cls.__doc__ or '')
        name = 'Class %s' % dep_cls.__name__
        if cls != dep_cls:
            name += ' (base class for %s)' % cls.__name__
        msg = '%s has been deprecated.  %s' % (name, doc.strip())
        msg = '\n' + textwrap.fill(msg.strip(), initial_indent='    ',
                                   subsequent_indent='    ')
        warnings.warn(msg, category=DeprecationWarning, stacklevel=2)
        # Do the actual work of __new__.
        return object.__new__(cls, *args, **kwargs)

__all__ = ['Counter', 'MinimalSet', 'OrderedDict', 'SortedDict', 'Trie',
           'breadth_first', 'edit_dist', 'filestring', 'guess_encoding',
           'invert_dict', 'pr', 'print_string', 're_show', 'config_java',
           'java', 'clean_html', 'windowdiff', 'deprecated', 'Deprecated',
           'convert_regexp_to_nongrouping']
