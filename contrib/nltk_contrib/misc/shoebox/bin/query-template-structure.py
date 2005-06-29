import sys
from shoebox.standardformat import StandardFormatFileParser

def handle_options() :
    try :
        return sys.argv[1]
    except :
        print "%s <FILEPATH>" % sys.argv[0]
        sys.exit(0)

def sort_by_value(d):
    items = d.items()
    backitems = [[v[1], v[0]] for v in items]
    backitems.sort()
    return [backitems[i][1] for i in range(0, len(backitems))]

def get_entries(filepath) :
    fp = StandardFormatFileParser(filepath)
    sff = fp.parse()
    return sff.getEntries()

def process_entries(entries) :
    counter = {}
    i = 0
    for e in entries :
        for fm in e.getFieldMarkers() :
            try :
                counter[fm] = counter[fm] + 1 
            except :
                counter[fm] = 1
    return counter

def print_results(entries, counter) :
    totalEntries = len(entries)
    fieldMarkers = sort_by_value(counter)
    fieldMarkers.reverse()
    for fieldMarker in fieldMarkers :
        numEntries = counter[fieldMarker]
        pctEntries = ((100.0 * numEntries)/totalEntries)
        print "\%s\t%i\t%i%%" % (fieldMarker, numEntries, pctEntries)
    
def main() :
    filepath = handle_options()
    entries = get_entries(filepath)
    counter = process_entries(entries)
    print_results(entries, counter)

main()
