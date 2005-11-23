#!/usr/local/bin/python

from nltk.token import Token
from nltk.probability import ConditionalFreqDist, FreqDist, WittenBellProbDist, ConditionalProbDist
import re
from math import log, exp
import codecs
import sys
import string

# Increase of threshold if desired (skew ~100, rel_ent ~2)
threshinc = 0

# -----------------------------------------------------------
# Calculate skew divergence of two 1-,2-,3-gram distributions
def skew_div(i_uni,i_bi,i_tri,j_uni,j_bi,j_tri):
	s_div = 0
	for item in i_uni.samples():
		s_div += i_uni.freq(item)*log(i_uni.freq(item)/(0.9*j_uni.freq(item)+0.1*i_uni.freq(item)))/log(2)
	for cond in i_bi.conditions():
		for item in i_bi[cond].samples():
			s_div += i_bi[cond].freq(item)*log(i_bi[cond].freq(item)/(0.9*j_bi[cond].freq(item)+0.1*i_bi[cond].freq(item)))/log(2)
	for cond in i_tri.conditions():
		for item in i_tri[cond].samples():
			s_div += i_tri[cond].freq(item)*log(i_tri[cond].freq(item)/(0.9*j_tri[cond].freq(item)+0.1*i_tri[cond].freq(item)))/log(2)
	return s_div
# -----------------------------------------------------------

# -----------------------------------------------------------
# Calculate relative entropy between two 1-,2-,3-gram distributions
def rel_ent(i_uni,i_bi,i_tri,j_uni,j_bi,j_tri):
	r_ent = 0
	i_unip = WittenBellProbDist(i_uni,100)
	i_bip = ConditionalProbDist(i_bi,WittenBellProbDist,False,100)
	i_trip = ConditionalProbDist(i_tri,WittenBellProbDist,False,100)
	j_unip = WittenBellProbDist(j_uni,100)
	j_bip = ConditionalProbDist(j_bi,WittenBellProbDist,False,100)
	j_trip = ConditionalProbDist(j_tri,WittenBellProbDist,False,100)
	for cond in i_tri.conditions():
		for item in i_tri[cond].samples():
			prob_p = 0
			prob_q = 0
			prob_p = i_trip[cond].logprob(item)+i_bip[cond[1:]].logprob(item)+i_unip.logprob(item)
			if len(j_tri[cond].samples())!=0:
				prob_q = j_trip[cond].logprob(item)+j_bip[cond[1:]].logprob(item)+j_unip.logprob(item)
			elif len(j_bi[cond[1:]].samples())!=0:
				prob_q = j_bip[cond[1:]].logprob(item)+j_unip.logprob(item)+log(0.01)
			elif j_uni.freq(item)!=0:
				prob_q = j_unip.logprob(item)+log(0.0001)
			else: prob_q = log(0.000001)
			r_ent += exp(prob_p)*(prob_p-prob_q)/log(2)
	return r_ent
# -----------------------------------------------------------

# Get -r, -t arguments
if (len(sys.argv)<2):
	print "Usage: proj.py data_file [-r] [-t threshold:350]"
	sys.exit()

if (len(sys.argv)>3 and sys.argv[2]=='-t' and sys.argv[3].isdigit()):
	thresh = string.atoi(sys.argv[3])
	if (len(sys.argv)>4 and sys.argv[4]=='-r'):
		RE = 1
	else: RE = 0

elif (len(sys.argv)>2 and sys.argv[2]=='-r'):
	RE = 1
	if (len(sys.argv)>4 and sys.argv[3]=='-t'):
		thresh = string.atof(sys.argv[4])
	else: thresh = 3.5

else: 
	thresh = 350
	RE = 0

# Get -p, -d arguments
if (len(sys.argv)>3 and (sys.argv[-2]=='-p') and sys.argv[-1].isdigit()): loopmax=string.atoi(sys.argv[-1])
elif (len(sys.argv)>4 and (sys.argv[-3]=='-p') and sys.argv[-2].isdigit()): loopmax=string.atoi(sys.argv[-2])
else: loopmax = 2
if (sys.argv[-1]=='-d'): DRM = 1
else: DRM = 0

# open data file
while True:
	try:
		file = codecs.open(sys.argv[1],'r','utf-8')
		break
	except IOError:
		print "Fatal error: Cannot open ",sys.argv[1]
		sys.exit()
filelines = file.readlines()

# declare lists of 1-,2-,3-gram distributions
unigrams=[]
bigrams=[]
trigrams=[]
# declare list of document numbers for referencing documents
nums=[]
index=0
# build n-gram distributions for each line in the test data
for line in filelines:
	# keep track of index
	if (index>=len(filelines)): break
	index+=1

	# build frequency distributions
	fdist = FreqDist()
	cfdist = ConditionalFreqDist()
	cf3dist = ConditionalFreqDist()

	# chop the new line
	corpus = line[:-1]+'--'
	corpus.replace('\s+','__')
	# use spaces as word padding
	prev2= '_'
	prev = '_'
	for letter in corpus:
		# ignore punctuation, etc.
		if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
		cf3dist[prev2+prev].inc(letter)
		cfdist[prev].inc(letter)
		fdist.inc(letter)
		prev2= prev
		prev = letter
	# set value above threshold for one document
	testval = thresh + 1
	# for each document and one currently being used
	for i in range(len(unigrams)):
		# get each value to compare with threshold
		if (RE): testval = rel_ent(unigrams[i],bigrams[i],trigrams[i],fdist,cfdist,cf3dist)
		else: testval = skew_div(unigrams[i],bigrams[i],trigrams[i],fdist,cfdist,cf3dist)
		# if testval within threshold, add to cluster
		if (testval<thresh):
			prev2= '_'
			prev = '_'
			for letter in corpus:
				if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
				trigrams[i][prev2+prev].inc(letter)
				bigrams[i][prev].inc(letter)
				unigrams[i].inc(letter)
				prev2= prev
				prev = letter
			nums[i].append(index)
			break
	# otherwise, make cluster for current item
	if (testval>=thresh):
		unigrams.append(fdist)
		bigrams.append(cfdist)
		trigrams.append(cf3dist)
		nums.append([index])
# print clusters after first pass
print nums
# perform further passes
for loopctr in range(loopmax):
	# increase threshold, if necessary
	thresh += threshinc
	# cross-check new clusters
	remove = []
	for i in range(len(unigrams)):
		for j in range(i+1,len(unigrams)):
			if (j>len(nums)): break
			# calculate skew div of cluster i and cluster j
			if (RE): testval = rel_ent(unigrams[i],bigrams[i],trigrams[i],unigrams[j],bigrams[j],trigrams[j])
			else: testval = skew_div(unigrams[i],bigrams[i],trigrams[i],unigrams[j],bigrams[j],trigrams[j])
			# if within threshold, combine clusters
			if (testval<thresh):
				for k in nums[j]:
					# combine clusters by adding corpus
					# documents to it, as above
					corpus = filelines[k-1][:-1]+'__'
					corpus.replace('\s+','__')
					prev2= '_'
					prev = '_'
					for letter in corpus:
						if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
						trigrams[i][prev2+prev].inc(letter)
						bigrams[i][prev].inc(letter)
						unigrams[i].inc(letter)
						prev2= prev
						prev = letter
				nums[i].extend(nums[j])
				nums[i].sort()
				remove.append(j)
		# remove combined clusters from cluster set
		remove.sort()
		remove.reverse()
		for k in remove:
			nums.remove(nums[k])
			unigrams.pop(k)
			bigrams.pop(k)
			trigrams.pop(k)
		remove=[]
	# print cluster set for this pass
	print nums

# Dreaming
if (not(DRM)): sys.exit()
temps=[];testlists=[]
for i in range(len(nums)):
	# ignore clusters of length 1
	if (len(nums[i])==1): continue
	testlists=[]
	# build list of testdocument, other documents pairs
	for j in nums[i]:
		temps=[]
		for k in nums[i]: temps.append(k)
		temps.remove(j)
		testlists.append((j,temps))
		# for clusters of size 2, only need one pair
		if (len(nums[i])==2): break
	# for each pair, build new distributions
	for (testdoc,docs) in testlists:
		testuni=FreqDist();dreamuni=FreqDist()
		testbi=ConditionalFreqDist();dreambi=ConditionalFreqDist()
		testtri=ConditionalFreqDist();dreamtri=ConditionalFreqDist()

		# build distributions, as above
		corpus = filelines[testdoc-1][:-1]+'__'
		corpus.replace('\s+','__')
		prev2= '_'
		prev = '_'
		for letter in corpus:
			if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
			testtri[prev2+prev].inc(letter)
			testbi[prev].inc(letter)
			testuni.inc(letter)
			prev2= prev
			prev = letter
		for docnum in docs:
			corpus = filelines[docnum-1][:-1]+'__'
			corpus.replace('\s+','__')
			prev2= '_'
			prev = '_'
			for letter in corpus:
				if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
				dreamtri[prev2+prev].inc(letter)
				dreambi[prev].inc(letter)
				dreamuni.inc(letter)
				prev2= prev
				prev = letter
		# get relative entropy or skew divergence of pair
		if (RE): testval=rel_ent(testuni,testbi,testtri,dreamuni,dreambi,dreamtri)
		else: testval=skew_div(testuni,testbi,testtri,dreamuni,dreambi,dreamtri)
		# if within threshold, leave clusters the same
		if (testval<thresh): continue
		# otherwise remove old cluster and add new clusters for pair
		nums.append(docs)
		unigrams.append(dreamuni)
		bigrams.append(dreambi)
		trigrams.append(dreamtri)
		nums.append([testdoc])
		unigrams.append(testuni)
		bigrams.append(testbi)
		trigrams.append(testtri)
		remove=[]
		remove.extend(docs)
		remove.append(testdoc)
		remove.sort()
		ind = nums.index(remove)
		nums.pop(ind)
		unigrams.pop(ind)
		bigrams.pop(ind)
		trigrams.pop(ind)
# do one more pass to attempt to reintegrate "dreamed-away" documents, as above
for loopctr in range(1):
	# cross-check new clusters
	remove = []
	for i in range(len(unigrams)):
		for j in range(i+1,len(unigrams)):
			if (j>len(nums)): break
			if (RE): testval = rel_ent(unigrams[i],bigrams[i],trigrams[i],unigrams[j],bigrams[j],trigrams[j])
			else: testval = skew_div(unigrams[i],bigrams[i],trigrams[i],unigrams[j],bigrams[j],trigrams[j])
			if (testval<thresh):
				for k in nums[j]:
					corpus = filelines[k-1][:-1]+'__'
					corpus.replace('\s+','__')
					prev2= '_'
					prev = '_'
					for letter in corpus:
						if (re.match(r'[0-9,.!?():;*\'\"\-\/\\]',letter)!=None): continue
						trigrams[i][prev2+prev].inc(letter)
						bigrams[i][prev].inc(letter)
						unigrams[i].inc(letter)
						prev2= prev
						prev = letter
				nums[i].extend(nums[j])
				nums[i].sort()
				remove.append(j)
		remove.sort()
		remove.reverse()
		for k in remove:
			nums.remove(nums[k])
			unigrams.pop(k)
			bigrams.pop(k)
			trigrams.pop(k)
		remove=[]
	print nums
