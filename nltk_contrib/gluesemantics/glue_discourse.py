# Natural Language Toolkit: Discourse Processing using Glue Semantics
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.inference.discourse import DiscourseTester, ReadingCommand
from nltk.sem.drt_resolve_anaphora import AnaphoraResolutionException
from nltk_contrib.gluesemantics.drt_glue import DrtGlue

from operator import add

class DrtGlueReadingCommand(ReadingCommand):
    def __init__(self, semtype_file=None):
        """
        @parameter gramfile: name of file where grammar can be loaded
        @type gramfile: C{str}
        """
        if semtype_file is None:
            semtype_file = 'drt_glue.semtype'
        self._glue = DrtGlue(semtype_file=semtype_file)
    
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
    discourse_demo(DrtGlueReadingCommand())
