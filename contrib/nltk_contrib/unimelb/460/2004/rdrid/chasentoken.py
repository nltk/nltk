"""
Token reader for reading tokens from strings in the format produced by the
Chasen Japanese Morphological Analysis program.
"""

from nltk.token import *
from nltk.tree import *
from nltk.tokenreader import TokenReaderI
from nltk import PropertyIndirectionMixIn
from nltk.corpus import SimpleCorpusReader
import re

class ChasenTokenReader(TokenReaderI, PropertyIndirectionMixIn):
	"""
	A token reader that splits a string of tagged text in the format produced by
	the Chasen Japanese Morphological Analysis program into tokens.
	"""
	def __init__(self, format=None, **property_names):
		PropertyIndirectionMixIn.__init__(self, **property_names)
		if format == None:
			self._format="%m\t%y\t%M\t%U(%P-)\t%T \t%F \n"
		else:
			#self._format= format
			# TODO allow it to take any ChaSen output format
			self._format="%m\t%y\t%M\t%U(%P-)\t%T \t%F \n"

	def read_token(self, s, add_contexts=False, add_locs=False, source=None):
		"""
		@return: A token containing the tagged token in the given string.
		@rtype: L{Token}
		@param add_contexts: If true, then add a subtoken context
			pointer to each subtoken.
		@param add_locs: If true, then add locations to each subtoken.
			Locations are based on sentence and word index numbers.
		@param source: The source for subtokens' locations (ignored
			unless C{add_locs=True}
		"""
		
		sentences = re.split('\s*\n\s*\n\s*', s)
		if sentences[0] == '': sentences = sentences[1:]
		if sentences[-1] == '': sentences = sentences[:-1]	
	
		sent_toks = [self._read_sent(sent, source) for sent in sentences]

		result = Token(SENTS=sent_toks)

		if add_locs:
			for sent_num, sent_tok in enumerate(sent_toks):
				sent_loc = SentIndexLocation(sent_num, source);
				sent_tok['LOC'] = sent_loc
				for word_num, word_tok in enumerate(sent_tok['WORDS']):
					word_loc = WordIndexLocation(word_num, sent_loc)
					word_tok['LOC'] = word_loc

		if add_contexts:
			for sent_num, sent_tok in enumerate(sent_toks):
				context = SubtokenContextPointer(result, 'SENTS', sent_num)
				sent_tok['CONTEXT'] = context
				for word_num, word_tok in enumerate(sent_tok['WORDS']):
					context = SubtokenContextPointer(result,'WORDS',word_num)
					word_tok['CONTEXT'] = context

		return result

	def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
		"""
		@return: A list containing a single token, containing the
			chunked tagged text that is encoded in the given CONLL
			2000 style string.
		@rtype: L{Token}
		@param add_contexts: If true, then add a subtoken context
			pointer to each subtoken.
		@param add_locs: If true, then add locations to each subtoken.
			Locations are based on sentence and word index numbers.
		@param source: The soruce for subtokens' locations (ignored
			unless C{add_locs=True}
		"""
		return [self.read_token(s, add_contexts, add_locs, source)]

	_LINE_RE = re.compile('(.*)\t(.*)\t(.*)\t(.*)\t(.*)\t(.*)')
	def _read_sent(self, s, source):
		words = []
		for lineno, line in enumerate(s.split('\n')):
			if line == '':
				continue;
			match = self._LINE_RE.match(line)
			if match is None:
				continue;
			(word, reading, base, pos, inftype, infform) = match.groups()

			word = Token(TEXT=word, TAG=pos, READ=reading, BASE=base)
			words.append(word)
		
		return Token(WORDS=words)
		
# set up crl corpus - tagged questions. Requires having a directory crl with the
# Chasen tagged data in your NLTK_CORPUS path
crl = SimpleCorpusReader('crl', 'crl/', r'0.*', token_reader=ChasenTokenReader())
