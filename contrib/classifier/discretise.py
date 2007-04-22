# Natural Language Toolkit - Discretise
#  The command line entry point to discretisers
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from optparse import OptionParser
from nltk_lite.contrib.classifier import discretiser
import sys

class Discretise(OptionParser):    
    def __init__(self):

        a_help = "Selects the discretisation algorithm                 " \
               + "Options: UEW for Unsupervised Equal Width            " \
               + "         UEF for Unsupervised Equal Frequency        " \
               + "         NS for Naive Supervised                     " \
               + "Default: UEW."
        t_help = "Training file for discretisation.                    "
        T_help = "Comma separated list of files to discterise based on " \
               + "the Training data."
        A_help = "Comma separated list of attribute indices.           "
        o_help = "Algorithm specific options                           " \
               + "UEW: Comma separated list of number of parts in which" \
               + "     each attribute should be split.                 "
        
        self.__algorithms = {'UEW':'unsupervised_equal_width', 'UEF':'unsupervised_equal_frequency', 'NS' : 'naive_supervised'}
        OptionParser.__init__(self)
        self.add_option("-a", "--algorithm", dest="algorithm", type="choice", \
                        choices=self.__algorithms.keys(), default="UEW", help= a_help)
        self.add_option("-t", "--training-file", dest="training", type="string", help=t_help)
        self.add_option("-T", "--test-files", dest="test", type="string", help=T_help)
        self.add_option("-A", "--attributes", dest="attributes", type="string", help=A_help)
        self.add_option("-o", "--options", dest="options", type="string", help=o_help)
        
    def parse(self, args):
        self.parse_args(args, None)
        
    def execute(self):
        algorithm = self.__algorithms[self.__get_value('algorithm')]
        training = self.__get_value('training')
        test = self.__get_value('test')
        attributes = self.__get_value('attributes')
        options = self.__get_value('options')
        if algorithm is None or test is None or training is None or attributes is None or \
           ((algorithm == self.__algorithms['UEW'] or algorithm == self.__algorithms['UEF']) and options is None): 
            self.error("Invalid arguments. One or more required arguments are not present.")
        self.invoke(training, test, attributes, options, algorithm)
        
    def __get_value(self, name):
        return self.values.ensure_value(name, None)
    
    def invoke(self, training, test, attributes, options, algorithm):
        disc = discretiser.Discretiser(training, test, attributes, options)
        files_written = getattr(disc, algorithm)()
        print 'The following files were created with discretised values...'
        for file_name in files_written:
            print file_name
    
    def run(self, args):
        self.parse(args)
        self.execute()

if __name__ == "__main__":
    Discretise().run(sys.argv[1:])
    
