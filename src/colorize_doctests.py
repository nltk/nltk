"""
Colorize doctests in a docbook document.
"""
import sys, re

######################################################################
# Argument parsing
######################################################################

def usage(exitcode):
    print 'Usage: %s <infile> <outfile>' % sys.argv[0]
    sys.exit(exitcode)
    
verbosity = 1
flags = [arg for arg in sys.argv[1:] if arg[:1] == '-']
files = [arg for arg in sys.argv[1:] if arg[:1] != '-']

for flag in flags:
    if flag == '-v': verbosity += 1
    elif flag == '-q': verbosity -= 1
    elif flag == '-h': usage(0)
    elif flag == '-?': usage(0)
    else: usage(-1)

if len(files) != 2: usage(-1)
infile, outfile = files

######################################################################
# Regular expressions
######################################################################

# This is used to skip over '#' in string literals:
STRING_LITERAL = r"""
u?r?(?:            # Single-quote ['] strings
  '''(?:                 # Tripple-quoted can contain...
      [^']               | # a non-quote
      \\'                | # a backslashed quote
      '{1,2}(?!')          # one or two quotes
    )*''' |
  '(?:                   # Non-tripple quoted can contain...
     [^']                | # a non-quote
     \\'                   # a backslashded quote
   )*'(?!') | """+r'''
                   # Double-quote ["] strings
  """(?:                 # Tripple-quoted can contain...
      [^"]               | # a non-quote
      \\"                | # a backslashed single
      "{1,2}(?!")          # one or two quotes
    )*""" |
  "(?:                   # Non-tripple quoted can contain...
     [^"]                | # a non-quote
     \\"                   # a backslashded quote
   )*"(?!")
)'''

# Commands get marked with <command>...</command>
COMMAND = re.compile(r'([\t\ ]*)(&gt;&gt;&gt;|\.\.\.)'+
                     r'([\t\ ]*)(.*?)[\t\ ]*$', re.MULTILINE)

# Comments get marked with <emphasis>...<emphasis>
COMMENT = re.compile('^([\t\ ]*)(#.*)', re.MULTILINE)
INLINE_COMMENT = re.compile(r'''
    <command>
        ((?:[^\'\"#\n]|%s)*?)  # Group 1: the command
        ([\t  \ ]*)            # group 2: the separating whitespace
        (\#.*)                 # group 3: the comment
    </command>
    ''' % STRING_LITERAL, re.VERBOSE)

# This regexp is used to search for doctest example strings.
PROGRAMLISTING_RE = re.compile(r'<programlisting>\s*<!\[CDATA\['+
                               r'(.*?)\]\]>\s*</programlisting>',
                               re.DOTALL)

######################################################################
# Script
######################################################################

# Colorize a single programlisting.
def colorize(s):
    # Mark commands.
    s = COMMAND.sub(r'\1<prompt>\2</prompt>\3<command>\4</command>', s)
    
    # Mark beginning-of-line comments.
    s = COMMENT.sub(r'\1<emphasis>\2</emphasis>', s)

    # Mark inline comments, but avoid '#' inside a string literal!
    return INLINE_COMMENT.sub(r'<command>\1</command>\2'+
                              r'<emphasis>\3</emphasis>', s)

# Process a single programlisting.
def programlisting_subfunc(match):
    if verbosity>1:
        if verbosity>2: print '-'*70
        # 'text' is a global variable containing the input.  see below.
        start_linenum = text[:match.start()].count('\n')
        end_linenum = text[:match.end()].count('\n')
        print >>sys.stderr, ('  Colorizing <programlisting> on lines '+
                             '%3d-%3d.' % (start_linenum, end_linenum))
    
    # Remove the <![CDATA[...]]> wrapping.
    s = match.group(1)
    
    # Escape any special characters (since it was in CDATA)
    s = s.replace('&', '&amp;')
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')

    # Mark the commands & comments
    s = colorize(s)

    if verbosity>2: print s

    # Rewrap in <programlisting> (without CDATA) and return:
    return '<programlisting>%s</programlisting>' % s

if verbosity>0:
    print >>sys.stderr, 'Colorizing: %s -> %s' % (infile, outfile)
text = open(infile).read()
text = PROGRAMLISTING_RE.sub(programlisting_subfunc, text)
open(outfile, 'w').write(text)
