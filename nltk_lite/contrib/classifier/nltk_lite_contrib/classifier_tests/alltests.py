# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier_tests import klasstests as klass, nameitemtests as nameitem, \
        attributestests as attributes, instancestests as instances, \
        attributetests as attribute, instancetests as instance, \
        itemtests as item, zerortests as zeror, \
        filetests as file, confusionmatrixtests as confusionmatrix, \
        decisionstumptests as decisionstump, onertests as oner
import unittest

def allTestsSuite():
    return unittest.TestSuite((unittest.makeSuite(klass.KlassTestCase), \
                               unittest.makeSuite(nameitem.NameItemTestCase), \
                               unittest.makeSuite(attributes.AttributesTestCase), \
                               unittest.makeSuite(instances.InstancesTestCase), \
                               unittest.makeSuite(attribute.AttributeTestCase), \
                               unittest.makeSuite(instance.InstanceTestCase), \
                               unittest.makeSuite(item.ItemTestCase), \
                               unittest.makeSuite(zeror.ZeroRTestCase), \
                               unittest.makeSuite(file.FileTestCase), \
                               unittest.makeSuite(confusionmatrix.ConfusionMatrixTestCase), \
                               unittest.makeSuite(decisionstump.DecisionStumpTestCase), \
                               unittest.makeSuite(oner.OneRTestCase)))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(allTestsSuite())
