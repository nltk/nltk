# -*- coding: utf-8 -*- 
#
# Natural Language Toolkit: The ISRI Arabic Stemmer
#
# Copyright (C) 2001-2011 NLTK Proejct
# Algorithm: Kazem Taghva, Rania Elkhoury, and Jeffrey Coombs (2005)
# Author: Hosam Algasaier <hosam_hme@yahoo.com>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""ISRI Arabic Stemmer

The algorithm for this stemmer is described in:

Taghva, K., Elkoury, R., and Coombs, J. 2005. Arabic Stemming without a root dictionary.
Information Science Research Institute. University of Nevada, Las Vegas, USA.

The Information Science Research Institute’s (ISRI) Arabic stemmer shares many features
with the Khoja stemmer. However, the main difference is that ISRI stemmer does not use root
dictionary. Also, if a root is not found, ISRI stemmer returned normalized form, rather than
returning the original unmodified word.

Additional adjustments were made to improve the algorithm:

1- Adding 60 stop words.
2- Adding the pattern (تفاعيل) to ISRI pattern set.
3- The step 2 in the original algorithm was normalizing all hamza. This step is discarded because it
increases the word ambiguities and changes the original root.

"""
import re
from api import *

class ISRIStemmer(StemmerI):
    '''
    ISRI Arabic stemmer based on algorithm: Arabic Stemming without a root dictionary.
    Information Science Research Institute. University of Nevada, Las Vegas, USA.

    A few minor modifications have been made to ISRI basic algorithm.
    See the source code of this module for more information.

    isri.stem(token) returns Arabic root for the given token.

    The ISRI Stemmer requires that all tokens have Unicode string types.
    If you use Python IDLE on Arabic Windows you have to decode text first
    using Arabic '1256' coding.
    '''

    def __init__(self):
        self.stm = 'defult none'

        self.p3 = [u'\u0643\u0627\u0644', u'\u0628\u0627\u0644', u'\u0648\u0644\u0644', u'\u0648\u0627\u0644']    # length three prefixes
        self.p2 = [u'\u0627\u0644', u'\u0644\u0644']    # length two prefixes
        self.p1 = [u'\u0644', u'\u0628', u'\u0641', u'\u0633', u'\u0648', u'\u064a', u'\u062a', u'\u0646', u'\u0627']   # length one prefixes

        self.s3 =  [u'\u062a\u0645\u0644', u'\u0647\u0645\u0644', u'\u062a\u0627\u0646', u'\u062a\u064a\u0646', u'\u0643\u0645\u0644']  # length three suffixes
        self.s2 = [u'\u0648\u0646', u'\u0627\u062a', u'\u0627\u0646', u'\u064a\u0646', u'\u062a\u0646', u'\u0643\u0645', u'\u0647\u0646', u'\u0646\u0627', u'\u064a\u0627', u'\u0647\u0627', u'\u062a\u0645', u'\u0643\u0646', u'\u0646\u064a', u'\u0648\u0627', u'\u0645\u0627', u'\u0647\u0645']   # length two suffixes
        self.s1 = [u'\u0629', u'\u0647', u'\u064a', u'\u0643', u'\u062a', u'\u0627', u'\u0646']   # length one suffixes

        self.pr4 = {0:[u'\u0645'], 1:[u'\u0627'], 2:[u'\u0627', u'\u0648', u'\u064A'], 3:[u'\u0629']}   # groups of length four patterns
        self.pr53 = {0:[u'\u0627', u'\u062a'], 1:[u'\u0627', u'\u064a', u'\u0648'], 2:[u'\u0627', u'\u062a', u'\u0645'], 3:[u'\u0645', u'\u064a', u'\u062a'], 4:[u'\u0645', u'\u062a'], 5:[u'\u0627', u'\u0648'], 6:[u'\u0627', u'\u0645']}   # Groups of length five patterns and length three roots

        self.re_short_vowels = re.compile(ur'[\u064B-\u0652]')
        self.re_hamza = re.compile(ur'[\u0621\u0624\u0626]')
        self.re_intial_hamza = re.compile(ur'^[\u0622\u0623\u0625]')

        self.stop_words = [u'\u064a\u0643\u0648\u0646', u'\u0648\u0644\u064a\u0633', u'\u0648\u0643\u0627\u0646', u'\u0643\u0630\u0644\u0643', u'\u0627\u0644\u062a\u064a', u'\u0648\u0628\u064a\u0646', u'\u0639\u0644\u064a\u0647\u0627', u'\u0645\u0633\u0627\u0621', u'\u0627\u0644\u0630\u064a', u'\u0648\u0643\u0627\u0646\u062a', u'\u0648\u0644\u0643\u0646', u'\u0648\u0627\u0644\u062a\u064a', u'\u062a\u0643\u0648\u0646', u'\u0627\u0644\u064a\u0648\u0645', u'\u0627\u0644\u0644\u0630\u064a\u0646', u'\u0639\u0644\u064a\u0647', u'\u0643\u0627\u0646\u062a', u'\u0644\u0630\u0644\u0643', u'\u0623\u0645\u0627\u0645', u'\u0647\u0646\u0627\u0643', u'\u0645\u0646\u0647\u0627', u'\u0645\u0627\u0632\u0627\u0644', u'\u0644\u0627\u0632\u0627\u0644', u'\u0644\u0627\u064a\u0632\u0627\u0644', u'\u0645\u0627\u064a\u0632\u0627\u0644', u'\u0627\u0635\u0628\u062d', u'\u0623\u0635\u0628\u062d', u'\u0623\u0645\u0633\u0649', u'\u0627\u0645\u0633\u0649', u'\u0623\u0636\u062d\u0649', u'\u0627\u0636\u062d\u0649', u'\u0645\u0627\u0628\u0631\u062d', u'\u0645\u0627\u0641\u062a\u0626', u'\u0645\u0627\u0627\u0646\u0641\u0643', u'\u0644\u0627\u0633\u064a\u0645\u0627', u'\u0648\u0644\u0627\u064a\u0632\u0627\u0644', u'\u0627\u0644\u062d\u0627\u0644\u064a', u'\u0627\u0644\u064a\u0647\u0627', u'\u0627\u0644\u0630\u064a\u0646', u'\u0641\u0627\u0646\u0647', u'\u0648\u0627\u0644\u0630\u064a', u'\u0648\u0647\u0630\u0627', u'\u0644\u0647\u0630\u0627', u'\u0641\u0643\u0627\u0646', u'\u0633\u062a\u0643\u0648\u0646', u'\u0627\u0644\u064a\u0647', u'\u064a\u0645\u0643\u0646', u'\u0628\u0647\u0630\u0627', u'\u0627\u0644\u0630\u0649']


    def stem(self, token):
        """
        Stemming a word token using the ISRI stemmer.
        """

        self.stm = token
        self.norm(1)       #  remove diacritics which representing Arabic short vowels
        if self.stm in self.stop_words: return self.stm     # exclude stop words from being processed
        self.pre32()        # remove length three and length two prefixes in this order
        self.suf32()        # remove length three and length two suffixes in this order
        self.waw()          # remove connective ‘و’ if it precedes a word beginning with ‘و’
        self.norm(2)       # normalize initial hamza to bare alif
        if len(self.stm)<=3: return self.stm     # return stem if less than or equal to three

        if len(self.stm)==4:       # length 4 word
            self.pro_w4()
            return self.stm
        elif len(self.stm)==5:     # length 5 word
            self.pro_w53()
            self.end_w5()
            return self.stm
        elif len(self.stm)==6:     # length 6 word
            self.pro_w6()
            self.end_w6()
            return self.stm
        elif len(self.stm)==7:     # length 7 word
            self.suf1()
            if len(self.stm)==7:
                self.pre1()
            if len(self.stm)==6:
                self.pro_w6()
                self.end_w6()
                return self.stm
        return self.stm              # if word length >7 , then no stemming

    def norm(self, num):
        """
        normalization:
        num=1  normalize diacritics
        num=2  normalize initial hamza
        num=3  both 1&2
        """
        self.k = num

        if self.k == 1:
            self.stm = self.re_short_vowels.sub('', self.stm)
            return self.stm
        elif self.k == 2:
            self.stm = self.re_intial_hamza.sub(ur'\u0627',self.stm)
            return self.stm
        elif self.k == 3:
            self.stm = self.re_short_vowels.sub('', self.stm)
            self.stm = self.re_intial_hamza.sub(ur'\u0627',self.stm)
            return self.stm

    def pre32(self):
        """remove length three and length two prefixes in this order"""
        if len(self.stm)>=6:
            for pre3 in self.p3:
                if self.stm.startswith(pre3):
                    self.stm = self.stm[3:]
                    return self.stm
                elif len(self.stm)>=5:
                    for pre2 in self.p2:
                        if self.stm.startswith(pre2):
                            self.stm = self.stm[2:]
                            return self.stm

    def suf32(self):
        """remove length three and length two suffixes in this order"""
        if len(self.stm)>=6:
            for suf3 in self.s3:
                if self.stm.endswith(suf3):
                    self.stm = self.stm[:-3]
                    return self.stm
                elif len(self.stm)>=5:
                    for suf2 in self.s2:
                        if self.stm.endswith(suf2):
                            self.stm = self.stm[:-2]
                            return self.stm


    def waw(self):
        """remove connective ‘و’ if it precedes a word beginning with ‘و’ """
        if (len(self.stm)>=4)&(self.stm[:2] == u'\u0648\u0648'):
            self.stm = self.stm[1:]
            return self.stm

    def pro_w4(self):
        """process length four patterns and extract length three roots"""
        if self.stm[0] in self.pr4[0]:      #  مفعل
            self.stm = self.stm[1:]
            return self.stm
        elif self.stm[1] in self.pr4[1]:      #   فاعل
            self.stm = self.stm[0]+self.stm[2:]
            return self.stm
        elif self.stm[2] in self.pr4[2]:     #    فعال   -   فعول    - فعيل
            self.stm = self.stm[:2]+self.stm[3]
            return self.stm
        elif self.stm[3] in self.pr4[3]:      #     فعلة
            self.stm = self.stm[:-1]
            return self.stm
        else:
            self.suf1()   # do - normalize short sufix
            if len(self.stm)==4:
                self.pre1()    # do - normalize short prefix
            return self.stm

    def pro_w53(self):
        """process length five patterns and extract length three roots"""
        if ((self.stm[2] in self.pr53[0]) & (self.stm[0] == u'\u0627')):    #  افتعل   -  افاعل
            self.stm = self.stm[1]+self.stm[3:]
            return self.stm
        elif ((self.stm[3] in self.pr53[1]) & (self.stm[0] == u'\u0645')):     # مفعول  -   مفعال  -   مفعيل
            self.stm = self.stm[1:3]+self.stm[4]
            return self.stm
        elif ((self.stm[0] in self.pr53[2]) & (self.stm[4] == u'\u0629')):      #  مفعلة  -    تفعلة   -  افعلة
            self.stm = self.stm[1:4]
            return self.stm
        elif ((self.stm[0] in self.pr53[3]) & (self.stm[2] == u'\u062a')):        #  مفتعل  -    يفتعل   -  تفتعل
            self.stm = self.stm[1]+self.stm[3:]
            return self.stm
        elif ((self.stm[0] in self.pr53[4]) & (self.stm[2] == u'\u0627')):      #مفاعل  -  تفاعل
            self.stm = self.stm[1]+self.stm[3:]
            return self.stm
        elif ((self.stm[2] in self.pr53[5]) & (self.stm[4] == u'\u0629')):    #     فعولة  -   فعالة
            self.stm = self.stm[:2]+self.stm[3]
            return self.stm
        elif ((self.stm[0] in self.pr53[6]) & (self.stm[1] == u'\u0646')):     #     انفعل   -   منفعل
            self.stm = self.stm[2:]
            return self.stm
        elif ((self.stm[3] == u'\u0627') & (self.stm[0] == u'\u0627')):     #   افعال
            self.stm = self.stm[1:3]+self.stm[4]
            return self.stm
        elif ((self.stm[4] == u'\u0646') & (self.stm[3] == u'\u0627')):      #   فعلان
            self.stm = self.stm[:3]
            return self.stm
        elif ((self.stm[3] == u'\u064a') & (self.stm[0] == u'\u062a')):        #    تفعيل
            self.stm = self.stm[1:3]+self.stm[4]
            return self.stm
        elif ((self.stm[3] == u'\u0648') & (self.stm[1] == u'\u0627')):       #     فاعول
            self.stm = self.stm[0]+self.stm[2]+self.stm[4]
            return self.stm
        elif ((self.stm[2] == u'\u0627') & (self.stm[1] == u'\u0648')):             #     فواعل
            self.stm = self.stm[0]+self.stm[3:]
            return self.stm
        elif ((self.stm[3] == u'\u0626') & (self.stm[2] == u'\u0627')):     #  فعائل
            self.stm = self.stm[:2]+self.stm[4]
            return self.stm
        elif ((self.stm[4] == u'\u0629') & (self.stm[1] == u'\u0627')):           #   فاعلة
            self.stm = self.stm[0]+self.stm[2:4]
            return self.stm
        elif ((self.stm[4] == u'\u064a') & (self.stm[2] == u'\u0627')):     # فعالي
            self.stm = self.stm[:2]+self.stm[3]
            return self.stm
        else:
            self.suf1()   # do - normalize short sufix
            if len(self.stm)==5:
                self.pre1()   # do - normalize short prefix
            return self.stm

    def pro_w54(self):
        """process length five patterns and extract length four roots"""
        if (self.stm[0] in self.pr53[2]):       #تفعلل - افعلل - مفعلل
            self.stm = self.stm[1:]
            return self.stm
        elif (self.stm[4] == u'\u0629'):      # فعللة
            self.stm = self.stm[:4]
            return self.stm
        elif (self.stm[2] == u'\u0627'):     # فعالل
            self.stm = self.stm[:2]+self.stm[3:]
            return self.stm

    def end_w5(self):
        """ending step (word of length five)"""
        if len(self.stm)==3:
            return self.stm
        elif len(self.stm)==4:
            self.pro_w4()
            return self.stm
        elif len(self.stm)==5:
            self.pro_w54()
            return self.stm

    def pro_w6(self):
        """process length six patterns and extract length three roots"""
        if ((self.stm.startswith(u'\u0627\u0633\u062a')) or (self.stm.startswith(u'\u0645\u0633\u062a'))):   #   مستفعل   -    استفعل
            self.stm= self.stm[3:]
            return self.stm
        elif (self.stm[0]== u'\u0645' and self.stm[3]== u'\u0627' and self.stm[5]== u'\u0629'):      #     مفعالة
            self.stm = self.stm[1:3]+self.stm[4]
            return self.stm
        elif (self.stm[0]== u'\u0627' and self.stm[2]== u'\u062a' and self.stm[4]== u'\u0627'):      #     افتعال
            self.stm = self.stm[1]+self.stm[3]+self.stm[5]
            return self.stm
        elif (self.stm[0]== u'\u0627' and self.stm[3]== u'\u0648' and self.stm[2]==self.stm[4]):      #    افعوعل
            self.stm = self.stm[1]+self.stm[4:]
            return self.stm
        elif (self.stm[0]== u'\u062a' and self.stm[2]== u'\u0627' and self.stm[4]== u'\u064a'):      #     تفاعيل    new pattern
            self.stm = self.stm[1]+self.stm[3]+self.stm[5]
            return self.stm
        else:
            self.suf1()    # do - normalize short sufix
            if len(self.stm)==6:
                self.pre1()    # do - normalize short prefix
            return self.stm

    def pro_w64(self):
        """process length six patterns and extract length four roots"""
        if (self.stm[0] and self.stm[4])==u'\u0627':      #  افعلال
            self.stm=self.stm[1:4]+self.stm[5]
            return self.stm
        elif (self.stm.startswith(u'\u0645\u062a')):     #   متفعلل
            self.stm = self.stm[2:]
            return self.stm

    def end_w6(self):
        """ending step (word of length six)"""
        if len(self.stm)==3:
            return self.stm
        elif len(self.stm)==5:
            self.pro_w53()
            self.end_w5()
            return self.stm
        elif len (self.stm)==6:
            self.pro_w64()
            return self.stm

    def suf1(self):
        """normalize short sufix"""
        for sf1 in self.s1:
            if self.stm.endswith(sf1):
                self.stm = self.stm[:-1]
                return self.stm

    def pre1(self):
        """normalize short prefix"""
        for sp1 in self.p1:
            if self.stm.startswith(sp1):
                self.stm = self.stm[1:]
                return self.stm
