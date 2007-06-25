"""
Sam Huston 2007

This is a simulation of the article:
"Evaluation of a language identification system for mono- and multilingual text documents"
by Artemenko, O; Mandl, T; Shramko, M; Womser-Hacker, C.
presented at: Applied Computing 2006, 21st Annual ACM Symposium on Applied Computing; 23-27 April 2006

This implementation is intended for monolingual documents only,
however it is performed over a much larger range of languages.
Additionally three supervised methods of classification are explored:
Cosine distance, NaiveBayes, and Spearman-rho

"""

from nltk_contrib import classify
from nltk import detect
from nltk.corpus import udhr
import string

def run(classifier, training_data, gold_data):
    classifier.train(training_data)
    correct = 0
    for lang in gold_data:
        cls = classifier.get_class(gold_data[lang])
        if cls == lang:
            correct += 1
    print correct, "in", len(gold_data), "correct"

# features: character bigrams
fd = detect.feature({"char-bigrams" : lambda t: [string.join(t)[n:n+2] for n in range(len(t)-1)]})

training_data = udhr.langs(['English-Latin1', 'French_Francais-Latin1', 'Indonesian-Latin1', 'Zapoteco-Latin1'])
gold_data = {}
for lang in training_data:
    gold_data[lang] = training_data[lang][:50]
    training_data[lang] = training_data[lang][100:200]

print "Cosine classifier: ",
run(classify.Cosine(fd), training_data, gold_data)

print "Naivebayes classifier: ",
run(classify.NaiveBayes(fd), training_data, gold_data)

print "Spearman classifier: ",
run(classify.Spearman(fd), training_data, gold_data)
