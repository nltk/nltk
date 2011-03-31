#
# Script that updates test-list.txt
#

import os, os.path, re, sys

DOCTEST_SRC = '../../nltk/test'

HEAD = (".. ==========================================================\n"
        ".. AUTO-GENERATED LISTING -- DO NOT EDIT!:\n\n"
        ".. role:: passed\n"
        "    :class: doctest-passed\n\n"
        ".. role:: failed\n"
        "    :class: doctest-failed\n\n"
        ".. role:: guide-linecount\n"
        "    :class: guide-linecount\n\n"
        ".. container:: doctest-list\n\n"
        " .. list-table::\n"
        "  :class: doctest-list \n"
        "  :widths: 60 10 10 20\n"
        "  :header-rows: 1\n\n"
        "  * - `Topic <sort-title.html>`__\n"
        "    - `Lines <sort-lines.html>`__\n"
        "    - `Tests <sort-tests.html>`__\n"
        "    - `Test Outcome <sort-outcome.html>`__\n")
FOOT = (".. END AUTO-GENERATED LISTING\n"
        ".. ==========================================================\n")

TITLE_REGEXPS = (
    '\s*----+[ ]*\n(.*)\n----+[ ]*\n',
    '\s*====+[ ]*\n(.*)\n====+[ ]*\n',
    '\s*(.*)\n====+[ ]*\n',
    '\s*(.*)\n----+[ ]*\n')

def find_title(basename):
    filename = os.path.join(DOCTEST_SRC, basename + '.doctest')
    head = open(filename).read(800)
    for regexp in TITLE_REGEXPS:
        regexp = '\A\s*(?:\.\..*\n)*'+regexp
        m = re.match(regexp, head)
        if m: return m.group(1).strip().replace('`', "'")
    print(('Warning: no title found for %s' % basename))
    return basename

def linecount(basename):
    filename = os.path.join(DOCTEST_SRC, basename + '.doctest')
    s = open(filename).read()
    return len(re.findall('(?m)^\s*>>>', s)), s.count('\n')

def fmt_num(n):
    if n > 50:
        n = n - n%10
    if n > 500:
        n = n - n%100
    if n >= 1000:
        n = str(n)[:-3]+','+str(n)[-3:]
    return n

def doctest_listing(sortkey=None):
    listing = ''
    
    files = [f for f in os.listdir(DOCTEST_SRC) if f.endswith('.doctest')]
    err_refs = []
    lines = []
    for filename in files:
        basename = filename.replace('.doctest', '')
        if basename == 'temp': continue

        result = '`Passed!`:passed:'
        if os.path.exists(basename+'.errs'):
            s = open(basename+'.errs').read()
            num_failed = 0
            if not re.search(r'OK\s*\Z', s):
                num_failed = len(re.findall(r'(?m)^Failed [Ee]xample:', s))
                result = '|%s|_' % basename
                err_refs.append( (basename, num_failed) )
                if sortkey is None:
                    print(('test %s failed (%d examples)' %
                           (basename, num_failed)))

        title = find_title(basename)
        numtests, numlines = linecount(basename)
        lines.append([title, basename, numtests, numlines, result, num_failed])

    if sortkey in ('title', None):
        lines.sort(key=lambda v:v[0])
    if sortkey == 'lines':
        lines.sort(key=lambda v:(-int(v[2]), v[0]))
    if sortkey == 'tests':
        lines.sort(key=lambda v:(-int(v[3]), v[0]))
    if sortkey == 'outcome':
        lines.sort(key=lambda v:(-v[5], v[0]))

    for (title, basename, numtests, numlines, result, num_failed) in lines:
        numlines = fmt_num(numlines)
        numtests = fmt_num(numtests)
        listing += ('  * - `%s <%s.html>`__\n' % (title,basename) +
                    '    - :guide-linecount:`%s`\n' % numlines +
                    '    - :guide-linecount:`%s`\n' % numtests +
                    '    - %s\n' % result)

    for (basename, num_failed) in err_refs:
         plural = (num_failed!=1 and 's' or '')
         listing += ('\n.. |%s| replace:: `%d test%s failed!`:failed:'
                     '\n.. _%s: %s.errs\n' %
                     (basename, num_failed, plural, basename, basename))
                    
    return listing

def main():
    out = open('test-list.txt', 'w')
    out.write('%s\n%s\n%s' % (HEAD, doctest_listing(), FOOT))
    out.close()
    
    for sortkey in ('title', 'basename', 'lines', 'tests', 'outcome'):
        out = open('test-list-sort-%s.txt' % sortkey, 'w')
        out.write('%s\n%s\n%s' % (HEAD, doctest_listing(sortkey), FOOT))
        out.close()

if __name__ == '__main__':
    main()
