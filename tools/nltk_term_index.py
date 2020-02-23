
import re
import sys
import nltk
import epydoc.docbuilder
import epydoc.cli
from epydoc import log

STOPLIST = '../../tools/nltk_term_index.stoplist'
FILENAMES = ['ch%02d.xml' % n for n in range(13)]
TARGET_DIR = 'nlp/'
# FILENAMES = ['../doc/book/ll.xml']

logger = epydoc.cli.ConsoleLogger(0)
logger._verbosity = 5
log.register_logger(logger)


def find_all_names(stoplist):
    ROOT = ['nltk']
    logger._verbosity = 0
    docindex = epydoc.docbuilder.build_doc_index(ROOT, add_submodules=True)
    valdocs = sorted(
        docindex.reachable_valdocs(
            imports=False,
            # packages=False, bases=False, submodules=False,
            # subclasses=False,
            private=False,
        )
    )
    logger._verbosity = 5
    names = nltk.defaultdict(list)
    n = 0
    for valdoc in valdocs:
        name = valdoc.canonical_name
        if name is not epydoc.apidoc.UNKNOWN and name is not None and name[0] == 'nltk':
            n += 1
            for i in range(len(name)):
                key = str(name[i:])
                if len(key) == 1:
                    continue
                if key in stoplist:
                    continue
                names[key].append(valdoc)

    log.info('Found {} names from {} objects'.format(len(names), n))

    return names


SCAN_RE1 = "<programlisting>[\s\S]*?</programlisting>"
SCAN_RE2 = "<literal>[\s\S]*?</literal>"
SCAN_RE = re.compile("({})|({})".format(SCAN_RE1, SCAN_RE2))

TOKEN_RE = re.compile('[\w\.]+')

LINE_RE = re.compile('.*')

INDEXTERM = '<indexterm type="nltk"><primary>%s</primary></indexterm>'


def scan_xml(filenames, names):
    fdist = nltk.FreqDist()

    def linesub(match):
        line = match.group()
        for token in TOKEN_RE.findall(line):
            if token in names:
                targets = names[token]
                fdist.inc(token)
                if len(targets) > 1:
                    log.warning(
                        '{} is ambiguous: {}'.format(
                            token,
                            ', '.join(str(v.canonical_name) for v in names[token]),
                        )
                    )
                line += INDEXTERM % token
                # line += INDEXTERM % names[token][0].canonical_name
        return line

    def scansub(match):
        return LINE_RE.sub(linesub, match.group())

    for filename in filenames:
        log.info('  {}'.format(filename))
        src = open(filename, 'rb').read()
        src = SCAN_RE.sub(scansub, src)
        #        out = open(filename[:-4]+'.li.xml', 'wb')
        out = open(TARGET_DIR + filename, 'wb')
        out.write(src)
        out.close()

    for word in fdist:
        namestr = ('\n' + 38 * ' ').join(
            [str(v.canonical_name[:-1]) for v in names[word][:1]]
        )
        print('[%3d]  %-30s %s' % (fdist[word], word, namestr))
        sys.stdout.flush()


def main():
    log.info('Loading stoplist...')
    stoplist = open(STOPLIST).read().split()
    log.info('  Stoplist contains {} words'.format(len(stoplist)))

    log.info('Running epydoc to build a name index...')
    names = find_all_names(stoplist)

    log.info('Scanning xml files...')
    scan_xml(FILENAMES, names)


main()
