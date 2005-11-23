# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# unique.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Sun May 15 23:21:07 EST 2005
#
#----------------------------------------------------------------------------#

import psyco
psyco.full()

import kana
from sets import Set

print 'Detecting unique kanji...'
data = open('edict').read()
data = unicode(data, 'utf8')

detected = Set()
outputStream = open('unique-kanji.txt', 'w')
for char in data:
	if len(char.encode('utf8')) > 1 and char not in kana.nonKanjiSet:
		detected.add(char)

detected = list(detected)
print '%d detected' % len(detected)
for i in xrange(len(detected)):
	outputStream.write(detected[i].encode('utf8'))
	if i+1 % 40 == 0:
		outputStream.write('\n')
