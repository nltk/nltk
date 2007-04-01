# Natural Language Toolkit - Decision Tree
#  Creates a Decision Tree Classifier
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier import oner

class DecisionTree(oner.OneR):
    def __init__(self, path):
        oner.OneR.__init__(self, path)
        self.root = self.build_tree(self.training, [])
        
    def build_tree(self, instances, used_attributes):
        decision_stump = self.best_decision_stump(instances, used_attributes, 'maximum_information_gain')
        used_attributes.append(decision_stump.attribute)
        for attr_value in decision_stump.attribute.values:
            if decision_stump.entropy(attr_value) == 0:
                continue
            new_instances = instances.filter(decision_stump.attribute, attr_value)
            new_child = self.build_tree(new_instances, used_attributes)
            if new_child is not None: decision_stump.children[attr_value] = new_child
        return decision_stump
    
    def classify(self, instances):
        instances.for_each(self.set_klass_on_test_or_gold)
        
    def set_klass_on_test_or_gold(self, instance):
        klass = self.root.klass(instance)
        instance.set_klass(klass)

    def maximum_information_gain(self):
        info_gain, max_info_gain_stump = -1, None
        for decision_stump in self.decision_stumps:
            new_info_gain = decision_stump.information_gain()
            if new_info_gain > info_gain: 
                info_gain = new_info_gain
                max_info_gain_stump = decision_stump
        return max_info_gain_stump
