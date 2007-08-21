# Spelling corrector by Maxime Biais http://www.biais.org/blog/
# http://snippets.dzone.com/posts/show/3395

from nltk import PorterStemmer
from nltk.corpus import brown
 
import sys
from collections import defaultdict
import operator
 
def sortby(nlist ,n, reverse=0):
    nlist.sort(key=operator.itemgetter(n), reverse=reverse)
 
class mydict(dict):
    def __missing__(self, key):
        return 0
 
class DidYouMean:
    def __init__(self):
        self.stemmer = PorterStemmer()
 
    def specialhash(self, s):
        s = s.lower()
        s = s.replace("z", "s")
        s = s.replace("h", "")
        for i in [chr(ord("a") + i) for i in range(26)]:
            s = s.replace(i+i, i)
        s = self.stemmer.stem(s)
        return s
 
    def test(self, token):
        hashed = self.specialhash(token)
        if hashed in self.learned:
            words = self.learned[hashed].items()
            sortby(words, 1, reverse=1)
            if token in [i[0] for i in words]:
                return 'This word seems OK'
            else:
                if len(words) == 1:
                    return 'Did you mean "%s" ?' % words[0][0]
                else:
                    return 'Did you mean "%s" ? (or %s)' \
                           % (words[0][0], ", ".join(['"'+i[0]+'"' \
                                                      for i in words[1:]]))
        return "I can't found similar word in my learned db"
 
    def learn(self, listofsentences=[], n=2000):
        self.learned = defaultdict(mydict)
        if listofsentences == []:
            listofsentences = brown.sents()
        for i, sent in enumerate(listofsentences):
            if i >= n: # Limit to the first nth sentences of the corpus
                break
            for word in sent:
                self.learned[self.specialhash(word)][word.lower()] += 1
 
def demo():
    d = DidYouMean()
    d.learn()
    # choice of words to be relevant related to the brown corpus
    for i in "birdd, oklaoma, emphasise, bird, carot".split(", "):
        print i, "-", d.test(i)
 
if __name__ == "__main__":
    demo()
