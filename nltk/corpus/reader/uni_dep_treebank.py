# Natural Language Toolkit: Universal Dependency Treebank Corpus Reader.
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Cyril Shcherbin <cyril.shcherbin@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.conll import ConllCorpusReader


class UniDepTreebankCorpusReader(ConllCorpusReader):

    """
    """

    def __init__(self, *args, **kwargs):
        """
        """

        super(UniDepTreebankCorpusReader, self).__init__(*args, **kwargs)


def demo():
    """
    """

    import re
    from pprint import pprint

    columntypes = (
        'ignore',   # 1
        'words',    # 2
        'ignore',   # 3
        'ignore',   # 4
        'pos',      # 5
        'ignore',   # 6
        'ignore',   # 7
        'ignore',   # 8
        'ignore',   # 9
        'ignore'    # 10
    )


    reader = UniDepTreebankCorpusReader(
        root='/home/ki/sandbox/universal_treebanks_v2.0',
        fileids='.*\.conll',
        columntypes=columntypes)

    print 'File Ids are:'
    pprint([f for f in reader.fileids()])
    print '------------------------------------------------'


    #print dir(reader)

    #print reader.raw(fileids=['std/de/de-universal-test.conll'])

    print 'WORDS'

    print len(reader.words(fileids=['std/de/de-universal-test.conll']))
    print len(reader.words(fileids=['std/de/de-universal-dev.conll']))
    print len(reader.words(fileids=['std/de/de-universal-test.conll', 'std/de/de-universal-dev.conll']))

    print '------------------------------------------------'

    print 'TAGGED WORDS'

    print len(reader.tagged_words(fileids=['std/de/de-universal-test.conll']))
    print len(reader.tagged_words(fileids=['std/de/de-universal-dev.conll']))
    print len(reader.tagged_words(fileids=['std/de/de-universal-test.conll', 'std/de/de-universal-dev.conll']))

    print '------------------------------------------------'
    #for word in reader.parsed_sents(fileids=['ch/de/de-universal-ch-test.conll']):
    #    pprint(word)



if __name__ == '__main__':
    demo()
