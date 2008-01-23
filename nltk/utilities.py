# Natural Language Toolkit: Utility functions
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import locale, re, types, textwrap, pydoc

######################################################################
# Short usage message
######################################################################

def usage(obj, selfname='self'):
    import inspect
    str(obj) # In case it's lazy, this will load it.
    
    if not isinstance(obj, (types.TypeType, types.ClassType)):
        obj = obj.__class__

    print '%s supports the following operations:' % obj.__name__
    for (name, method) in sorted(pydoc.allmethods(obj).items()):
        if name.startswith('_'): continue
        if getattr(method, '__deprecated__', False): continue
            
        args, varargs, varkw, defaults = inspect.getargspec(method)
        if (args and args[0]=='self' and
            (defaults is None or len(args)>len(defaults))):
            args = args[1:]
            name = '%s.%s' % (selfname, name)
        argspec = inspect.formatargspec(
            args, varargs, varkw, defaults)
        print textwrap.fill('%s%s' % (name, argspec),
                            initial_indent='  - ',
                            subsequent_indent=' '*(len(name)+5))

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
# Breadth-First Search
##########################################################################

def breadth_first(tree, children=iter, depth=-1, queue=None):
    """Traverse the nodes of a tree in breadth-first order.
    (No need to check for cycles.)
    The first argument should be the tree root;
    children should be a function taking as argument a tree node
    and returning an iterator of the node's children.
    """
    if queue == None:
        queue = []
    queue.append(tree)
    
    while queue:
        node = queue.pop(0)
        yield node
        if depth != 0:
            try:
                queue += children(node)
                depth -= 1
            except:
                pass
        
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

def clean_url(url):
   from urllib import urlopen
   html = urlopen(url).read()
   return clean_html(html)

