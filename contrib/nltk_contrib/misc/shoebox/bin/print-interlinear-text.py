import Shoebox
import StandardFormat
import sys
from optparse import OptionParser

# Handle Options
parser = OptionParser()
parser.add_option("-s",
                  "--shoebox",
                  dest="shoebox",
                  help="path to Shoebox dictionary file")
parser.add_option("-m",
                  "--metadata",
                  dest="metadata",
                  help="path to Shoebox metadata file (.typ)")
parser.add_option("-f",
                   "--headfield",
                   dest="headfield",
                   help="field to parse on")
parser.add_option("-v",
                   "--verbose",
                   action="store_false",
                   dest="verbose",
                   default=True,
                   help="provide verbose output (more fine-grained detail)")
(options, args) = parser.parse_args()

# Get file contents
fo = open(options.shoebox, 'r')
sbFc = fo.read()
fo.close()

# Parse file contents
fp = StandardFormat.StandardFormatFileParser(sbFc)
if options.metadata :
    fo = open(options.metadata, 'r')
    mdFc = fo.read()
    fo.close()
    mp = Shoebox.MetadataParser(mdFc)
    md = mp.parse()
    fp.setHeadFieldMarker(md.getHeadFieldMarker())
elif options.headfield :
    fp.setHeadFieldMarker(options.headfield)
sff = fp.parse()
i = 0
for e in sff.getEntries() :
    i = i + 1
    print ""
    print "Entry %i" % i
    for fm in e.getFields() :
        fvs = e.getValueByMarker(fm)
        for fv in fvs :
            print "[%s]=[%s]" % (fm, fv)
