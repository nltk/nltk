from nltk_contrib.classifier import cfile, item, attribute as a, instance as ins, instances as inss
from nltk_contrib.classifier.exceptions import systemerror as se, filenotfounderror as fnf

class FormatI:    
    def __init__(self, name):
        self.name = name
        
    def metadata(self, file_path):
        """
        Returns a tuple containing attributes and class instances
        """
        return AssertionError()
    
    def training(self, file_path):
        """
        Returns training instances
        """
        return AssertionError()
    
    def test(self, file_path):
        """
        Returns test instances
        """
        return AssertionError()
    
    def gold(self, file_path):
        """
        Returns gold instances
        """
        return AssertionError()
        
    def write_training(self, training, file_path):
        """
        Writes training instances to file system
        """
        return AssertionError()
    
    def write_test(self, test, file_path, including_classification=True):
        """
        Writes test instances to file system
        """
        return AssertionError()

    def write_gold(self, gold, file_path, including_classification=True):
        """
        Writes gold instances to file system
        """
        return AssertionError()
        
    def write_metadata(self, attributes, klass, file_path):
        """
        Writes attributes and class instances to file system
        """
        return AssertionError()
    
class C45Format(FormatI):
    DATA = 'data'
    TEST = 'test'
    GOLD = 'gold'
    NAMES = 'names'

    def __init__(self):
        FormatI.__init__(self, "c45")
        
    def metadata(self, file_path):
        lines = self.__get_lines(file_path, self.NAMES)
        klass_values = item.NameItem(lines[0]).processed().split(',')
        index,attributes = 0, []
        for line in lines:
            nameitem = item.NameItem(line)      
            processed = nameitem.processed()
            if not len(processed) == 0 and nameitem.isAttribute():
                attributes.append(a.Attribute(self.get_name(processed), self.get_values(processed), index))
                index += 1
        return (a.Attributes(attributes), klass_values)
    
    def training(self, file_path):
        all_values = self.__get_all_values(file_path, self.DATA)
        return inss.TrainingInstances([ins.TrainingInstance(values[:-1], values[-1]) for values in all_values if values is not None])
    
    def test(self, file_path):
        all_values = self.__get_all_values(file_path, self.TEST)
        return inss.TestInstances([ins.TestInstance(values) for values in all_values if values is not None])
    
    def gold(self, file_path):
        all_values = self.__get_all_values(file_path, self.GOLD)
        return inss.GoldInstances([ins.GoldInstance(values[:-1], values[-1]) for values in all_values if values is not None])
    
    def __get_all_values(self, file_path, ext):
        lines = self.__get_lines(file_path, ext)
        return [self.__get_comma_sep_values(line) for line in lines]        
    
    def write_training(self, instances, file_path):
        return self.write_to_file(file_path, self.DATA, instances, lambda instance: instance.str_attrs() + ',' + str(instance.klass_value))
        
    def write_test(self, instances, file_path, including_classification=True):
        if not including_classification:
            return self.write_to_file(file_path, self.TEST, instances, lambda instance: instance.str_attrs())
        return self.write_to_file(file_path, self.TEST, instances, lambda instance: instance.str_attrs() + ',' + str(instance.classified_klass))

    def write_gold(self, instances, file_path, including_classification=True):
        if not including_classification:
            return self.write_to_file(file_path, self.GOLD, instances, lambda instance: instance.str_attrs() + ',' + str(instance.klass_value))
        return self.write_to_file(file_path, self.GOLD, instances, lambda instance: instance.str_attrs() + ',' + str(instance.klass_value) + ',' + str(instance.classified_klass))
        
    def write_metadata(self, attributes, klass, file_path):
        new_file = self.create_file(file_path, self.NAMES)
        lines = [','.join([str(value) for value in klass]) + '.']
        for attribute in attributes:
            lines.append(attribute.name + ':' + attribute.values_as_str() + '.')
        new_file.write(lines)
        return file_path + cfile.DOT + self.NAMES
        
    def write_to_file(self, file_path, extension, instances, method):
        new_file = self.create_file(file_path, extension)
        new_file.write([method(instance) for instance in instances])
        return file_path + cfile.DOT + extension
    
    def create_file(self, file_path, extension):
        new_file = cfile.File(file_path, extension)
        new_file.create(True)
        return new_file

    def __get_comma_sep_values(self, line):
        _line = item.Item(line).stripNewLineAndWhitespace()
        if not len(_line) == 0:
            return _line.split(',')
        return None
    
    def __get_lines(self, file_path, ext):
        if file_path is None:
            raise se.SystemError('Cannot open file. File name not specified.')
        return cfile.File(file_path, ext).for_each_line(lambda line: line)
    
    def get_name(self, line):
        return line[:self.__pos_of_colon(line)]
            
    def get_values(self, line):
        return line[self.__pos_of_colon(line) + 1:].split(',')
        
    def __pos_of_colon(self, line):
        return line.find(':')

c45 = C45Format()
