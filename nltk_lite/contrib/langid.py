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


from nltk_lite import classify, detect
from nltk_lite.corpora import udhr

def get_result(classifier):

    training_data = udhr.langs()
    gold_data = {}
    for lang in training_data:
        gold_data[lang] = training_data[lang][:100]
        training_data[lang] = training_data[lang][100:]

    classifier.train(training_data)

    correct = 0
    for lang in gold_data:
        cls = classifier.get_class(gold_data[lang])
        if cls == lang:
            correct += 1
    print correct, "in", len(gold_data), "correct"

fd = detect.feature({"3-tuples" : lambda t: [' '.join(t)[n:n+3] for n in range(len(t)-2)]})

classifier = classify.Cosine(fd)
print "Cosine classifier: ",
get_result(classifier)

'''classifier = classify.NaiveBayes(fd)
print "Naivebayes classifier: ",
get_result(classifier)
'''

classifier = classify.Spearman(fd)
print "Spearman classifier: ",
get_result(classifier)
