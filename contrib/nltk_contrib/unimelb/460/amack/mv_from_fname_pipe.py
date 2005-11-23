#!/usr/bin/python
import commands
import sys

for line in sys.stdin:
	commands.getoutput('mv ' + line.rstrip() + ' ' + sys.argv[1])
