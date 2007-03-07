from nltk_lite import tag
from nltk_lite.corpora import brown
import yaml

t0 = tag.Default('nn')
t1 = tag.Unigram(backoff=t0)
t1.train(brown.tagged('f'))    # section a: press-reportage

f = open('demo_tagger.yaml', 'w')
yaml.dump(t1, f)

