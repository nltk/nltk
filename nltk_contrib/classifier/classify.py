from nltk_contrib.classifier import commandline as cl
from nltk_contrib.classifier import oner, zeror, decisiontree, format, naivebayes, knn
import sys

a_help = "Selects the classification algorithm                  " \
        + "Options: 0R for Zero R, 1R for One R, DT for Decision" \
        + " Trees, NB for Naive Bayes, IB1 for Instance Based   " \
        + " Learner with one nearest neighbour.                " \
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

w_help = "Writes resulting gold file with a modified base name  " \
         "Is always true for test files.                        "
         
c_help = "Classify by using a cross validation dataset with the " \
         "specified fold.                                       "
         
o_help = "Classifier options                                    " \
         " Decision Tree: IG - Max Information Gain             " \
         "                GR - Max Gain Ratio                   "

ZERO_R = '0R'
ONE_R = '1R'
DECISION_TREE = 'DT'
NAIVE_BAYES = 'NB'
IB1 = 'IB1'

ALGORITHM_MAPPINGS = {ZERO_R:zeror.ZeroR, ONE_R:oner.OneR, DECISION_TREE:decisiontree.DecisionTree, NAIVE_BAYES:naivebayes.NaiveBayes, IB1:knn.IB1}
ALL_ALGORITHMS = ALGORITHM_MAPPINGS.keys()

VERIFY='verify'
ACCURACY='accuracy'
ERROR='error'
F_SCORE='fscore'
PRECISION='precision'
RECALL='recall'
WRITE='write'
CROSS_VALIDATION='cross_validation'

class Classify(cl.CommandLineInterface):    
    def __init__(self):
        cl.CommandLineInterface.__init__(self, ALGORITHM_MAPPINGS.keys(), ONE_R, a_help, f_help, t_help, T_help, g_help, o_help)
        self.add_option("-v", "--verify", dest=VERIFY, action="store_true", default=False, help=v_help)
        self.add_option("-A", "--accuracy", dest=ACCURACY, action="store_false", default=True, help=A_help)
        self.add_option("-e", "--error", dest=ERROR, action="store_true", default=False, help=e_help)
        self.add_option("-F", "--f-score", dest=F_SCORE, action="store_false", default=True, help=F_help)
        self.add_option("-p", "--precision", dest=PRECISION, action="store_true", default=False, help=p_help)
        self.add_option("-r", "--recall", dest=RECALL, action="store_true", default=False, help=r_help)
        self.add_option("-w", "--write", dest=WRITE, action="store_true", default=False, help=r_help)
        self.add_option("-c", "--cross-validation-fold", dest=CROSS_VALIDATION, type="string", help=c_help)
        
    def execute(self):
        cl.CommandLineInterface.execute(self)
        self.validate_basic_arguments_are_present()
        self.validate_files_arg_is_exclusive()
        cross_validation_fold = self.get_value(CROSS_VALIDATION)
        if cross_validation_fold is None and self.files is None and self.test_path is None and self.gold_path is None:
            self.required_arguments_not_present_error()
        if self.test_path is not None and self.gold_path is not None:
            self.error('Invalid arguments. Test and gold files are mutually exclusive.')
        if self.files is None and self.test_path is not None and self.get_value(VERIFY):
            self.error('Invalid arguments. Cannot verify classification for test data.')
        
        file_strategy = get_file_strategy(self.files, self.training_path, self.test_path, self.gold_path, self.get_value(VERIFY))
        self.training_path, self.test_path, self.gold_path = file_strategy.values()
        
        training, attributes, klass, test, gold = self.get_instances(self.training_path, self.test_path, self.gold_path, cross_validation_fold is not None)
        classifier = ALGORITHM_MAPPINGS[self.algorithm](training, attributes, klass)
        classification_strategy = self.get_classification_strategy(classifier, test, gold, training, cross_validation_fold, attributes, klass)
        classification_strategy.train()
        self.log_common_params('Classification')
        classification_strategy.classify()
        classification_strategy.print_results(self.log, self.get_value(ACCURACY), self.get_value(ERROR), self.get_value(F_SCORE), self.get_value(PRECISION), self.get_value(RECALL))
        classification_strategy.write(self.log, self.get_value(WRITE), self.data_format, '-c_' + self.algorithm)

    #ugh!! ugly!!!.. need to find a better way.. there are way too many params here! till then.. this stays
    def get_classification_strategy(self, classifier, test, gold, training, cross_validation_fold, attributes, klass):
        if self.algorithm == DECISION_TREE: 
            classifier_options = DecisionTreeOptions(self.options)
        else:
            classifier_options = NoOptions()
        
        if cross_validation_fold is not None:
            return CrossValidationStrategy(self.algorithm, attributes, klass, training, cross_validation_fold, self.training_path, classifier_options)
        if test is not None:
            return TestStrategy(classifier, test, self.test_path, classifier_options)
        return VerifyStrategy(classifier, gold, self.gold_path, classifier_options)

def get_file_strategy(files, training, test, gold, verify):
    if files is not None:
        return CommonBaseNameStrategy(files, verify)
    return ExplicitNamesStrategy(training, test, gold)    

class CrossValidationStrategy:
    def __init__(self, algorithm, attributes, klass, training, fold, training_path, classifier_options):
        self.algorithm = algorithm
        self.training = training
        self.fold = fold
        self.confusion_matrices = []
        self.gold_instances = []
        self.klass = klass
        self.attributes = attributes
        self.training_path = training_path
        self.classifier_options = classifier_options

    def classify(self):
        datasets = self.training.cross_validation_datasets(self.fold)
        for each in datasets:
            classifier = ALGORITHM_MAPPINGS[self.algorithm](each[0], self.attributes, self.klass)
            self.classifier_options.set_options(classifier)
            classifier.train()
            self.confusion_matrices.append(classifier.verify(each[1]))
            self.gold_instances.append(classifier.gold_instances)
        
    def print_results(self, log, accuracy, error, fscore, precision, recall):
        self.__print_value(log, accuracy, ACCURACY, 'Accuracy')
        self.__print_value(log, error, ERROR, 'Error')
        self.__print_value(log, fscore, F_SCORE, 'F-score')
        self.__print_value(log, precision, PRECISION, 'Precision')
        self.__print_value(log, recall, RECALL, 'Recall')
        
    def __print_value(self, log, is_true, attribute, str_repn):
        if is_true:
            total = 0
            for each in self.confusion_matrices:
                total += getattr(each, attribute)()
            print >>log, str_repn + ': ' + str(float(total)/len(self.confusion_matrices))
        
    def write(self, log, should_write, data_format, suffix):
        if should_write:
            for index in range(len(self.gold_instances)):
                new_path = self.training_path + str(index + 1) + suffix
                data_format.write_gold(self.gold_instances[index], new_path)
                print >>log, 'Gold classification written to ' + new_path + ' file.'
    
    def train(self):
        #do Nothing
        pass

class TestStrategy:
    def __init__(self, classifier, test, test_path, classifier_options):
        self.classifier = classifier
        self.test = test
        self.test_path = test_path
        classifier_options.set_options(self.classifier)
        
    def classify(self):
        self.classifier.test(self.test)
        
    def print_results(self, log, accuracy, error, fscore, precision, recall):
        """
        Nothing to print in tests
        """
        
    def write(self, log, should_write, data_format, suffix):
        """
        Will always write in the case of test files
        """
        data_format.write_test(self.test, self.test_path + suffix)
        print >>log, 'Test classification written to ' + self.test_path + suffix + ' file.'
        
    def train(self):
        self.classifier.train()
        
class VerifyStrategy:
    def __init__(self, classifier, gold, gold_path, classifier_options):
        self.classifier = classifier
        self.gold = gold
        self.gold_path = gold_path
        self.confusion_matrix = None
        classifier_options.set_options(self.classifier)
        
    def classify(self):
        self.confusion_matrix = self.classifier.verify(self.gold)
        
    def print_results(self, log, accuracy, error, fscore, precision, recall):
        self.__print_value(log, accuracy, ACCURACY, 'Accuracy')
        self.__print_value(log, error, ERROR, 'Error')
        self.__print_value(log, fscore, F_SCORE, 'F-score')
        self.__print_value(log, precision, PRECISION, 'Precision')
        self.__print_value(log, recall, RECALL, 'Recall')
        
    def __print_value(self, log, is_true, attribute, str_repn):
        if is_true: 
            print >>log, str_repn + ': ' + getattr(self.confusion_matrix, attribute)().__str__()
            
    def write(self, log, should_write, data_format, suffix):
        if should_write:
            data_format.write_gold(self.gold, self.gold_path + suffix)
            print >>log, 'Gold classification written to ' + self.gold_path + suffix + ' file.'
            
    def train(self):
        self.classifier.train()
    
class CommonBaseNameStrategy:
    def __init__(self, files, verify):
        self.files = files
        self.verify = verify
        
    def values(self):
        return [self.files] + self.__test_or_gold()
    
    def __test_or_gold(self):
        if self.verify:
            return [None, self.files]
        return [self.files, None]

class ExplicitNamesStrategy:
    def __init__(self, training, test, gold):
        self.training = training
        self.test = test
        self.gold = gold
        
    def values(self):
        return [self.training, self.test, self.gold]
                
class DecisionTreeOptions:
    VALID = {'IG': 'maximum_information_gain', 'GR': 'maximum_gain_ratio'}
    
    def __init__(self, options):
        self.options = options
        
    def valid(self):
        if self.options not in self.VALID:
            return False
        return True
        
    def set_options(self, classifier):
        if self.valid():
            classifier.set_options(self.VALID[self.options])
        
class NoOptions:
        
    def set_options(self, classifier):
        #do Nothing
        pass

if __name__ == "__main__":
    Classify().run(sys.argv[1:])
