from featurechart import *
from parse import ncategory

g = ncategory.GrammarFile.read_file('german_ma2.cfg')

good = [
    'der hund sieht die katze', 
    'der hund kommt',
    'ich sehe den hund',
    'ich helfe dem hund',
    'der hund sieht mich',
    'den hund sieht der hund',
    'mich mag der hund'
]

bad = [
    'der hunde kommt',
    'die hunde sehe die hunde', 
    'der hund sehe die hunde', 
    'ich sehe ich',
    'ich hilft den hund',
    'ich hilft der hund',
    'ich sehe dem hund',
    'ich sehe die katzen',
    'ich komme den hund' 
]

def test_sents(sents, show_tree=False):
    for sent in sents:
        tokens = list(tokenize.whitespace(sent))
        #cp = g.earley_parser(trace=0)
        cp = load_earley('german_ma2.cfg', trace=0)
        trees = cp.parse(tokens)

        if not trees is None:
            for tree in trees:
                print '*' * 30
                print sent
                if show_tree:
                    print tree
                else: 
                    print "Parsed!"
        else:
            print '*' * 30
            print sent
            print "Failed!"
            


if __name__ == '__main__':
    test_sents(good)
    #test_sents(bad)