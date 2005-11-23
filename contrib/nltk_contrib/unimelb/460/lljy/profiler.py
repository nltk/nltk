#!/usr/bin/python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# profile.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Fri May 20 10:45:45 EST 2005
#
#----------------------------------------------------------------------------#

import segment
import profile

def testMethod():
	segment.performSegmentation('edict', 'align.out')

if __name__ == '__main__':
	profile.run('testMethod()', 'profile.out')
