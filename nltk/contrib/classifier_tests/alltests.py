# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk.contrib.classifier_tests import \
        attributestests as attributes, instancestests as instances, \
        attributetests as attribute, instancetests as instance, \
        itemtests as item, zerortests as zeror, \
        cfiletests as cfile, confusionmatrixtests as confusionmatrix, \
        decisionstumptests as decisionstump, onertests as oner, \
        classifytests as classify, decisiontreetests as decisiontree, \
        autoclasstests as autoclass, numrangetests as numrange, \
        discretisedattributetests as discretisedattribute, \
        discretisetests as discretise, formattests as format, \
        featureselecttests as featureselect, inittests as init, \
        commandlinetests as commandline, naivebayestests as naivebayes
import unittest

def allTestsSuite():
    return unittest.TestSuite((unittest.makeSuite(attributes.AttributesTestCase), \
                               unittest.makeSuite(instances.InstancesTestCase), \
                               unittest.makeSuite(attribute.AttributeTestCase), \
                               unittest.makeSuite(instance.InstanceTestCase), \
                               unittest.makeSuite(item.ItemTestCase), \
                               unittest.makeSuite(zeror.ZeroRTestCase), \
                               unittest.makeSuite(cfile.FileTestCase), \
                               unittest.makeSuite(confusionmatrix.ConfusionMatrixTestCase), \
                               unittest.makeSuite(decisionstump.DecisionStumpTestCase), \
                               unittest.makeSuite(oner.OneRTestCase), \
                               unittest.makeSuite(classify.ClassifyTestCase),
                               unittest.makeSuite(decisiontree.DecisionTreeTestCase),
                               unittest.makeSuite(autoclass.AutoClassTestCase), \
                               unittest.makeSuite(numrange.RangeTestCase), \
                               unittest.makeSuite(discretisedattribute.DiscretisedAttributeTestCase), \
                               unittest.makeSuite(discretise.DiscretiseTestCase), \
                               unittest.makeSuite(format.FormatTestCase), \
                               unittest.makeSuite(featureselect.FeatureSelectTestCase), \
                               unittest.makeSuite(init.InitTestCase), \
                               unittest.makeSuite(commandline.CommandLineTestCase), \
                               unittest.makeSuite(naivebayes.NaiveBayesTestCase)))

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(allTestsSuite())
