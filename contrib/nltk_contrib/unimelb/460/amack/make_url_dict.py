#!/usr/bin/python

from getopt import *
import sys
import commands
import time
import re
import pickle

def main():
	opts, args = getopt(sys.argv[1:], "o:")
	for o, p in opts:
		if o == "-o":
			pickled_dict_fname = p
	url_dict = dict()
	for fname in args:
		fp = open(fname, 'r')
		url = fp.readline().rstrip()
		url_dict[url] = fname
	pickle.dump(url_dict, open(pickled_dict_fname, 'w'))

if __name__ == "__main__":
    main()
