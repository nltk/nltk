# Natural Language Toolkit: Discourse Processing using Glue Semantics
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
from operator import add

from nltk import data
from nltk.tag import RegexpTagger
from nltk.parse.malt import MaltParser
from nltk.inference.discourse import DiscourseTester, ReadingCommand
from drt_resolve_anaphora import AnaphoraResolutionException
from drt_glue import DrtGlue


class DrtGlueReadingCommand(ReadingCommand):
    def __init__(self, semtype_file=None, remove_duplicates=False, 
                 depparser=None):
        """
        @param semtype_file: name of file where grammar can be loaded
        @param remove_duplicates: should duplicates be removed?
        @param depparser: the dependency parser
        """
        if semtype_file is None:
            semtype_file = 'drt_glue.semtype'
        self._glue = DrtGlue(semtype_file=semtype_file, 
                             remove_duplicates=remove_duplicates, 
                             depparser=depparser)
    
    def parse_to_readings(self, sentence):
        """@see: ReadingCommand.parse_to_readings()"""
        return self._glue.parse_to_meaning(sentence)

    def process_thread(self, sentence_readings):
        """@see: ReadingCommand.process_thread()"""
        try:
            return [self.combine_readings(sentence_readings)]
        except AnaphoraResolutionException:
            return []

    def combine_readings(self, readings):
        """@see: ReadingCommand.combine_readings()"""
        thread_reading = reduce(add, readings)
        return thread_reading.simplify().resolve_anaphora()


def discourse_demo(reading_command=None):
    """
    Illustrate the various methods of C{DiscourseTester}
    """
    dt = DiscourseTester(['every dog chases a boy', 'he runs'], 
                         reading_command)
    dt.models()
    print
    dt.sentences()
    print 
    dt.readings()
    print
    dt.readings(show_thread_readings=True)
    print
    dt.readings(filter=True, show_thread_readings=True)


if __name__ == '__main__':
    tagger = RegexpTagger(
        [('^(chases|runs)$', 'VB'),
         ('^(a)$', 'ex_quant'),
         ('^(every)$', 'univ_quant'),
         ('^(dog|boy)$', 'NN'),
         ('^(he)$', 'PRP')
    ])
    depparser = MaltParser(tagger=tagger)

    discourse_demo(DrtGlueReadingCommand(remove_duplicates=False, depparser=depparser))
