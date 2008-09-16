from sys import stdin

class TextLineInput:
    """ 
    treat the input as lines of text
    
    emit None as key and text line as value
    """

    @staticmethod
    def read_line(file=stdin):
        """
        read and parse input file, for each line, yield a (None, line) pair

        @return: yield a (None, line) pair
        @param file: input file, default to stdin
        """
        for line in file:
        # split the line into words, trailing space truncated
            yield None, line.strip()

class KeyValueInput:
    """ 
    treat the input as lines of (key, value) pair splited by separator
    
    emit text before separator as key and the rest as value
    """

    @staticmethod
    def read_line(file=stdin, separator='\t'):
        """
        read and parse input file, for each line, 
        separate the line and yield a (key, value) pair

        @return: yield a (key, value) pair
        @param file: input file, default to stdin
        @param separator: specify the character to 
        separate a line of input, default to '\t'
        """
        for line in file:
            yield line.rstrip().split(separator, 1)
