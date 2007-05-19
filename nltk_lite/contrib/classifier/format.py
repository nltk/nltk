from nltk_lite.contrib.classifier import cfile, item, attribute as a, instance as ins, instances as inss
from nltk_lite.contrib.classifier.exceptions import systemerror as se, filenotfounderror as fnf

class FormatI:    
    def __init__(self, name):
        self.name = name
        
    def get_attributes(self, path):
        return AssertionError()
    
    def get_training_instances(self, path):
        return AssertionError()
    
    def get_test_instances(self, path):
        return AssertionError()
    
    def get_gold_instances(self, path):
        return AssertionError()
    
    def get_klass(self, path):
        return AssertionError()
    
    def write_training_to_file(self, training, path):
        return AssertionError()
    
    def write_test_to_file(self, training, path, including_classification=True):
        return AssertionError()

    def write_gold_to_file(self, instances, path, including_classification=True):
        return AssertionError()
        
    def write_metadata_to_file(self, attributes, klass, path):
        return AssertionError()
    
class C45Format(FormatI):
    DATA = 'data'
    TEST = 'test'
    GOLD = 'gold'
    NAMES = 'names'

    def __init__(self):
        FormatI.__init__(self, "c45")
        
    def get_attributes(self, path):
        lines = self.__get_lines(path, self.NAMES)
        index,attributes = 0, []
        for line in lines:
            nameitem = item.NameItem(line)      
            processed = nameitem.processed()
            if not len(processed) == 0 and nameitem.isAttribute():
                attributes.append(a.Attribute(self.get_name(processed), self.get_values(processed), index))
                index += 1
        return a.Attributes(attributes)
    
    def get_training_instances(self, path):
        lines = self.__get_lines(path, self.DATA)
        instances = []
        for line in lines:
            values = self.__get_comma_sep_values(line)
            if values is not None:
                instances.append(ins.TrainingInstance(values[:-1], values[-1]))
        return inss.TrainingInstances(instances)
    
    def get_test_instances(self, path):
        instances = []
        lines = self.__get_lines(path, self.TEST)
        for line in lines:
            values = self.__get_comma_sep_values(line)
            if values is not None:
                instances.append(ins.TestInstance(values))                
        return inss.TestInstances(instances)
    
    def get_gold_instances(self, path):
        instances = []
        lines = self.__get_lines(path, self.GOLD)
        for line in lines:
            values = self.__get_comma_sep_values(line)
            if values is not None:
                instances.append(ins.GoldInstance(values[:-1], values[-1]))
        return inss.GoldInstances(instances)
    
    def get_klass(self, path):
        lines = self.__get_lines(path, self.NAMES)
        values = item.NameItem(lines[0]).processed().split(',')
        return values
    
    def write_training_to_file(self, instances, path):
        return self.write_to_file(path, self.DATA, instances, lambda instance: instance.attr_values_as_str() + ',' + str(instance.klass_value))
        
    def write_test_to_file(self, instances, path, including_classification=True):
        if not including_classification:
            return self.write_to_file(path, self.TEST, instances, lambda instance: instance.attr_values_as_str())
        return self.write_to_file(path, self.TEST, instances, lambda instance: instance.attr_values_as_str() + ',' + str(instance.classified_klass))

    def write_gold_to_file(self, instances, path, including_classification=True):
        if not including_classification:
            return self.write_to_file(path, self.GOLD, instances, lambda instance: instance.attr_values_as_str() + ',' + str(instance.klass_value))
        return self.write_to_file(path, self.GOLD, instances, lambda instance: instance.attr_values_as_str() + ',' + str(instance.klass_value) + ',' + str(instance.classified_klass))
        
    def write_metadata_to_file(self, attributes, klass, path):
        new_file = self.create_file(path, self.NAMES)
        klass_values = ''
        for value in klass:
            klass_values += str(value) + ','
        lines = [klass_values[:-1] + '.']
        for attribute in attributes:
            lines.append(attribute.name + ':' + attribute.values_as_str() + '.')
        new_file.write(lines)
        return path + cfile.DOT + self.NAMES
        
    def write_to_file(self, path, extension, instances, method):
        new_file = self.create_file(path, extension)
        lines = []
        for instance in instances:
            lines.append(method(instance))
        new_file.write(lines)
        return path + cfile.DOT + extension
    
    def create_file(self, path, extension):
        new_file = cfile.File(path, extension)
        new_file.create(True)
        return new_file

    def __get_comma_sep_values(self, line):
        _line = item.Item(line).stripNewLineAndWhitespace()
        if not len(_line) == 0:
            return _line.split(',')
        return None
    
    def __get_lines(self, path, ext):
        if path is None:
            raise se.SystemError('Cannot open file. File name not specified.')
        return cfile.File(path, ext).for_each_line(lambda line: line)
    
    def get_name(self, line):
        return line[:self.__pos_of_colon(line)]
            
    def get_values(self, line):
        return line[self.__pos_of_colon(line) + 1:].split(',')
        
    def __pos_of_colon(self, line):
        return line.find(':')

C45_FORMAT = C45Format()