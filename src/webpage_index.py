#!/usr/bin/env python
#
# Make the technical report index file
#

"""
This script is used to generate indices for NLTK's homepage.  It can
generate indices for the technical reports, the tutorials, and the
sample problem sets.  It uses the .info files in each document's
directory to generate these indices.  See README.TXT in the root
directory of the NLTK repository for more information about the .info
files. 

Usage::
  webpage_index.py index directory

Where "index" is one of "tech", "psets", or "tutorial"
and "directory" is the location of said documents.
"""

import os, os.path, sys, string, re, time

class Info:
    """
    A class for extracting information from .info files.
    """
    def __init__(self, dirname, dir):
        """
        @param dirname: The name of the directory that is specific to
            this document.
        @param dir: The directory that contains all of the documents.
        """
        self.dirname = dirname
        infoname = os.path.join(dir, dirname+'.info')

        # Default values
        self.name = dirname
        self.status = '&nbsp;'
        self.deadline = '&nbsp;'
        self.abstract = ''
        self.sequence_id = ''

        if not os.path.exists(infoname):
            self.error('Missing info file '+infoname)
            return

        dict = {}
        key = None
        for line in open(infoname).readlines():
            line = string.split(line, '#')[0]
            line = string.strip(line)
            if line == '': continue
            if ':' in line:
                (key, rest) = string.split(line, ':', 1)
                key = string.lower(string.strip(key))
                line = string.strip(rest)
            if key == None:
                self.error('Bad info file')
                continue
            if dict.has_key(key):
                dict[key] = dict[key]+' '+line
            else:
                dict[key] = line
                
        for (key, val) in dict.items():
            if key == 'name': self.name = val
            elif key == 'status': self.status = val
            elif key == 'deadline': self.deadline = val
            elif key == 'abstract': self.abstract = val
            elif key == 'id': self.sequence_id = val
            else: self.error('Unknown key: '+key)

    def error(self, str):
        sys.stderr.write("Warning in "+self.dirname+": "+str+"\n") 

#############################################################
## Technical reports
        
TECH="""<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
  <head>
    <title>Technical Reports for the NLP Toolkit</title>
  </head>

  <body bgcolor='white' text='black' link='blue'
        vlink='#204080' alink='#204080'>
    <h2>Technical Reports for the NLP Toolkit</h2>

    <P> Technical reports explain and justify the NLP toolkit's design
    and implementation.  Each report addresses a specific aspect of
    the design and/or implementation of the toolkit.  </P>

    <P> Technical reports are primarily intended for developers;
    students should not need to read the technical reports to use the
    toolkit.  However, students can consult these reports if they
    would like further information about how the toolkit is designed
    and why it is designed that way. </P>

<!-- ========== REPORT TABLE =========== -->
    <h3>List of Technical Report</h3>
%s

<!-- ========== ABSTRACTS =========== -->
    <h3>Report Abstracts</h3>
%s

    <hr>
    <address><a href='mailto:edloper@mit.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""

def techindex(root):
    pages = []
    for name in os.listdir(root):
        if (name == 'CVS'): continue
        dir = os.path.join(root, name)
        if not os.path.isdir(dir): continue
        pages.append(Info(name, dir))
    pages.sort(lambda p1,p2: cmp(p1.name, p2.name))

    return TECH % (techtable(pages), techabstracts(pages), time.ctime())

def techtable(pages):
    str = """<TABLE BORDER='1' CELLPADDING='3' 
                    CELLSPACING='0' WIDTH='100%' BGCOLOR='white'>
      <TR BGCOLOR='#70b0f0'>
        <TD>Report</TD>
        <TD>&nbsp;</TD><TD>&nbsp;</TD>
        <TD>Status</TD>
        <TD>Est. Completion</TD></TR>\n"""

    for page in pages:
        name = page.name
        dirname = page.dirname
        status = page.status
        deadline = page.deadline
        str = str + '      <TR>\n'
        str = str + '        <TD>%s</TD>\n' % name
        str = str + '        <TD><a href="%s.pdf">pdf</a></TD>\n' % dirname
        str = str + '        <TD><a href="%s.ps">ps</a></TD>\n' % dirname
        str = str + '        <TD>%s</TD>\n' % status
        str = str + '        <TD>%s</TD>\n' % deadline
        str = str + '      </TR>\n'

    str = str + "    </TABLE>\n"
    return str

def techabstracts(pages):
    str = '\n'
    for page in pages:
        str = str + '    <H4>%s</H4>\n' % page.name
        str = str + '    <P>%s</P>\n\n' % page.abstract
    return str

#############################################################
## Tutorial documents

TUTORIAL="""<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
  <head>
    <title>Tutorials for the NLP Toolkit</title>
  </head>

  <body bgcolor='white' text='black' link='blue'
        vlink='#204080' alink='#204080'>
    <h2>Tutorials for the NLP Toolkit</h2>

    <P> Tutorials teach students how to use the toolkit, in the context
    of performing specific tasks. They are appropriate for anyone who
    wishes to learn how to use the toolkit. </P>

<!-- ========== TUTORIAL LIST =========== -->
%s

    <hr>
    <address><a href='mailto:edloper@mit.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""

def tutorialindex(root):
    pages = []
    for name in os.listdir(root):
        if (name == 'CVS'): continue
        dir = os.path.join(root, name)
        if not os.path.isdir(dir): continue
        pages.append(Info(name, dir))
    pages.sort(lambda p1,p2: cmp(p1.name, p2.name))

    return TUTORIAL % (tutoriallist(pages), time.ctime())

def tutorialsublist(pages):
    s = "    <DL><DT><DD><DL>\n"
    
    pages.sort(lambda p1,p2: cmp(p1.sequence_id, p2.sequence_id))
    
    for page in pages:
        extra = ''
        if (string.lower(page.status) not in
            ('&nbsp;', 'none', 'complete', 'completed',
             'done', 'finished')):
            extra = ' <I>('+page.status+')</I>'

        if page.sequence_id: id = str(page.sequence_id)+': '
        else: id = ''

        s = s + (('      <DT> <B>%s%s</B> (<A HREF="%s/t1.html">html</A>, '+
                  '<A HREF="%s.pdf">pdf</A>, '+
                  '<A HREF="%s/nochunks.html">one-page html</A>)%s\n') %
                 (id, page.name, page.dirname,
                  page.dirname, page.dirname, extra))
        s = s + ('        <DD><I>%s</I>\n      </DD></DT>' %
                 page.abstract) 
        
    return s + '</DL></DD></DT></DL>\n'

def tutoriallist(pages):
    numbered_pages = [p for p in pages
                      if re.match('\d+', p.sequence_id)]
    lettered_pages = [p for p in pages if (re.match('\w+', p.sequence_id)
                                           and p not in numbered_pages)]
    other_pages = [p for p in pages if (p not in numbered_pages and p
                                        not in lettered_pages)]
                                  
    
    for page in numbered_pages:
        page.sequence_id = int(page.sequence_id)

    str = tutorialsublist(numbered_pages)

    if lettered_pages:
        str += '  <h3> Additional Tutorials </h3>'
        str += tutorialsublist(lettered_pages)

    if other_pages:
        str += '  <h3> Un-Filed Tutorials </h3>'
        str += tutorialsublist(other_pages)

    return str


#############################################################
## Problem Sets

PSETS="""<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
  <head>
    <title>Problem Sets for the NLP Toolkit</title>
  </head>

  <body bgcolor='white' text='black' link='blue'
        vlink='#204080' alink='#204080'>
    <h2>Problem Sets for the NLP Toolkit</h2>

    <P> (under development) </P>

    <hr>
    <address><a href='mailto:edloper@mit.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""
def psetsindex(root):
    return PSETS % time.ctime()

#############################################################
## Main
        
def usage():
    print
    print 'Usage:'
    if len(sys.argv)>0: name = os.path.split(sys.argv[0])[-1]
    else: name = 'webpage_index'
    print '  %s <index> <directory> <output>' % name
    print
    print 'Where <index> is one of "tech", "psets", or "tutorial";'
    print '<directory> is the location of said documents; and <output>'
    print 'is the file to which the index should be written.'
    print
    sys.exit(-1)
    
def main():
    if len(sys.argv) != 4:
        usage()
    index = sys.argv[1].strip().lower()
    if index.startswith('tech'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, techindex(sys.argv[2])
        outfile.close()
    elif index.startswith('pset'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, psetsindex(sys.argv[2])
        outfile.close()
    elif index.startswith('tut'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, tutorialindex(sys.argv[2])
        outfile.close()
    else:
        usage()

if __name__ == '__main__': main()
