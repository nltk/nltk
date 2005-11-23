#!/usr/bin/python

from getopt import *
import sys
import commands
import time
import re
import math
import pickle

def main():
	opts, args = getopt(sys.argv[1:], "p:s:u")
	file_pref = None
	old_url_dict = None
	for o, p in opts:
		if o == "-p":
			file_pref = p
		if o == "-u":
			old_url_dict = pickle.load(open(p, "r"))
	if file_pref == None:
		print("usage: python fetch_text.py -p file_prefix")
		sys.exit()
	if old_url_dict: fetch_urls(file_pref, old_url_dict)
	else: fetch_urls(file_pref)

def fetch_urls(file_pref, url_dict = dict()):
	url_ctr = 0
	term_ctr = 0
	url_re = re.compile(r'^\s*URL\s*=\s*"([^"]+)"$')
	term_re = re.compile(r'^\s*Q\s*=\s*"([^"]+)"$')
	num_res_re = re.compile(r'^\s*Estimated Total Results Number\s*=\s*(\d+)$')
	for line in sys.stdin:
		term_match = term_re.match(line)
		url_match = url_re.match(line)	
		num_res_match = num_res_re.match(line)	
		if (term_match != None):
			term = term_match.group(1)	
			term_ctr += 1
		elif (num_res_match != None):
			num_res = num_res_match.group(1)
			log_freq_str = ("%.0f" % (10 * math.log10(max(1, int(num_res))))).zfill(2)
		elif url_match != None:
			url = url_match.group(1)
			if not url_dict.has_key(url):
				url_ctr += 1
				filename = 'f' + log_freq_str + '.' + file_pref + '_' + str(url_ctr).zfill(4) \
					+ '.t' + str(term_ctr).zfill(3)
				commands.getoutput('lynx -dump -nolist "' + url + '" | ../strip_non_std.py > ' + filename)
				info_fname = filename + '.info'
				url_dict[url] = info_fname
				info_file = open(info_fname, "w")
				info_file.write(url + '\n')
				info_file.write(term + '\n')
				info_file.write(num_res + '\n')
				info_file.close()
				print(filename)
				sys.stderr.write("u")

			else:	
				info_file = open(url_dict[url], "a")
				info_file.write(term+ '\n')
				info_file.write(num_res + '\n')
				info_file.close()



if __name__ == "__main__":
    main()
