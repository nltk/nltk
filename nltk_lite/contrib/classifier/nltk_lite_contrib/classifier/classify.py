from optparse import OptionParser
from nltk_lite_contrib.classifier import oner, zeror
import sys

class Classify(OptionParser):    
    def __init__(self):
        OptionParser.__init__(self)
        self.add_option("-a", "--algorithm", dest="algorithm", type="choice", \
                        choices=["0R", "1R"], default="0R", help="Option to choose the classification algorithm\n" \
                        + "\t 0R for Zero R\n\t 1R for One R" \
                        + "default: Zero R")
        self.add_option("-f", "--files", dest="files", type="string")
        self.add_option("-v", "--verify", dest="verify", action="store_true", default=False)
        self.add_option("-t", "--training-file", dest="training", type="string")
        self.add_option("-T", "--test-file", dest="test", type="string")
        self.add_option("-g", "--gold-file", dest="gold", type="string")
        self.add_option("-A", "--accuracy", dest="accuracy", action="store_false", default=True)
        self.add_option("-e", "--error", dest="error", action="store_true", default=False)
        self.add_option("-F", "--f-score", dest="fscore", action="store_false", default=True)
        self.add_option("-p", "--precision", dest="precision", action="store_true", default=False)
        self.add_option("-r", "--recall", dest="recall", action="store_true", default=False)
        self.__klasses = {'0R':zeror.ZeroR, '1R':oner.OneR}
        
    def parse(self, args):
        self.parse_args(args, None)
        
    def execute(self):
        algorithm = self.__get_value('algorithm')
        files = self.__get_value('files')
        training = self.__get_value('training')
        test = self.__get_value('test')
        gold = self.__get_value('gold')
        
        if algorithm is None or files is None and (training is None or (test is None and gold is None)): 
            self.error("Invalid attributes")
        if files is not None and (training is not None or test is not None or gold is not None):
            self.error("Invalid attributes")
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

if __name__ == "__main__":
    classify = Classify()
    classify.parse(sys.argv[1:])
    classify.execute()
