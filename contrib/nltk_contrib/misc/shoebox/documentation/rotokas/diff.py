import sys

def usage() :
  print "Usage: %s" % (sys.argv[0])

def extractWordlist(fn) :
    wl = {}
    fo = open(fn, 'r')
    for l in fo.readlines() :
        w = l.strip("\n")
        #print "[%s]" % (w)
        if wl.has_key(w) :
            count = wl[w]
            wl[w] = count + 1
        else :
            wl[w] = 1
    fo.close()
    return wl

def main() :
  try :	
      file1 = sys.argv[1]
      file2 = sys.argv[2]
      wl1 = extractWordlist(file1)
      wl2 = extractWordlist(file2)
      keys1 = wl1.keys()
      keys1.sort()
      for k1 in keys1 :
          try :
            v1 = wl1[k1]
            v2 = wl2[k1]
            if (v1 != v2) :
              print "%s -> %i" % (k1, v1)
          except KeyError :
            print "%s not found in %s" % (k1, file2)
  except IndexError :
      usage()

main()
