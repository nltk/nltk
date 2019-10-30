# -*- coding=utf-8 -*-
#
# Natural Language Toolkit: The Arabic Normalization
#
# Copyright (C) 2001-2019 NLTK Proejct
# Author: Mohammad Modallal <m.modallal99@hotmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

"""
Arabic Strip Harakat and Normalization. 

"""
import re

class ArabicStriperNormalizer():
    '''
    The Arabic Normalization unifies the orthography of alifs, hamzas, and yas/alif maqsuras
    '''
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

        HAMZAT = (HAMZA, WAW_HAMZA, YEH_HAMZA, HAMZA_ABOVE, HAMZA_BELOW, ALEF_HAMZA_BELOW, ALEF_HAMZA_ABOVE,)
        TANWIN = (FATHATAN, DAMMATAN, KASRATAN)
        TASHKEEL = (FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, SUKUN, SHADDA)
        HARAKAT = (FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, SUKUN)
        LIGUATURES = (LAM_ALEF, LAM_ALEF_HAMZA_ABOVE, LAM_ALEF_HAMZA_BELOW,LAM_ALEF_MADDA_ABOVE,)

        HAMZAT_PATTERN = re.compile(u"[" + u"".join(HAMZAT) + u"]", re.UNICODE)
        HARAKAT_PATTERN = re.compile(u"[" + u"".join(HARAKAT) + u"]", re.UNICODE)
        LASTHARAKA_PATTERN = re.compile(u"[%s]$|[%s]"%(u"".join(HARAKAT), u''.join(TANWIN)), re.UNICODE)
        LIGUATURES_PATTERN = re.compile(u"[" + u"".join(LIGUATURES) + u"]", re.UNICODE)

       
    def strip_harakat(text):
	    """
            This function strip Harakat(FATHATAN, DAMMATAN, KASRATAN, FATHA, DAMMA, KASRA, and SUKUN) from Arabic text.

	    """
	    if not text:
               return text
	    elif is_vocalized(text):
	       for char in HARAKAT:
                            text = text.replace(char, '')
	    return text

    def is_vocalizedtext(text):
	    """
            This function Checks if the arabic text is vocalized.
	    """
	    return bool(re.search(HARAKAT_PATTERN, text))

    def strip_lastharaka(text):
	    """
            This function strip Haraka from Arabic text.
	    """
	    if text:
               if is_vocalized(text):
                  return re.sub(LASTHARAKA_PATTERN, u'', text)
	    return text


    def strip_tashkeel(text):
	    """
            This function strip vowels from Arabic text"""
	    if not text:
                return text
	    elif is_vocalized(text):
                for char in TASHKEEL:
                    text = text.replace(char, '')
	    return text


    def strip_tatweel(text):
	    """
	    This Function Strip tatweel from Arabic text.
	    """
	    return text.replace(TATWEEL, '')


    def strip_shadda(text):
	    """
	    This Function Strip Shadda from Arabic text.
	    """
	    return text.replace(SHADDA, '')


    def normalize_ligature(text):
	    """
            This function Normalize Lam Alef ligatures into two letters (LAM and ALEF),
	    """
	    if text:
	        return LIGUATURES_PATTERN.sub(u'%s%s' % (LAM, ALEF), text)
	    return text


    def normalize_hamza(word):
	    """
            This function Normalize the Hamzat into one form of hamza,
	    """
	    if word.startswith(ALEF_MADDA):
	        if len(word) >= 3 and (word[1] not in HARAKAT) and (word[2] == SHADDA or len(word) == 3):
                      word = HAMZA + ALEF + word[1:]
	        else:
                      word = HAMZA + HAMZA + word[1:]
	    # convert all Hamza from into one form
	    word = word.replace(ALEF_MADDA, HAMZA + HAMZA)
	    word = HAMZAT_PATTERN.sub(HAMZA, word)
	    return word

