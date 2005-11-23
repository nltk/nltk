#!/usr/bin/python

import pickle
import re
import sys
import commands
from string import rstrip
from getopt import getopt
from nltk.tokenizer import Token
from nltk.tokenizer import RegexpTokenizer
from nltk.probability import WittenBellProbDist
from nltk.probability import FreqDist

def main():
	num_divs = 10
	alpha = 0.5
	opts, args = getopt(sys.argv[1:], "d:a:i:r:w:")
	estimator_load_fname = None
	estimator_save_fname = None
	textcat_path = None
	training_mode = False
	bootstrap_mode = False
	rank_bootstrap_mode = False
	start_file_ind = 0
	for o, p in opts:
		if o == "-d":
			num_divs = int(p)
		if o == "-a":
			alpha = float(p)
		if o == "-i":
			start_file_ind = int(p)
		if o == "-r":
			right_suff = p
		if o == "-w":
			wrong_suff = p

	cor_count = []
	inc_count = []
	flines = sys.stdin.readlines()[start_file_ind:]
	lowest_ent = float(flines[1].split()[1])
	highest_ent = float(flines[-1:][0].split()[1])
	ent_range = highest_ent - lowest_ent
	ent_cutoffs = [lowest_ent + x * ent_range/num_divs for x in range(1, num_divs + 1)]
	ent_cutoffs.append(2 * highest_ent) # sentinel
	print ent_cutoffs
	ec_ind = 1
	line_ind = 0
	cutoffs = []
	for line in flines:
		details = line.split()
		fname = details[0]
		entrop = float(details[1])
		if entrop >= ent_cutoffs[ec_ind]:
			cutoffs.append(line_ind)
			ec_ind += 1
		suff = fname.split('.').pop()
		if suff == wrong_suff:
			inc_count.append(1)
			cor_count.append(0)
		elif suff == right_suff:
			inc_count.append(0)
			cor_count.append(1)
		line_ind += 1	
	cutoffs.append(line_ind)	
	total_correct = sum(cor_count)	
	pos = 1
	threshold = []
	prec = []
	recall = []
	f_score = []
	for i in cutoffs:
		threshold.append(float(pos)/num_divs)
		num_inc = sum(inc_count[:i+1])
		num_cor = sum(cor_count[:i+1])
		prec.append(float(num_cor)/(num_cor + num_inc))
		recall.append(float(num_cor)/total_correct)
		f_score.append(1.0/(alpha/prec[len(prec) - 1] + (1.0 - alpha)/recall[len(recall) - 1]))
		pos += 1
	
	for val in threshold:
		print("& %2.0f" % (100 * val) + "\\%"),
	print(r'\\')	
	for val in cutoffs:
		print("& %2d" % val + "\\"),
	print(r'\\')	
	for array in [prec, recall, f_score]:
		for val in array:
			print("& %2.1f" % (100 * val) + "\\%"),
		print(r'\\')	

if __name__ == "__main__":
    main()


