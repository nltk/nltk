'''
Created on 6 de may. de 2015

@author: lorenzorubio
'''
import unittest
import os
import filecmp
from nltk.twitter.util import guess_path, json2csv, json2csv_entities

class Test(unittest.TestCase):


    def setUp(self):
        from nltk.corpus import tweets
        self.inpf = tweets.abspath("tweets.20150430-223406.json")
        pass


    def tearDown(self):
        pass


    def testTextOutput(self):
        outf = os.path.join(guess_path("twitter-files"), 'tweets.20150430-223406.text.csv')
        json2csv(self.inpf, outf,
                 ['text'])

        assert filecmp.cmp(outf,
                       'tweets.20150430-223406.text.csv.ref'), 'Error in csv file'


if __name__ == "__main__":
    unittest.main()