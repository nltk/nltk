from itertools import groupby
from operator import itemgetter

from inputformat import KeyValueInput
from outputcollector import LineOutput

class ReducerBase:
    """
    Base class for every reduce tasks

    Your reduce class should extend this base class 
    and override the reduce function 
    """

    def __init__(self):
        """
        set the default input formatter and output collector
        """
        self.inputformat = KeyValueInput
        self.outputcollector = LineOutput

    def set_inputformat(self, format):
        """
        set the input formatter to parse the input

        @param format: the input formatter to parse the input
        """

        self.inputformat = format

    def set_outputcollector(self, collector):
        """ 
        set the output collector for reduce task

        @param collector: the ouput collector to collect output
        """

        self.outputcollector = collector

    def group_data(self, data):
        """ 
        collect data that have the same key into a group
        assume the data is sorted 
        """

        for key, group in  groupby(data, itemgetter(0)):
            values = map(itemgetter(1), group)
            yield key, values

    def reduce(self, key, values):
        """
        do reduce operation for each (key, [value,...]) pair

        It is the only function needs to and 
        have to be implemented in your own class

        It is a callback function that is called in C{call_reduce()} function
        you should not call this function directly

        the actual content of key and values is determined by the inputformat

        @param key: key
        @type key: C{string}
        @param values: a list of values correspond to the key
        @type values: C{list}
        """

        raise NotImplementedError('reduce() is not implemented in this class')

    def call_reduce(self):
        """
        driver function for reduce task, you should call this method 
        instead of the reduce method in main function 
        """

        data = self.inputformat.read_line()
        for key, values in self.group_data(data):
            self.reduce(key, values)
