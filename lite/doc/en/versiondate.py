#
# versiondate.py
#
# Create a version and date for a docbook document using CVS data
#

import sys, re

if len(sys.argv) != 2:
    print 'Usage: %s <input>' % sys.argv[0]
    sys.exit(1)
tutorial = sys.argv[1]

# Define a regexp that finds the CVS entry
CVS_RE = re.compile(tutorial + '/([\d\.]+)/\w+ (\w+) +(\d+) [\d:]+ (\w+)/')

# Get the CVS data
cvsentries = open("CVS/Entries")
for line in cvsentries.readlines():
    s = CVS_RE.search(line)
    if s:
        version, month, day, year = s.groups()
        break;

# Build the XML string and output
print '<pubdate>Revision %s, %s %s %s</pubdate>' % (version, day, month, year)
