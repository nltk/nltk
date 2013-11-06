u"""Module to find keywords using the Montemurro and Zanette algorithm.
Created by Dr Peter J. Bleackley """
from math import log,exp,lgamma
import re
import codecs
import urllib
import sys



def LogCombinations(x,y):
    u"""Calculates the logarithm of a binomial coefficient.
    This avoids overflows. Implemented with gamma functions for efficiency"""
    result=lgamma(x+1)
    result-=lgamma(y+1)
    result-=lgamma(x-y+1)
    return result

class EntropyCalculator:
    u"""Class that contains data and methods for calculating the entropy of
        words in a text"""
    StripXML=re.compile(u'<[^>]*>')
    SplitWords=re.compile(u"[^A-Za-z0-9']+")
    SplitSentences=re.compile(u'[.!?]')
    SplitXML=re.compile(u'</p>')
    StripTimes=re.compile(u'\d\d:\d\d:\d\d\.\d\d\d')
    def __init__(self,P):
        u"""Creates an EntropyCalculator that uses P blocks to analyse the text"""
        self.Parts=P
        self.Nwords=0
        self.text=[]
        self.WordsPerPart=0
        self.unique=None
        self.RawText=u''
        self.CleanText=u''
        self.TotalEntropy=0.0
        self.RankedWords=[]
        self.Sentences=[]
        self.RankedSentences=[]
        self.XML=[]
        self.search=[]

    def MarginalProb(self,m,n):
        u"""Calculates the Marginal Probability in the Analytic Entropy calculation"""
        result=LogCombinations(n,m)
        result+=LogCombinations(self.Nwords-n,self.WordsPerPart-m)
        result-=LogCombinations(self.Nwords,self.WordsPerPart)
        prob=exp(result)
        return prob

    def AnalyticEntropy(self,n):
        u"""Calculates the Analytic entropy of a word that occurs randomly n times
        in the text"""
        result=0.0
        Upperbound=min((n,self.WordsPerPart))
        for m in range(1,Upperbound+1):
            x=float(m)/n
            result-=self.MarginalProb(m,n)*x*log(x,2)
        result*=self.Parts
        return result

    def Entropy(self,word):
        u"""Calculates the entropy of a word"""
        n=self.text.count(word)
        H=0.0
        for i in range(self.Parts):
            nj=float(self.text[i*self.WordsPerPart:(i+1)*self.WordsPerPart].count(word))
            x=nj/n
            if x>0:
                H-=x*log(x,2)
        result=self.AnalyticEntropy(n)-H
        return (result,n*result/self.Nwords)

    def SetText(self,data):
        u"""Loads the text to be analysed"""
        self.RawText=u''
        if type(data).__name__ == 'str' or type(data).__name__ == 'unicode':
            self.RawText=re.sub(u'\xa3','&pound;',data)
        else:
            for line in data:
                self.RawText+=re.sub(u'\xa3','&pound;',line)
        self.CleanText=EntropyCalculator.StripTimes.sub('',EntropyCalculator.StripXML.sub(u'',self.RawText))
        self.text=EntropyCalculator.SplitWords.split(self.CleanText)
        self.Sentences=EntropyCalculator.SplitSentences.split(self.CleanText)
        for i in range(len(self.Sentences)):
            if self.Sentences[i]==' ':
                self.Sentences[i]+='.'
            else:
                place=self.CleanText.find(self.Sentences[i])+len(self.Sentences[i])
                if place<len(self.CleanText):
                    self.Sentences[i]+=self.CleanText[place]+' '
        self.XML=EntropyCalculator.SplitXML.split(self.RawText)
        for i in range(len(self.XML)):
            self.XML[i]+='</p>'
        self.search=[EntropyCalculator.StripTimes.sub('',EntropyCalculator.StripXML.sub('',line)) for line in self.XML]
        while self.text[-1]==u'':
            self.text.pop()
        self.Nwords=len(self.text)
        self.WordsPerPart=self.Nwords/self.Parts
        if self.Nwords%self.Parts!=0:
            self.WordsPerPart+=1
        self.unique=set(self.text)
                        

    def SetWordsPerPart(self,BlockSize):
        u"""Changes the block size"""
        self.WordsPerPart=BlockSize
        self.Parts=self.Nwords/self.WordsPerPart
        if self.Nwords%self.WordsPerPart>0:
            self.Parts+=1

    def SetParts(self,P):
        u"""Changes the number of blocks"""
        self.Parts=P
        self.WordsPerPart=self.Nwords/self.Parts
        if self.Nwords%self.Parts!=0:
            self.WordsPerPart+=1

    def AnalyseText(self):
        u"""Calculates the entropy for each unique word in the text"""
        self.RankedWords=[(self.Entropy(word),word) for word in self.unique]
        self.RankedWords.sort()
        self.RankedWords.reverse()
        self.TotalEntropy=sum([item[0][1] for item in self.RankedWords])

    def AnalyseSentences(self):
        EntropyByWord=dict([(item[1],item[0][0]) for item in self.RankedWords])
        self.RankedSentences=[]
        for sentence in self.Sentences:
            words=EntropyCalculator.SplitWords.split(sentence)
            nwords=len(words)
            total=0.0
            for word in words:
                if word in EntropyByWord:
                    total+=EntropyByWord[word]
            self.RankedSentences.append((total,sentence))
        self.RankedSentences.sort()
        self.RankedSentences.reverse()

    def FilterWords(self,FilterType=None,Threshold=0.0):
        u"""Selects a subset of the words according to a criterion"""
        result=[]
        if FilterType==u'Entropy':
            result = [item for item in self.RankedWords if item[0][0]>=Threshold]
        elif FilterType==u'Number':
            result=self.RankedWords[:Threshold]
        elif FilterType==u'Percentile':
            N=int((self.Nwords*Threshold/100)+0.5)
            result=RankedWords[:N]
        elif FilterType==u'Cumulative':
            RunningTotal=0.0
            i=0
            while RunningTotal<Threshold:
                RunningTotal+=self.RankedWords[i][0][1]
                if RunningTotal<Threshold:
                    result.append(self.RankedWords[i])
                    i+=1
        elif FilterType==u'ProportionOfEntropy':
            x=Threshold*self.TotalEntropy
            result=self.FilterWords(u'Cumulative',x)
        else:
            result=self.RankedWords
        return result

    def OutputWords(self,ofile,FilterType=None,Threshold=0.0):
        u"""Outputs a set of selected keywords and their scores to a file"""
        Keywords=self.FilterWords(FilterType,Threshold)
        ofile.write(u'Word,Entropy,Proportion of document entropy\n')
        for ((entropy,contrib),word) in Keywords:
            ofile.write(word+u','+unicode(entropy)+','+unicode(contrib)+u'\n')

    def KeywordDictionary(self):
        u"""Outputs a dictionary of keywords and their entropies"""
        self.AnalyseText()
        return dict([(word,Entropy[0]) for (Entropy,word) in self.RankedWords if Entropy[0]>0.0])
        
