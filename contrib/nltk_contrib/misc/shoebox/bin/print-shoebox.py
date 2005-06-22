import sys
from optparse import OptionParser
from shoebox.standardformat import StandardFormatFileParser
from shoebox.shoebox import MetadataParser

def handle_options() :
    parser = OptionParser()
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
    if not args[0] :
        sys.stderr.write("%s [ -m <METADATA> | -f <HEADFIELD> ] <FILE>\n" % sys.argv[0])
        sys.exit(0)
    return (args[0], options.metadata, options.headfield)

def main() :
    filepath, metadata, headfield = handle_options()
    fp = StandardFormatFileParser(filepath)
    if metadata :
        mp = MetadataParser(metadata)
        md = mp.parse()
        fp.setHeadFieldMarker(md.getHeadFieldMarker())
    elif headfield :
        fp.setHeadFieldMarker(headfield)
    sff = fp.parse()
    i = 0
    for e in sff.getEntries() :
        i = i + 1
        print ""
        print "Entry %i" % i
        hf = e.getHeadField()
        print "[%s]=[%s]" % (hf[0], hf[1])
        for fm in e.getFieldMarkers() :
            fvs = e.getFieldValuesByFieldMarker(fm)
            for fv in fvs :
                print "[%s]=[%s]" % (fm, fv)

main()
