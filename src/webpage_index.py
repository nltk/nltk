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
##  Shared HTML constants
#############################################################
HEADER = '''\
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<html> 
  <head>
    <title>%s</title>
    <link rel="stylesheet" href="../nltk.css" type="text/css"/>
  </head>
<body>

<table width="100%%" class="navbox" cellpadding="1" cellspacing="0">
  <tr><th class="navtitle" colspan="6">Natural Language Toolkit</th></tr>
  <tr>
  <td align="center" width="16.6%%" class="navbutton">
    <a class="nav" href="../index.html">Home</a></td>
  <td align="center" width="16.6%%" class="navbutton">
    <a class="nav" href="../install.html">Installation</a></td>
  <td align="center" width="16.6%%" class="navbutton">
    <a class="nav" href="../docs.html">Documentation</a></td>
  <td align="center" width="16.6%%" class="navbutton">
    <a class="nav" href="../teach.html">Teaching</a></td>
  <td align="center" width="16.6%%" class="navbutton">
    <a class="nav" href="../contrib.html">Contributing</a></td>
  <td align="center" width="16.6%%">
    <a href="http://sourceforge.net/projects/nltk"> 
    <img src="../sflogo.png" width="88" height="26" border="0"
    alt="SourceForge" align="top"/></a></td>
    </tr>
</table>
<div class="body">
'''

FOOTER = '''\
</div>
<table class="transparent" width="100%%">
<tr><td align="left"><font size="-1">
<!-- hhmts start -->
Last modified: %s
<!-- hhmts end -->
</font></td><td align="right"><font size="-1">
<address><a href="mailto:edloper@gradient.cis.upenn.edu,sb@cs.mu.oz.au">Edward D. Loper, Steven Bird</a></address>
</font></td></tr></table>
</body> </html>
'''

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
        self.externals = []

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
            elif key.startswith('external.'):
                title = key[9:]
                urls = val.split()
                self.externals.append([title, urls])
            else: self.error('Unknown key: '+key)

        # Build a sorting identifier.
        if re.match('\d+', self.sequence_id):
            self._sid = (0, int(self.sequence_id), self.name)
        elif re.match('\w+', self.sequence_id):
            self._sid = (1, self.sequence_id, self.name)
        elif re.match('-\d+', self.sequence_id):
            self._sid = (3, int(self.sequence_id), self.name)
        else:
            self._sid = (2, self.name)

    def error(self, str):
        sys.stderr.write("Warning in "+self.basename+": "+str+"\n")

    def __cmp__(self, other):
        return cmp(self._sid, other._sid)

#############################################################
##  Technical reports
#############################################################
        
TECH = '''\
    <h1>NLTK Technical Reports</h1>

    <p> Technical reports explain and justify NLTK\'s design and
    implementation.  They are used by the developers of the toolkit to
    guide and document the toolkit\'s construction.  Students can
    consult these reports if they would like further information about
    how the toolkit is designed and why it is designed that way.  Each
    report addresses a specific aspect of the design and/or
    implementation of the toolkit.  </p>

<!-- ========== REPORT TABLE =========== -->
    <center>
%s
    </center>

<!-- ========== ABSTRACTS =========== -->
    <h2>Report Abstracts</h2>
%s
'''

def techindex(reports):
    return (HEADER % 'NLTK Technical Reports' +
            TECH % (techtable(reports), techabstracts(reports)) +
            FOOTER % time.ctime())

TECH_TABLE_HEADER = '''\
    <table class="tech" border="1" cellpadding="3" cellspacing="0">
      <tr>
        <th class="tech" width="45%">Report</th>
        <th class="tech">Download</th>
        <th class="tech">Status</th>
        <th class="tech">Est.&nbsp;Completion</th></tr>
'''

def techtable(reports):
    str = TECH_TABLE_HEADER

    reports.sort()
    for report in reports:
        name = report.name
        abstract = report.abstract.replace('"', "'").strip()
        basename = report.basename
        status = report.status or '&nbsp;'
        deadline = report.deadline or '&nbsp;'
        
        files = []
        for ext in 'pdf ps mov mp3'.split():
            if os.path.isfile(os.path.join(report.path,
                                           '%s.%s' % (basename, ext))):
                files.append('<a href="%s.%s">%s</a>' %
                             (basename, ext, ext))

        #for url in report.external_urls:
        #    ext = url.split('.')[-1]
        #    files.append('<a href="%s">%s</a>' % (url, ext))
        
        str += '      <tr>\n'
        str += '        <td class="tech">'
        str += '<span title="%s">%s' % (abstract, name)
        for title,urls in report.externals:
            str += '<br />\n        '+'&nbsp;'*4+'<i>%s</i>' % title.title()
        str += '</span></td>\n'
        str += ('       <td class="tech" align="center">%s' %
                ', '.join(files))
        for title,urls in report.externals:
            links = ['<a href="http://%s">%s</a>' %
                     (url, url.split('.')[-1])
                     for url in urls]
            str += '<br />\n%s' % ', '.join(links)
        str += '</td>\n'
        str += '        <td class="tech" valign="top">%s</td>\n' % status
        str += '        <td class="tech" valign="top">%s</td>\n' % deadline
        str += '      </tr>\n'

    str = str + "    </table>\n"
    return str

def techabstracts(reports):
    str = '\n'
    reports.sort(lambda p1,p2: cmp(p1.name.lower(), p2.name.lower()))
    for report in reports:
        str = str + '    <b>%s</b>\n' % report.name
        str = str + '    <p>%s</p>\n\n' % report.abstract
    return str

#############################################################
##  Tutorial documents
#############################################################
TUTORIAL = '''\
    <h1>NLTK Tutorials</h1>

    <P> Tutorials teach students how to use the toolkit, in the context
    of performing specific tasks. They are appropriate for anyone who
    wishes to learn how to use the toolkit. </P>

<!-- ========== TUTORIAL LIST =========== -->
%s

  <h2>Term Index (<a href="tutorial_index.html">html</a>)</h2>

  <dl><dt></dt>
  <dd><i>Definitions of technical terms that are discussed in the
  NLTK tutorials.  Each individual tutorial also has its own index,
  which lists only the terms discussed in that tutorial.  These
  individual indices can be found at the end of each tutorial.
  </i></dd></dl>    
'''

def tutorialindex(reports):
    return (HEADER % 'NLTK Tutorials' +
            TUTORIAL % (tutoriallist(reports)) +
            FOOTER % time.ctime())

def tutorialsublist(reports):
    s = "    <DL><DT><DD><DL>\n"
    
    reports.sort()
    
    for report in reports:
        extra = ''
        # Don't show this (for now?)
        #if (string.lower(report.status) not in
        #    ('&nbsp;', 'none', 'complete', 'completed',
        #     'done', 'finished')):
        #    extra = ' <I>('+report.status+')</I>'

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
        str += '  <h2> Additional Tutorials </h2>\n'
        str += tutorialsublist(lettered_reports)

    if other_reports:
        str += '  <h2> Un-Filed Tutorials </h2>\n'
        str += tutorialsublist(other_reports)

    return str


#############################################################
##  Problem Sets
#############################################################

PSETS = '''\
    <h2>NLTK Problem Sets</h2>

    <P> (under development) </P>
'''

def psetsindex(root):
    return (HEADER % 'NLTK Problem Sets' +
            PSETS +
            FOOTER % time.ctime())

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
