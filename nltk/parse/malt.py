# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Liling Tan <alvations@gmail.com>
#
# Copyright (C) 2001-2015 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import print_function

import os
import fnmatch
import tempfile
import glob
from operator import add
from functools import reduce
import subprocess

from nltk.tag import RegexpTagger
from nltk.tokenize import word_tokenize

from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph

def find_jars_within_path(path_to_jars):
	return [os.path.join(root, filename) 
			for root, dirnames, filenames in os.walk(path_to_jars) 
			for filename in fnmatch.filter(filenames, '*.jar')]

def create_regex_tagger():
	cardinals = 	(r'^-?[0-9]+(.[0-9]+)?$', 'CD') # cardinal numbers
	articles = 		(r'(The|the|A|a|An|an)$', 'AT') # articles
	adjectives = 	(r'.*able$', 'JJ') # adjectives
	nounfromadj = 	(r'.*ness$', 'NN') # nouns formed from adjectives
	adverbs = 		(r'.*ly$', 'RB') # adverbs
	pluralnouns = 	(r'.*s$', 'NNS')# plural nouns
	gerunds = 		(r'.*ing$', 'VBG') # gerunds
	pastverbs = 	(r'.*ed$', 'VBD') # past tense verbs
	nouns = 		(r'.*', 'NN') # nouns (default)
	return RegexpTagger([cardinals, articles, adjectives, 
						nounfromadj, adverbs, pluralnouns, 
						gerunds, pastverbs, nouns])
			
class MaltParser(ParserI):
	def __init__(self, path_to_maltparser, model=None, tagger=None, working_dir=None, additional_java_args=[]):
		"""
		An interface for parsing with the Malt Parser.

		:param model: The name of the pre-trained model with .mco file 
		extension. If provided, training will not be required.
		(see http://www.maltparser.org/mco/mco.html and 
		see http://www.patful.com/chalk/node/185)
		:type mco: str
		:param tagger: The tagger used to POS tag the raw string before 
		formatting to CONLL format. It should behave like `nltk.pos_tag`
		:type tagger: function
		:param additional_java_args: This is the additional Java arguments that 
		one can use when calling Maltparser, usually this is the heapsize 
		limits, e.g. `additional_java_args=['-Xmx1024m']`
		(see http://goo.gl/mpDBvQ)
		:type additional_java_args: list
		:param path_to_maltparser: The path to the maltparser directory that 
		contains the maltparser-1.x.jar
		:type path_to_malt_binary: str
		"""
		# Collects all the jar files found in the MaltParser distribution.
		self.malt_jars = find_jars_within_path(path_to_maltparser)
		# Initialize additional java arguments.
		self.additional_java_args = additional_java_args

		# Set the working_dir parameters i.e. `-w` from MaltParser's option.
		self.working_dir = tempfile.gettempdir() if working_dir is None else working_dir
		
		# Initialize POS tagger.
		if tagger is not None:
			self.tagger = tagger
		else: # Use a default Regex Tagger if none specified.
			self.tagger = create_regex_tagger()
			
		# Initialize maltparser model.
		self.mco = model
		if self.mco == None:
			self.train()
		self._trained = True
	

	def tagged_parse_sents(self, sentences, verbose=False):
		"""
		Use MaltParser to parse multiple sentences. Takes multiple sentences
		where each sentence is a list of (word, tag) tuples.
		The sentences must have already been tokenized and tagged.

		:param sentences: Input sentences to parse
		:type sentence: list(list(tuple(str, str)))
		:return: iter(iter(``DependencyGraph``)) the dependency graph 
		representation of each sentence
		"""
		if not self._trained:
			raise Exception("Parser has not been trained.  Call train() first.")
			
		input_file = tempfile.NamedTemporaryFile(prefix='malt_input.conll', 
										dir=self.working_dir, delete=False)
		output_file = tempfile.NamedTemporaryFile(prefix='malt_output.conll', 
										dir=self.working_dir, delete=False)

		try:
			# Convert list of sentences to CONLL format.
			for sentence in sentences:
				for (i, (word, tag)) in enumerate(sentence, start=1):
					input_str = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' %\
						(i, word, '_', tag, tag, '_', '0', 'a', '_', '_')
					input_file.write(input_str.encode("utf8"))
				input_file.write(b'\n\n')
			input_file.close()

			# Generate command to run maltparser.
			cmd =self.generate_parse_command(input_file.name, 
												output_file.name)
			ret = self._execute(cmd, verbose)

			if ret != 0:
				raise Exception("MaltParser parsing (%s) failed with exit "
					"code %d" % (' '.join(cmd), ret))
			# Must return iter(iter(Tree))
			return (iter([dep_graph]) for dep_graph in 
				DependencyGraph.load(output_file.name))

		finally:
			# Deletes temp files created in the process.
			input_file.close()
			os.remove(input_file.name)
			output_file.close()
			os.remove(output_file.name)
			
	def generate_parse_command(self, inputfilename, outputfilename):
		"""
		This function generates the maltparser command use at the terminal.

		:param inputfilename: path to the input file
		:type inputfilename: str
		:param outputfilename: path to the output file
		:type outputfilename: str
		"""

		cmd = ['java']
		cmd+= self.additional_java_args # Adds additional java arguments.
		cmd+= ['-cp', ':'.join(self.malt_jars)] # Adds classpaths for jars
		cmd+= ['org.maltparser.Malt'] # Adds the main function.
		cmd+= ['-c', self.mco] # Adds the model file.
		cmd+= ['-i', inputfilename]
		cmd+= ['-o', outputfilename]
		cmd+= ['-m', 'parse'] # Option use to generate parses.
		return cmd
		
	@staticmethod
	def _execute(cmd, verbose=False):
		output = None if verbose else subprocess.PIPE
		p = subprocess.Popen(cmd, stdout=output, stderr=output)
		return p.wait()
		

	def parse_sents(self, sentences, verbose=False):
		"""
		Use MaltParser to parse multiple sentences. 
		Takes a list of sentences, where each sentence is a list of words.
		Each sentence will be automatically tagged with this 
		MaltParser instance's tagger.

		:param sentences: Input sentences to parse
		:type sentence: list(list(str))
		:return: iter(DependencyGraph)
		"""
		tagged_sentences = [self.tagger.tag(sentence) for sentence in sentences]
		return iter(self.tagged_parse_sents(tagged_sentences, verbose))	

	def tagged_parse(self, sentence, verbose=False):
		"""
		Use MaltParser to parse a sentence. Takes a sentence as a list of
		(word, tag) tuples; the sentence must have already been tokenized and
		tagged.

		:param sentence: Input sentence to parse
		:type sentence: list(tuple(str, str))
		:return: iter(DependencyGraph) the possible dependency graph 
		representations of the sentence
		"""
		return next(self.tagged_parse_sents([sentence], verbose))

		
	def train(self, depgraphs, verbose=False):
		"""
		Train MaltParser from a list of ``DependencyGraph`` objects

		:param depgraphs: list of ``DependencyGraph`` objects for training input data
		"""
		input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
										dir=self.working_dir, delete=False)
		try:
			input_str = ('\n'.join(dg.to_conll(10) for dg in depgraphs))
			input_file.write(input_str.encode("utf8"))
			input_file.close()
			self.train_from_file(input_file.name, verbose=verbose)
		finally:
			input_file.close()
			os.remove(input_file.name)


	def train_from_file(self, conll_file, verbose=False):
		"""
		Train MaltParser from a file

		:param conll_file: str for the filename of the training input data
		"""
		if not self._malt_bin:
			raise Exception("MaltParser location is not configured. ''Call config_malt() first.")

		# If conll_file is a ZipFilePathPointer, then we need to do some extra
		# massaging
		if isinstance(conll_file, ZipFilePathPointer):
		input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
		dir=self.working_dir,
		delete=False)
		try:
		conll_str = conll_file.open().read()
		conll_file.close()
		input_file.write(conll_str)
		input_file.close()
		return self.train_from_file(input_file.name, verbose=verbose)
		finally:
		input_file.close()
		os.remove(input_file.name)

		cmd = ['java', '-cp', self._malt_bin, self._malt_dependencies, 
		'org.maltparser.Malt', '-w', self.working_dir,
		'-c', self.mco, '-i', conll_file, '-m', 'learn']

		ret = self._execute(cmd, verbose)
		if ret != 0:
		raise Exception("MaltParser training (%s) "
		"failed with exit code %d" %
		(' '.join(cmd), ret))

		self._trained = True
