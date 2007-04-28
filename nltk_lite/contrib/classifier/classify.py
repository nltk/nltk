from nltk_lite.contrib.classifier.__init__ import CommandLineInterface
from nltk_lite.contrib.classifier import oner, zeror, decisiontree, format
import sys

class Classify(CommandLineInterface):    
    def __init__(self):
        CommandLineInterface.__init__(self)
        a_help = "Selects the classification algorithm                  " \
                + "Options: 0R for Zero R, 1R for One R, DT for Decision" \
                + " Trees.                                              " \
                + "Default: 0R."
        f_help = "Specifies the common name of test, training or gold files." \
                + "By default it searches for training and test files, look at the verify option for more details."
        v_help = "Used in conjunction with the files option to verify  "\
                + "the efficiency with a gold file instead of testing "\
                + "the classifier on a test file. Setting this option "\
                + "will mean that a gold file is present with the common" \
                + " name.                                               "\
                + "Options: True/False or yes/no."
        t_help = "When the files option is not used this option is used "\
                + "to specify the path to the training file without the "\
                + "extension."
        T_help = "When the files option is not used this option is used "\
                + "to specify the path to the test file without the "\
                + "extension."
        g_help = "When the files option is not used this option is used "\
                + "to specify the path to the gold file without the "\
                + "extension."
        A_help = "Used to disable calculation of Accuracy.              "\
                + "Options: True/False or yes/no."
        e_help = "Used to enable calculation of Error rate.             "\
                + "Options: True/False or yes/no."
        F_help = "Used to disable calculation of F-score.               "\
                + "Options: True/False or yes/no."
        p_help = "Used to enable calculation of Precision.              "\
                + "Options: True/False or yes/no."
        r_help = "Used to enable calculation of Recall.                 "\
                + "Options: True/False or yes/no."
        r_help = "Used to enable calculation of Recall.                 "\
                + "Options: True/False or yes/no."
        D_help = "Used to specify the data format                       " \
                + "Options: C45 for C4.5 format (default)               "
        
        self.__klasses = {'0R':zeror.ZeroR, '1R':oner.OneR, 'DT':decisiontree.DecisionTree}
        self.__data_formats = {'C45': format.C45_FORMAT}
        self.add_option("-a", "--algorithm", dest="algorithm", type="choice", \
                        choices=self.__klasses.keys(), default="0R", help= a_help)
        self.add_option("-f", "--files", dest="files", type="string", help=f_help)
        self.add_option("-v", "--verify", dest="verify", action="store_true", default=False, help=v_help)
        self.add_option("-t", "--training-file", dest="training", type="string", help=t_help)
        self.add_option("-T", "--test-file", dest="test", type="string", help=T_help)
        self.add_option("-g", "--gold-file", dest="gold", type="string", help=g_help)
        self.add_option("-A", "--accuracy", dest="accuracy", action="store_false", default=True, help=A_help)
        self.add_option("-e", "--error", dest="error", action="store_true", default=False, help=e_help)
        self.add_option("-F", "--f-score", dest="fscore", action="store_false", default=True, help=F_help)
        self.add_option("-p", "--precision", dest="precision", action="store_true", default=False, help=p_help)
        self.add_option("-r", "--recall", dest="recall", action="store_true", default=False, help=r_help)
        self.add_option("-D", "--data-format", dest="data_format", type="choice", choices=self.__data_formats.keys(), \
                        default="C45", help=D_help)
        
    def execute(self):
        algorithm = self.get_value('algorithm')
        files = self.get_value('files')
        training_path = self.get_value('training')
        test_path = self.get_value('test')
        gold_path = self.get_value('gold')
        test = gold = None
        if algorithm is None or files is None and (training_path is None or (test_path is None and gold_path is None)): 
            self.error("Invalid arguments. One or more required arguments are not present.")
        if files is not None and (training_path is not None or test_path is not None or gold_path is not None):
            self.error("Invalid arguments. The files parameter should not be followed by training, test or gold parameters.")
        if test_path is not None and gold_path is not None:
            self.error('Invalid arguments. Test and gold files are mutually exclusive.')
        if files is None and test_path is not None and self.get_value('verify'):
            self.error('Invalid arguments. Cannot verify classification for test data.')
        data_format = self.__data_formats[self.get_value("data_format")]
        if files is not None:
            training_path = files
            test_path, gold_path = self.__test_and_gold(files)
        training = data_format.get_training_instances(training_path)
        attributes = data_format.get_attributes(training_path)
        klass = data_format.get_klass(training_path)
        if test_path is not None: test = data_format.get_test_instances(test_path)
        if gold_path is not None: gold = data_format.get_gold_instances(gold_path)
        classifier = self.__klasses[algorithm](training, attributes, klass, format)
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
    
