# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite.contrib.classifier import cfile, item
from nltk_lite.contrib.classifier_tests import *

class FileTestCase(unittest.TestCase):
    def testFileOperation(self):
        self.contents = ""
        f = cfile.File(datasetsDir(self) + 'test_phones' + SEP + 'phoney', cfile.NAMES)
        f.execute(self.printline)
        
        verificationContents = ""
        check = open(datasetsDir(self) + 'test_phones' + SEP + 'phoney.names', 'r')
        for l in check:
            verificationContents += l
        self.assertEqual(verificationContents, self.contents)
            
    def printline(self, l):
        self.contents += l