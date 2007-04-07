from optparse import OptionParser
from nltk_lite.contrib.classifier import oner, zeror, decisiontree
import sys

class Classify(OptionParser):    
    def __init__(self):

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
        
        self.__klasses = {'0R':zeror.ZeroR, '1R':oner.OneR, 'DT':decisiontree.DecisionTree}
        OptionParser.__init__(self)
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
        
    def parse(self, args):
        self.parse_args(args, None)
        
    def execute(self):
        algorithm = self.__get_value('algorithm')
        files = self.__get_value('files')
        training = self.__get_value('training')
        test = self.__get_value('test')
        gold = self.__get_value('gold')
        
        if algorithm is None or files is None and (training is None or (test is None and gold is None)): 
            self.error("Invalid arguments. One or more required arguments are not present.")
        if files is not None and (training is not None or test is not None or gold is not None):
            self.error("Invalid arguments. The files parameter should not be followed by training, test or gold parameters.")
        if test is not None and gold is not None:
            self.error('Invalid arguments. Test and gold files are mutually exclusive.')
        if files is None and test is not None and self.__get_value('verify'):
            self.error('Invalid arguments. Cannot verify classification for test data.')
        if files is not None:
            training = files
            test, gold = self.__test_and_gold(files)
        classifier = self.__klasses[algorithm](training)
        self.classify(classifier, test, gold)
        
    def __test_and_gold(self, files):
        if self.__get_value('verify'):
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
        if (self.__get_value(attribute)): 
            print str_repn + ': ' + getattr(self.confusion_matrix, attribute)().__str__()

    def __get_value(self, name):
        return self.values.ensure_value(name, None)
    
    def run(self, args):
        self.parse(args)
        self.execute()

if __name__ == "__main__":
    Classify().run(sys.argv[1:])
    
