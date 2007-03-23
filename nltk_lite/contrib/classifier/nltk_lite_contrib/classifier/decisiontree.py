from nltk_lite_contrib.classifier import Classifier, oner

class DecisionTree(Classifier):
    def __init__(self, path):
        Classifier.__init__(self, DecisionTreeTrainingInstances(path))
        self.build_tree()
        
    def build_tree(self):
        decision_stump = self.training.best_decision_stump()
        Node(decision_stump)
    
    def test(self, path, printResults=True):
        pass
    
    def verify(self, path):
        pass
    
    def depth(self):
        return 0
    
class Node:
    def __init__(self, decision_stump):
        self.root = decision_stump
        children = []
    
class DecisionTreeTrainingInstances(oner.OneRTrainingInstances):
    def __init__(self, path):
        oner.OneRTrainingInstances.__init__(self, path)