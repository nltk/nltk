from inputformat import TextLineInput
from outputcollector import LineOutput


class MapperBase:
    """ 
    Base class for every map tasks
    
    Your map class should extend this base class 
    and override the map function
    """

    def __init__(self):
        """
        set the default input formatter and output collector
        """
        self.inputformat = TextLineInput
        self.outputcollector = LineOutput

    def set_inputformat(self, format):
        """
        set the input formatter for map task

        @param format: the input formatter to parse the input
        """

        self.inputformat = format
    
    def set_outputcollector(self, collector):
        """
        set the output collector for map task 

        @param collector: the ouput collector to collect output
        """

        self.outputcollector = collector

    def map(self, key, value):
        """
        do map operation on each (key, value) pair

        It is the only function needs to and 
        have to be implemented in your own class

        It is a callback function that is called in C{call_map()} function
        you should not call this function directly

        the actual content of key and value is determined by the inputformat

        @param key: key part in (key, value) pair
        @type key: C{string}
        @param value: value part in (key, value) pair
        @type value: C{string}
        """

        raise NotImplementedError('map() is not implemented in this class')

    def call_map(self):
        """ 
        driver function for map task, you should call this method 
        instead of the map method in main function 
        """

        data = self.inputformat.read_line()
        for key, value in data:
            self.map(key, value)
