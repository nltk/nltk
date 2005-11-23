# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# kana.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Sun May 15 23:12:04 EST 2005
#
#----------------------------------------------------------------------------#

""" This module is responsible for Japanese script/encoding specific methods,
	especially determining the script type of an entry. It is thus the only
	module which requires a utf8 encoding for the additional Japanese
	characters.
"""

#----------------------------------------------------------------------------#

from sets import Set
import string

#----------------------------------------------------------------------------#

hiragana = 'ーぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん'
katakana = 'ーァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶ'
hiragana = unicode(hiragana, 'utf8')
katakana = unicode(katakana, 'utf8')

smallKana = 'ぁぃぅぇぉっょゅゃ'
smallKana = unicode(smallKana, 'utf8')
smallKanaSet = Set(smallKana)

eigo = 'ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ１２３４５６７８９０ヽヾゝゞ〃仝々〆〇＠＠○○※〒？Πβθ・'
eigo = unicode(eigo, 'utf8')
eigoSet = Set(eigo)

nKana = unicode('ん', 'utf8')

toKatakana = dict(zip(katakana+hiragana, 2*katakana))

#----------------------------------------------------------------------------#

def isAscii(char):
	return ord(char) < 256

#----------------------------------------------------------------------------#

def compareSingleKana(kanaA, kanaB):
	return toKatakana[kanaA] == toKatakana[kanaB]

def compareKana(kanaA, kanaB):
	return map(toKatakana.get, kanaA) == map(toKatakana.get, kanaB)

def katakanaForm(kanaString):
	return string.join(map(toKatakana.get, kanaString), '')

#----------------------------------------------------------------------------#

def containsRoman(word):
	""" Determines whether or not a word contains any non-script characters.
	"""
	for char in word:
		if scriptType(char) != 'kanji':
			# if it's kana, it can't be roman
			continue
	
		cNum = ord(char)
		if cNum <= 256 or (cNum >= 12294 and cNum <= 12318) or \
					(cNum >= 65282 and cNum <= 65374):
			return True
	else:
		return False

#----------------------------------------------------------------------------#

def scriptType(segment):
	""" Determine what type of script a character is. A whole word can be
		passed in, but only the first character is looked at. Furthermore, any
		non-kana script is classified as kanji.
	"""
	char = segment[0]
	if (char >= u'\u3041' and char <= u'\u3093') or char == u'\u30fc':
		return 'hiragana'
	elif char >= u'\u30a1' and char <= u'\u30f6':
		return 'katakana'
	else:
		return 'kanji'
	
#----------------------------------------------------------------------------#

