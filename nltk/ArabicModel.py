#!/usr/bin/python
# -*- coding=utf-8 -*-
#
# Natural Language Toolkit: The Arabic Normalization
#
# Copyright (C) 2001-2019 NLTK Proejct
# Author: Mohammad Modallal <m.modallal99@hotmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
	Arabic Model language text Normalization
	Features:
		 - Text normalization
		 - Strip Diacritics
"""
import re
class ArabicModel:
    def __init__(self):
        # Diacritics
        FATHATAN = u'\u064b'
        DAMMATAN = u'\u064c'
        KASRATAN = u'\u064d'
        FATHA = u'\u064e'
        DAMMA = u'\u064f'
        KASRA = u'\u0650'
        SHADDA = u'\u0651'
        SUKUN = u'\u0652'
        TATWEEL = u'\u0640'
        ALEF_MADDA = u'\u0622'
        SHADDA = u'\u0651'
        HAMZA = u'\u0621'
        ALEF_MADDA = u'\u0622'
        ALEF_HAMZA_ABOVE = u'\u0623'
        WAW_HAMZA = u'\u0624'
        ALEF_HAMZA_BELOW = u'\u0625'
        YEH_HAMZA = u'\u0626'
        ALEF = u'\u0627'

	#Ligatures
        LAM_ALEF = u'\ufefb'
        LAM_ALEF_HAMZA_ABOVE = u'\ufef7'
        LAM_ALEF_HAMZA_BELOW = u'\ufef9'
        LAM_ALEF_MADDA_ABOVE = u'\ufef5'

        FULL_STOP = u'\u06d4'
        COMMA = u'\u060C'
	SEMICOLON = u'\u061B'
	QUESTION = u'\u061F'

        HAMZAT = (HAMZA, WAW_HAMZA, YEH_HAMZA, HAMZA_ABOVE, HAMZA_BELOW, ALEF_HAMZA_BELOW, ALEF_HAMZA_ABOVE,)
        TANWIN = (FATHATAN, DAMMATAN, KASRATAN)
        TASHKEEL = (FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, SUKUN, SHADDA)
        DIACRITICS = (FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, SUKUN)
        LIGUATURES = (LAM_ALEF, LAM_ALEF_HAMZA_ABOVE, LAM_ALEF_HAMZA_BELOW,LAM_ALEF_MADDA_ABOVE,)

        HAMZAT_PATTERN = re.compile(u"[" + u"".join(HAMZAT) + u"]", re.UNICODE)
        DIACRITICS_PATTERN = re.compile(u"[" + u"".join(DIACRITICS) + u"]", re.UNICODE)
        LASTHARAKA_PATTERN = re.compile(u"[%s]$|[%s]"%(u"".join(DIACRITICS), u''.join(TANWIN)), re.UNICODE)
        LIGUATURES_PATTERN = re.compile(u"[" + u"".join(LIGUATURES) + u"]", re.UNICODE)

       
    def strip_diacritics(text):
	    """
            This function Strip Arabic language Diacritics (KASRATAN, FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, SUKUN, VOWELS, SHADDA, HAMZA) 

	    """
	    if not text:
                 return text
	    else:
                 for char in DIACRITICS:         #Strip Diacritics (KASRATAN, FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, and SUKUN) from Arabic text.
                         text = text.replace(char, '')
                 for char in TASHKEEL:           #Strip vowels from Arabic text
                    text = text.replace(char, '')
                 text=text.replace(TATWEEL, '')  #Strip tatweel from Arabic text.
                 text=text.replace(SHADDA, '')   #Strip Shadda from Arabic text.
                 text=LIGUATURES_PATTERN.sub(u'%s%s' % (LAM, ALEF), text) #Normalize Lam Alef ligatures into two letters (LAM and ALEF)
                 if text.startswith(ALEF_MADDA): #Normalize the Hamzat into one form of hamza,
			if len(text) >= 3 and (text[1] not in DIACRITICS) and (text[2] == SHADDA or len(text) == 3):
		              text = HAMZA + ALEF + text[1:]
			else:
		              text = HAMZA + HAMZA + text[1:]
		        # convert all Hamza from into one form
		        text = text.replace(ALEF_MADDA, HAMZA + HAMZA)
		        text = HAMZAT_PATTERN.sub(HAMZA, text)
                 
	    return text

    def normalization2(text):
	    """
            This function normalize Arabic language text by removing the following from the input text:
              - Stops
              - Semicolon 
              - Question Mark
              - Commas
              - Diacritics (KASRATAN, FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, SUKUN, VOWELS, SHADDA, HAMZA) 

	    """
	    if not text:
                 return text
	    else:
                 text=strip_diacritics(text) #Strip Arabic language Diacritics
                 text=text.replace(FULL_STOP, '') #Remove full stop
                 text=text.replace(COMMA, '')     #Remove Comma
                 text=text.replace(SEMICOLON, '') #Remove Semicolon
                 text=text.replace(QUESTION, '')  #Remove Question Mark
	    return text
