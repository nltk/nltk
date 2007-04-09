# Natural Language Toolkit - Discretiser tests
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
from nltk_lite.contrib.classifier_tests import *
from nltk_lite.contrib.classifier import discretiser as d, numrange as nr, instances as ins
from nltk_lite.contrib.classifier.exceptions import invaliddataerror as inv

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
        
    def test_option_cannot_be_zero(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'person'
        try:
            disc = d.Discretiser(path, path + '.test', '4,6', '2,0')
            self.fail('should raise error as an option is zero')
        except inv.InvalidDataError:
            pass
        
    def test_ranges_from_chunks(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        disc = d.Discretiser(path, path + '.test,'+ path + '.gold', '1', '3')
        ranges = disc.ranges_from_chunks([[6, 6, 7, 7, 8], [9, 10, 10, 13, 14], [15, 16, 16, 16, 19]])
        self.assertEqual(3, len(ranges))
        self.assertTrue(ranges[0].includes(6))
        self.assertTrue(ranges[0].includes(8))
        self.assertTrue(ranges[0].includes(8.9))
        self.assertTrue(ranges[1].includes(9))
        self.assertTrue(ranges[1].includes(14))
        self.assertTrue(ranges[2].includes(15))
        self.assertTrue(ranges[2].includes(19))
        
    def test_get_chunks_with_frequency(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        disc = d.Discretiser(path, path + '.test,'+ path + '.gold', '1', '3')
        chunks = disc.get_chunks_with_frequency([6, 6, 7, 7, 8, 8, 8, 9, 10, 10, 13, 14, 14, 15, 16, 16, 16, 19], 5)
        self.assertEqual(3, len(chunks))
        self.assertEqual([[6, 6, 7, 7, 8], [9, 10, 10, 13, 14], [15, 16, 16, 16, 19]], chunks)

    def test_unsupervised_equal_frequency(self):
        path = datasetsDir(self) + 'numerical' + SEP + 'weather'
        disc = d.Discretiser(path, path + '.test,'+ path + '.gold', '1', '3')
        self.assertTrue(disc.attributes[1].is_continuous())
        self.assertEqual('27.5', disc.training[0].value(disc.attributes[1]))
        self.assertEqual('32', disc.training[2].value(disc.attributes[1]))
        self.assertEqual('25.4', disc.instances[0][0].value(disc.attributes[1]))
        values = disc.training.values_grouped_by_attribute([disc.attributes[1]])
        values[0].sort()
        self.assertEqual([6.0, 9.0, 9.0, 10.699999999999999, 12.0, 12.0, 12.0, 14.1, 18.0, 27.5, 32.0, 33.100000000000001], values[0])
        
        disc.unsupervised_equal_frequency()
        
        self.assertFalse(disc.attributes[1].is_continuous())
        self.assertEqual(4, len(disc.attributes[1].values))
        self.assertEqual('c', disc.training[0].value(disc.attributes[1]))
        self.assertEqual('d', disc.training[2].value(disc.attributes[1]))
        self.assertEqual('c', disc.instances[0][0].value(disc.attributes[1]))
        
        
        