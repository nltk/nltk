"""
Extract doctests from a docbook document.
"""
import sys, re

######################################################################
# Process command line
######################################################################

def usage(exitcode):
    print 'Usage: %s <infile> <outfile>' % sys.argv[0]
    sys.exit(exitcode)
    
if len(sys.argv[1:]) != 2: usage(-1)
infile, outfile = sys.argv[1:]

######################################################################
# Useful regular expressions
######################################################################

# program listings
PROGRAMLISTING_RE = re.compile(r'<programlisting>\s*<!\[CDATA\['+
                               r'(.*?)\]\]>\s*</programlisting>',
                               re.DOTALL)
# code lines
CODE_RE = re.compile(r'(>>>|\.\.\.) ')

######################################################################
# Script
######################################################################

# Read the docbook file
text = open(infile).read()
frags = PROGRAMLISTING_RE.findall(text)
text = "\n".join(frags)

# Extract the code, including blank lines
code = []
for line in text.split('\n'):
    if CODE_RE.match(line):
        code.append(line[4:])
    if len(line) == 0:
        code.append(line)

# collate and output the code
text = "\n".join(code)
open(outfile, 'w').write(text)
