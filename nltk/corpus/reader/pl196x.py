# Natural Language Toolkit:
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Piotr Kasprzyk <p.j.kasprzyk@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import os
import re

from nltk import compat
from nltk import tokenize, tree

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.corpus.reader.xmldocs import XMLCorpusReader

# (?:something) -- non-capturing parentheses!

PARA = re.compile(r'<p(?: [^>]*){0,1}>(.*?)</p>')
SENT = re.compile(r'<s(?: [^>]*){0,1}>(.*?)</s>')

TAGGEDWORD = re.compile(r'<([wc](?: [^>]*){0,1}>)(.*?)</[wc]>')
WORD   =   re.compile(r'<[wc](?: [^>]*){0,1}>(.*?)</[wc]>')

TYPE = re.compile(r'type="(.*?)"')
ANA  = re.compile(r'ana="(.*?)"')

TEXTID = re.compile(r'text id="(.*?)"')


class TEICorpusView(StreamBackedCorpusView):
	def __init__(self, corpus_file,
					tagged, group_by_sent, group_by_para,
					tagset=None, headLen=0, textids=None):
		self._tagged = tagged
		self._textids = textids

		self._group_by_sent = group_by_sent
		self._group_by_para = group_by_para
		# WARNING -- skip header
		StreamBackedCorpusView.__init__(self, corpus_file, startpos=headLen)

	_pagesize = 4096

	def read_block(self, stream):
		block = stream.readlines(self._pagesize)
		block = concat(block)
		while (block.count('<text id') > block.count('</text>')) \
				or block.count('<text id') == 0:
			tmp = stream.readline()
			if len(tmp) <= 0:
				break
			block += tmp

		block = block.replace('\n','')

		textids = TEXTID.findall(block)
		if self._textids:
			for tid in textids:
				if tid not in self._textids:
					beg = block.find(tid)-1
					end = block[beg: ].find('</text>')+len('</text>')
					block = block[ :beg]+block[beg+end: ]

		output = []
		for para_str in PARA.findall(block):
			para = []
			for sent_str in SENT.findall(para_str):
				if not self._tagged:
					sent = WORD.findall(sent_str)
				else:
					sent = list(map(self._parse_tag, TAGGEDWORD.findall(sent_str)))
				if self._group_by_sent:
					para.append(sent)
				else:
					para.extend(sent)
			if self._group_by_para:
				output.append(para)
			else:
				output.extend(para)
		return output

	def _parse_tag(self, tag_word_tuple):
		(tag, word) = tag_word_tuple
		if tag.startswith('w'):
			tag = ANA.search(tag).group(1)
		else: # tag.startswith('c')
			tag = TYPE.search(tag).group(1)
		return (word, tag)


class Pl196xCorpusReader(CategorizedCorpusReader, XMLCorpusReader):

	headLen = 2770

	def __init__(self, *args, **kwargs):
		if 'textid_file' in kwargs: self._textids = kwargs['textid_file']
		else: self._textids = None

		XMLCorpusReader.__init__(self, *args)
		CategorizedCorpusReader.__init__(self, kwargs)

		self._init_textids()

	def _init_textids(self):
		self._f2t = defaultdict(list)
		self._t2f = defaultdict(list)
		if self._textids is not None:
			for line in self.open(self._textids).readlines():
				line = line.strip()
				file_id, text_ids = line.split(' ', 1)
				if file_id not in self.fileids():
					raise ValueError('In text_id mapping file %s: %s '
									 'not found' % (catfile, file_id))
				for text_id in text_ids.split(self._delimiter):
					self._add_textids(file_id, text_id)

	def _add_textids(self, file_id, text_id):
		self._f2t[file_id].append(text_id)
		self._t2f[text_id].append(file_id)

	def _resolve(self, fileids, categories, textids=None):
		tmp = None
		if fileids is not None:
			if not tmp:
				tmp = fileids, None
			else:
				raise ValueError('Specify only fileids, categories or textids')
		if categories is not None:
			if not tmp:
				tmp = self.fileids(categories), None
			else:
				raise ValueError('Specify only fileids, categories or textids')
		if textids is not None:
			if not tmp:
				if isinstance(textids, compat.string_types): textids = [textids]
				files = sum((self._t2f[t] for t in textids), [])
				tdict = dict()
				for f in files:
					tdict[f] = (set(self._f2t[f]) & set(textids))
				tmp = files, tdict
			else:
				raise ValueError('Specify only fileids, categories or textids')
		return None, None

	def decode_tag(self, tag):
		# to be implemented
		return tag

	def textids(self, fileids=None, categories=None):
		"""
		In the pl196x corpus each category is stored in single
		file and thus both methods provide identical functionality. In order
		to accommodate finer granularity, a non-standard textids() method was
		implemented. All the main functions can be supplied with a list
		of required chunks---giving much more control to the user.
		"""
		fileids, _ = self._resolve(fileids, categories)
		if fileids is None: return sorted(self._t2f)

		if isinstance(fileids, compat.string_types):
			fileids = [fileids]
		return sorted(sum((self._f2t[d] for d in fileids), []))

	def words(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										False, False, False,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										False, False, False,
										headLen=self.headLen)
								for fileid in fileids])

	def sents(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										False, True, False,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										False, True, False,
										headLen=self.headLen)
								for fileid in fileids])

	def paras(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										False, True, True,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										False, True, True,
										headLen=self.headLen)
								for fileid in fileids])

	def tagged_words(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										True, False, False,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										True, False, False,
										headLen=self.headLen)
								for fileid in fileids])

	def tagged_sents(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										True, True, False,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										True, True, False,
										headLen=self.headLen)
								for fileid in fileids])

	def tagged_paras(self, fileids=None, categories=None, textids=None):
		fileids, textids = self._resolve(fileids, categories, textids)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]

		if textids:
			return concat([TEICorpusView(self.abspath(fileid),
										True, True, True,
										headLen=self.headLen,
										textids=textids[fileid])
								for fileid in fileids])
		else:
			return concat([TEICorpusView(self.abspath(fileid),
										True, True, True,
										headLen=self.headLen)
								for fileid in fileids])

	def xml(self, fileids=None, categories=None):
		fileids, _ = self._resolve(fileids, categories)
		if len(fileids) == 1: return XMLCorpusReader.xml(self, fileids[0])
		else: raise TypeError('Expected a single file')

	def raw(self, fileids=None, categories=None):
		fileids, _ = self._resolve(fileids, categories)
		if fileids is None: fileids = self._fileids
		elif isinstance(fileids, compat.string_types): fileids = [fileids]
		return concat([self.open(f).read() for f in fileids])

