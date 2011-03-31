# -*- coding: iso-8859-1 -*-
#
# Code coverage colorization:
#  - s?stien Martini <sebastien.martini@gmail.com>
#    * 5/24/2006 fixed: bug when code is completely covered (Kenneth Lind).
#
# URL:
#  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/491274
#
# Original recipe:
#  http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52298
#
# Original Authors:
#  - J?Hermann
#  - Mike Brown <http://skew.org/~mike/>
#  - Christopher Arndt <http://chrisarndt.de>
#
import cgi
import string
import sys
import io
import os
import keyword
import token
import tokenize

_VERBOSE = False

_KEYWORD = token.NT_OFFSET + 1

_css_classes = {
    token.STRING:       'pysrc-string',
    tokenize.COMMENT:   'pysrc-comment',
    token.ERRORTOKEN:   'pysrc-error',
    _KEYWORD:           'pysrc-keyword',
}

_HTML_HEADER = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
  "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>code coverage of %(module_name)s</title>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">

<style type="text/css">
pre.code {
    font-style: Lucida,"Courier New";
    background-color: #eeeeff;
    border: 1px solid black;
    padding: 0.5em;
}
span.pysrc-keyword  { color: #e06000; }
span.pysrc-string   { color: #00aa00; }
span.pysrc-comment  { color: #ff0000; }
span.pysrc-error    { color: #FF8080; border: solid 1.5pt #FF0000; }
span.notcovered     { background-color: #FFB2B2; }
a.red:link       { color: #800000; }
a.red:visited    { color: #800000; }
a.yellow:link    { color: #808000; }
a.yellow:visited { color: #808000; }
</style>

</head>
<body>
<h1>Code Coverage for <code>%(module_name)s</code></h1>
"""

_HTML_FOOTER = """\
</body>
</html>
"""

class Parser:
    """ Send colored python source.
    """
    def __init__(self, raw, out=sys.stdout, not_covered=[], def_info=[]):
        """ Store the source text.
        """
        self.raw = string.strip(string.expandtabs(raw))
        self.out = out
        self.not_covered = not_covered  # not covered list of lines
        self.cover_flag = False  # is there a <span> tag opened?
        # map lineno -> name.
        self.anchors = dict([(info.defstart, info.name) for info in def_info])

    def format(self):
        """ Parse and send the colored source.
        """
        # store line offsets in self.lines
        self.lines = [0, 0]
        pos = 0
        while 1:
            pos = string.find(self.raw, '\n', pos) + 1
            if not pos: break
            self.lines.append(pos)
        self.lines.append(len(self.raw))

        # parse the source and write it
        self.pos = 0
        text = io.StringIO(self.raw)
        self.out.write('<pre class="code">\n')
        try:
            tokenize.tokenize(text.readline, self)
        except tokenize.TokenError as ex:
            msg = ex[0]
            line = ex[1][0]
            self.out.write("<h3>ERROR: %s</h3>%s\n" % (
                msg, self.raw[self.lines[line]:]))
        if self.cover_flag:
            self.out.write('</span>')
            self.cover_flag = False
        self.out.write('\n</pre>')

    def __call__(self, toktype, toktext, xxx_todo_changeme, xxx_todo_changeme1, line):
        """ Token handler.
        """
        (srow,scol) = xxx_todo_changeme
        (erow,ecol) = xxx_todo_changeme1
        if _VERBOSE:
            print("type", toktype, token.tok_name[toktype], "text", toktext, end=' ')
            print("start", srow,scol, "end", erow,ecol, "<br>")

        # calculate new positions
        oldpos = self.pos
        newpos = self.lines[srow] + scol
        self.pos = newpos + len(toktext)

        if srow in self.anchors:
            self.out.write('<a name="%s"></a>' % self.anchors.pop(srow))

        if not self.cover_flag and srow in self.not_covered:
            self.out.write('<span class="notcovered">')
            self.cover_flag = True

        # handle newlines
        if toktype in [token.NEWLINE, tokenize.NL]:
            if self.cover_flag:
                self.out.write('</span>')
                self.cover_flag = False

        # send the original whitespace, if needed
        if newpos > oldpos:
            self.out.write(self.raw[oldpos:newpos])

        # skip indenting tokens
        if toktype in [token.INDENT, token.DEDENT]:
            self.pos = newpos
            return

        # map token type to a color group
        if token.LPAR <= toktype and toktype <= token.OP:
            toktype = token.OP
        elif toktype == token.NAME and keyword.iskeyword(toktext):
            toktype = _KEYWORD
        css_class = _css_classes.get(toktype)

        # send text
        if css_class: self.out.write('<span class="%s">' % (css_class,))
        self.out.write(cgi.escape(toktext))
        if css_class: self.out.write('</span>')


class MissingList(list):
    def __init__(self, i):
        list.__init__(self, i)

    def __contains__(self, elem):
        for i in list.__iter__(self):
            v_ = m_ = s_ = None
            try:
                v_ = int(i)
            except ValueError:
                m_, s_ = i.split('-')
            if v_ is not None and v_ == elem:
                return True
            elif (m_ is not None) and (s_ is not None) and \
                     (int(m_) <= elem) and (elem <= int(s_)):
                return True
        return False

def coverage_summary(out, def_info, src_url=''):
    # Just report on functions.  Split into wholly & partially
    # untested.  Use a separate column for each.
    def_info = [info for info in def_info if info.typ == 'func']
    untested = [info for info in def_info if info.coverage==0.0]
    partially_tested = [info for info in def_info
                        if 0.0<info.coverage<1.0]
    if not (untested or partially_tested):
        out.write('<h2>100% Covered by Tests!</h2>')
        return
    both = (untested and partially_tested)
    if both: out.write('<table border="0" width="100%">\n'
                       '<tr valign="top"><td width="50%">\n')
    _summary(out, 'Untested Functions', untested, 'red', src_url)
    if both: out.write('</td><td width="50%">\n')
    _summary(out, 'Partially Tested Functions', partially_tested,
             'yellow', src_url)
    if both: out.write('</td></tr></table>\n')

def _summary(out, title, def_info, css, src_url):
    # If nothing remains, we're done.
    if not def_info: return
    names = [info.name for info in def_info]
    # Display a summary table.
    out.write('<h2>%s</h2>\n' % title)
    out.write('<ul>\n')
    #for name in sorted(names):
    #    out.write('  <li><a class="%s" href="%s#%s">%s()</a>'
    #              '</li>\n' % (css, src_url, name, name))
    for (context, f_names) in sorted(_group_names(names).items()):
        out.write('  <li>')
        if context: out.write('<b>%s</b>: ' % context)
        out.write(', '.join(['<a class="%s" href="%s#%s">%s()</a>' %
                             (css, src_url, f_name, f_name.split('.')[-1])
                             for f_name in sorted(f_names)]))
        out.write('</li>\n')
    out.write('</ul>\n')

def _group_names(names):
    grouped = {}
    for name in names:
        pieces = name.split('.')
        grouped.setdefault('.'.join(pieces[:-1]), []).append(name)
    return grouped

def colorize_file(filename, module_name, out, not_covered, def_info):
    """
    Convert a python source file into colorized HTML.

    Reads file and writes to out.
    """
    fo = file(filename, 'rb')
    try:
        source = fo.read()
    finally:
        fo.close()
    out.write(_HTML_HEADER % {'module_name': module_name})
    coverage_summary(out, def_info)
    missing = MissingList((not_covered and not_covered.split(', ')) or [])
    Parser(source, out, missing, def_info).format()
    out.write(_HTML_FOOTER)
