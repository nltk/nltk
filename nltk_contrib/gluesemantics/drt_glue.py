# Natural Language Toolkit: Glue Semantics 
#     with Discourse Representation Theory (DRT) as meaning language 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.sem import drt
import linearlogic
import glue
from nltk import data
from nltk.inference.tableau import ProverParseError
from nltk.internals import Counter
from nltk_contrib.dependency import malt

class DrtGlueFormula(glue.GlueFormula):
    def __init__(self, meaning, glue, indices=None):
        if not indices:
            indices = set()

        if isinstance(meaning, str):
            self.meaning = drt.DrtParser().parse(meaning)
        elif isinstance(meaning, drt.AbstractDrs):
            self.meaning = meaning
        else:
            raise RuntimeError, 'Meaning term neither string or expression: %s, %s' % (meaning, meaning.__class__)
            
        if isinstance(glue, str):
            self.glue = linearlogic.LinearLogicParser().parse(glue)
        elif isinstance(glue, linearlogic.Expression):
            self.glue = glue
        else:
            raise RuntimeError, 'Glue term neither string or expression: %s, %s' % (glue, glue.__class__)

        self.indices = indices

    def make_VariableExpression(self, name):
        return drt.DrtVariableExpression(name)
        
    def make_LambdaExpression(self, variable, term):
        return drt.DrtLambdaExpression(variable, term)
        
class DrtGlueDict(glue.GlueDict):
    def get_GlueFormula_factory(self):
        return DrtGlueFormula

class DrtGlue(glue.Glue):
    def __init__(self, verbose=False, semtype_file=None, remove_duplicates=False):
        self.verbose = verbose
        self.remove_duplicates = remove_duplicates
        
        if semtype_file:
            self.semtype_file = semtype_file
        else:
            self.semtype_file = 'drt_glue_event.semtype'

    def get_glue_dict(self):
        return DrtGlueDict(self.semtype_file)
    

def examples():
    return [    'David sees Mary',
                'David eats a sandwich',
                'every man chases a dog',
                'every man believes a dog sleeps',
#                'John gives David a sandwich',
                'John chases himself',
                'John persuades David to order a pizza',
                'John tries to go',
#                'John tries to find a unicorn',
                'John seems to vanish',
                'a unicorn seems to approach',
#                'every big cat leaves',
#                'every gray cat leaves',
#                'every big gray cat leaves',
#                'a former senator leaves',
                'John likes a cat',
                'John likes every cat',
                'he likes a dog',
                'a dog walks and he leaves']

def demo(show_example=-1, remove_duplicates=False):
    malt.train('glue', 'glue_train.conll')
    
    example_num = 0
    hit = False
    for sentence in examples():
        if example_num==show_example or show_example==-1:
            print '[[[Example %s]]]  %s' % (example_num, sentence)
            glueclass = DrtGlue(verbose=False, remove_duplicates=remove_duplicates)
            readings = glueclass.parse_to_meaning(sentence)
            for reading in readings:
                print reading.simplify().resolve_anaphora()
            print ''
            hit = True
        example_num += 1
    if not hit:
        print 'example not found'

def test():
    parser = drt.DrtParser()
    every = parser.parse(r'\P Q.([],[((([x],[])+P(x)) -> Q(x))])')
    man = parser.parse(r'\x.([],[man(x)])')
    chases = parser.parse(r'\x y.([],[chases(x,y)])')
    a = parser.parse(r'\P Q.((([x],[])+P(x))+Q(x))')
    dog = parser.parse(r'\x.([],[dog(x)])')

def test1():
    cs = parse_to_compiled('David walks')
    print cs
    
def test2():
    cs = parse_to_compiled('David sees Mary')
    c = cs[0]
    f1 = c[0]
    f3 = c[1]
    f2 = c[2]
    f5 = c[3]
    f4 = c[4]
    
    f14 = f1.applyto(f4)
    f124 = f14.applyto(f2)
    f1234 = f3.applyto(f124)
    f12345 = f5.applyto(f1234)
 
    print f12345
    print f12345.simplify()    

def testPnApp():
    print "'John seems to vanish'"
    print 'The goal here is to retrieve the reading some x.((x = john) and (seems (vanish x))) \n\
           without the reading (seems (some x.((x = john) and (vanish x))) because John, as a \n\
           named entity, is assumed to always exist.  This is accomplished by always adding \n\
           named entities to the outermost scope.  (See Kamp and Reyle for more)'
    john = DrtGlueFormula(r'\P.(([x],[(x = john)])+P(x))', '((g -o G) -o G)')
    print "'john':                      %s" % john
    seems = DrtGlueFormula(r'\P.([],[seems(P)])', '(h -o f)')
    print "'seems':                     %s" % seems
    vanish = DrtGlueFormula(r'\x.([],[vanish(x)])', '(g -o h)')
    print "'vanish':                    %s" % vanish

    print "  'John' can take wide scope: 'There is a John, and he seems to vanish'"
    xPrime = DrtGlueFormula('x1', 'g')
    print "      'x1':                          %s" % xPrime
    xPrime_vanish = vanish.applyto(xPrime)
    print "      'x1 vanishes':                 %s" % xPrime_vanish.simplify()
    seems_xPrime_vanish = seems.applyto(xPrime_vanish)
    print "      'it seems that x1 vanishes':   %s" % seems_xPrime_vanish.simplify()
    seems_vanish = seems_xPrime_vanish.lambda_abstract(xPrime)
    print "      'seems to vanish':             %s" % seems_vanish.simplify()
    john_seems_vanish = john.applyto(seems_vanish)
    print "      'john seems to vanish':        %s" % john_seems_vanish.simplify()

    print "  'Seems' takes wide scope: 'It seems that there is a John and that he vanishes'"
    john_vanish = john.applyto(vanish)
    print "      'john vanishes':               %s" % john_vanish.simplify()
    seems_john_vanish = seems.applyto(john_vanish)
    print "      'it seems that john vanishes': %s" % seems_john_vanish.simplify()

def test_malt_parse():
    print 'DRT-Glue using MaltParser:'
    for s in ['John sees Mary',
              'a man runs',
              #'a man ran'
              ]:
        print s
        for reading in parse_to_meaning(s, verbose=True):
            print '    ', reading.simplify()
            print '        ', reading.simplify().toFol()

def test_event_representations():
#    This doesn't allow 'e' to be modified
    a = DrtGlueFormula(r'\P Q.((([x],[]) + P(x)) + Q(x))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x.([e],[walk(e), subj(x,e)])', '(g -o f)')
    print '1) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    a = DrtGlueFormula(r'\P Q e.((([x],[]) + P(x)) + Q(x,e))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x e.([],[walk(e), subj(x,e)])', '(g -o f)')
    print '2) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    a = DrtGlueFormula(r'\P Q e.((([x],[]) + P(x)) + Q(x,e))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x e.([],[walk(e), subj(x,e)])', '(g -o f)')
    print '3) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach is a problem because the proof is ambiguous and 'finalize' isn't always 
#    applied to the entire formula 
    finalize = DrtGlueFormula(r'\P.([e],[P(e)])', '(f -o f)')
    print '4) a dog walks.'
    x = drt.DrtParser().parse(r'(\P.([e],[P(e)]) \e.([x],[dog(x),walk(e),subj(x,e)]))')
    print x.simplify()
    for r in get_readings(gfl_to_compiled([a,dog,walks,finalize])):
        print r 
        #r.simplify()
    print ''

#    This approach always adds 'finalize' manually  
    finalize = drt.DrtParser().parse(r'\P.(([e],[]) + P(e))')
    print '5) a dog walks.'
    for r in get_readings(gfl_to_compiled([a,dog,walks])):
        print finalize.applyto(r).simplify()
    print ''

#    This approach add 'finalize' as a GF, but not always at the end
    finalize = DrtGlueFormula(r"\P.(([e],[]) + P(e))", "(f -o f')")
    print '6) a dog walks.'
    for r in get_readings(gfl_to_compiled([a,dog,walks,finalize])):
        print r
        #print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    quickly1 = DrtGlueFormula(r'\P x e.(P(x e) + ([],[(quick e)]))', 'q')
    quickly2 = DrtGlueFormula(r'\P Q.P(Q)', '(Q -o ((g -o f) -o (g -o f)))')
    print '7) a dog walks quickly'
    for r in get_readings(gfl_to_compiled([a,dog,walks, quickly1, quickly2])): 
        print r.simplify()
    print ''

#    TV approach
    every = DrtGlueFormula(r'\P Q e.((([x],[]) + P(x)) + Q(x,e))', '((hv -o hr) -o ((h -o H) -o H))')
    cat = DrtGlueFormula(r'\x.([],[cat(x)])', '(hv -o hr)')
    chases = DrtGlueFormula(r'\x y e.([],[chase(e), subj(x,e), obj(y,e)])', '(g -o (h -o f))')
    print '8) a dog chases every cat'
    for r in get_readings(gfl_to_compiled([a,dog,chases,every,cat])): print r.simplify()
    print ''

#    S conjunction
    f1 = DrtGlueFormula(r'([e,x],[dog(x),walk(e),subj(x,e)])', 'a')
    f2 = DrtGlueFormula(r'([e,x],[cat(x),run(e), subj(x,e)])', 'b')
    and1 = DrtGlueFormula(r'\P Q.(P + Q)', '(a -o (b -o f))')
    print '9) a dog walks and a cat runs'
    for r in get_readings(gfl_to_compiled([f1,and1,f2])): 
        print r
        #print r.simplify()
    print ''
    
    a_man = DrtGlueFormula(r'\Q e.(([x],[man(x)]) + Q(x,e))', '((g -o G) -o G)')
    believes = DrtGlueFormula(r'\x R e1.(([e2],[believe(e1),subj(x,e1),comp(e2,e1)]) + (R e2))', '(g -o (i -o f))')
    a_dog = DrtGlueFormula(r'\Q e.(([x],[dog(x)]) + Q(x,e))', '((h -o H) -o H)')
    walks = DrtGlueFormula(r'\x e.([],[walk(e), subj(x,e)])', '(h -o i)')
    finalize = DrtGlueFormula(r'\P.([e],[P(e)])', "(f -o f')")
    print '10) a man believes a dog walks.'
    for r in get_readings(gfl_to_compiled([a_man, believes, a_dog, walks])): print r.simplify()
    print ''


if __name__ == '__main__':
    demo(remove_duplicates=False)
    print "\n\n\n"
    #testPnApp()
    print ''  
    test_malt_parse()
    print ''
    test_event_representations()
