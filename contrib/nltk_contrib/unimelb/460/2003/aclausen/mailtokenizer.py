import nltk.corpus
import nltk.tokenizer
import nltk.token

import email
import re
import string


# Get the compile list of most frequent words form top.txt
def init_frequent():
	f = open('top.txt', 'r')
	dict = {}
	words = f.read()
	f.close()
	words = words.lower().split('\n')

	for word in words:
		dict[word] = 1
	return dict

frequent_words = init_frequent()

def intersperse(start, mid, end, lists):
	if len(lists) == 0:
		return []
	result = start + lists[0]
	for list in lists[1:len(lists)]:
		result += mid + list
	result += end
	return result

# DESIGN PHILOSOPHY
#	I designed this with informal electronic text in mind, such as
#	email and SMS.  Therefore, it handles things like email addresses,
#	smiley faces, and odd use of punctuation like ?!?!.
#
#	I also usually chose rules that would yield words closest-as-
#	sensibly-possible to what you would find in a dictionary.
#	eg: better-than-sex is 5 tokens.  U.S.A. is one token.

class MailTokenizer(nltk.tokenizer.RETokenizer):
	def __init__(self):
		emailch = r'[-a-zA-Z0-9.]'
		# rules are processed (and prefered) top to bottom.
		rules = [
			# internal use (represents deleted quotations)
			r'\[quote\]',

			# email: require exactly one @ and at least one .
			# motivation: usually required in literal form
			r'<?[a-zA-Z]' + emailch + r'*@' + emailch +
				r'+\.[-a-zA-Z0-9]+>?',

			# URLs:
			r'[fh]t?tp://[^ \n\t]*',

			# NLTK BROKEN... waiting for patch to be applied
			# phone numbers: (too hard with spaces!)
			#r'[#+(][0-9][-0-9()]+-[0-9()]'

			# common abbreviations (hard to disambiguate with
			# end-of-sentence)
			r'etc.',

			# elipsis
			r'\.\.\.',

			# repeated punctuation often used for emphasis / ascii
			# art eg: ?!?!,  ***WARNING***,  ////\\\\
			r'-+',
			r'=+',
			r'_+',
			r'[?!]+',
			r'\*+',
			r'\++',
			r'/+',
			r'\\+',

			# some common smiley faces
			r'\(:', r':\)', r'B\)', r':-\)', r';\)', r';-\)', ':p',

			# high-precedence symbols (ones that don't "attach"
			# much)
			r'["()<>{}\[\]#%&;:|~^]',

			# ,. with space identifies punctuation/sentence usage.
			# (as opposed to A.P.C. or 12,300)
			r'[,.](?=\s)',

			# currencies  ($R, $AU, US$)
			r'[a-zA-Z]*\$[a-zA-Z]*',

			# ordinals
			#r'[0-9]+(?:st|nd|rd|th)',

			# numbers  (12,300.40)
			r'[0-9]+(?:[,.][0-9]+)*',

			# hex/octal numbers
			r'[0-9][0-9a-fA-FxX]+',

			# A.P.C. acronyms
			r'I(?=\.(?:\s|$))',	# avoid confusion: "you and I."
			r'(?:[a-zA-Z]\.)+',

			# general words (including TI83, including sus' and
			# her's) it is probably a good idea to separate her's
			# into [her]['s] - but it's rather difficult to do with
			# regular expressions.  consider: "the dog next door's
			# kennel".  (why don't REs have complement and
			# intersection?!)
			r'[a-zA-Z\'][a-zA-Z0-9\']*',

			# low-precedence symbols (ones that "attach" lots)
			r'[$@\']',
		]

		rexpr = intersperse("(?:", ")|(", ")", rules)
		nltk.tokenizer.RETokenizer.__init__(self, rexpr)


# MailCleanTokenizer turns email messages into format required by
# the trainers and classifiers. It tokenizes emails and implements
# some censorship of the data.

class MailCleanTokenizer(nltk.tokenizer.TokenizerI):
	def __init__(self, names):
		self._names = names
		# censorship rules
		rules = [
			(r'<?[a-zA-Z].*@.*\..*',	'[email]'),
			(r'[fh]t?tp://.*',		'[url]'),
			(r'[0-9].*',		        '[number]'),
		]
		self._rules = [ (re.compile(rule), symbol)
				for (rule, symbol) in rules ]
		self._tokenizer = MailTokenizer()
		self._quote_regexp = re.compile(r'^\|?>.*$', re.M)

	# tokenize the body of an email message, with censorship

	def tokenize(self, raw_text, source=None):
		mail = email.message_from_string(raw_text)
		body = mail.get_payload()
		unquoted_body = re.sub(self._quote_regexp, '[quote]', body)
		tokenized_body = self._tokenizer.tokenize(unquoted_body)
		for token in tokenized_body:
			self._simplify_token(token)
		return tokenized_body

	# Perform censorship on a name if necessary
	def _simplify_token(self, token):
		rule_matched = 0	
		toktype = token.type().lower()
		for rule in self._rules:
			if rule[0].match(toktype):
				token._type = rule[1]	
				rule_matched = 1	

		if (not rule_matched and self._names.has_key(toktype)
				and not frequent_words.has_key(toktype)):
			token._type = '[name]'

	# get names that appear in address field (so they can be
	# censored in the email body).  Thi
	def get_header_names(self, mail):
		names = [] 
		names += self._tokenizer.tokenize(mail.get('To', ''))
		names += self._tokenizer.tokenize(mail.get('From', ''))
		names += self._tokenizer.tokenize(mail.get('Cc', ''))
		names = [name.type().lower() for name in names 
				if not '@' in name.type() and name.type()[0] 
							in string.ascii_letters]

		dict  = {}
		for name in names:
			dict[name] = 1 	

		return dict

#-------------------------------------------------------------------------

# determine the top 1000 words from a newsgroup

def top_1000(filename):
	from nltk.probability import FreqDist
	fdist = FreqDist()

	newsgroups = nltk.corpus.twenty_newsgroups
	items = [newsgroups.read(item) for item
	 	in newsgroups.items('soc.religion.christian')]

	tokenizer = MailTokenizer()
	tokens = []

	for item in items:
		mail = email.message_from_string(item)
		body = mail.get_payload()
		tokens += tokenizer.tokenize(body)

	for token in tokens:
		fdist.inc(token.type().lower())

	samples = [(fdist.count(s), s) for s in fdist.samples()]
	samples.sort()
	samples.reverse()

	f = open(filename, 'w')
	if len(samples) < 1000:
		for x in samples: 
			f.write(x[1])
			f.write('\n')	
		#return list2dict([s[1] for s in samples])
	else:
		for x in samples[0:1000]:
			f.write(x[1])
			f.write('\n')	
		#return list2dict([s[1] for s in samples[0:1000]])	



#--------------------------------------------------------------------#



