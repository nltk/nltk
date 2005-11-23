#!/usr/bin/python

from getopt import *
import sys
import commands
import time
import re

def main():
	non_text_pattern = r'\[[^\s\[\]]*\]'
	non_text_re = re.compile(non_text_pattern)
	url_pattern = r'[a-z]*:(//\w+\.(\w+\.)*/)?[^\s:]*\s'
	url_re = re.compile(url_pattern)
	for line in sys.stdin:
		texted_line = non_text_re.sub(' ', line)
		de_urled_line = url_re.sub(' ', texted_line)
		print(de_urled_line),





if __name__ == "__main__":
    main()
