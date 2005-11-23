#!/usr/bin/python

from getopt import *
import sys
import re
import commands

location_csv = '/nlptools/loc051cs/UNLOCODE_CodeList.csv_2005-1.csv'

def main():
	optseen = 0

	country_locs_csv_fname = ""
	exp_countries_fname = ""
	textcat_path = ""
	expected_textcat_output = ""
	file_suff = ""
	results_fname = "" 
	opts, args = getopt(sys.argv[1:], "l:c:t:e:s:")
	for o, p in opts:
		optseen += 1
		if o == "-l":
			country_locs_csv_fname = p
		elif o == "-c":
			exp_countries_fname = p
		elif o == "-t":
			textcat_path = p
		elif o == "-e":
			expected_textcat_output = p
		elif o == "-s":
			file_suff = p
#		elif o == "-r":
#			results_fname = p
#		elif o == "-i":
#			input_file_list = open(p, "r+")
	if (optseen < 5):
		print("usage: work it out, chump")
		sys.exit()
	exp_countries = []
	exp_countries_file = open(exp_countries_fname, "r")
	for line in exp_countries_file.readlines():
		if line != '\n':
			exp_countries.append(line[:-1])
	country_locs = read_country_locs_csv(country_locs_csv_fname, exp_countries)
	print country_locs
	country_grep_qs = max_combine(country_locs, 4096, '|')
	print country_grep_qs
	potential_samples = []
#	results_file = open(results_fname, "w")
	num_correct = 0
	total_idd = 0
	for fname_line in sys.stdin.readlines():
		i = 0
		fname = fname_line.rstrip()
		if fname == None:
			break
		found_loc = False 
		for qry in country_grep_qs:
			if commands.getstatusoutput('egrep -iqw "' + qry + '" ' + fname)[0] == 0:
				found_loc = True
				break
		sys.stderr.write("c")
		if found_loc:
			textcat_output = commands.getoutput(textcat_path + ' ' + fname)
			if textcat_output == expected_textcat_output:
				num_correct += 1
				result_string = " correctly identified"
				res_suff = 'cor'
			else: 
				result_string = " incorrectly identified"
				res_suff = 'inc'
				
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
		print("Total identified by location lookup: %2d" % total_idd)
		print("Number correctly identified according to Textcat: %2d" % num_correct)
		acc = 100 * float(num_correct)/total_idd
		print("Overall Precision: %2.2f" % acc + "%")

def max_combine(strlist, mxl, spch):
	whole_str = ""
	for string in strlist:
		whole_str += string + spch
	ret_list = [whole_str[i * mxl: min((i+1) * mxl, len(whole_str))] \
		for i in range(0, len(whole_str)/mxl + 1)]
	prepend = ""
	for h in range(0, len(ret_list)):
		string = prepend + ret_list[h]
		i = len(string) - 1
		while(i > 0 and string[i] !=  spch):
			i -= 1
		ret_list[h] = string[:i]
		if i < len(string) - 1:
			prepend = string[i:]
		else:
			prepend = ''

	return ret_list	

def read_country_locs_csv(filename, country_codes):
	cell_pattern = r'\s*(?:"([^"]*)")?\s*'
	line_pattern = '^' + (cell_pattern + ',') * 4 + cell_pattern
	line_re = re.compile(line_pattern)
	multiname_pattern = r'([^(]*)\(([^)]*)\)'
	multiname_re = re.compile(multiname_pattern)
	place_dict = dict()
	country_places =[] 
	infile = open(filename, "r")
	for line in infile.readlines():
		line_match = line_re.match(line)
		if line_match:
			if line_match.group(2) in country_codes and line_match.group(3) != None:
				place_name = line_match.group(4)
				multi_match = multiname_re.match(place_name)
				if multi_match:
					country_places += [multi_match.group(1), multi_match.group(2)]
				elif len(country_places) == 0 or place_name != country_places[-1:][0]:
					country_places += [place_name]
	return country_places				





if __name__ == "__main__":
    main()
