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

#############################################################
##  Info file processing
#############################################################
class Info:
    """
    A class for extracting information from .info files.

    @ivar name: The report's name
    @ivar status: The report's status (e.g., 'complete', 'draft',
        'partial', '80%')
    @ivar deadline: The report's deadline (a date).
    @ivar abstract: A (multiline) abstract for the report
    @ivar sequence_id: The sequence identifier for a report; used to
        order some kinds of reports on the index pages.
    @ivar basename: The base name of the report's info file, and of
        any content files (.pdf, .xml, .ps, etc) for the report.
    @ivar path: The complete path to the report.
    """
    def __init__(self, basename, path):
        """
        @param basename: The base name of the info file (without .info
            extension)
        @param dir: The path to the report.
        """
        self.basename = basename
        self.path = path
        infoname = os.path.join(path, basename+'.info')

        # Default values
        self.name = basename
        self.status = ''
        self.deadline = ''
        self.abstract = ''
        self.sequence_id = ''

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

        # Build a sorting identifier.
        if re.match('\d+', self.sequence_id):
            self._sid = (0, int(self.sequence_id), self.name)
        elif re.match('\w+', self.sequence_id):
            self._sid = (1, self.sequence_id, self.name)
        else:
            self._sid = (2, self.name)

    def error(self, str):
        sys.stderr.write("Warning in "+self.basename+": "+str+"\n")

    def __cmp__(self, other):
        return cmp(self._sid, other._sid)

#############################################################
##  Technical reports
#############################################################
        
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
    <address><a href='mailto:edloper@gradient.cis.upenn.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""

def techindex(reports):
    return TECH % (techtable(reports), techabstracts(reports), time.ctime())

def techtable(reports):
    str = """    <TABLE BORDER='1' CELLPADDING='3' 
                    CELLSPACING='0' WIDTH='100%' BGCOLOR='white'>
      <TR BGCOLOR='#70b0f0'>
        <TD align="center"><b>Report</b></TD>
        <TD>&nbsp;</TD><TD>&nbsp;</TD>
        <TD align="center"><b>Status</b></TD>
        <TD align="center"><b>Est. Completion</b></TD></TR>\n"""

    reports.sort()
    for report in reports:
        name = report.name
        basename = report.basename
        status = report.status or '&nbsp;'
        deadline = report.deadline or '&nbsp;'
        if os.path.isfile(os.path.join(report.path, basename+".pdf")):
            pdf = '<a href="%s.pdf">pdf</a>' % basename
        else:
            pdf = '&nbsp;'
        if os.path.isfile(os.path.join(report.path, basename+".ps")):
            ps = '<a href="%s.ps">ps</a>' % basename
        else:
            ps = '&nbsp;'
        
        str += '      <TR>\n'
        str += '        <TD>%s</TD>\n' % name
        str += '        <TD align="center">%s</TD>\n' % pdf
        str += '        <TD align="center">%s</TD>\n' % ps
        str += '        <TD>%s</TD>\n' % status
        str += '        <TD>%s</TD>\n' % deadline
        str += '      </TR>\n'

    str = str + "    </TABLE>\n"
    return str

def techabstracts(reports):
    str = '\n'
    reports.sort(lambda p1,p2: cmp(p1.name.lower(), p2.name.lower()))
    for report in reports:
        str = str + '    <H4>%s</H4>\n' % report.name
        str = str + '    <P>%s</P>\n\n' % report.abstract
    return str

#############################################################
##  Tutorial documents
#############################################################

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
    <address><a href='mailto:edloper@gradient.cis.upenn.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""

def tutorialindex(reports):
    return TUTORIAL % (tutoriallist(reports), time.ctime())

def tutorialsublist(reports):
    s = "    <DL><DT><DD><DL>\n"
    
    reports.sort()
    
    for report in reports:
        extra = ''
        if (string.lower(report.status) not in
            ('&nbsp;', 'none', 'complete', 'completed',
             'done', 'finished')):
            extra = ' <I>('+report.status+')</I>'

        if report.sequence_id: id = str(report.sequence_id)+': '
        else: id = ''

        s = s + (('      <DT> <B>%s%s</B> (<A HREF="%s/index.html">html</A>, '+
                  '<A HREF="%s.pdf">pdf</A>, '+
                  '<A HREF="%s/nochunks.html">one-page html</A>)%s\n') %
                 (id, report.name, report.basename,
                  report.basename, report.basename, extra))
        s = s + ('        <DD><I>%s</I>\n      </DD></DT>' %
                 report.abstract) 
        
    return s + '</DL></DD></DT></DL>\n'

def tutoriallist(reports):
    numbered_reports = [p for p in reports
                        if re.match('\d+', p.sequence_id)]
    lettered_reports = [p for p in reports if (re.match('\w+', p.sequence_id)
                                               and p not in numbered_reports)]
    other_reports = [p for p in reports if (p not in numbered_reports and p
                                            not in lettered_reports)]
    
    for report in numbered_reports:
        report.sequence_id = int(report.sequence_id)

    str = tutorialsublist(numbered_reports)

    if lettered_reports:
        str += '  <h3> Additional Tutorials </h3>'
        str += tutorialsublist(lettered_reports)

    if other_reports:
        str += '  <h3> Un-Filed Tutorials </h3>'
        str += tutorialsublist(other_reports)

    return str


#############################################################
##  Problem Sets
#############################################################

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
    <address><a href='mailto:edloper@gradient.cis.upenn.edu'>Edward Loper</a></address>
Last modified: %s
  </body>
</html>
"""
def psetsindex(root):
    return PSETS % time.ctime()

#############################################################
##  Main
#############################################################
        
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

    # Load the reports.
    reports = []
    for name in os.listdir(sys.argv[2]):
        if (name == 'CVS'): continue
        dir = os.path.join(sys.argv[2], name)
        if not os.path.isdir(dir): continue
        if not os.path.exists(os.path.join(dir, name+'.info')):
            print '    WARNING: no info file for report %r' %  name
            continue
        reports.append(Info(name, dir))

    # Print the index.
    if index.startswith('tech'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, techindex(reports)
        outfile.close()
    elif index.startswith('pset'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, psetsindex(reports)
        outfile.close()
    elif index.startswith('tut'):
        outfile = open(sys.argv[3], 'w')
        print >>outfile, tutorialindex(reports)
        outfile.close()
    else:
        usage()

if __name__ == '__main__': main()
