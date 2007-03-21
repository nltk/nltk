# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import instance as ins, klass as k
import unittest

class InstanceTestCase(unittest.TestCase):
    def setUp(self):
        self.a = 'a'
        self.b = 'b'
    
    def testValidateAndCreateInstance(self):
        instance = ins.TestInstance('bar,two,a')
        self.assertEqual(3, len(instance.attrs))
        self.assertEqual('bar', instance.attrs[0])
        self.assertEqual('two', instance.attrs[1])
        self.assertEqual('a', instance.attrs[2])
        
    def testTrainingInstanceHasClassAndAttributes(self):
        instance = ins.TrainingInstance('bar,two,a')
        self.assertEqual(self.a, instance.klassValue)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def testTestInstanceHasOnlyAttributesAndNoneAsClass(self):
        instance = ins.TestInstance('bar,two')
        self.assertEqual(None, instance.klassValue)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def testCannotSetClassInTrainingInstance(self):
        instance = ins.TrainingInstance('bar,two,a')
        try:
            instance.setClass(self.b)
            fail('should not be able to set a class on a Training Instance')
        except AttributeError:
            self.assertEqual(self.a, instance.klassValue, 'should not have changed the original class')
        
    def testShouldBeAbleToSetClassOnTestInstance(self):
        instance = ins.TestInstance('bar,two')
        try:
            instance.setClass('c')
            self.assertEqual('c', instance.classifiedKlass)
            self.assertEqual(None, instance.klassValue)
        except AttributeError:
            fail('should be able to set class in Test Instance')
        
    def testGoldInstanceCreatesClass(self):
        gold = ins.GoldInstance('bar,two,a')
        self.assertEqual(2, len(gold.attrs))
        self.assertEqual('bar', gold.attrs[0])
        self.assertEqual('two', gold.attrs[1])
        self.assertEqual(self.a, gold.klassValue)
        self.assertEqual(None, gold.classifiedKlass)
        
    def testClassesCanBeSetOnGoldInstance(self):
        gold = ins.GoldInstance('bar,two,a')
        self.assertEqual(self.a, gold.klassValue)
        self.assertEqual(None, gold.classifiedKlass)
        gold.setClass(self.b)
        self.assertEqual(self.a, gold.klassValue)
        self.assertEqual(self.b, gold.classifiedKlass)
        
    def testStringRepresentation(self):
        instance = ins.TrainingInstance('bar,two,a')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a", instance.__str__());
        
        instance = ins.TestInstance('bar,two')
        self.assertEqual("Attributes: ['bar', 'two'] Classified as:  ", instance.__str__());
        instance.setClass('b')
        self.assertEqual("Attributes: ['bar', 'two'] Classified as: b", instance.__str__());
                
        instance = ins.GoldInstance('bar,two,a')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a Classified as:  ", instance.__str__());
        instance.setClass('b')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a Classified as: b", instance.__str__());