# Implement classifiers based on models
import classifier
import model
import progress

# ModelClassifier is an abstract class for classifiers that train several
# models (of type ModelI) - one for each classification category.
class ModelClassifier(classifier.Classifier):
	def __init__(self, corpus):
		self.groups = corpus.groups()
		self.train(corpus)

	# XXX: corpus is a parameter to work around a Python bug
	def train(self, corpus):
		timer = progress.SimpleTimer()
		timer.set_task('training')
		timer.start()

		item_done = 0
		item_count = 0
		for group in self.groups:
			item_count += len(corpus.items(group))

		for group in self.groups:
			for item in corpus.items(group):
				timer.update(1.0 * item_done / item_count)
				item_done += 1
				self._train_item(corpus, group, item)

		timer.update(1.0)
		timer.stop()
		print ''

	# internal: tells the model that "item" is an example of that category
	# a separate method in case it needs to be overridden...
	#
	# XXX: corpus is a parameter to work around a Python bug
	def _train_item(self, corpus, group, item):
		tokens = corpus.tokenize(item)
		self.models[group].train(tokens)

	# returns a dictionary mapping each category ("group") to a score.
	def classify(self, text):
		assert 0, "Abstract method"

# RelEntClassifier: a classifier based on a relative entropy measure
class RelEntClassifier(ModelClassifier):
	# RelEntClassifier takes a corpus builds a classifier
	# using n-grams of order, order
	def __init__(self, corpus, order):
		self.order = order
		self.models = {}
		for group in corpus.groups():
			self.models[group] = model.NGramModel(order)
		ModelClassifier.__init__(self, corpus)

	# Classify: score each classification group according
	# the relative entropy between a group model and the text input model.
	def classify(self, text):  
		text_model = model.NGramModel(self.order)
		text_model.train(text)
		scores = {}
		for group in self.groups:
			scores[group] = self.models[group].rel_entropy(
					text_model)
		return scores

# MinInfoClassifier: Classify text according to information content
# measure. 

class MinInfoClassifier(ModelClassifier):
	def __init__(self, corpus, max_order, freq_word_count):
		self.models = {}
		for group in corpus.groups():
			self.models[group] = model.PartialContextModel(
                                               max_order, freq_word_count)
		ModelClassifier.__init__(self, corpus)

	def classify(self, text):
		scores = {}
		for group in self.groups:
			scores[group] = self.models[group].info_content(text)
		return scores

