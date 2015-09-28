# Natural Language Toolkit: Aligner Utilities
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Anna Garbar
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.translate.api import Alignment

def pharaohtext2tuples(pharaoh_text):
    """
    Converts pharaoh text format into an Alignment object (a list of tuples).
    
        >>> pharaoh_text = '0-0 2-1 9-2 21-3 10-4 7-5'
        >>> pharaohtext2tuples(pharaoh_text)
        Alignment([(0, 0), (2, 1), (7, 5), (9, 2), (10, 4), (21, 3)])
        
    :type pharaoh_text: str
    :param pharaoh_text: the word alignment outputs in the pharaoh output format
    :rtype: Alignment
    :return: An Alignment object that contains a list of integer tuples 
    """

    # Converts integers to strings for a word alignment point.
    list_of_tuples = [tuple(map(int,a.split('-'))) for a in pharaoh_text.split()]
    return Alignment(list_of_tuples)
    

def alignment2pharaohtext(alignment):
    """
    Converts an Alignment object (a list of tuples) into pharaoh text format.
    
        >>> alignment = [(0, 0), (2, 1), (9, 2), (21, 3), (10, 4), (7, 5)]
        >>> alignment2pharaohtext(alignment)
        '0-0 2-1 9-2 21-3 10-4 7-5'
        
    :type alignment: Alignment
    :param alignment: An Alignment object that contains a list of integer tuples 
    :rtype: str
    :return: the word alignment outputs in the pharaoh output format
    """

    pharaoh_text = ' '.join(str(i) + "-" + str(j) for i,j in alignment)
    return pharaoh_text
