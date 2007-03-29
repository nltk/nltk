# Natural Language Toolkit - Confusion Matrix
#  Updates itself with each classification result and constructs a matrix 
#  Using the matrix it is capable of calculating several performance figures
#
# Author: Sumukh Ghodke <sumukh dot ghodke at gmail dot com>
#
# URL: <http://nltk.sf.net>
# This software is distributed under GPL, for license information see LICENSE.TXT

from nltk_lite_contrib.classifier.exceptions import systemerror as se
class ConfusionMatrix:
    def __init__(self, klass):
        self.index, self.matrix = {}, []
        self.__num_class_vals = len(klass.values)
        for i in range(self.__num_class_vals): 
            self.index[klass.values[i]] = i
            self.matrix.append([0] * self.__num_class_vals)
        
    def count(self, actual, predicted):
        self.matrix[self.index[actual]][self.index[predicted]] += 1
        
    def accuracy(self):
        return self.__div(self.tp() + self.tn(), self.tp() + self.fp() + self.fn() + self.tn())
        
    def error(self):
        return 1 - self.accuracy()
    
    def tpr(self, index = 0):
        return self.__div(self.tp(index), self.tp(index) + self.fn(index))
    sensitivity = tpr
    
    def tnr(self, index = 0):
        return self.__div(self.tn(index), self.fp(index) + self.tn(index))
    specificity = tnr
    
    def fpr(self, index = 0):
        return self.__div(self.fp(index), self.fp(index) + self.tn(index))
    
    def precision(self, index = 0):
        return self.__div(self.tp(index), self.tp(index) + self.fp(index))
    
    def recall(self, index = 0):
        return self.__div(self.tp(index), self.tp(index) + self.fn(index))
    
    def fscore(self, beta = 1, index = 0):
        p, r = self.precision(index), self.recall(index)
        return (1 + beta * beta) * self.__div(p * r, r + beta * beta * p)
    
    def __div(self, num, den):
        if num == 0: return 0;
        if den == 0: raise se.SystemError('Divide by Zero Error')
        return float(num)/ den
    
    def tp(self, index = 0):
        return self.matrix[index][index]
        
    def tn(self, index = 0):
        sum = 0
        for i in range(self.__num_class_vals):
            if i == index: continue
            for j in range(self.__num_class_vals):
                if j == index: continue
                sum += self.matrix[i][j]
        return sum
        
    def fp(self, index = 0):
        sum = 0
        for i in range(self.__num_class_vals):
            if i == index: continue
            sum += self.matrix[i][index]
        return sum
            
    def fn(self, index = 0):
        sum = 0
        for i in range(self.__num_class_vals):
            if i == index: continue
            sum += self.matrix[index][i]
        return sum