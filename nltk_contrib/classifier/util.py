# Natural Language Toolkit utilities used in classifier module, should be migrated to main utilities later
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://www.nltk.org/>
# This software is distributed under GPL, for license information see LICENSE.TXT
import UserList, math

class StatList(UserList.UserList):
    def __init__(self, values=None):
        UserList.UserList.__init__(self, values)
        
    def mean(self):
        if len(self.data) == 0: return 0
        return float(sum([each for each in self.data])) / len(self.data)
    
    def variance(self):
        _mean = self.mean()
        if len(self.data) < 2: return 0
        return float(sum([pow((each - _mean), 2) for each in self.data])) / (len(self.data) - 1)
    
    def std_dev(self):
        return math.sqrt(self.variance())

def int_array_to_string(int_array):
    return ','.join([str(each) for each in int_array])
