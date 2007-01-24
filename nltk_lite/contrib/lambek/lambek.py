#!/usr/bin/python
#
# lambek.py
#
# Edward Loper
# Created [12/10/00 03:41 AM]
# $Id$
#

"""Lambek Calculus Theorem Prover

"""

# For while I'm coding..
#import term;reload(term)
#import typedterm; reload(typedterm)

_VERBOSE = 0
_VAR_NAMES = 1
_SHOW_VARMAP = not _VAR_NAMES

from term import *
from typedterm import *
from lexicon import *
import sys, re

class Sequent:
    """A sequent maps an ordered sequence of TypedTerm's to an ordered 
    sequence of TypedTerm's."""
    # left and right are lists of TypedTerms.
    def __init__(self, left, right):

        # Check types, because we're paranoid.
        if type(left) not in [types.ListType, types.TupleType] or \
           type(right) not in [types.ListType, types.TupleType]:
            raise TypeError('Expected lists of TypedTerms')
        for elt in left+right:
            if not isinstance(elt, TypedTerm):
                raise TypeError('Expected lists of TypedTerms')
        
        self.left = left
        self.right = right

    def __repr__(self):
        left_str = `self.left`[1:-1]
        right_str = `self.right`[1:-1]
        return left_str + ' => ' + right_str

    def to_latex(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = {}
        for te in self.left+self.right:
            extend_pp_varmap(pp_varmap, te.term)
        str = ''
        for i in range(len(self.left)):
            str += self.left[i].to_latex(pp_varmap) + ', '
        str = str[:-2] + ' \Rightarrow '
        for i in range(len(self.right)):
            str += self.right[i].to_latex(pp_varmap) + ', '
        return str[:-2]
        
    def pp(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = {}
        for te in self.left+self.right:
            extend_pp_varmap(pp_varmap, te.term)
        str = ''
        for i in range(len(self.left)):
            str += self.left[i].pp(pp_varmap) + ', '
        str = str[:-2] + ' => '
        for i in range(len(self.right)):
            str += self.right[i].pp(pp_varmap) + ', '
        return str[:-2]

    def simplify(self, varmap):
        left = [te.simplify(varmap) for te in self.left]
        right = [te.simplify(varmap) for te in self.right]
        return Sequent(left, right)
    
class Proof:
    "Represents 1 step of a proof tree.."
    # rule: which rule was used (str)
    # assumptions: what is assumed (list of Proofs)
    # conclusion: what is concluded (Sequent)
    def __init__(self, rule, assumptions, conclusion, varmap):
        self.rule = rule
        self.assumptions = assumptions
        self.conclusion = conclusion
        self.varmap = varmap

    def __repr__(self):
        return self.rule+' '+`self.assumptions`+' -> '\
               +`self.conclusion`

    def simplify(self, varmap=None):
        if varmap == None:
            varmap = self.varmap
        assum = [a.simplify(varmap) for a in self.assumptions] 
        concl = self.conclusion.simplify(varmap)
        return Proof(self.rule, assum, concl, varmap)

    def to_latex_array(self, depth = 1, pp_varmap=None):
        if pp_varmap == None: pp_varmap={}

        # Draw asumptions
        str = '\\begin{array}{c}\n'
        for assumption in self.assumptions:
            str += '      '*depth + \
                   assumption.to_latex(depth+1, pp_varmap) + \
                   ' \\quad \n'
        str = str[:-1] + '\\\\'+'\\hline'+'\n'

        # Add conclusion
        str += '      '*depth + '{' + \
               self.conclusion.to_latex(pp_varmap) + '}'

        # Close array
        str += '\\\\\n'+'      '*depth+'\\end{array}'
        
        # The rule type
        str += ' \\textrm{' + \
               re.sub(r'\\', r'$\\backslash$', self.rule) + '}' 

        if depth == 1:
            return '$$\n'+str+'\n$$'
        else:
            return '{'+str+'}'
    
    def to_latex(self, depth = 1, pp_varmap=None):
        if pp_varmap == None: pp_varmap={}

        # Draw asumptions
        str = '\\frac{\\textrm{$ \n'
        for assumption in self.assumptions:
            str += '      '*depth + \
                   assumption.to_latex(depth+1, pp_varmap) + \
                   ' \\quad \n'
        str = str[:-1] + '$}}\n'

        # Add conclusion
        str += '      '*depth + '{' + \
               self.conclusion.to_latex(pp_varmap) + '}'

        # The rule type
        rule = re.sub(r'\\', r'$\\backslash$', self.rule)
        rule = re.sub(r'\*', r'$\\cdot$', rule)
        str += ' \\textrm{' + rule + '}'

        if depth == 1:
            return '$$\n'+str+'\n$$'
        else:
            return '{'+str+'}'
    
    # Returns (str, right)
    def pp(self, left=0, toplevel=1, pp_varmap=None):
        if pp_varmap == None: pp_varmap={}
        right = left
        str = ''
        
        if _VAR_NAMES:
            concl = self.conclusion.pp(pp_varmap)
        else:
            concl = `self.conclusion`

        # Draw assumptions
        for assumption in self.assumptions:
            (s, right) = assumption.pp(right, 0, pp_varmap)
            str = _align_str(str, s)
            right += 5

        # Draw line.
        right = max(right-5, left+len(concl))
        str += ' '*left + '-'*(right-left) + ' ' + self.rule + '\n' 

        # Draw conclusion
        start = left+(right-left-len(concl))/2
        str += ' '*start + concl + '\n'

        if toplevel:
            if _SHOW_VARMAP:
                return str+'\nVarmap: '+ `self.varmap`+'\n'
            else:
                return str
        else:
            return (str, right)

def _align_str(s1, s2):
    lines1 = s1.split('\n')
    lines2 = s2.split('\n')

    if lines1[-1] == '': lines1 = lines1[:-1]
    if lines2[-1] == '': lines2 = lines2[:-1]

    str = ''

    while len(lines1) > len(lines2):
        str += lines1[0] + '\n'
        lines1 = lines1[1:]
        
    while len(lines2) > len(lines1):
        str += lines2[0] + '\n'
        lines2 = lines2[1:]

    for n in range(len(lines1)):
        x = 0
        for x in range(min(len(lines1[n]), len(lines2[n]))):
            if lines1[n][x] == ' ':
                str += lines2[n][x]
            elif lines2[n][x] == ' ':
                str += lines1[n][x]
            else:
                raise ValueError('Overlapping strings')
        str += lines1[n][x+1:]
        str += lines2[n][x+1:]
        str += '\n'
    return str
        
######################################
# PROOF LOGIC
######################################

# Prove a sequent.  Variables can have their values filled in.
# If short_circuit is 1, return once we find any proof.  If
# short_circuit is 0, return all proofs.
def prove(sequent, short_circuit=0):
    proofs = _prove(sequent, VarMap(), short_circuit, 0)
    return [proof.simplify() for proof in proofs]

def _prove(sequent, varmap, short_circuit, depth):
    if _VERBOSE:
        print ('  '*depth)+'Trying to prove', sequent

    proofs = []

    if proofs == [] or not short_circuit:
        proofs = proofs + introduce(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + rslash_l(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + lslash_l(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + rslash_r(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + lslash_r(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + dot_l(sequent, varmap, short_circuit, depth+1)
    if proofs == [] or not short_circuit:
        proofs = proofs + dot_r(sequent, varmap, short_circuit, depth+1)

    if _VERBOSE:
        print '  '*depth+'Found '+`len(proofs)`+' proof(s)'

    return proofs

def introduce(sequent, varmap, short_circuit, depth):
    if len(sequent.left) != 1 or \
       len(sequent.right) != 1 or \
       sequent.left[0].type != sequent.right[0].type:
        return []

    newseq = Sequent(sequent.left, sequent.right)
    r_term = sequent.right[0].term
    l_term = sequent.left[0].term

    # Try to unify
    te = sequent.left[0].unify(sequent.right[0], varmap)
    if te == None: newseq = sequent
    else: newseq = Sequent([te], [te])

    return [Proof('I', (), newseq, varmap)]

def rslash_l(sequent, varmap_in, short_circuit, depth):
    proofs = []

    for i in range(len(sequent.left)-1):
        if isinstance(sequent.left[i].type, RSlash) and \
           len(sequent.right) == 1:
            # Set up some variables...
            beta = Var()
            alpha = sequent.left[i].term
            A = sequent.left[i].type.result
            B = sequent.left[i].type.arg
            Gamma1 = sequent.left[:i]
            gamma = sequent.right[0].term
            C = sequent.right[0].type

            # Try all combinations of Delta, Gamma2..
            for j in range(i+1, len(sequent.left)):
                Delta = sequent.left[i+1:j+1]
                Gamma2 = sequent.left[j+1:]

                # Try proving the left assumption.
                l_seq = Sequent(Delta, [TypedTerm(beta, B)])
                l_proofs = _prove(l_seq, varmap_in, short_circuit, depth)

                # For each proof, try proving the right half.  Make
                # sure to keep beta bound to the same thing..
                for l_proof in l_proofs:
                    beta = l_proof.conclusion.right[0].term
                    r_seq = Sequent(Gamma1+\
                                    [TypedTerm(Appl(alpha, beta), A)]+\
                                    Gamma2, [TypedTerm(gamma, C)])
                    r_proofs = _prove(r_seq, varmap_in, short_circuit, depth)
                    for r_proof in r_proofs:
                        varmap = r_proof.varmap + l_proof.varmap
                        right = r_proof.conclusion.right[0]
                        right = right.unify(TypedTerm(gamma, C), varmap)
                        proofs.append(Proof('/L', [l_proof, r_proof],\
                                            Sequent(sequent.left,[right]),\
                                            varmap))
                        if short_circuit: return proofs

    return proofs

def lslash_l(sequent, varmap_in, short_circuit, depth):
    proofs = []

    for i in range(1, len(sequent.left)):
        if isinstance(sequent.left[i].type, LSlash) and \
           len(sequent.right) == 1:
            # Set up some variables...
            beta = Var()
            alpha = sequent.left[i].term
            A = sequent.left[i].type.result
            B = sequent.left[i].type.arg
            gamma = sequent.right[0].term
            C = sequent.right[0].type
            Gamma2 = sequent.left[i+1:]

            # Try all combinations of Delta, Gamma2..
            for j in range(i):
                Delta = sequent.left[j:i]
                Gamma1 = sequent.left[:j]

                # Try proving the left assumption.
                l_seq = Sequent(Delta, [TypedTerm(beta, B)])
                l_proofs = _prove(l_seq, varmap_in, short_circuit, depth)

                # For each proof, try proving the right half.  Make
                # sure to keep beta bound to the same thing..
                for l_proof in l_proofs:
                    beta = l_proof.conclusion.right[0].term
                    r_seq = Sequent(Gamma1+\
                                    [TypedTerm(Appl(alpha, beta), A)]+\
                                    Gamma2, [TypedTerm(gamma, C)])
                    r_proofs = _prove(r_seq, varmap_in, short_circuit, depth)
                    for r_proof in r_proofs:
                        varmap = r_proof.varmap + l_proof.varmap
                        right = r_proof.conclusion.right[0]
                        right = right.unify(TypedTerm(gamma, C), varmap)
                        
                        proofs.append(Proof('\\L', [l_proof, r_proof],\
                                            Sequent(sequent.left,[right]),
                                            varmap))
                        if short_circuit: return proofs
    return proofs

def rslash_r(sequent, varmap, short_circuit, depth):
    proofs = []

    # Make sure the right side is properly formatted..
    if len(sequent.right) != 1 or \
       not isinstance(sequent.right[0].type, RSlash):
        return proofs

    # Set up variables..
    x = Var()
    varmap.add(x, None)
    alpha = Appl(sequent.right[0].term, x)
    B = sequent.right[0].type.result
    A = sequent.right[0].type.arg
    Gamma = sequent.left

    seq = Sequent(Gamma + [TypedTerm(x, A)], \
                  [TypedTerm(alpha, B)])

    s_proofs = _prove(seq, varmap, short_circuit, depth)
    for proof in s_proofs:
        varmap = proof.varmap.copy()
        right1 = TypedTerm(Abstr(x, proof.conclusion.right[0].term),\
                           RSlash(B, A))
        right2 = TypedTerm(Abstr(x, alpha), sequent.right[0].type)
        right = right1.unify(right2, varmap)
        if right == None: continue
        varmap.add(x, None)
        concl = Sequent(Gamma, [right])
        proofs.append(Proof('/R', [proof], concl, varmap))

    return proofs

def lslash_r(sequent, varmap, short_circuit, depth):
    proofs = []

    # Make sure the right side is properly formatted..
    if len(sequent.right) != 1 or \
       not isinstance(sequent.right[0].type, LSlash):
        return proofs

    # Set up variables..
    x = Var()
    varmap.add(x, None)
    alpha = Appl(sequent.right[0].term, x)
    B = sequent.right[0].type.result
    A = sequent.right[0].type.arg
    Gamma = sequent.left

    seq = Sequent([TypedTerm(x, A)] + Gamma, \
                  [TypedTerm(alpha, B)])

    s_proofs = _prove(seq, varmap, short_circuit, depth)
    for proof in s_proofs:
        right1 = TypedTerm(Abstr(x, proof.conclusion.right[0].term),\
                           LSlash(A, B))
        right2 = TypedTerm(Abstr(x, alpha), sequent.right[0].type)
        right = right1.unify(right2, varmap)
        if right == None: continue
        varmap = varmap + proof.varmap
        varmap.add(x, None)
        concl = Sequent(Gamma, [right])
        proofs.append(Proof('\\R', [proof], concl, varmap))

    return proofs

def dot_l(sequent, varmap, short_circuit, depth):
    proofs = []

    for i in range(0, len(sequent.left)):
        if isinstance(sequent.left[i].type, Dot) and \
           len(sequent.right) == 1:
            Gamma1 = sequent.left[:i]
            Gamma2 = sequent.left[i+1:]
            A = sequent.left[i].type.left
            B = sequent.left[i].type.right
            alpha = sequent.left[i].term

            # Deal with alpha if we can
            if isinstance(alpha, Tuple):
                alpha1 = alpha.left
                alpha2 = alpha.right
            elif isinstance(alpha, Var):
                alpha_var = alpha
                alpha1 = Var()
                alpha2 = Var()
                alpha = Tuple(alpha1, alpha2)
                varmap.add(alpha_var, alpha)
            else:
                # We can't deal.. :(  Move on...
                continue

            left = Gamma1 + [TypedTerm(alpha1, A)] + \
                   [TypedTerm(alpha2, B)] + Gamma2
            right = sequent.right
            s_proofs = _prove(Sequent(left, right), varmap, \
                              short_circuit, depth)
            for proof in s_proofs:
                varmap = proof.varmap.copy()
                sequent.right[0].unify(proof.conclusion.right[0], varmap) 
                proofs.append(Proof('*L', [proof], sequent, varmap))
                if short_circuit: return proofs
                
    return proofs

def dot_r(sequent, varmap_in, short_circuit, depth):
    proofs = []

    for i in range(1, len(sequent.left)):
        if isinstance(sequent.right[0].type, Dot) and \
           len(sequent.right) == 1:
            Gamma1 = sequent.left[:i]
            Gamma2 = sequent.left[i:]
            A = sequent.right[0].type.left
            B = sequent.right[0].type.right
            alphabeta = sequent.right[0].term

            # Deal with alpha if we can
            if isinstance(alphabeta, Tuple):
                alpha = alphabeta.left
                beta = alphabeta.right
            elif isinstance(alphabeta, Var):
                alphabeta_var = alphabeta
                alpha = Var()
                beta = Var()
                alphabeta = Tuple(alpha, beta)
                varmap_in.add(alphabeta_var, alphabeta)
            else:
                # We can't deal.. :(  Move on...
                continue

            left = Sequent(Gamma1, [TypedTerm(alpha, A)])
            right = Sequent(Gamma2, [TypedTerm(beta, B)])

            for r_proof in _prove(right, varmap_in, short_circuit, depth):
                for l_proof in _prove(left, varmap_in, short_circuit, depth):
                    varmap = r_proof.varmap + l_proof.varmap
                    right = TypedTerm(Tuple(l_proof.conclusion.right[0].term,\
                                            r_proof.conclusion.right[0].term),
                                      sequent.right[0].type)
                    right = right.unify(sequent.right[0], varmap)
                    concl = Sequent(Gamma1+Gamma2, [right])
                    proofs.append(Proof('*R', [l_proof, r_proof],\
                                        concl, varmap))
                    if short_circuit: return proofs
    return proofs
######################################
# TESTING
######################################

def find_proof(left, right, short_circuit=1):
    sq = Sequent(left, right)
    proofs = prove(sq, short_circuit)
    if proofs:
        print '#'*60
        print "## Proof(s) for", sq.pp()
        for proof in proofs:
            print
            print proof.to_latex()
    else:
        print '#'*60
        print "## Can't prove", sq.pp()

def test_lambek():
    lex = Lexicon()
    lex.load(open('lexicon.txt', 'r'))

    find_proof(lex.parse('[np/n] [n]'), lex.parse('[np]'))
    find_proof(lex.parse('[np] [np\s]'), lex.parse('[s]'))
    find_proof(lex.parse('[n] [np\s]'), lex.parse('[(np/n)\s]'))
    find_proof(lex.parse('dog sleeps'), lex.parse('[(np/n)\s]'))
    find_proof(lex.parse('the kid runs'), lex.parse('[s]'))
    find_proof(lex.parse('john believes tom likes'), lex.parse('[s/np]'))
    find_proof(lex.parse('john likes mary'), lex.parse('[s]'))
    find_proof(lex.parse('likes'), lex.parse('[np\s/np]'), 0)
    find_proof(lex.parse('[a/b] [b]'), lex.parse('foo'))
    find_proof(lex.parse('[(np/n)*n]'), lex.parse('[np]'))
    find_proof(lex.parse('[(np\\s)/np]'), lex.parse('[np\\(s/np)]'))
    find_proof(lex.parse('gives2 tom mary'), lex.parse('[np\\s]'))
    find_proof(lex.parse('gives'), lex.parse('[np\\s/(np*np)]'))
    find_proof(lex.parse('the city tom likes'), lex.parse('[np*(s/np)]'))


HELP="""% Lambek Calculus Theorem Proover
%
% Type a sequent you would like prooved.  Examples are:
%   [np/n] [n] => [np]
%   [np] [np\s] => [s]
%   [n] [np\s] => [(np/n)\s]
%   dog sleeps => [(np/n)\s]
%   the kid runs => [s]
%   john believes tom likes => [s/np]
%   john likes mary => [s]
%   likes => [np\s/np]
%   [a/b] [b] => foo
%   [(np/n)*n] => [np]
%   [(np\\s)/np] => [np\\(s/np)]
%   gives2 tom mary => [np\\s]
%   gives => [np\\s/(np*np)]
%   the city tom likes => [np*(s/np)]
%
% Other commands:
%   help         -- show this information
%   latexmode    -- toggle latexmode (outputs in LaTeX)
%   shortcircuit -- toggle shortcircuit mode (return just one proof)
%   lexicon      -- display the lexicon contents
%   quit         -- quit
"""
    
def mainloop(input, out, lex, latexmode, shortcircuit):
    while 1:
        out.write('%>> ')
        str = input.readline()
        if str == '': return
        str = str.strip()
        if (str=='') or (str[0]=='#') or (str[0]=='%'): continue
        if str.find('=>') == -1:
            if str.lower().startswith('latex'):
                if str.lower().endswith('off'): latexmode = 0
                elif str.lower().endswith('on'): latexmode = 1
                else: latexmode = not latexmode
                if latexmode: print >>out, '% latexmode on'
                else: print >>out, 'latexmode off'
            elif str.lower().startswith('short'):
                if str.lower().endswith('off'): shortcircuit = 0
                elif str.lower().endswith('on'): shortcircuit = 1
                else: shortcircuit = not shortcircuit
                if shortcircuit: print >>out, '%shortcircuit on'
                else: print >>out, '% shortcircuit off'
            elif str.lower().startswith('lex'):
                words = lex.words()
                print >>out, '% Lexicon: '
                for word in words:
                    print >>out, '%  ' + word + ':', \
                          ' '*(14-len(word)) + lex[word].pp() 
            elif str.lower().startswith('q'): return
            elif str.lower().startswith('x'): return
            else:
                print >>out, HELP
        else:
            try:
                (left, right) = str.split('=>')
                seq = Sequent(lex.parse(left), lex.parse(right))
                proofs = prove(seq, shortcircuit)
                print >>out
                print >>out, '%'*60
                if proofs:
                    print >>out, "%% Proof(s) for", seq.pp()
                    for proof in proofs:
                        print >>out
                        if latexmode: print >>out, proof.to_latex()
                        else: print >>out, proof.pp()
                else:
                    print >>out, "%% Can't prove", seq.pp()
            except KeyError, e:
                print 'Mal-formatted sequent'
                print 'Key error (unknown lexicon entry?)'
                print e
            except ValueError, e:
                print 'Mal-formatted sequent'
                print e

# Usage: argv[0] lexiconfile
def main(argv):
    if (len(argv) != 2) and (len(argv) != 4):
        print 'Usage:', argv[0], '<lexicon_file>'
        print 'Usage:', argv[0], '<lexicon_file> <input_file> <output file>'
        return
    lex = Lexicon()
    try: lex.load(open(argv[1], 'r'))
    except:
        print "Error loading lexicon file"
        return

    if len(argv) == 2:
        mainloop(sys.stdin, sys.stdout, lex, 0, 1)
    else:
        out = open(argv[3], 'w')
        print >>out, '\documentclass{article}'
        print >>out, '\usepackage{fullpage}'
        print >>out, '\\begin{document}'
        print >>out
        mainloop(open(argv[2], 'r'), out, lex, 1, 1)
        print >>out
        print >>out, '\\end{document}'

if __name__ == '__main__':
    main(sys.argv)

    

