# Natural Language Toolkit - Discretiser tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier import discretiser as d, numrange as nr, instances as ins

class DiscretiserTestCase(unittest.TestCase):
    def test_instances_attributes_and_options_are_extracted_from_strings(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        disc = d.Discretiser(path, path + '.test,' + path + 'extra.test', '0,1,4,5,6,7', '2,3,2,3,4,2')
        self.assertEqual(6, len(disc.training))
        self.assertEqual(2, len(disc.instances))
        self.assertEqual(ins.TestInstances, disc.instances[0].__class__)
        self.assertEqual(ins.TestInstances, disc.instances[1].__class__)
        self.assertEqual([0, 1, 4, 5, 6, 7], disc.attribute_indices)
        self.assertEqual([2, 3, 2, 3, 4, 2], disc.options)
        
    def test_unsupervised_equal_width_discretisation(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        disc = d.Discretiser(path, path + '.test', '1,4,5,6,7', '3,2,3,4,2')
        self.assertTrue(disc.attributes[0].is_continuous())
        self.assertTrue(disc.attributes[1].is_continuous())
        self.assertTrue(disc.attributes[4].is_continuous())
        self.assertTrue(disc.attributes[5].is_continuous())
        self.assertTrue(disc.attributes[6].is_continuous())
        self.assertTrue(disc.attributes[7].is_continuous())
        self.assertEqual('25', disc.training[0].value(disc.attributes[1]))
        self.assertEqual('26', disc.instances[0][0].value(disc.attributes[1]))
        disc.unsupervised_equal_width()
        self.assertTrue(disc.attributes[0].is_continuous())
        self.assertFalse(disc.attributes[1].is_continuous())
        self.assertFalse(disc.attributes[4].is_continuous())
        self.assertFalse(disc.attributes[5].is_continuous())
        self.assertFalse(disc.attributes[6].is_continuous())
        self.assertFalse(disc.attributes[7].is_continuous())
        self.assertEqual('a', disc.training[0].value(disc.attributes[1]))
        self.assertEqual('a', disc.instances[0][0].value(disc.attributes[1]))
        
    def test_returns_array_of_discretised_attributes(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        disc = d.Discretiser(path, path + '.test', '4,6', '2,4')
        disc_attrs = disc.discretised_attributes([nr.Range(0, 2), nr.Range(0, 120000)])
        self.assertEqual(2, len(disc_attrs))
        self.assertEqual(4, disc_attrs[0].index)
        self.assertEqual(2, len(disc_attrs[0].values))
        self.assertEqual(4, len(disc_attrs[1].values))

    def test_create_instances_from_file_names(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        disc = d.Discretiser(path, path + '.test,'+ path + '.gold', '1', '3')
        self.assertEqual(2, len(disc.instances))
        self.assertEqual(ins.TestInstances, disc.instances[0].__class__)
        self.assertEqual(ins.GoldInstances, disc.instances[1].__class__)