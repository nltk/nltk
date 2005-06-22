import sys
from shoebox.shoebox import MetadataParser
from optparse import OptionParser

def main() :
  parser = OptionParser()
  parser.add_option("-m",
                    "--metadata",
                    dest="metadata",
                    help="path to Shoebox metadata file (.typ)")
  (options, args) = parser.parse_args()

  if not options.metadata :
    print "Usage: %s -m <METADATA-FILE>" % sys.argv[0]
    sys.exit(0)

  fo = open(options.metadata, 'rU')
  fc = fo.read()
  fo.close()
  
  fp = MetadataParser(fc)
  meta = fp.parse()
  markerSet = meta.getMarkerSet()
  fieldMarkers = markerSet.keys()
  fieldMarkers.sort()
  for i, fm in enumerate(fieldMarkers) :
      m = markerSet[fm]
      print ""
      print "Field %i             " % (i + 1)
      print "  Marker         [%s]" % m.getFieldMarker()
      print "  Name           [%s]" % m.getName()
      print "  Parent         [%s]" % m.getParentFieldMarker()
      print "  Next           [%s]" % m.getNextFieldMarker()
      print "  Language       [%s]" % m.getLanguage()
      print "  No Word Wrap   [%s]" % m.getIsNoWordWrap()
      print "  Single Word    [%s]" % m.getIsSingleWord()
      print "  Range Set      [%s]" % m.getRangeSet()
      print "  Description    [%s]" % m.getDescription()
      print "  Must Have Data [%s]" % m.getMustHaveData()

main()
