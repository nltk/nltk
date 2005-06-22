# --------------------------------------------------------
# AUTHOR: Steven Bird
# DATE:   29 March 2005
# DESC:   Add a CV field to show the consonant-vowel
#         skeleton of the word in the 'fri' field
# --------------------------------------------------------

import sys, re
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser

FIELD_MARKER_FRISIAN = "fri"
FIELD_MARKER_CONTOUR = "cv"
    
def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]', r'-', s)
    s = re.sub(r'[aeiou]', r'V', s)
    s = re.sub(r'[^V-]', r'C', s)
    return(s)

def main() :
    # Handle Options
    parser = OptionParser()
    parser.add_option("-s",
                      "--shoebox",
                      dest="shoebox",
                      help="path to Shoebox dictionary file")
    (options, args) = parser.parse_args()

    # Parse file contents
    fp = StandardFormatFileParser(options.shoebox)
    sff = fp.parse()
    for e in sff.getEntries() :
        print ""
        fri = e.getFieldValuesByFieldMarkerAsString(FIELD_MARKER_FRISIAN)
        e.setField(FIELD_MARKER_CONTOUR, cv(fri))
        for fm in e.getFields() :
            fvs = e.getFieldValuesByFieldMarker(fm)
            for fv in fvs :
                print "\\%s %s" % (fm, fv)
    # How would I do this using addField()?
    # How would I get the __str__ for a whole entry?

main()
