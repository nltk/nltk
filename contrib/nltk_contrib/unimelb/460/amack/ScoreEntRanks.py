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
	opts, args = getopt(sys.argv[1:], "d:a:")
	estimator_load_fname = None
	estimator_save_fname = None
	textcat_path = None
	training_mode = False
	bootstrap_mode = False
	rank_bootstrap_mode = False
	for o, p in opts:
		if o == "-d":
			num_divs = int(p)
		if o == "-a":
			alpha = float(p)
	cor_count = []
	inc_count = []
	for line in sys.stdin.readlines():
		fname = line.split()[0]
		suff = fname.split('.').pop()
		if suff == "inc":
			inc_count.append(1)
			cor_count.append(0)
		elif suff == "cor":
			inc_count.append(0)
			cor_count.append(1)
	rank = len(inc_count)
	total_correct = sum(cor_count)	
	cutoffs = [int(x * float(rank)/num_divs) for x in range (1, num_divs + 1)]
	pos = 0
	threshold = []
	prec = []
	recall = []
	f_score = []
	for i in cutoffs:
		threshold.append(float(i)/rank)
		num_inc = sum(inc_count[:i])
		num_cor = sum(cor_count[:i])
		prec.append(float(num_cor)/(num_cor + num_inc))
		recall.append(float(num_cor)/total_correct)
		f_score.append(1.0/(alpha/prec[len(prec) - 1] + (1.0 - alpha)/recall[len(recall) - 1]))
	
	for val in threshold:
		print("& %2.0f" % (100 * val) + "\\%"),
	print(r'\\')	
	for array in [prec, recall, f_score]:
		for val in array:
			print("& %2.2f" % (100 * val) + "\\%"),
		print(r'\\')	

if __name__ == "__main__":
    main()


