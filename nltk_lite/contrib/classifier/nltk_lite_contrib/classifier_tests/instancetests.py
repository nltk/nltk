# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import instance as ins, klass as k, attribute
import unittest

class InstanceTestCase(unittest.TestCase):
    def setUp(self):
        self.a = 'a'
        self.b = 'b'
    
    def test_create_n_validate_instance(self):
        instance = ins.TestInstance('bar,two,a')
        self.assertEqual(3, len(instance.attrs))
        self.assertEqual('bar', instance.attrs[0])
        self.assertEqual('two', instance.attrs[1])
        self.assertEqual('a', instance.attrs[2])
        
    def test_training_instance_has_class_and_attributes(self):
        instance = ins.TrainingInstance('bar,two,a')
        self.assertEqual(self.a, instance.klass_value)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def test_test_instance_has_only_attributes_and_none_as_class(self):
        instance = ins.TestInstance('bar,two')
        self.assertEqual(None, instance.klass_value)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def test_cannot_set_class_in_training_instance(self):
        instance = ins.TrainingInstance('bar,two,a')
        try:
            instance.set_klass(self.b)
            self.fail('should not be able to set a class on a Training Instance')
        except AttributeError:
            self.assertEqual(self.a, instance.klass_value, 'should not have changed the original class')
        
    def test_should_be_able_to_set_class_on_test_instance(self):
        instance = ins.TestInstance('bar,two')
        try:
            instance.set_klass('c')
            self.assertEqual('c', instance.classifiedKlass)
            self.assertEqual(None, instance.klass_value)
        except AttributeError:
            self.fail('should be able to set class in Test Instance')
        
    def test_gold_instance_creates_class(self):
        gold = ins.GoldInstance('bar,two,a')
        self.assertEqual(2, len(gold.attrs))
        self.assertEqual('bar', gold.attrs[0])
        self.assertEqual('two', gold.attrs[1])
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(None, gold.classifiedKlass)
        
    def test_classes_can_be_set_on_gold_instance(self):
        gold = ins.GoldInstance('bar,two,a')
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(None, gold.classifiedKlass)
        gold.set_klass(self.b)
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(self.b, gold.classifiedKlass)
        
    def test_string_representation(self):
        instance = ins.TrainingInstance('bar,two,a')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a", instance.__str__());
        
        instance = ins.TestInstance('bar,two')
        self.assertEqual("Attributes: ['bar', 'two'] Classified as:  ", instance.__str__());
        instance.set_klass('b')
        self.assertEqual("Attributes: ['bar', 'two'] Classified as: b", instance.__str__());
                
        instance = ins.GoldInstance('bar,two,a')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a Classified as:  ", instance.__str__());
        instance.set_klass('b')
        self.assertEqual("Attributes: ['bar', 'two'] Class: a Classified as: b", instance.__str__());
        
    def test_get_attribute_value_from_instance_using_attribute(self):
        instance = ins.TrainingInstance('bar,two,a')
        attr = attribute.Attribute('second:two,duo', 1)
        self.assertEqual('two', instance.value(attr))
        
        test = ins.TestInstance('bar,two')
        self.assertEqual('two', test.value(attr))

        gold = ins.GoldInstance('bar,two,a')
        self.assertEqual('two', gold.value(attr))
