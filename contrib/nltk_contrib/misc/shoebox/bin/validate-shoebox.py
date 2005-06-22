import sys
from optparse               import OptionParser
from shoebox.shoebox        import MetadataParser, ShoeboxValidator
from shoebox.standardformat import StandardFormatFileParser

# Handle Options
parser = OptionParser()
parser.add_option("-s", "--shoebox",
                  dest="shoebox",
                  help="path to Shoebox dictionary file (.dic)")
parser.add_option("-m", "--metadata",
                  dest="metadata",
                  help="path to Shoebox metadata file (.typ)")
parser.add_option("-v", "--verbose",
                   action="store_false",
                   dest="verbose",
                   default=True,
                   help="provide verbose output (more fine-grained detail)")
(options, args) = parser.parse_args()

# Deal with metadata
fo = open(options.metadata, 'rU')
mdFc = fo.read()
fo.close()
mp = MetadataParser(mdFc)
md = mp.parse()

# Deal with Shoebox
fp = StandardFormatFileParser(options.shoebox)
fp.setHeadFieldMarker(md.getHeadFieldMarker())
sb = fp.parse()

# Validate
ev = ShoeboxValidator()
ev.setMetadata(md)
ev.setShoebox(sb)
ev.validate()
