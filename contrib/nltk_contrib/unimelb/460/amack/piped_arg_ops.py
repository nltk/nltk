#!/usr/bin/python
import sys
import commands
from string import *

sub_ind = sys.argv.index('-')
if sub_ind == ValueError:
	print("Usage: %s command with '-' in place of the arg to be replaced by a piped in filename" % sys.argv[0])
	exit
else:
	 com_line = ' '.join(sys.argv[1:sub_ind]) + ' %s ' + ' '.join(sys.argv[sub_ind+1:])
for line in sys.stdin:
	fname = line.split()[0]
	print commands.getoutput(com_line % fname)
