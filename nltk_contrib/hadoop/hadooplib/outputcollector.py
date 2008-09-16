class LineOutput:
    """ 
    default output class, output key and value 
    as (key, value) pair separated by separator
    """

    @staticmethod
    def collect(key, value, separator = '\t'):
        """
        collect the key and value, output them to
        a line separated by a separator character

        @param key: key part in (key, value) pair
        @type key: C{string}
        @param value: value part in (key, value) pair
        @type value: C{string}
        @param separator: character to separate the key and value
        @type separator: C{string}
        """
        
        keystr = str(key)
        valuestr = str(value)
        print '%s%s%s' % (keystr, separator, valuestr)
