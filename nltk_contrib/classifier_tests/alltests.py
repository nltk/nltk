# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

import unittest
import re, os

def allTestsSuite():
    testfilenames = []
    for dn,d,f in os.walk('.'):
        if dn is not '.': continue
        testfilenames = [filename for filename in f if re.search('tests\.py$', filename) is not None]
    modulenames = map(lambda f: re.sub('\.py$', '', f), testfilenames)         
    modules = map(__import__, modulenames)                 
    load = unittest.defaultTestLoader.loadTestsFromModule  
    return unittest.TestSuite(map(load, modules))    

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(allTestsSuite())
