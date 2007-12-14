from nltk_contrib.drt import DRT
import linearlogic
import lfg
from nltk import data

class GlueFormula:
    def __init__(self, meaning, glue, indices=set([])):
        if isinstance(meaning, str):
            try:
                self.meaning = DRT.Parser().parse(meaning)
            except Exception:
                raise RuntimeError, 'Parsing meaning string: %s' % (meaning)
        elif isinstance(meaning, DRT.AbstractDRS) or isinstance(meaning, DRT.Expression):
            self.meaning = meaning
        else:
            raise RuntimeError, 'Meaning term neither string or expression: %s' % (meaning)
            
            
        if isinstance(glue, str):
            try:
                self.glue = linearlogic.Parser().parse(glue)
            except Exception:
                raise RuntimeError, 'Parsing glue string: %s' % (glue)

        elif isinstance(glue, linearlogic.Expression):
            self.glue = glue
        else:
            raise RuntimeError, 'Glue term neither string or expression: %s' % (glue)

        self.indices = indices

    def applyto(self, arg):
        """ self = (\\x.(walk x), (subj -o f))
            arg  = (john        ,  subj      )
            returns ((walk john),          f )
        """
        if self.indices.intersection(arg.indices): # if the sets are NOT disjoint
            raise linearlogic.LinearLogicApplicationError, '%s applied to %s.  indices are not disjoint.' % (self, arg)
        else: # if the sets ARE disjoint
            return_indices = self.indices.union(arg.indices)

        try:
            return_glue = linearlogic.ApplicationExpression(self.glue, arg.glue, arg.indices)
        except linearlogic.LinearLogicApplicationError:
            raise linearlogic.LinearLogicApplicationError, '%s applied to %s' % (self, arg)

        arg_meaning_abstracted = arg.meaning
        if not return_indices == set([]):
            for dep in self.glue.simplify().first.second.dependencies[::-1]: # if self.glue is (A -o B), dep is in A.dependencies
                arg_meaning_abstracted = DRT.LambdaDRS(DRT.Variable('v%s' % dep), arg_meaning_abstracted)
        return_meaning = DRT.ApplicationDRS(self.meaning, arg_meaning_abstracted)

        return self.__class__(return_meaning, return_glue, return_indices)
        
    def lambda_abstract(self, other):
        assert isinstance(other, GlueFormula)
        assert isinstance(other.meaning, DRT.VariableExpression)
        return self.__class__(DRT.LambdaDRS(other.meaning.variable, self.meaning), \
                              linearlogic.ApplicationExpression(
                                  linearlogic.ApplicationExpression(
                                      linearlogic.Operator(linearlogic.Parser.IMPLIES),
                                      other.glue),
                                  self.glue
                                  )
                              )

    def compile(self, fresh_index=[1]):
        """From Iddo Lev's PhD Dissertation p108-109"""
        r = self.glue.simplify().compile_pos(fresh_index, True)
        return [self.__class__(self.meaning, r[0], set([fresh_index[0]]))]+r[1]

    def infixify(self):
        return self.__class__(self.meaning.infixify(), self.glue.infixify(), self.indices)

    def simplify(self):
        return self.__class__(self.meaning.simplify(), self.glue.simplify(), self.indices)

    def __str__(self):
        assert isinstance(self.indices, set)
        accum = '%s : %s' % (self.meaning, self.glue)
        if self.indices:
            accum += ' : {'
            first = True
            for index in self.indices:
                if first:
                    first = False
                else:
                    accum += ', '
                accum += '%s' % index
            accum += '}'
        return accum
    
    def __repr__(self):
        return self.__str__()

class GlueDict(dict):
    def read_file(self, empty_first = True):
        if empty_first: 
            self.clear()

        try:
            f = open(data.find('grammars/drt_glue.semtype'))
        except LookupError:
            f = open('drt_glue.semtype')
        lines = f.readlines()
        f.close()

        for line in lines:                          # example: 'n : (\\x.(<word> x), (v-r))'
                                                    #     lambdacalc -^  linear logic -^
            line = line.strip()                     # remove trailing newline
            if not len(line): continue              # skip empty lines
            if line[0] == '#': continue             # skip commented out lines

            parts = line.split(' : ', 1)            # ['n', '(\\x.(<word> x), (v-r))']

            glue_formulas = []
            parenCount = 0
            tuple_start = 0
            tuple_comma = 0
            for i in range(len(parts[1])):
                if parts[1][i] == '(':
                    if parenCount == 0:             # if it's the first '(' of a tuple
                        tuple_start = i+1           # then save the index
                    parenCount += 1
                elif parts[1][i] == ')':
                    parenCount -= 1
                    if parenCount == 0:             # if it's the last ')' of a tuple
                        meaning_term =  parts[1][tuple_start:tuple_comma]   # '\\x.(<word> x)'
                        glue_term =     parts[1][tuple_comma+1:i]           # '(v-r)'
                        glue_formulas.append([meaning_term, glue_term])    # add the GlueFormula to the list
                elif parts[1][i] == ',' or parts[1][i] == ':':
                    if parenCount == 1:             # if it's a comma separating the parts of the tuple
                        tuple_comma = i             # then save the index
                elif parts[1][i] == '#':            # skip comments at the ends of lines
                    if parenCount != 0:             # if the line hasn't parsed correctly so far
                        raise RuntimeError, 'Formula syntax is incorrect for entry %s' % (line)
                    break                           # break to the next line
            self[parts[0]] = glue_formulas          # add the glue entry to the dictionary

    def __str__(self):
        accum = ''
        for entry in self:
            accum += '%s : ' % entry
            first = True
            for gf in self[entry]:
                if not first:
                    accum += ' '*(len(entry)+3)
                accum += '%s\n' % (gf)
        return accum

    def lookup(self, sem, word, current_subj, fstruct):
        lookup = self[sem]
        glueformulas = []

        for entry in lookup:
            gf = GlueFormula(entry[0].replace('<word>', word), entry[1])
            if len(glueformulas)==0:
                gf.word = word
            else:
                gf.word = '%s%s' % (word, len(glueformulas)+1)
            if isinstance(gf.glue, linearlogic.ApplicationExpression):
                gf.glue.initialize_labels(fstruct)
            elif isinstance(gf.glue, linearlogic.ConstantExpression) and not isinstance(gf.glue, linearlogic.Operator):
                new_label = fstruct.initialize_label(gf.glue.constant.name.lower())
                if new_label[0].isupper():
                    gf.glue = linearlogic.VariableExpression(linearlogic.Variable(new_label))
                else:
                    gf.glue = linearlogic.ConstantExpression(linearlogic.Constant(new_label))
            elif isinstance(gf.glue, linearlogic.VariableExpression):
                new_label = fstruct.initialize_label(gf.glue.variable.name.lower())
                if new_label[0].isupper():
                    gf.glue = linearlogic.VariableExpression(linearlogic.Variable(new_label))
                else:
                    gf.glue = linearlogic.ConstantExpression(linearlogic.Constant(new_label))

            glueformulas.append(gf)
        return glueformulas

def parse_to_meaning(sentence, remove_duplicates=False):
    readings = []
    for agenda in parse_to_compiled(sentence):
        readings.extend(get_readings(agenda, remove_duplicates))
    return readings

def get_readings(agenda, remove_duplicates=False):
    readings = []
    agenda_length = len(agenda)
    atomics = dict()
    nonatomics = dict()
    while agenda: # is not empty
        cur = agenda.pop()
        # if agenda.glue is non-atomic
        if isinstance(cur.glue.simplify(), linearlogic.ApplicationExpression):
            for key in atomics:
                if cur.glue.simplify().first.second.can_unify_with(key, cur.glue.varbindings):
                    for atomic in atomics[key]:
                        if cur.indices.intersection(atomic.indices):
                            continue
                        else: # if the sets of indices are disjoint
                            try:
                                agenda.append(cur.applyto(atomic))
                            except linearlogic.LinearLogicApplicationError:
                                pass
            try:
                nonatomics[cur.glue.simplify().first.second].append(cur)
            except KeyError:
                nonatomics[cur.glue.simplify().first.second] = [cur]

        else: # else agenda.glue is atomic
            for key in nonatomics:
                for nonatomic in nonatomics[key]:
                    if cur.glue.simplify().can_unify_with(key, nonatomic.glue.varbindings):
                        if cur.indices.intersection(nonatomic.indices):
                            continue
                        else: # if the sets of indices are disjoint
                            try:
                                agenda.append(nonatomic.applyto(cur))
                            except linearlogic.LinearLogicApplicationError:
                                pass
            try:
                atomics[cur.glue.simplify()].append(cur)
            except KeyError:
                atomics[cur.glue.simplify()] = [cur]
                
    for entry in atomics:
        for gf in atomics[entry]:
            if len(gf.indices) == agenda_length:
                _add_to_reading_list(gf, readings, remove_duplicates)
    for entry in nonatomics:
        for gf in nonatomics[entry]:
            if len(gf.indices) == agenda_length:
                _add_to_reading_list(gf, readings, remove_duplicates)
    return readings
        
def _add_to_reading_list(glueformula, reading_list, remove_duplicates=False):
    add_reading = True
    if remove_duplicates:
        for reading in reading_list:
            try:
                if reading.tp_equals(glueformula.meaning):
                    add_reading = False
                    break;
            except:
                #if there is an exception, the syntax of the formula  
                #may not be understandable by the prover, so don't
                #throw out the reading.
                pass
    if add_reading:
        reading_list.append(glueformula.meaning)
    

def parse_to_compiled(sentence='a man sees Mary'):
    parsetrees = parse(sentence)
    fstructs = [pt_to_fstruct(pt) for pt in parsetrees]
    gfls = [fstruct_to_glue(f) for f in fstructs]
    return [gfl_to_compiled(gfl) for gfl in gfls]

def parse_to_glue(sentence='a man sees Mary'):
    parsetrees = parse(sentence)
    fstructs = [pt_to_fstruct(pt) for pt in parsetrees]
    return [fstruct_to_glue(f) for f in fstructs]

def parse(sentence='a man sees Mary'):
    from nltk.parse import load_earley
    cp = load_earley(r'grammars/gluesemantics.fcfg')
    tokens = sentence.split()
    trees = cp.nbest_parse(tokens)
    return trees

def pt_to_fstruct(pt):
    return lfg.FStructure(pt, [0])

def fstruct_to_glue(fstruct):
    glue_pos_dict = GlueDict()
    glue_pos_dict.read_file()
    return fstruct.to_glueformula_list(glue_pos_dict, [], None)

def gfl_to_compiled(gfl):
    return_list = []
    for gf in gfl:
        return_list.extend(gf.compile([len(return_list)+1]))
    return return_list
        

def compile_demo():
    examples = [
        GlueFormula('m', '(b -o a)'),
        GlueFormula('m', '((c -o b) -o a)'),
        GlueFormula('m', '((d -o (c -o b)) -o a)'),
        GlueFormula('m', '((d -o e) -o ((c -o b) -o a))'),
        GlueFormula('m', '(((d -o c) -o b) -o a)'),
        GlueFormula('m', '((((e -o d) -o c) -o b) -o a)'),
    ]

    for i in range(len(examples)):
        print ' [[[Example %s]]]  %s' % (i+1, examples[i])
        compiled_premises = examples[i].compile([1])
        for cp in compiled_premises:
            print '    %s' % cp.infixify()
        print

def compiled_proof_demo():
    a = GlueFormula('\\P Q.((drs([x],[])+(P x))+(Q x))', '((gv -o gr) -o ((g -o G) -o G))')
    man = GlueFormula('\\x.drs([],[(man x)])', '(gv -o gr)')
    walks = GlueFormula('\\x.drs([],[(walks x)])', '(g -o f)')

    print 'Reading of \'a man walks\''
    print '  Premises:'
    print '    %s' % a
    print '    %s' % man
    print '    %s' % walks

    print '  Compiled Premises:'
    ahc = a.compile([1])
    g1 = ahc[2]
    print '    %s' % g1
    g2 = ahc[1]
    print '    %s' % g2
    g3 = ahc[0]
    print '    %s' % g3
    g4 = man.compile([4])[0]
    print '    %s' % g4
    g5 = walks.compile([5])[0]
    print '    %s' % g5

    print '  Derivation:'
    g24 = g4.applyto(g2)
    print '    %s' % g24.simplify().infixify()
    g234 = g3.applyto(g24)
    print '    %s' % g234.simplify().infixify()

    g15 = g5.applyto(g1)
    print '    %s' % g15.simplify().infixify()
    g12345 = g234.applyto(g15)
    print '    %s' % g12345.simplify().infixify()
    
def proof_demo():
    john = GlueFormula('John', 'g')
    walks = GlueFormula('\\x.drs([],[(walks x)])', '(g -o f)')
    print '\'john\':  %s' % john
    print '\'walks\': %s' % walks
    print walks.applyto(john)
    print walks.applyto(john).simplify().infixify()
    print '\n'

    a = GlueFormula('\\P Q.((drs([x],[])+(P x))+(Q x))', '((gv -o gr) -o ((g -o G) -o G))')
    man = GlueFormula('\\x.drs([],[(man x)])', '(gv -o gr)')
    walks = GlueFormula('\\x.drs([],[(walks x)])', '(g -o f)')
    print '\'a\':           %s' % a.infixify()
    print '\'man\':         %s' % man.infixify()
    print '\'walks\':       %s' % walks.infixify()
    a_man = a.applyto(man)
    print '\'a man\':       %s' % a_man.simplify().infixify()
    a_man_walks = a_man.applyto(walks)
    print '\'a man walks\': %s' % a_man_walks.simplify().infixify()
    print '\n'

    print 'Meaning of \'every girl chases a dog\''
    print 'Individual words:'
    every = GlueFormula('\P Q.drs([],[((drs([x],[])+(P x)) implies (Q x))])', '((gv -o gr) -o ((g -o G) -o G))')
    print '  \'every\':                       %s' % every.infixify()
    girl = GlueFormula('\\x.drs([],[(girl x)])', '(gv -o gr)')
    print '  \'girl\':                        %s' % girl.infixify()
    chases = GlueFormula('\\x y.drs([],[(chases x y)])', '(g -o (h -o f))')
    print '  \'chases\':                      %s' % chases.infixify()
    a = GlueFormula('\\P Q.((drs([x],[])+(P x))+(Q x))', '((hv -o hr) -o ((h -o H) -o H))')
    print '  \'a\':                           %s' % a.infixify()
    dog = GlueFormula('\\x.drs([],[(dog x)])', '(hv -o hr)')
    print '  \'dog\':                         %s' % dog.infixify()

    print 'Noun Quantification can only be done one way:'
    every_girl = every.applyto(girl)
    print '  \'every girl\':                  %s' % every_girl.simplify().infixify()
    a_dog = a.applyto(dog)
    print '  \'a dog\':                       %s' % a_dog.simplify().infixify()

    print 'The first reading is achieved by combining \'chases\' with \'a dog\' first.'
    print '  Since \'a girl\' requires something of the form \'(h -o H)\' we must'
    print '    get rid of the \'g\' in the glue of \'chases\'.  We will do this with'
    print '    the \'-o elimination\' rule.  So, x1 will be our subject placeholder.'
    xPrime = GlueFormula('x1', 'g')
    print '      \'x1\':                      %s' % xPrime.infixify()
    xPrime_chases = chases.applyto(xPrime)
    print '      \'x1 chases\':               %s' % xPrime_chases.simplify().infixify()
    xPrime_chases_a_dog = a_dog.applyto(xPrime_chases)
    print '      \'x1 chases a dog\':         %s' % xPrime_chases_a_dog.simplify().infixify()

    print '  Now we can retract our subject placeholder using lambda-abstraction and'
    print '    combine with the true subject.'
    chases_a_dog = xPrime_chases_a_dog.lambda_abstract(xPrime)
    print '      \'chases a dog\':            %s' % chases_a_dog.simplify().infixify()
    every_girl_chases_a_dog = every_girl.applyto(chases_a_dog)
    print '      \'every girl chases a dog\': %s' % every_girl_chases_a_dog.simplify().infixify()

    print 'The second reading is achieved by combining \'every girl\' with \'chases\' first.'
    xPrime = GlueFormula('x1', 'g')
    print '      \'x1\':                      %s' % xPrime.infixify()
    xPrime_chases = chases.applyto(xPrime)
    print '      \'x1 chases\':               %s' % xPrime_chases.simplify().infixify()
    yPrime = GlueFormula('x2', 'h')
    print '      \'x2\':                      %s' % yPrime.infixify()
    xPrime_chases_yPrime = xPrime_chases.applyto(yPrime)
    print '      \'x1 chases x2\':            %s' % xPrime_chases_yPrime.simplify().infixify()
    chases_yPrime = xPrime_chases_yPrime.lambda_abstract(xPrime)
    print '      \'chases x2\':               %s' % chases_yPrime.simplify().infixify()
    every_girl_chases_yPrime = every_girl.applyto(chases_yPrime)
    print '      \'every girl chases x2\':    %s' % every_girl_chases_yPrime.simplify().infixify()
    every_girl_chases = every_girl_chases_yPrime.lambda_abstract(yPrime)
    print '      \'every girl chases\':       %s' % every_girl_chases.simplify().infixify()
    every_girl_chases_a_dog = a_dog.applyto(every_girl_chases)
    print '      \'every girl chases a dog\': %s' % every_girl_chases_a_dog.simplify().infixify()

def examples():
    return [    'David sees Mary',
                'David eats a sandwich',
                'every man chases a dog',
                'every man believes a dog yawns',
#                'John gives David a sandwich',
                'John chases himself',
                'John persuades David to order a pizza',
                'John tries to go',
#                'John tries to find a unicorn',
                'John seems to vanish',
                'a unicorn seems to approach',
#                'every big cat leaves',
#                'every gray cat leaves',
                'every big gray cat leaves',
                'a former senator leaves',
                'John likes a cat',
                'John likes every cat',
                'he likes a dog',
                'a dog walks and he leaves']

def demo(show_example=-1, remove_duplicates=False):
    example_num = 0
    hit = False
    for sentence in examples():
        if example_num==show_example or show_example==-1:
            print '[[[Example %s]]]  %s' % (example_num, sentence)
            readings = parse_to_meaning(sentence, remove_duplicates)
            for j in range(len(readings)):
                reading = readings[j].simplify().resolve_anaphora()
                print reading
            print ''
            hit = True
        example_num += 1
    if not hit:
        print 'example not found'

def test():
    every = DRT.Parser().parse('\P Q.drs([],[((drs([x],[])+(P x)) implies (Q x))])')
    man = DRT.Parser().parse('\\x.drs([],[(man x)])')
    chases = DRT.Parser().parse('\\x y.drs([],[(chases x y)])')
    a = DRT.Parser().parse('\\P Q.((drs([x],[])+(P x))+(Q x))')
    dog = DRT.Parser().parse('\\x.drs([],[(dog x)])')
    

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
    print '\'John seems to vanish\''
    print 'The goal here is to retrieve the reading some x.((x = john) and (seems (vanish x))) \n\
           without the reading (seems (some x.((x = john) and (vanish x))) because John, as a \n\
           named entity, is assumed to always exist.  This is accomplished by always adding \n\
           named entities to the outermost scope.  (See Kamp and Reyle for more)'
    john = GlueFormula(r'\P.(drs([x],[(x = john)])+(P x))', '((g -o G) -o G)')
    print '\'john\':                      %s' % john
    seems = GlueFormula(r'\P.drs([],[(seems P)])', '(h -o f)')
    print '\'seems\':                     %s' % seems
    vanish = GlueFormula(r'\x.drs([],[(vanish x)])', '(g -o h)')
    print '\'vanish\':                    %s' % vanish

    print '  \'John\' can take wide scope: \'There is a John, and he seems to vanish\''
    xPrime = GlueFormula('x1', 'g')
    print '      \'x1\':                          %s' % xPrime.infixify()
    xPrime_vanish = vanish.applyto(xPrime)
    print '      \'x1 vanishes\':                 %s' % xPrime_vanish.simplify().infixify()
    seems_xPrime_vanish = seems.applyto(xPrime_vanish)
    print '      \'it seems that x1 vanishes\':   %s' % seems_xPrime_vanish.simplify().infixify()
    seems_vanish = seems_xPrime_vanish.lambda_abstract(xPrime)
    print '      \'seems to vanish\':             %s' % seems_vanish.simplify().infixify()
    john_seems_vanish = john.applyto(seems_vanish)
    print '      \'john seems to vanish\':        %s' % john_seems_vanish.simplify().infixify()

    print '  \'Seems\' takes wide scope: \'It seems that there is a John and that he vanishes\''
    john_vanish = john.applyto(vanish)
    print '      \'john vanishes\':               %s' % john_vanish.simplify().infixify()
    seems_john_vanish = seems.applyto(john_vanish)
    print '      \'it seems that john vanishes\': %s' % seems_john_vanish.simplify().infixify()

if __name__ == '__main__':
      proof_demo()
      print "\n\n\n"
      compiled_proof_demo()
      print "\n\n\n"
      demo()
      #print "\n\n\n"
      #testPnApp()