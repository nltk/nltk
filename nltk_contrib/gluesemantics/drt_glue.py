# Natural Language Toolkit: Glue Semantics 
#     with Discourse Representation Theory (DRT) as meaning language 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

from nltk.sem import drt
import linearlogic
import lfg
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
    def __init__(self, verbose=False, dependency=False, semtype_file=None, remove_duplicates=False):
        self.verbose = verbose
        self.dependency = dependency
        self.remove_duplicates = remove_duplicates
        
        if semtype_file:
            self.semtype_file = semtype_file
        elif dependency:
            self.semtype_file = 'drt_glue_event.semtype'
        else:
            self.semtype_file = 'drt_glue.semtype'

    def get_glue_dict(self):
        return DrtGlueDict(self.semtype_file)
    

def compile_demo():
    examples = [
        DrtGlueFormula('m', '(b -o a)'),
        DrtGlueFormula('m', '((c -o b) -o a)'),
        DrtGlueFormula('m', '((d -o (c -o b)) -o a)'),
        DrtGlueFormula('m', '((d -o e) -o ((c -o b) -o a))'),
        DrtGlueFormula('m', '(((d -o c) -o b) -o a)'),
        DrtGlueFormula('m', '((((e -o d) -o c) -o b) -o a)')
    ]

    for i in range(len(examples)):
        print ' [[[Example %s]]]  %s' % (i+1, examples[i])
        compiled_premises = examples[i].compile([1])
        for cp in compiled_premises:
            print '    %s' % cp
        print

def compiled_proof_demo():
    a = DrtGlueFormula(r'\P Q.((drs([x],[])+P(x))+Q(x))', '((gv -o gr) -o ((g -o G) -o G))')
    man = DrtGlueFormula(r'\x.drs([],[man(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x.drs([],[walks(x)])', '(g -o f)')

    print "Reading of 'a man walks'"
    print "  Premises:"
    print "    %s" % a
    print "    %s" % man
    print "    %s" % walks

    counter = Counter()

    print '  Compiled Premises:'
    ahc = a.compile(counter)
    g1 = ahc[1]
    print '    %s' % g1
    g2 = ahc[0]
    print '    %s' % g2
    g3 = ahc[2]
    print '    %s' % g3
    g4 = man.compile(counter)[0]
    print '    %s' % g4
    g5 = walks.compile(counter)[0]
    print '    %s' % g5

    print '  Derivation:'
    g24 = g4.applyto(g2)
    print '    %s' % g24.simplify()
    g234 = g3.applyto(g24)
    print '    %s' % g234.simplify()

    g15 = g5.applyto(g1)
    print '    %s' % g15.simplify()
    g12345 = g234.applyto(g15)
    print '    %s' % g12345.simplify()
    
def proof_demo():
    john = DrtGlueFormula('John', 'g')
    walks = DrtGlueFormula(r'\x.drs([],[walks(x)])', '(g -o f)')
    print "'john':  %s" % john
    print "'walks': %s" % walks
    print walks.applyto(john)
    print walks.applyto(john).simplify()
    print '\n'

    a = DrtGlueFormula(r'\P Q.((drs([x],[])+P(x))+Q(x))', '((gv -o gr) -o ((g -o G) -o G))')
    man = DrtGlueFormula(r'\x.drs([],[man(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x.drs([],[walks(x)])', '(g -o f)')
    print "'a':           %s" % a
    print "'man':         %s" % man
    print "'walks':       %s" % walks
    a_man = a.applyto(man)
    print "'a man':       %s" % a_man.simplify()
    a_man_walks = a_man.applyto(walks)
    print "'a man walks': %s" % a_man_walks.simplify()
    print '\n'

    print "Meaning of 'every girl chases a dog'"
    print 'Individual words:'
    every = DrtGlueFormula('\P Q.drs([],[((drs([x],[])+P(x)) implies Q(x))])', '((gv -o gr) -o ((g -o G) -o G))')
    print "  'every':                       %s" % every
    girl = DrtGlueFormula(r'\x.drs([],[girl(x)])', '(gv -o gr)')
    print "  'girl':                        %s" % girl
    chases = DrtGlueFormula(r'\x y.drs([],[chases(x,y)])', '(g -o (h -o f))')
    print "  'chases':                      %s" % chases
    a = DrtGlueFormula(r'\P Q.((drs([x],[])+P(x))+Q(x))', '((hv -o hr) -o ((h -o H) -o H))')
    print "  'a':                           %s" % a
    dog = DrtGlueFormula(r'\x.drs([],[dog(x)])', '(hv -o hr)')
    print "  'dog':                         %s" % dog

    print 'Noun Quantification can only be done one way:'
    every_girl = every.applyto(girl)
    print "  'every girl':                  %s" % every_girl.simplify()
    a_dog = a.applyto(dog)
    print "  'a dog':                       %s" % a_dog.simplify()

    print "The first reading is achieved by combining 'chases' with 'a dog' first."
    print "  Since 'a girl' requires something of the form '(h -o H)' we must"
    print "    get rid of the 'g' in the glue of 'chases'.  We will do this with"
    print "    the '-o elimination' rule.  So, x1 will be our subject placeholder."
    xPrime = DrtGlueFormula('x1', 'g')
    print "      'x1':                      %s" % xPrime
    xPrime_chases = chases.applyto(xPrime)
    print "      'x1 chases':               %s" % xPrime_chases.simplify()
    xPrime_chases_a_dog = a_dog.applyto(xPrime_chases)
    print "      'x1 chases a dog':         %s" % xPrime_chases_a_dog.simplify()

    print "  Now we can retract our subject placeholder using lambda-abstraction and"
    print "    combine with the true subject."
    chases_a_dog = xPrime_chases_a_dog.lambda_abstract(xPrime)
    print "      'chases a dog':            %s" % chases_a_dog.simplify()
    every_girl_chases_a_dog = every_girl.applyto(chases_a_dog)
    print "      'every girl chases a dog': %s" % every_girl_chases_a_dog.simplify()

    print "The second reading is achieved by combining 'every girl' with 'chases' first."
    xPrime = DrtGlueFormula('x1', 'g')
    print "      'x1':                      %s" % xPrime
    xPrime_chases = chases.applyto(xPrime)
    print "      'x1 chases':               %s" % xPrime_chases.simplify()
    yPrime = DrtGlueFormula('x2', 'h')
    print "      'x2':                      %s" % yPrime
    xPrime_chases_yPrime = xPrime_chases.applyto(yPrime)
    print "      'x1 chases x2':            %s" % xPrime_chases_yPrime.simplify()
    chases_yPrime = xPrime_chases_yPrime.lambda_abstract(xPrime)
    print "      'chases x2':               %s" % chases_yPrime.simplify()
    every_girl_chases_yPrime = every_girl.applyto(chases_yPrime)
    print "      'every girl chases x2':    %s" % every_girl_chases_yPrime.simplify()
    every_girl_chases = every_girl_chases_yPrime.lambda_abstract(yPrime)
    print "      'every girl chases':       %s" % every_girl_chases.simplify()
    every_girl_chases_a_dog = a_dog.applyto(every_girl_chases)
    print "      'every girl chases a dog': %s" % every_girl_chases_a_dog.simplify()

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
            glueclass = DrtGlue(verbose=False, dependency=True, remove_duplicates=remove_duplicates)
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
    every = parser.parse(r'\P Q.drs([],[((drs([x],[])+P(x)) -> Q(x))])')
    man = parser.parse(r'\x.drs([],[man(x)])')
    chases = parser.parse(r'\x y.drs([],[chases(x,y)])')
    a = parser.parse(r'\P Q.((drs([x],[])+P(x))+Q(x))')
    dog = parser.parse(r'\x.drs([],[dog(x)])')

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
    john = DrtGlueFormula(r'\P.(drs([x],[(x = john)])+P(x))', '((g -o G) -o G)')
    print "'john':                      %s" % john
    seems = DrtGlueFormula(r'\P.drs([],[seems(P)])', '(h -o f)')
    print "'seems':                     %s" % seems
    vanish = DrtGlueFormula(r'\x.drs([],[vanish(x)])', '(g -o h)')
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
        for reading in parse_to_meaning(s, dependency=True, verbose=True):
            #print '    ', reading
            print '    ', reading.simplify()
            print '        ', reading.simplify().toFol()

def test_event_representations():
#    This doesn't allow 'e' to be modified
    a = DrtGlueFormula(r'\P Q.((drs([x],[]) + P(x)) + Q(x))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.drs([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x.drs([e],[walk(e), subj(x,e)])', '(g -o f)')
    print '1) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    a = DrtGlueFormula(r'\P Q e.((drs([x],[]) + P(x)) + Q(x,e))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.drs([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x e.drs([],[walk(e), subj(x,e)])', '(g -o f)')
    print '2) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    a = DrtGlueFormula(r'\P Q e.((drs([x],[]) + P(x)) + Q(x,e))', '((gv -o gr) -o ((g -o G) -o G))')
    dog = DrtGlueFormula(r'\x.drs([],[dog(x)])', '(gv -o gr)')
    walks = DrtGlueFormula(r'\x e.drs([],[walk(e), subj(x,e)])', '(g -o f)')
    print '3) a dog walks'
    for r in get_readings(gfl_to_compiled([a,dog,walks])): print r.simplify()
    print ''

#    This approach is a problem because the proof is ambiguous and 'finalize' isn't always 
#    applied to the entire formula 
    finalize = DrtGlueFormula(r'\P.drs([e],[P(e)])', '(f -o f)')
    print '4) a dog walks.'
    x = drt.DrtParser().parse(r'(\P.drs([e],[P(e)]) \e.DRS([x],[dog(x),walk(e),subj(x,e)]))')
    print x.simplify()
    for r in get_readings(gfl_to_compiled([a,dog,walks,finalize])):
        print r 
        #r.simplify()
    print ''

#    This approach always adds 'finalize' manually  
    finalize = drt.DrtParser().parse(r'\P.(drs([e],[]) + P(e))')
    print '5) a dog walks.'
    for r in get_readings(gfl_to_compiled([a,dog,walks])):
        print finalize.applyto(r).simplify()
    print ''

#    This approach add 'finalize' as a GF, but not always at the end
    finalize = DrtGlueFormula(r"\P.(drs([e],[]) + P(e))", "(f -o f')")
    print '6) a dog walks.'
    for r in get_readings(gfl_to_compiled([a,dog,walks,finalize])):
        print r
        #print r.simplify()
    print ''

#    This approach finishes with a '\e' in front
    quickly1 = DrtGlueFormula(r'\P x e.(P(x e) + drs([],[(quick e)]))', 'q')
    quickly2 = DrtGlueFormula(r'\P Q.P(Q)', '(Q -o ((g -o f) -o (g -o f)))')
    print '7) a dog walks quickly'
    for r in get_readings(gfl_to_compiled([a,dog,walks, quickly1, quickly2])): 
        print r.simplify()
    print ''

#    TV approach
    every = DrtGlueFormula(r'\P Q e.((drs([x],[]) + P(x)) + Q(x,e))', '((hv -o hr) -o ((h -o H) -o H))')
    cat = DrtGlueFormula(r'\x.drs([],[cat(x)])', '(hv -o hr)')
    chases = DrtGlueFormula(r'\x y e.drs([],[chase(e), subj(x,e), obj(y,e)])', '(g -o (h -o f))')
    print '8) a dog chases every cat'
    for r in get_readings(gfl_to_compiled([a,dog,chases,every,cat])): print r.simplify()
    print ''

#    S conjunction
    f1 = DrtGlueFormula(r'DRS([e,x],[dog(x),walk(e),subj(x,e)])', 'a')
    f2 = DrtGlueFormula(r'DRS([e,x],[cat(x),run(e), subj(x,e)])', 'b')
    and1 = DrtGlueFormula(r'\P Q.(P + Q)', '(a -o (b -o f))')
    print '9) a dog walks and a cat runs'
    for r in get_readings(gfl_to_compiled([f1,and1,f2])): 
        print r
        #print r.simplify()
    print ''
    
    a_man = DrtGlueFormula(r'\Q e.(drs([x],[man(x)]) + Q(x,e))', '((g -o G) -o G)')
    believes = DrtGlueFormula(r'\x R e1.(drs([e2],[believe(e1),subj(x,e1),comp(e2,e1)]) + (R e2))', '(g -o (i -o f))')
    a_dog = DrtGlueFormula(r'\Q e.(drs([x],[dog(x)]) + Q(x,e))', '((h -o H) -o H)')
    walks = DrtGlueFormula(r'\x e.drs([],[walk(e), subj(x,e)])', '(h -o i)')
    finalize = DrtGlueFormula(r'\P.drs([e],[P(e)])', "(f -o f')")
    print '10) a man believes a dog walks.'
    for r in get_readings(gfl_to_compiled([a_man, believes, a_dog, walks])): print r.simplify()
    print ''

if __name__ == '__main__':
    proof_demo()
    print "\n\n\n"
    compiled_proof_demo()
    print "\n\n\n"
    demo(remove_duplicates=False)
    print "\n\n\n"
    #testPnApp()
    print ''  
    test_malt_parse()
    print ''
    test_event_representations()
    
