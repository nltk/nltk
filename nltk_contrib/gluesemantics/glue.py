# Natural Language Toolkit: Glue Semantics 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT

import os
from nltk.sem import logic
import linearlogic
from nltk.parse import *
import lfg
from nltk import data
from nltk.internals import Counter

class GlueFormula:
    def __init__(self, meaning, glue, indices=None):
        if not indices:
            indices = set()
        
        if isinstance(meaning, str):
            self.meaning = logic.LogicParser().parse(meaning)    # lp.parse('\\x.(<word> x)') -> LambdaExpression('x', '(<word> x)')
        elif isinstance(meaning, logic.Expression):
            self.meaning = meaning
        else:
            raise RuntimeError, 'Meaning term neither string or expression: %s, %s' % (meaning, meaning.__class__)
            
        if isinstance(glue, str):
            self.glue = linearlogic.LinearLogicParser().parse(glue) # llp.parse('(v -o r)') -> ApplicationExpression('(-o v)', 'r')
        elif isinstance(glue, linearlogic.Expression):
            self.glue = glue
        else:
            raise RuntimeError, 'Glue term neither string or expression: %s, %s' % (glue, glue.__class__)

        self.indices = indices

    def applyto(self, arg):
        """ self = (\\x.(walk x), (subj -o f))
            arg  = (john        ,  subj)
            returns ((walk john),          f)
        """
        if self.indices & arg.indices: # if the sets are NOT disjoint
            raise linearlogic.LinearLogicApplicationException, '%s applied to %s.  Indices are not disjoint.' % (self, arg)
        else: # if the sets ARE disjoint
            return_indices = (self.indices | arg.indices)

        try:
            return_glue = linearlogic.ApplicationExpression(self.glue, arg.glue, arg.indices)
        except linearlogic.LinearLogicApplicationException:
            raise linearlogic.LinearLogicApplicationException, '%s applied to %s' % (self, arg)

        arg_meaning_abstracted = arg.meaning
        if return_indices:
            for dep in self.glue.simplify().antecedent.dependencies[::-1]: # if self.glue is (A -o B), dep is in A.dependencies
                arg_meaning_abstracted = self.make_LambdaExpression(logic.Variable('v%s' % dep), 
                                                                    arg_meaning_abstracted)
        return_meaning = self.meaning.applyto(arg_meaning_abstracted)

        return self.__class__(return_meaning, return_glue, return_indices)
        
    def make_VariableExpression(self, name):
        return logic.VariableExpression(name)
        
    def make_LambdaExpression(self, variable, term):
        return logic.LambdaExpression(variable, term)
        
    def lambda_abstract(self, other):
        assert isinstance(other, GlueFormula)
        assert isinstance(other.meaning, logic.AbstractVariableExpression)
        return self.__class__(self.make_LambdaExpression(other.meaning.variable, 
                                                         self.meaning),
                              linearlogic.ImpExpression(other.glue, self.glue))

    def compile(self, counter=None):
        """From Iddo Lev's PhD Dissertation p108-109"""
        if not counter:
            counter = Counter()
        (compiled_glue, new_forms) = self.glue.simplify().compile_pos(counter, self.__class__)
        return new_forms + [self.__class__(self.meaning, compiled_glue, set([counter.get()]))]

    def simplify(self):
        return self.__class__(self.meaning.simplify(), self.glue.simplify(), self.indices)

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.meaning == other.meaning and self.glue == other.glue

    def __str__(self):
        assert isinstance(self.indices, set)
        accum = '%s : %s' % (self.meaning, self.glue)
        if self.indices:
            accum += ' : {' + ', '.join([str(index) for index in self.indices]) + '}'
        return accum
    
    def __repr__(self):
        return str(self)

class GlueDict(dict):
    def __init__(self, filename):
        self.filename = filename
        self.read_file()
    
    def read_file(self, empty_first=True):
        if empty_first: 
            self.clear()

        try:
            f = open(data.find(os.path.join('grammars', self.filename)))
        except LookupError:
            f = open(self.filename)
        lines = f.readlines()
        f.close()

        for line in lines:                          # example: 'n : (\\x.(<word> x), (v-r))'
                                                    #     lambdacalc -^  linear logic -^
            line = line.strip()                     # remove trailing newline
            if not len(line): continue              # skip empty lines
            if line[0] == '#': continue             # skip commented out lines

            parts = line.split(' : ', 2)            # ['verb', '(\\x.(<word> x), ( subj -o f ))', '[subj]']

            glue_formulas = []
            parenCount = 0
            tuple_start = 0
            tuple_comma = 0

            relationships = None
            
            for (i, tok) in enumerate(parts[1]):
                if tok == '(':
                    if parenCount == 0:             # if it's the first '(' of a tuple
                        tuple_start = i+1           # then save the index
                    parenCount += 1
                elif tok == ')':
                    parenCount -= 1
                    if parenCount == 0:             # if it's the last ')' of a tuple
                        meaning_term =  parts[1][tuple_start:tuple_comma]   # '\\x.(<word> x)'
                        glue_term =     parts[1][tuple_comma+1:i]           # '(v-r)'
                        glue_formulas.append([meaning_term, glue_term])     # add the GlueFormula to the list
                elif tok == ',':
                    if parenCount == 1:             # if it's a comma separating the parts of the tuple
                        tuple_comma = i             # then save the index
                elif tok == '#':            # skip comments at the ends of lines
                    if parenCount != 0:             # if the line hasn't parsed correctly so far
                        raise RuntimeError, 'Formula syntax is incorrect for entry ' + line
                    break                           # break to the next line
            
            if len(parts) > 2:                     #if there is a relationship entry at the end
                relStart = parts[2].index('[')+1
                relEnd   = parts[2].index(']')
                if(relStart == relEnd):
                    relationships = frozenset()
                else:
                    relationships = frozenset([r.strip() for r in parts[2][relStart:relEnd].split(',')])

            if parts[0] in self:
                self[parts[0]][relationships] = glue_formulas
            else:
                self[parts[0]] = {relationships: glue_formulas} # add the glue entry to the dictionary

    def __str__(self):
        accum = ''
        for pos in self:
            for relset in self[pos]:
                for gf in self[pos][relset]:
                    accum += str(pos) + ': ' + str(gf)
                    if relset:
                        accum += ' : ' + str(relset)
                    accum += '\n'
        return accum

    def lookup(self, sem, word, current_subj, fstruct):
        relationships = frozenset([r for r in fstruct])
        try:
            semtype = self[{'a'     : 'ex_quant',
                            'an'    : 'ex_quant',
                            'every' : 'univ_quant'
                            }[word.lower()]]
        except:
            try:
                semtype = self[sem]
            except KeyError:
                raise KeyError, "There is no GlueDict entry for sem type '%s' (for '%s')" %\
                                (str(sem), word)
                                
        try:
            lookup = semtype[relationships]
        except KeyError:
            # An exact match is not found, so find the best match where
            # 'best' is defined as the glue entry whose relationship set has the
            # most relations of any possible relationship set that is a subset
            # of the actual fstruct 
            best_match = frozenset()
            for relset_option in set(semtype)-set([None]):
                if len(relset_option) > len(best_match) and relset_option < relationships:
                    best_match = relset_option
            if not best_match:
                if None in semtype:
                    best_match = None
                else:
                    raise KeyError, "There is no GlueDict entry for sem type '%s' with the relationship set %s" %\
                                    (str(sem),str(relationships))
            lookup = semtype[best_match]
                
        glueformulas = []

        glueFormulaFactory = self.get_GlueFormula_factory()
        for entry in lookup:
            gf = glueFormulaFactory(entry[0].replace('<word>', word), entry[1])
            if len(glueformulas) == 0:
                gf.word = word
            else:
                gf.word = '%s%s' % (word, len(glueformulas)+1)

            if isinstance(gf.glue, linearlogic.AtomicExpression):
                new_label = fstruct.initialize_label(gf.glue.name.lower())
                if new_label[0].isupper():
                    gf.glue = linearlogic.VariableExpression(new_label)
                else:
                    gf.glue = linearlogic.ConstantExpression(new_label)
            else:
                gf.glue.initialize_labels(fstruct)

            glueformulas.append(gf)
        return glueformulas

    def get_GlueFormula_factory(self):
        return GlueFormula

class Glue:
    def __init__(self, verbose=False, dependency=False, semtype_file=None, remove_duplicates=False):
        self.verbose = verbose
        self.dependency = dependency
        self.remove_duplicates = remove_duplicates
        
        if semtype_file:
            self.semtype_file = semtype_file
        elif dependency:
            self.semtype_file = 'glue_event.semtype'
        else:
            self.semtype_file = 'glue.semtype'
    
    def parse_to_meaning(self, sentence):
        readings = []
        for agenda in self.parse_to_compiled(sentence):
            readings.extend(self.get_readings(agenda))
        return readings
    
    def get_readings(self, agenda):
        readings = []
        agenda_length = len(agenda)
        atomics = dict()
        nonatomics = dict()
        while agenda: # is not empty
            cur = agenda.pop()
            glue_simp = cur.glue.simplify()
            if isinstance(glue_simp, linearlogic.ImpExpression): # if cur.glue is non-atomic
                for key in atomics:
                    try:
                        if isinstance(cur.glue, linearlogic.ApplicationExpression):
                            bindings = cur.glue.bindings
                        else:
                            bindings = linearlogic.BindingDict()
                        glue_simp.antecedent.unify(key, bindings)
                        for atomic in atomics[key]:
                            if not (cur.indices & atomic.indices): # if the sets of indices are disjoint
                                try:
                                    agenda.append(cur.applyto(atomic))
                                except linearlogic.LinearLogicApplicationException:
                                    pass
                    except linearlogic.UnificationException:
                        pass
                try:
                    nonatomics[glue_simp.antecedent].append(cur)
                except KeyError:
                    nonatomics[glue_simp.antecedent] = [cur]
    
            else: # else cur.glue is atomic
                for key in nonatomics:
                    for nonatomic in nonatomics[key]:
                        try:
                            if isinstance(nonatomic.glue, linearlogic.ApplicationExpression):
                                bindings = nonatomic.glue.bindings
                            else:
                                bindings = linearlogic.BindingDict()
                            glue_simp.unify(key, bindings)
                            if not (cur.indices & nonatomic.indices): # if the sets of indices are disjoint
                                try:
                                    agenda.append(nonatomic.applyto(cur))
                                except linearlogic.LinearLogicApplicationException:
                                    pass
                        except linearlogic.UnificationException:
                            pass
                try:
                    atomics[glue_simp].append(cur)
                except KeyError:
                    atomics[glue_simp] = [cur]
                    
        for entry in atomics:
            for gf in atomics[entry]:
                if len(gf.indices) == agenda_length:
                    self._add_to_reading_list(gf, readings)
        for entry in nonatomics:
            for gf in nonatomics[entry]:
                if len(gf.indices) == agenda_length:
                    self._add_to_reading_list(gf, readings)
        return readings
            
    def _add_to_reading_list(self, glueformula, reading_list):
        add_reading = True
        if self.remove_duplicates:
            for reading in reading_list:
                try:
                    if reading.tp_equals(glueformula.meaning, 'Prover9'):
                        add_reading = False
                        break;
                except:
                    #if there is an exception, the syntax of the formula  
                    #may not be understandable by the prover, so don't
                    #throw out the reading.
                    pass
        if add_reading:
            reading_list.append(glueformula.meaning)
        
    def parse_to_compiled(self, sentence='a man sees Mary'):
        if self.dependency:
            fstructs = [lfg.FStructure.read_depgraph(dep_graph) for dep_graph in self.dep_parse(sentence)]
        else:
            fstructs = [lfg.FStructure.read_parsetree(pt, [0]) for pt in self.earley_parse(sentence)]
        gfls = [self.fstruct_to_glue(f) for f in fstructs]
        return [self.gfl_to_compiled(gfl) for gfl in gfls]
    
    def dep_parse(self, sentence='every cat leaves'):
        from nltk_contrib.dependency import malt
        return [malt.parse(sentence, 'glue', 'tnt', verbose=self.verbose)]
    
    def earley_parse(self, sentence='every cat leaves'):
        from nltk.parse import load_earley
        cp = load_earley(r'grammars/gluesemantics.fcfg')
        return cp.nbest_parse(sentence.split())
    
    def fstruct_to_glue(self, fstruct):
        glueformulas = fstruct.to_glueformula_list(self.get_glue_dict(), [], verbose=self.verbose)
        
        if self.verbose:
            print fstruct
            for gf in glueformulas: 
                print gf
                
        return glueformulas
    
    def get_glue_dict(self):
        return GlueDict(self.semtype_file)
    
    def gfl_to_compiled(self, gfl):
        index_counter = Counter()
        return_list = []
        for gf in gfl:
            return_list.extend(gf.compile(index_counter))
        
        if self.verbose:
            print 'Compiled Glue Premises:'
            for cgf in return_list:
                print cgf    
        
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
        compiled_premises = examples[i].compile(Counter())
        for cp in compiled_premises:
            print '    %s' % cp
        print

def compiled_proof_demo():
    a = GlueFormula('\\P Q.some x.(P(x) and Q(x))', '((gv -o gr) -o ((g -o G) -o G))')
    man = GlueFormula('\\x.man(x)', '(gv -o gr)')
    walks = GlueFormula('\\x.walks(x)', '(g -o f)')

    print "Reading of 'a man walks'"
    print "  Premises:"
    print "    %s" % a
    print "    %s" % man
    print "    %s" % walks

    counter = Counter()

    print "  Compiled Premises:"
    ahc = a.compile(counter)
    g1 = ahc[0]
    print "    %s" % g1
    g2 = ahc[1]
    print "    %s" % g2
    g3 = ahc[2]
    print "    %s" % g3
    g4 = man.compile(counter)[0]
    print "    %s" % g4
    g5 = walks.compile(counter)[0]
    print "    %s" % g5

    print "  Derivation:"
    g14 = g4.applyto(g1)
    print "    %s" % g14.simplify()
    g134 = g3.applyto(g14)
    print "    %s" % g134.simplify()

    g25 = g5.applyto(g2)
    print "    %s" % g25.simplify()
    g12345 = g134.applyto(g25)
    print "    %s" % g12345.simplify()
    
def proof_demo():
    john = GlueFormula("John", "g")
    walks = GlueFormula("\\x.walks(x)", "(g -o f)")
    print "'john':  %s" % john
    print "'walks': %s" % walks
    print walks.applyto(john)
    print walks.applyto(john).simplify()
    print "\n"

    a = GlueFormula("\P Q.some x.(P(x) and Q(x))", "((gv -o gr) -o ((g -o G) -o G))")
    man = GlueFormula("\\x.man(x)", "(gv -o gr)")
    walks = GlueFormula("\\x.walks(x)", "(g -o f)")
    print "'a':           %s" % a
    print "'man':         %s" % man
    print "'walks':       %s" % walks
    a_man = a.applyto(man)
    print "'a man':       %s" % a_man.simplify()
    a_man_walks = a_man.applyto(walks)
    print "'a man walks': %s" % a_man_walks.simplify()
    print "\n"

    print "Meaning of 'every girl chases a dog'"
    print "Individual words:"
    every = GlueFormula("\P Q.all x.(P(x) implies Q(x))", "((gv -o gr) -o ((g -o G) -o G))")
    print "  'every x2':                    %s" % every
    girl = GlueFormula("\\x.girl(x)", "(gv -o gr)")
    print "  'girl':                        %s" % girl
    chases = GlueFormula("\\x y.chases(x,y)", "(g -o (h -o f))")
    print "  'chases':                      %s" % chases
    a = GlueFormula("\P Q.some x.(P(x) and Q(x))", "((hv -o hr) -o ((h -o H) -o H))")
    print "  'a':                           %s" % a
    dog = GlueFormula("\\x.dog(x)", "(hv -o hr)")
    print "  'dog':                         %s" % dog

    print "Noun Quantification can only be done one way:"
    every_girl = every.applyto(girl)
    print "  'every girl':                  %s" % every_girl.simplify()
    a_dog = a.applyto(dog)
    print "  'a dog':                       %s" % a_dog.simplify()

    print "The first reading is achieved by combining 'chases' with 'a dog' first."
    print "  Since 'a girl' requires something of the form '(h -o H)' we must"
    print "    get rid of the 'g' in the glue of 'see'.  We will do this with"
    print "    the '-o elimination' rule.  So, x1 will be our subject placeholder."
    xPrime = GlueFormula("x1", "g")
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
    xPrime = GlueFormula("x1", "g")
    print "      'x1':                      %s" % xPrime
    xPrime_chases = chases.applyto(xPrime)
    print "      'x1 chases':               %s" % xPrime_chases.simplify()
    yPrime = GlueFormula("x2", "h")
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

def demo(show_example=-1, dependency=False):
    examples = ['David sees Mary',
                'David eats a sandwich',
                'every man chases a dog',
                'every man believes a dog sleeps',
                'John gives David a sandwich',
                'John chases himself',
                'John persuades David to order a pizza',
                'John tries to go',
                'John tries to find a unicorn',
                'John seems to vanish',
                'a unicorn seems to approach',
                'every big cat leaves',
                'every gray cat leaves',
                'every big gray cat leaves',
                'a former senator leaves']

    print '============== DEMO =============='
    if dependency: 
        print '     ====== DEPENDENCY ======     '
    else: 
        print '     ========= FCFG =========     '
    
    for (i, sentence) in zip(range(len(examples)), examples):
        if i==show_example or show_example==-1:
            print '[[[Example %s]]]  %s' % (i, sentence)
            for reading in Glue(verbose=False, dependency=dependency).parse_to_meaning(sentence):
                print reading.simplify()
            print ''
    
if __name__ == '__main__':
    proof_demo()
    print "\n\n"
    compile_demo()
    print "\n\n"
    compiled_proof_demo()
#    print "\n\n"
#    demo(dependency=False)
    print "\n\n"
    demo(dependency=True)
