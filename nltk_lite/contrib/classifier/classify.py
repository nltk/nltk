from nltk_lite.contrib.classifier import commandline as cl
from nltk_lite.contrib.classifier import oner, zeror, decisiontree, format
import sys

a_help = "Selects the classification algorithm                  " \
        + "Options: 0R for Zero R, 1R for One R, DT for Decision" \
        + " Trees.                                              " \
        + "Default: 0R."

f_help = "Specifies the base name of test, training or gold files." \
        + "By default it searches for training and test files, look at the verify option for more details."

v_help = "Used in conjunction with the files option to verify  " \
        + "the efficiency with a gold file instead of testing " \
        + "the classifier on a test file. Setting this option " \
        + "will mean that a gold file is present with the common" \
        + "name.                                               " \
        + "Options: True/False or yes/no."

t_help = "When the files option is not used this option is used " \
        + "to specify the path to the training file without the " \
        + "extension."

T_help = "When the files option is not used this option is used " \
        + "to specify the path to the test file without the " \
        + "extension."

g_help = "When the files option is not used this option is used " \
        + "to specify the path to the gold file without the " \
        + "extension."

A_help = "Used to disable calculation of Accuracy.              " \
        + "Options: True/False or yes/no.                       " \
        + "Default: False.                                      "

e_help = "Used to enable calculation of Error rate.             " \
        + "Options: True/False or yes/no.                       " \
        + "Default: False.                                      "

F_help = "Used to disable calculation of F-score.               " \
        + "Options: True/False or yes/no.                       " \
        + "Default: False.                                      "

p_help = "Used to enable calculation of Precision.              " \
        + "Options: True/False or yes/no.                       " \
        + "Default: False.                                      "

r_help = "Used to enable calculation of Recall.                 " \
        + "Options: True/False or yes/no.                       " \
        + "Default: False.                                      "
        
ZERO_R = '0R'
ONE_R = '1R'
DECISION_TREE = 'DT'

ALGORITHM_MAPPINGS = {ZERO_R:zeror.ZeroR, ONE_R:oner.OneR, DECISION_TREE:decisiontree.DecisionTree}

class Classify(cl.CommandLineInterface):    
    def __init__(self):
        cl.CommandLineInterface.__init__(self, ALGORITHM_MAPPINGS.keys(), ONE_R, a_help, f_help, t_help, T_help, g_help)
        self.add_option("-v", "--verify", dest="verify", action="store_true", default=False, help=v_help)
        self.add_option("-A", "--accuracy", dest="accuracy", action="store_false", default=True, help=A_help)
        self.add_option("-e", "--error", dest="error", action="store_true", default=False, help=e_help)
        self.add_option("-F", "--f-score", dest="fscore", action="store_false", default=True, help=F_help)
        self.add_option("-p", "--precision", dest="precision", action="store_true", default=False, help=p_help)
        self.add_option("-r", "--recall", dest="recall", action="store_true", default=False, help=r_help)
        
    def execute(self):
        cl.CommandLineInterface.execute(self)
        self.validate_basic_arguments_are_present()
        self.validate_files_arg_is_exclusive()
        if self.test_path is not None and self.gold_path is not None:
            self.error('Invalid arguments. Test and gold files are mutually exclusive.')
        if self.files is None and self.test_path is not None and self.get_value('verify'):
            self.error('Invalid arguments. Cannot verify classification for test data.')
        if self.files is not None:
            self.training_path = self.files
            self.test_path, self.gold_path = self.__test_and_gold(self.files)
        training, attributes, klass, test, gold = self.get_instances(self.training_path, self.test_path, self.gold_path)
        classifier = ALGORITHM_MAPPINGS[self.algorithm](training, attributes, klass)
        self.classify(classifier, test, gold)
        
    def __test_and_gold(self, files):
        if self.get_value('verify'):
            return [None, files]
        return [files, None]
        
    def classify(self, classifier, test, gold):
        if (test is not None):
            classifier.test(test)
        else:
            self.confusion_matrix = classifier.verify(gold)
            self.print_value('accuracy', 'Accuracy')
            self.print_value('error', 'Error')
            self.print_value('fscore', 'F-score')
            self.print_value('precision', 'Precision')
            self.print_value('recall', 'Recall')

    def print_value(self, attribute, str_repn):
        if (self.get_value(attribute)): 
            print str_repn + ': ' + getattr(self.confusion_matrix, attribute)().__str__()

if __name__ == "__main__":
    Classify().run(sys.argv[1:])
    
