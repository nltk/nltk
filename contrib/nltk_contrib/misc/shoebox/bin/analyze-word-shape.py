# --------------------------------------------------------
# AUTHOR: Steven Bird (revised by Stuart Robinson)
# DATE:   29 March 2005
# DESC:   Add a CV field to show the consonant-vowel
#         skeleton of the word in the 'fri' field
# --------------------------------------------------------

import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser, StandardFormatFile

FIELD_MARKER_FRISIAN = "fri"
FIELD_MARKER_CONTOUR = "cv"


# --------------------------------------------------------
# FUNCTIONS
# --------------------------------------------------------

def handle_options() :
    parser = OptionParser()
    parser.add_option("-s", "--shoebox",
                      dest="shoebox",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()
    if not options:
        print "%s -s/--shoebox <FILE>" % sys.argv[0]
    return options.shoebox


def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]',     r'-', s)
    s = re.sub(r'[^aeiou\-]', r'C', s)
    s = re.sub(r'[aeiou]',    r'V', s)
    return (s)


def main() :
    fn = handle_options()
    fp = StandardFormatFileParser(fn)
    sff = fp.parse()

    d = {}
    for e in sff.getEntries() :
        fri = e.getFieldValuesByFieldMarkerAsString(FIELD_MARKER_FRISIAN)
        fri_cv = cv(fri)
        if not d.has_key(fri_cv) :
            d[fri_cv] = 0
        d[fri_cv] = d[fri_cv] + 1

    wordshapes = d.keys()
    wordshapes.sort()
    for ws in wordshapes :
        count = d[ws]
        print "%s %i" % (ws, count)

        
main()
