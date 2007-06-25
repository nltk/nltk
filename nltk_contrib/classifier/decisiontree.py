# Natural Language Toolkit - Decision Tree
#  Creates a Decision Tree Classifier
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk.contrib.classifier import oner

class DecisionTree(oner.OneR):
    def __init__(self, training, attributes, klass, internal=False):
        oner.OneR.__init__(self, training, attributes, klass, internal)
        self.root = self.build_tree(self.training, [])
        
    def build_tree(self, instances, used_attributes):
        decision_stump = self.best_decision_stump(instances, used_attributes, 'maximum_information_gain')
        if len(self.attributes) - len(used_attributes) == 1: return decision_stump
        used_attributes.append(decision_stump.attribute)
        for attr_value in decision_stump.attribute.values:
            if decision_stump.entropy(attr_value) == 0:
                continue
            new_instances = instances.filter(decision_stump.attribute, attr_value)
            new_child = self.build_tree(new_instances, used_attributes)
            if new_child is not None: decision_stump.children[attr_value] = new_child
        return decision_stump
    
    def classify(self, instances):
        for instance in instances:
            klass = self.root.klass(instance)
            instance.set_klass(klass)
        
    def maximum_information_gain(self):
        return self.higher_value_preferred(lambda decision_stump: decision_stump.information_gain())
    
    def maximum_gain_ratio(self):
        return self.higher_value_preferred(lambda decision_stump: decision_stump.gain_ratio())
    
    def higher_value_preferred(self, method):
        highest, max_stump = -1, None
        for decision_stump in self.decision_stumps:
            new = method(decision_stump)
            if new > highest: highest, max_stump = new, decision_stump
        return max_stump
        
