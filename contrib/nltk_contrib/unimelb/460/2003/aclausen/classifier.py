import email
import mailtokenizer
import progress

import nltk.corpus
import nltk.tokenizer

def maybe(item, no_case):
	if item is None:
		return no_case
	return item

# A convenience class :)
# Carefully structured to pickle effiently...
class SubCorpusReader(nltk.corpus.SimpleCorpusReader):
	def __init__(self, parent_corpus,
		     items=None, groups=None, default_tokenizer=None):
		self._parent_corpus = parent_corpus
		self._default_tokenizer = maybe(
			default_tokenizer, parent_corpus._default_tokenizer)
		items = maybe(items, list(parent_corpus.items()))
		self._groups = {}
		for group in list(maybe(groups, parent_corpus.groups())):
			self._groups[group] = [
				item for item in parent_corpus.items(group)
				if item in items
			]

	def name(self): return self._parent_corpus.name()
	def description(self): return self._parent_corpus.description()
	def licence(self): return self._parent_corpus.licence()
	def copyright(self): return self._parent_corpus.copyright()
	def installed(self): return self._parent_corpus.installed()
    	def path(self, item): return self._parent_corpus.path(item)
    	def open(self, item): return self._parent_corpus.open(item)
    	def read(self, item): return self._parent_corpus.read(item)
    	def readlines(self, item): return self._parent_corpus.readlines(item)
    	def tokenize(self, item, tokenizer=None):
		if tokenizer is None:
			tokenizer = self._default_tokenizer
		return self._parent_corpus.tokenize(item, tokenizer)

    	def groups(self):
		return self._groups.keys()

	def items(self, group=None):
		if group is None:
			return self._groups.keys()
		return tuple(self._groups[group])

# Joins groups together.  Eg: ('male', *) => 'male'
# Exactly like quotient groups/rings/graphs!
# Also like "group by" in SQL, which is represented by "/" in relational algebra
class QuotientCorpusReader(SubCorpusReader):
	def __init__(self, parent_corpus, get_coset_name):
		self._parent_corpus = parent_corpus
		self._default_tokenizer = parent_corpus._default_tokenizer
		self._groups = {}
		for group in parent_corpus.groups():
			self._groups[get_coset_name(group)] = []
		for group in parent_corpus.groups():
			self._groups[get_coset_name(group)] \
				+= parent_corpus.items(group)

# A class to deal with male.txt and female.txt lists of names.
class MFNames:
	def __init__(self):
		self.names = {}
		for gender in ['male', 'female']:
			for name in self.read_names(gender):
				if self.names.has_key(name):
					self.names[name].append(gender)
				else:
					self.names[name] = [gender]

	def read_names(self, gender):
		raw_text = nltk.corpus.names.read(gender + '.txt')
		return raw_text.lower().split('\n')

	def is_name(self, name):
		return self.names.has_key(name)
	
	def get_name_gender(self, name):
		if len(self.names.get(name, [])) != 1:
			return None
		return self.names[name][0]


# MFCorpusReader generates a corpus and methods for the problem of
# gender text classification.

class MFCorpusReader(SubCorpusReader):

	# MFCorpusReader takes a parent_corpus for labelling, and 
	# an optional default_tokenier for the corpus.
	
	def __init__(self, parent_corpus, default_tokenizer=None):
		self._parent_corpus = parent_corpus
		self._default_tokenizer = maybe(
			default_tokenizer, parent_corpus._default_tokenizer)

		self._groups = {}

		header_tokenizer = mailtokenizer.MailTokenizer()
		names = MFNames()

		item_count = 0
		for group in parent_corpus.groups():
			item_count += len(parent_corpus.items(group))
		done = 0

		# Progress meter for your enjoyment!

		timer = progress.SimpleTimer()
		timer.set_task('classifying gender')
		timer.start()

		# label items in each newsgroup in parent_corpus
		# as male of female.

		for group in list(parent_corpus.groups()):
			self._groups[('male', group)] = []
			self._groups[('female', group)] = []
			for item in parent_corpus.items(group):
				timer.update(1.0 * done / item_count)
				done += 1
				raw_text = parent_corpus.read(item)
				mail = email.message_from_string(raw_text)
				from_line = header_tokenizer.tokenize(
						mail['From'])
				if len(from_line) < 3:
					continue

				# Decide gender by first name.		
				name = from_line[2].type().lower()
				gender = names.get_name_gender(name)
				if gender is None:
					continue
				self._groups[(gender, group)].append(item)
		timer.update(1.0)
		timer.stop()
		print ''


class Classifier:
	# constructs a classifier from a corpus
	def __init__(self, corpus=None):
		if corpus is not None:
			self.train(corpus)
			self.groups = list(corpus.groups())   

	def train(self, corpus):
		assert 0, "Abstract class"

	# returns a list of (group, score) tuples.
	def classify(self, text):
		assert 0, "Abstract class"

class ClassifierTester:
	def __init__(self, testing_corpus):
		self._testing_corpus = testing_corpus

        def print_tokens(self, tokens):
                str = ''
                for token in tokens:
                        str += token.type() + ' '
                print str, '\n\n'


	# test a classifier and output confusion matrix entries.

	def test(self, classifier):

		# Determine our best choice of classification for a text
		# by the group that resulted in the lowest score	

		def get_classification(results):
			smallest = results.items()[0][0]
			for group in results.keys():
				if results[group] < results[smallest]:
					smallest = group
			return smallest

		matrix = {}

		# initialize confusion matrix

		for a in self._testing_corpus.groups():
			for b in classifier.groups:
				matrix[(a, b)] = 0

		# progress meter again!

		timer = progress.SimpleTimer()
		timer.set_task('testing')
		timer.start()
		item_num = 0
		total_items = 0
		for group in self._testing_corpus.groups():
			total_items += len(self._testing_corpus.items(group))

		for group in self._testing_corpus.groups():
			for item in self._testing_corpus.items(group):
				timer.update(1.0 * item_num / total_items)
				item_num += 1

				# classify items in testing corpus 
				tokens = self._testing_corpus.tokenize(item)
				result = classifier.classify(tokens)
				result_group = get_classification(result)

				# add to the confusion matrix, group
				# is the true classification.
				matrix[(group, result_group)] += 1

		timer.update(1.0)
		timer.stop()
		print ''

		# print confusion matrix
		group_pairs = matrix.keys()
		group_pairs.sort()
		for group_pair in group_pairs:
			print "%s:\t%d" % (str(group_pair), matrix[group_pair])

