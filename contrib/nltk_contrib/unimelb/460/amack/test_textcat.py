#!/usr/bin/python

from getopt import *
import sys
import re
import commands

location_csv = '/nlptools/loc051cs/UNLOCODE_CodeList.csv_2005-1.csv'

def main():
	optseen = 0

	textcat_path = ""
	expected_textcat_output = ""
	file_suff = ""
	results_fname = "" 
	opts, args = getopt(sys.argv[1:], "t:e:s:")
	for o, p in opts:
		optseen += 1
		if o == "-t":
			textcat_path = p
		elif o == "-e":
			expected_textcat_output = p
		elif o == "-s":
			file_suff = p
	if (optseen < 2):
		print("usage: work it out, chump")
		sys.exit()
	if len(args) != 0:
		fnames = args
	else:
		fnames = sys.stdin
	potential_samples = []
#	results_file = open(results_fname, "w")
	num_correct = 0
	total_idd = 0
	for fname_line in fnames:
		i = 0
		fname = fname_line.rstrip()
		if fname == None:
			break
		textcat_output = commands.getoutput(textcat_path + ' ' + fname)
		if expected_textcat_output != "":
			if textcat_output == expected_textcat_output:
				num_correct += 1
				result_string = " +ve acc to Textcat"
				res_suff = 'tcy'
			else: 
				result_string = " -ve acc to Textcat"
				res_suff = 'tcn'
		else:		
			split_tc_out = textcat_output.split()
			if len(split_tc_out) > 3:
				num_correct += 1
				result_string = " unknown by textcat"
				res_suff = 'utc'
			else: 
				result_string = " +vely identified by textcat"
				res_suff = 'ktc'
				
		new_fname = fname + '.' + file_suff + '.' + res_suff
		output_string = new_fname + ":" + result_string
		tc_out_file = open(fname + '.tc', "w")
		tc_out_file.write(textcat_output + '\n')
		tc_out_file.close()
		total_idd += 1	
		assoc_fnames = commands.getoutput('ls ' + fname + '*')
		for af in assoc_fnames.split('\n'):
			ass_suff_match = re.match(fname + '(.*)', af)
			ass_suff = ass_suff_match.group(1)
			commands.getoutput('mv ' + fname + ass_suff+ ' ' + new_fname + ass_suff)
		print(output_string)	
	if total_idd > 0:		
		print("Number identified by Textcat: %2d" % num_correct)
		print("Number examined: %2d" % total_idd)

if __name__ == "__main__":
	main()

