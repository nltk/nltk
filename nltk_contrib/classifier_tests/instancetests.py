# Natural Language Toolkit
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_contrib.classifier import instance as ins, attribute, discretisedattribute as da, numrange as r
import unittest

class InstanceTestCase(unittest.TestCase):
    def setUp(self):
        self.a = 'a'
        self.b = 'b'
    
    def test_create_n_validate_instance(self):
        instance = ins.TestInstance(['bar','two','a'])
        self.assertEqual(3, len(instance.attrs))
        self.assertEqual('bar', instance.attrs[0])
        self.assertEqual('two', instance.attrs[1])
        self.assertEqual('a', instance.attrs[2])
        
    def test_training_instance_has_class_and_attributes(self):
        instance = ins.TrainingInstance(['bar','two'],'a')
        self.assertEqual(self.a, instance.klass_value)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def test_test_instance_has_only_attributes_and_none_as_class(self):
        instance = ins.TestInstance(['bar','two'])
        self.assertEqual(None, instance.klass_value)
        self.assertEqual(['bar', 'two'], instance.attrs)
        
    def test_cannot_set_class_in_training_instance(self):
        instance = ins.TrainingInstance(['bar','two'],'a')
        try:
            getattr(instance, 'set_klass')(self.b)
            self.fail('should not be able to set a class on a Training Instance')
        except AttributeError:
            self.assertEqual(self.a, instance.klass_value, 'should not have changed the original class')
        
    def test_should_be_able_to_set_class_on_test_instance(self):
        instance = ins.TestInstance(['bar','two'])
        try:
            instance.set_klass('c')
            self.assertEqual('c', instance.classified_klass)
            self.assertEqual(None, instance.klass_value)
        except AttributeError:
            self.fail('should be able to set class in Test Instance')
        
    def test_gold_instance_creates_class(self):
        gold = ins.GoldInstance(['bar','two'],'a')
        self.assertEqual(2, len(gold.attrs))
        self.assertEqual('bar', gold.attrs[0])
        self.assertEqual('two', gold.attrs[1])
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(None, gold.classified_klass)
        
    def test_classes_can_be_set_on_gold_instance(self):
        gold = ins.GoldInstance(['bar','two'],'a')
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(None, gold.classified_klass)
        gold.set_klass(self.b)
        self.assertEqual(self.a, gold.klass_value)
        self.assertEqual(self.b, gold.classified_klass)
        
    def test_string_representation(self):
        instance = ins.TrainingInstance(['bar','two'],'a')
        self.assertEqual("[bar,two;a]", instance.__str__());
        
        instance = ins.TestInstance(['bar','two'])
        self.assertEqual("[bar,two; ]", instance.__str__());
        instance.set_klass('b')
        self.assertEqual("[bar,two;b]", instance.__str__());
                
        instance = ins.GoldInstance(['bar','two'],'a')
        self.assertEqual("[bar,two;a; ]", instance.__str__());
        instance.set_klass('b')
        self.assertEqual("[bar,two;a;b]", instance.__str__());
        
    def test_get_attribute_value_from_instance_using_attribute(self):
        instance = ins.TrainingInstance(['bar','two'],'a')
        attr = attribute.Attribute('second', ['two','duo'], 1)
        self.assertEqual('two', instance.value(attr))
        
        test = ins.TestInstance(['bar','two'])
        self.assertEqual('two', test.value(attr))

        gold = ins.GoldInstance(['bar','two'],'a')
        self.assertEqual('two', gold.value(attr))

    def test_discretise_using_discretised_attributes(self):
        dependents = attribute.Attribute('dependents',['continuous'], 4)
        annual_salary = attribute.Attribute('annualsalary', ['continuous'], 6)
        disc_dependents = da.DiscretisedAttribute('dependents', r.Range(0, 2, True).split(2), 4)
        disc_annual_salary = da.DiscretisedAttribute('annualsalary', r.Range(0, 120000, True).split(5), 6)
        discretised_attributes = [disc_dependents, disc_annual_salary]
        
        instance = ins.TrainingInstance(['3','34','self-employed','married','2','3','120000','2'],'yes')
        self.assertEqual(2, instance.value(dependents))
        self.assertEqual(120000, instance.value(annual_salary))
        instance.discretise(discretised_attributes)
        
        self.assertEqual('b', instance.value(disc_dependents))
        self.assertEqual('e', instance.value(disc_annual_salary))

    def test_values_of_atrributes(self):
        _training = ins.TrainingInstance(['3','34','self-employed','married','2','3','120000','2'],'yes')
        dependents = attribute.Attribute('dependents', ['continuous'], 4)
        annual_salary = attribute.Attribute('annualsalary', ['continuous'], 6)
        self.assertEqual(['2','120000'], _training.values([dependents, annual_salary]))
        
    def test_remove_attrbutes(self):
        _training = ins.TrainingInstance(['3','34','self-employed','married','2','3','120000','2'],'yes')
        id = attribute.Attribute('id', ['continuous'], 0)
        annual_salary = attribute.Attribute('annualsalary', ['continuous'], 6)
        _training.remove_attributes([id, annual_salary])
        self.assertEqual(6, len(_training.attrs))
        self.assertEqual('34', _training.attrs[0])
    
    def test_get_training_as_gold(self):
        _training = ins.TrainingInstance(['3','34','self-employed','married','2','3','120000','2'],'yes')
        gold = _training.as_gold()
        self.assertEqual(gold.attrs, _training.attrs)
        self.assertEqual(gold.klass_value, _training.klass_value)
