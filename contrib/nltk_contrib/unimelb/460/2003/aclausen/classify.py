import mailtokenizer
import modelclassifier
import cPickle
import sys


# Classify one or more emails given a (pickled) classifier 
#(model)

if len(sys.argv) < 3:
	print 'use: classify <classifier> { <email> }+\n'
	sys.exit(1)

# get classifier name:
classifier_file_name = sys.argv[1]
# get email names:
email_file_names = sys.argv[2:]
print 'loading classifier...'
(classifier, _training_info) = cPickle.load(file(classifier_file_name, 'r'))
mail_tokenizer = mailtokenizer.MailCleanTokenizer(mailtokenizer.frequent_words)

# classify each email
for email_file_name in email_file_names:
	raw_text = open(email_file_name, 'r').read()
	tokens = mail_tokenizer.tokenize(raw_text)
	classification = classifier.classify(tokens)
	print '%s:' % email_file_name
	for (group, score) in classification.items():
		print '\t%s:\t%0.2f' % (str(group), score)

