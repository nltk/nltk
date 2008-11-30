# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import cfile, item, format
from nltk_contrib.classifier_tests import *

class FileTestCase(unittest.TestCase):
    def test_file_read_operation(self):
        self.contents = ""
        f = cfile.File(datasetsDir(self) + 'test_phones' + SEP + 'phoney', format.c45.NAMES)
        f.for_each_line(self.printline)
        
        verificationContents = ""
        check = open(datasetsDir(self) + 'test_phones' + SEP + 'phoney.names', 'r')
        for l in check:
            verificationContents += l
        self.assertEqual(verificationContents, self.contents)
        
    def test_name_extension(self):
        basename, extension = cfile.name_extension('/home/something.something/else/test_phones' + SEP + 'phoney.' + format.c45.NAMES)
        self.assertEqual('/home/something.something/else/test_phones/phoney', basename)
        self.assertEqual('names', extension)
        
    def test_filter_comments(self):
        f = cfile.File(datasetsDir(self) + 'test_phones' + SEP + 'phoney', format.c45.NAMES)
            
    def printline(self, l):
        self.contents += l + '\n' # the \n is to simulate a new line
