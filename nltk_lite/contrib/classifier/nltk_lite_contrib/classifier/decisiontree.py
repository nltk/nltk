from nltk_lite_contrib.classifier import Classifier, oner
import copy

class DecisionTree(oner.OneR):
    def __init__(self, path):
        Classifier.__init__(self, DecisionTreeTrainingInstances(path))
        self.__used_attributes = []
        self.root = self.build_tree(self.training)
        
    def build_tree(self, instances):
        decision_stump = instances.best_decision_stump(self.__used_attributes, 'maximum_information_gain')
        self.__used_attributes.append(decision_stump.attribute)
        for attr_value in decision_stump.attribute.values:
            if decision_stump.entropy(attr_value) == 0:
                continue
            new_instances = instances.filter(decision_stump.attribute, attr_value)
            new_child = self.build_tree(new_instances)
            if new_child is not None: decision_stump.children[attr_value] = new_child
        return decision_stump
    
    def classify(self, instances):
        instances.classify(self.root)

            
class DecisionTreeTrainingInstances(oner.OneRTrainingInstances):
    #if path is None we are trying to make a copy
    def __init__(self, path):
        if (path is not None):
            oner.OneRTrainingInstances.__init__(self, path)
        
    def filter(self, attribute, attr_value):
        new = DecisionTreeTrainingInstances(None)
        new.klass, new.attributes = self.klass, self.attributes
        new.instances = []
        for instance in self.instances:
            if(instance.value(attribute) == attr_value):
                new.instances.append(instance)
        return new
            
    def maximum_information_gain(self, decision_stumps):
        ig, max_ig_stump = -1, None
        for decision_stump in decision_stumps:
            new_ig = decision_stump.information_gain()
            if new_ig > ig: 
                ig = new_ig
                max_ig_stump = decision_stump
        return max_ig_stump
