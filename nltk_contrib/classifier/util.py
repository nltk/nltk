# Natural Language Toolkit utilities used in classifier module, should be migrated to main utilities later
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT
import UserList, math

class StatList(UserList.UserList):
    def __init__(self, values=None):
        UserList.UserList.__init__(self, values)
        
    def mean(self):
        sum = 0
        if len(self.data) == 0: return 0
        for each in self.data:
            sum += each
        return float(sum) / len(self.data)
    
    def variance(self):
        _mean = self.mean()
        if len(self.data) < 2: return 0
        sum = 0
        for each in self.data:
            sum += pow((each - _mean), 2)
        return float(sum) / (len(self.data) - 1)
    
    def std_dev(self):
        return math.sqrt(self.variance())
