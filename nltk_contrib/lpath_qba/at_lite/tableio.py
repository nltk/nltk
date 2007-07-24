
#
# ChangeLogs:
# $Log: tableio.py,v $
# Revision 1.9  2006/06/27 19:03:28  haejoong
# tdf reader now handles different formats of newline characters
#
# Revision 1.8  2006/04/12 14:55:24  haejoong
# fixes for error handling
#
# Revision 1.7  2006/01/26 15:46:46  haejoong
# *** empty log message ***
#
# Revision 1.6  2006/01/23 16:32:29  haejoong
# improved exception handling
#
# Revision 1.5  2006/01/19 17:53:17  haejoong
# added some error handling for importTdf
#
# Revision 1.4  2005/12/15 19:08:40  haejoong
# added missing "
#
# Revision 1.3  2005/12/15 19:05:55  haejoong
# added error handling for TableIo.importTdf
#
#

import codecs
import re
from error import *

__all__ = ['TableIo']

version = "$Revision: 1.9 $"

class TableIo:
    def printTable(self):
        size = [len(str(x)) for x,t in self.header]
        for row in self.table:
            for i,c in enumerate(row):
                if type(c)==str or type(c)==unicode:
                    n = len(c)
                else:
                    n = len(str(c))
                if n > size[i]:
                    size[i] = n

        def printRow(row,bar=True):
            s = ""
            for i,c in enumerate(row):
                if type(c) == int or type(c) == float:
                    s += "%%%ds|" % size[i] % str(c)
                else:
                    s += "%%-%ds|" % size[i] % c
            print s[:-1] 

        printRow([s for s,t in self.header])
        for row in self.table:
            printRow(row)
            
    def importList(cls, L):
        data = cls(L[0])
        for i,row in enumerate(L[1:]):
            data.insertRow(i,row)
        data.resetUndoStack()
        return data

    importList = classmethod(importList)

    def exportTdf(self, filename):
        try:
            _,_,_,writer = codecs.lookup('utf-8')
            f = writer(file(filename,'w'))
            f.write("\t".join([a[0]+';'+a[1].__name__
                               for a in self.header]) + "\n")
            for item in self.metadata.items():
                f.write(";;MM %s\t%s\n" % item)
            for row in self.table:
                for c in row[:-1]:
                    if c is None:
                        f.write("\t")
                    else:
                        t = type(c)
                        if t==str or t==unicode:
                            f.write(c+"\t")
                        else:
                            f.write(str(c)+"\t")
                if row[-1] is None:
                    f.write("\n")
                else:
                    t = type(row[-1])
                    if t==str or t==unicode:
                        f.write(row[-1]+"\n")
                    else:
                        f.write(str(row[-1])+"\n")
        except IOError, e:
            raise Error(ERR_TDF_EXPORT, str(e))

    def importTdf(cls, filename):
        _,_,reader,_ = codecs.lookup('utf-8')
        try:
            f = reader(file(filename))
        except IOError, e:
            raise Error(ERR_TDF_IMPORT, e)
        head = []
        for h in f.readline().rstrip("\r\n").split("\t"):
            try:
                a,b = h.split(';')
            except ValueError:
                raise Error(ERR_TDF_IMPORT, "invalid header")
            head.append((a,eval(b)))
        tab = cls(head)
        l = f.readline().rstrip('\r\n')
        lno = 2
        while l:
            if l[:2] != ';;': break
            if l[2:4] == 'MM':
                nam,val = re.split("\t+",l[4:].strip())
                tab.metadata[nam] = val
            l = f.readline().rstrip('\r\n')
            lno += 1
        while l:
            if l[:2] != ';;':
                row = []
                try:
                    for i,cell in enumerate(l.rstrip("\n").split("\t")):
                        row.append(head[i][1](cell))
                except ValueError, e:
                    raise Error(ERR_TDF_IMPORT,
                                "[%d:%d] %s" % (lno,i,str(e)))
                except IndexError, e:
                    msg = "record has too many fields"
                    raise Error(ERR_TDF_IMPORT,
                                "[%d:%d] %s" % (lno,i,msg))
                tab.insertRow(None,row)
            l = f.readline().rstrip('\r\n')
            lno += 1
        tab.resetUndoStack()
        return tab

    importTdf = classmethod(importTdf)
