#!/usr/bin/python
# -*- coding: utf8 -*-

import os
from chasentoken import *
from netypes import *

# example question: q = "北海道の岩見沢の年間平均積雪量は？"
def tokenize_question(q):
	"""Takes a Japanese utf8 question as input and returns a sentence token,
	where each 'word' (word acording to ChaSen) has it's TEXT, POS TAG, BASE form
	and READing represented.
	"""
	
	# Tag the question with ChaSen. Need to translate to and from eucjp encoding
	# since I can't make ChaSen read or produce utf8 encoding
	cmd = 'iconv -f utf8 -t eucjp - |chasen |iconv -f eucjp -t utf8 -'
	cmd2 = 'echo "' + q + '"|' + cmd
	out = os.popen(cmd2)
	sentence = ''
	line = out.readline()
	while(line != ''):
		sentence = sentence + line
		line = out.readline()
	reader = ChasenTokenReader()

	# Tokenise the output of ChaSen
	tok = reader.read_token(sentence)
	
	return tok

# key words that indicate a question type 
questionclass = {}
questionclass['誰'] = ['誰', 'だれ']
questionclass['何年'] = ['何年', '何月', '何日']
questionclass['何人'] = ['何人']
questionclass['何時'] = ['何時', '何分']
questionclass['何％'] = ['何％', '何パーセント']
questionclass['いくつ'] = ['いくつ', '何個', '幾つ']
questionclass['いくら'] = ['いくら', '何ドル', '何円']
questionclass['どこ'] = ['どこ', '何処', '何所']


def classify_question(tok):
	""" Classify the tokenised question as one of the question types:
	'いくつ'				how many
	'いくら' 			how much
	'いつ'				when
	'どう'				how
	'どこ'				where
	'どちら'				which
	'どの'				which/what
	'どれくらい'		how long/far/much
	'どんな'				what kind of
	'なに＋ひらがな'	what (with hiragana center word)
	'なに＋漢字'		what (with kanji center word)
	'何％'				what percentage
	'何時'				what time
	'何人'				how many people
	'何年'				date
	'誰'					who
	'は'					what

	Return <UNK> if it can't classify.
	"""
	nani = -1
	nan = -1
	lastwa = -1
	itsu = -1
	ikutsu = -1
	ikura = -1
	dou = -1
	doko = -1
	dochira = -1
	dore = -1
	dono = -1
	donna = -1

	inquotes = 0
	
	# look at each 'word' in turn
	for i, word in enumerate(tok['SENTS'][0]['WORDS']):

		# in quotes is the state of being within quotes,
		if word['TEXT'] == '「':
			inquotes = 1
		if word['TEXT'] == '」':
			inquotes = 0
			
		#strip 'か' if final word (か being a question marker)
		#Japanese characters take up 3 bytes
		if word['TEXT'][-3:] == 'か' and len(tok['SENTS'][0]['WORDS']) == i+2:
			newword = word['TEXT'][:-3]
		else:
			newword = word['TEXT']
		if inquotes == 0:
		# ignore keywords if between quotes
			for key in questionclass.keys():
				for word in questionclass[key]:
					if newword.find(word) > -1:
						return key
		#if we find 何 (what) or it's phonetic equivalents, record the word 
		#position for further processing
		if newword.find('何') > -1 or newword == 'なに' or newword == 'なん' or newword == 'なんと' or newword == 'なんで':
			nani = i
		#record the last found は (topical marker)
		if newword == 'とは':
			lastwa = i
		if newword == 'は':
			lastwa = i

		#record index of question words for use later, if a better pointer is not
		#found
		if newword == 'いつ':
			itsu = i
		if newword == 'いつまで':
			itsu = i
		if newword == 'いつ頃':
			itsu = i
		if newword == 'いつごろ':
			itsu = i
		if newword == 'いつか':
			if tok['SENTS'][0]['WORDS'][i+1]['TEXT'] == 'ら':
				itsu = i
		if newword == 'どう':
			dou = i
		if newword == 'どういう':
			dou = i
		if newword == 'どこ':
			doko = i
		if newword == 'とどこ':
			doko = i
		if newword == 'どこで':
			doko = i
		if newword == 'どちら':
			dochira = i
		if newword == 'どれ':
			dore = i
		if newword == 'どれくらい':
			dore = i
		if newword == 'どの':
			dono = i
		if newword == 'どんな':
			donna = i
		if newword == 'どんなもの':
			donna = i
		if newword == 'どのような':
			donna = i
	
	#if 何 was found, check what followed it 
	if nani > -1:
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == 'パーセント':
			return '何％'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '％':
			return '何％'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '処':
			return 'どこ'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '所':
			return 'どこ'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '個':
			return 'いくつ'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '年ぶり':
			return '何年'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '年度':
			return '何年'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '年前':
			return '何年'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'].find('月') > -1:
			return '何年'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == 'ねん':
			return '何年'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '時':
			return '何時'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '時間':
			return '何時'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '時に':
			return '何時'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == 'じ':
			return '何時'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == 'ドル':
			return 'いくら'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] == '円':
			return 'いくら'
		if tok['SENTS'][0]['WORDS'][nani]['TEXT'].find('なん') > -1 and tok['SENTS'][0]['WORDS'][nani]['TEXT'] != 'なん':
			# check if the following character is a hiragana character
			if tok['SENTS'][0]['WORDS'][nani]['TEXT'][6:] <= '\xe3\x82\x96':
				return 'なに＋ひらがな'
			else:
				return 'なに＋漢字'
		if tok['SENTS'][0]['WORDS'][nani]['TEXT'].find('何') > -1 and tok['SENTS'][0]['WORDS'][nani]['TEXT'] != '何':
			if tok['SENTS'][0]['WORDS'][nani]['TEXT'][3:] <= '\xe3\x82\x96':
				return 'なに＋ひらがな'
			else:
				return 'なに＋漢字'
		if tok['SENTS'][0]['WORDS'][nani+1]['TEXT'] <= '\xe3\x82\x96':
			return 'なに＋ひらがな'
		else:
			return 'なに＋漢字'

	#if は was the last word found before a ？, return type は
	if lastwa == len(tok['SENTS'][0]['WORDS']) - 2:
		return 'は'

	#if no better pointer has been found, return question word type	
	if itsu > -1:
		return 'いつ'
	if ikutsu > -1:
		return 'いくつ'
	if ikura > -1:
		return 'いくら'
	if	dou  > -1:
		return 'どう'
	if	doko  > -1:
		return 'どこ'
	if	dochira  > -1:
		return 'どちら'
	if	dore  > -1:
		return 'どれくらい'
	if	dono  > -1:
		if tok['SENTS'][0]['WORDS'][dono+1]['TEXT'] == 'くらい':
			return 'どれくらい'
		else:
			return 'どの'
	if	donna  > -1:
		return 'どんな'
	# if we don't find anything that helps, return <UNK>
	return '<UNK>'

def eval(debug=False, datadir="/home/rdrid/japaneseresources/data"):
	#total questions seen
	total = 0
	#total questions not <UNK>
	totalknown = 0
	#total question types correctly classified
	correct = 0
	#total answer types correctly classified
	necorrect = 0
	#lenient ne eval correct
	lenientne = 0
	
	#for each question
	for item in crl.items():
		total += 1
		#find gold standard question type
		fname = datadir + "/questiontypes/" + item
		f = open(fname, "r")
		goldtype = f.read()
		f.close()
		goldtype = goldtype.splitlines()[0]
		
		#find gold standard answer type
		fname2 = datadir + "/netypes/" + item
		f = open(fname2, "r")
		goldnetype = f.read()
		f.close()
		goldnetype = goldnetype.splitlines()[0]
		
		#read and tokenise question from tagged corpus
		token = crl.read(item)

		# classify question type
		type = classify_question(token)

		#classify answer type
		netype = classify_answer(token, type)

		if type != '<UNK>':
			totalknown += 1

		# if question type is not correct
		if type != goldtype:
			#print the gold standard type and the classified type, if debug is on
			if debug == True:
				print item,
				print goldtype,
				print type
		else:
			#count correct
			correct += 1

		# if answer type is correct
		if netype == goldnetype:
			# count correct
			necorrect += 1
			
		if parents(ner, netype).count(goldnetype) > 0:
			lenientne += 1
		else:
			if parents(ner, goldnetype).count(netype) > 0:
				lenientne += 1
			else:
				if search_tree(ner,netype).node == search_tree(ner,goldnetype).node:
					lenientne += 1
				else:
					if debug == True:
						print item,
						print type,
						print netype,
						print goldnetype
				
	print
	print "%d/%d of question types correct" % (correct, total)
	print "%d/%d precision (correct question types when type was not <UNK>)" % (correct, totalknown)
	print "%d/%d answer types correct" % (necorrect, total)
	print "%d/%d answer types correct (lenient evaluation)" % (lenientne, total)

def classify_answer(token, type):
	"""Classify the answer type as one of the named entity types in the topology
	designed by Satoshi Sekine (New York University).

	"""
	
	if type == '誰':
		return '人名'
	if type == 'いくら':
		return '金額表現'
	if type == 'いつ':
		return '日付表現'
	if type == '何％':
		return '割合表現'
	if type == '何年':
		return '日付表現'
	if type == '何人':
		return '人数'
	if type == '何時':
		return '時刻表現'
		
	if type == 'いくつ':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-2]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '組織数'
		
	if type == 'どこ':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'].find('国') > -1:
				return '国名'
			if word['TEXT'] == type or word['TEXT'] == 'は':
				centerword = token['SENTS'][0]['WORDS'][i-1]['TEXT']
				centerword = centerword+'名'
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '地名'

	if type == 'どう':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-2]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return 'グループ名'
	if type == 'どちら':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-2]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '物質名'
	
	if type == 'どの':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i+1]['TEXT']
				centerword = centerword+'名'
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '国名'
	
	if type == 'どれくらい':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-2]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '年期間'
		
	if type == 'どんな':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-2]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '方式制度名'
	if type == 'なに＋ひらがな':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i+1]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '製品名'
	if type == 'なに＋漢字':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i+1]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '製品数'
	if type == 'は':
		for (i,word) in enumerate(token['SENTS'][0]['WORDS']):
			if word['TEXT'] == type:
				centerword = token['SENTS'][0]['WORDS'][i-1]['TEXT']
				if lookup.has_key(centerword):
					centerword = lookup[centerword]
				if search_tree(ner, centerword):
					return centerword
		return '人名'
	
	return '日付表現'

def analyse_question(q):
	"""
	Given a Japanese question (in UTF-8), reports the question type and expected
	answer type.
	"""
	tok = tokenize_question(q)
	type = classify_question(tok)
	answertype = classify_answer(tok, type)

	print "The question: %s " % q
	print "has a question type %s" % type
	print "and an expected answer type of %s" % answertype

