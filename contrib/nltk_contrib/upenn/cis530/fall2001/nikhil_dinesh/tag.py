"""
A parser for Tree Adjoining Grammars, driven by a bottom-up embedded
push down automaton.  The L{demo} function creates a sample grammar,
and uses it to parse a simple sentence.  It then draws the resulting
tree, and prints information about the parse derivation.

Administrivia
=============

Copyleft Nikhil Dinesh nikhild@gradient.cis.upenn.edu

I hereby authorise anyone to do whatever they want with this code. 

If while going through the code, it seems that a particular variable does
nothing then it probably doesn't. If you think that there was a better way
to code something you are probably right. If you have any doubts or are
amazed at what this code does feel free to e-mail me.

Details
=======

This is intended as a Tree Adjoining Grammar tool. It provides two
utilities in terms of classes that can be used:

  1. Definition of Tree Adjoining Grammars (the Tag class)
  2. A TAG parser which extends the ParserI interface. In addition to the
     parse method which returns a list of parse trees there is a
     print_derivations method which gives a step by step derivation of the
     parse tree. The derivation output is textual. (the TagParser class)

Terminology
===========

I hope that anyone using this tool will have some idea of what a TAG is.
You should know what is/are:
  1. An initial tree
  2. An auxiliary tree
  3. A frontier node
  4. A foot node
  5. The operations of substitution and adjoining.

If you don't and want to use this tool (and understand it), it might be
a good idea to read a paper on Tag. Google should help you.

Thats about it. Please let me know if there are any bugs.
"""
  
from nltk.tree import *
from nltk.cfg import *
from nltk.parser import ParserI
from nltk.tokenizer import WSTokenizer
import time
from nltk.chktype import chktype

############################################################
# BEGIN TEMPORARY BACKWARDS COMPATIBILITY FIXES
class Rule:
    def __init__(self, lhs, rhs):
        self._lhs = lhs
        self._rhs = rhs
    def drule(self):
        return DottedRule(self._lhs, self._rhs)
    def __len__(self):
        return len(self._rhs)
    def __getitem__(self, index):
        return self._rhs[index]
    def lhs(self):
        return self._lhs
    def rhs(self):
        return self._rhs

class DottedRule(Rule):
    def __init__(self, lhs, rhs, pos=0):
        self._lhs = lhs
        self._rhs = rhs
        self._pos = pos
    def pos(self):
        return self._pos
    def shift(self):
        return DottedRule(self._lhs, self._rhs, self._pos + 1)
    def __eq__(self, other):
        return (Rule.__eq__(self, other) and
                self._pos == other._pos)
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash((self._lhs, self._rhs, self._pos))
# END TEMPORARY BACKWARDS COMPATIBILITY FIXES
############################################################

######################################################################

class Tag:
    """
    This class defines Tree Adjoining Grammars and their substitution and
    adjoining operations.
      
    Definition
    ==========
      The position of a node in a tree is represented by a list as
      follows:
        
        1. [0] root node
        2. [0,a,b,c,d...] where a is the ath child of the root,
           b is the bth child of a ...and so on

    Specification
    =============
      The terminals should be on the frontier of the trees because
      all interior nodes are considered non terminals. The
      nonterminals on the frontier of the tree should be trees with
      only the node and no children.
      
      The foot node of auxiliary trees should have a '*' appended to
      it's label. This is to distinguish it from other nodes on the
      frontier with the same label.
    """
    
    def __init__(self,initialtrees,auxiliarytrees):
        self._initialtrees = initialtrees
        self._auxiliarytrees = auxiliarytrees

    def getinitialtrees(self):
        return self._initialtrees

    def getauxiliarytrees(self):
        return self._auxiliarytrees
    
    ################################################################### 
    #Substitutes tree2 on the frontier of t1 at the appropriate position
    
    def substitute(self,tree1,tree2,position):
        """
          Substitutes tree2 on the frontier of tree1 at the appropriate
          position.
        """
        
        if (len(position)==1 and position[0]==0) and isinstance(tree1.node(),Tree) and tree1.node().node() == tree2.node():
            return tree2
        else:
            return self._substitution(tree1,tree2,position[1:])


    def _substitution(self,tree1,tree2,position):
        if isinstance(tree1,Tree):
            kids = []
            ctr = 1
            donesub = 0
            for tree in tree1.children():
                if isinstance(tree,Tree):
                   if tree.children() == ():
                      if len(position) == 1 and position[0] == ctr:
                         if tree.node() == tree2.node() or (tree.node()[:-1]==tree2.node() and tree.node()[-1]=='*'):
                            kids.append(tree2)
                            donesub = 1
                         else:
                            return Tree(tree1.node(),'Bad Positon')
                      else:
                         kids.append(tree)
                   else:
                      
                      if ctr == position[0]:
                        kids.append(self._substitution(tree,tree2,position[1:]))
                      else:
                        kids.append(tree)
                else:
                   kids.append(tree)
                ctr += 1
        else:
            return(Tree('Bad Tree'))
        if len(position) == 1 and donesub == 0:
            return Tree(tree1.node(),'Bad Position')
        else:
            return(Tree(tree1.node(),*kids))
    ########################################################################
        
    ########################################################################
    

    def adjoin(self,tree1,tree2,position):
        """
          Adjoins tree2 to tree1 in the appropriate position. tree2 should
          be an auxiliary tree. Adjoining is basically a splicing operation
          which:
          1.excises the subtree of tree1 at the position,
          2.attaches tree2 there ,and 
          3.attaches the excised subtree at the foot node (defined earlier)
          of tree2.
        """
        if len(position)==1 and position[0]==0:
            
            return self.substitute(tree2,tree1,self.foot(tree2))
        else:
            return self._adjoining(tree1,tree2,position[1:])

    def _adjoining(self,tree1,tree2,position):
        if isinstance(tree1,Tree):
            kids = []
            ctr = 1
            doneadj = 0
            for tree in tree1.children():
                if ctr == position[0] and isinstance(tree,Tree):
                    if len(position) == 1:
                        
                        if tree.node() == tree2.node() or (tree.node()[-1] == '*' and tree.node()[:-1]==tree2.node()):
                            doneadj = 1
                            kids.append(self.substitute(tree2,tree,self.foot(tree2)))
                        else:
                            kids.append('Bad Adjunction')
                    else:
                        kids.append(self._adjoining(tree,tree2,position[1:]))
                else:
                    kids.append(tree)
                ctr += 1

            
                
            if len(position) == 1 and doneadj == 0:
                return Tree(tree1.node(),'Bad Position')
            else:
                return(Tree(tree1.node(),*kids))
           
        else:
            return('Bad Tree')
    ######################################################################
    
    ######################################################################## 
    
    def foot(self,tree1):
        """
           Returns the position of the foot i.e. the node at the frontier
           which has the same label as the root
        """
        return [0]+self.footpos(tree1,tree1.node())

    def footpos(self,tree1,root):
        position = []
        ctr = 1
        
        if isinstance(tree1,Tree):
            for tree in tree1.children():
                if isinstance(tree,Tree):
                    if tree.children() == () and tree.node()[:-1] == root and tree.node()[-1] == '*':
                        return [ctr] 
                    else:
                        position = position + self.footpos(tree,root)
                        if position <> []:
                            position = [ctr] + position
                            return position
                ctr += 1

        return []
     ####################################################################

    
#######################################################################
        
###############################################################

class ParsingStructure:
    """
      The state of a particular parse which is represented by:
        1. The stack set - which is a set of stacks. In the simplified
           version of the BEPDA here a single list (not stack) would have
           sufficed. But to keep some semblance with the formalism I have
           used the term stack set. It might be easier to just think of it
           as a stack.
        
        2. and 3. The tree stack and queue. These structures used together
           by the methods of the BEPDA ensure that:
               1. The tree being traversed is on top of the stack
               2. Substitution uses the first two elements of the stack
               3. Adjoining uses the first element of the stack and the
                  last element of the queue.
           Just to draw the parse trees. The final tree will be
           available on the top of the stack.
               
        4. The pending adjunctions stack
      
        5. The unconsumed input
      
        6. The unconsumed frontier nodes ( which gives us an idea whether
           or not a particular tree could be added to the derivation at this
           state because each unconsumed node will  consume atleast one
           lexical item. That together with the unconsumed input and the
           number of frontier nodes on a tree tells us whether it is worth
           our while to use the tree. Basically reduces the number of
           redundant parses)
      
        7. The operations done so that the steps can be shown.
    """
                                        
    def __init__(self,stackset,ts,tq,pas,ip,ut,op):
        self._stackset = stackset
        self._treestack = ts
        self._treeq = tq
        self._pendadj = pas
        self._ip = ip
        self._unconsumedterminals = ut
        self._op = op

    def stack(self):
        return copystackset(self._stackset)

    def treestack(self):
        return self._treestack

    def treeq(self):
        return self._treeq

    def pastack(self):
        return self._pendadj

    def ip(self):
        return self._ip

    def update(self,i):
        self._unconsumedterminals += i

    def ut(self):
        return self._unconsumedterminals

    def ops(self):
        return self._op
###########################################################

    
##########################################################

class TreeRule:
    """
      The details of a context free rule in a tree containing:
      1.The dotted rule
      2.Whether it is from an initial or auxiliary tree
      3.The tree number
      4.The position of the lhs node of rule in the tree in list form
    """
    
    def __init__(self,rule,category,treeno,position):
        self._rule = rule
        self._category = category
        self._treeno = treeno
        self._position = position

    def rule(self):
        return self._rule

    def cat(self):
        return self._category

    def treeno(self):
        return self._treeno

    def pos(self):
        return self._position

    def __len__(self):
        return 1
###############################################################


###############################################################


def treetorules(tree1):
    """
     Converts a tree to a set of context free productions
    """
    RuleList = []
    RuleRhs = []
    if isinstance(tree1,Tree):
        for tree in tree1.children():
            if isinstance(tree,Tree):
                RuleRhs.append(tree.node())
                RuleList.append(treetorules(tree))
            else:
                RuleRhs.append(tree)
                RuleList.append(treetorules(tree))
    else:
        return [Rule(tree1,(tree1,))]

    if RuleRhs == []:
        return [Rule(tree1,(tree1,))]

    return [Rule(tree1.node(),tuple(RuleRhs))] + RuleList
#################################################################

#################################################################
#Copy the stack set before modification to avoid any memory
#complications


def copystackset(stack_set):
    new_stack_set = []
    for elt in stack_set:
        l=[]
        for ele in elt:
            l.append(ele)
        new_stack_set.append(l)
    return new_stack_set

##################################################################
#A few operations to make life easier for stack manipulation in the
#automaton

def swap(stack_set,c,f):
    new_stack_set = copystackset(stack_set)
    l = new_stack_set[len(new_stack_set)-1]
    i = 0
    done = 0
    while len(l[i:])>= len(c) and done==0:
        if l[i:i + len(c)] == c:
            l[i:i+len(c)] = f
            done = 1
        i = i+1
    
    return new_stack_set

def push(stack_set,f):
    new_stack_set = copystackset(stack_set)
    new_stack_set[len(new_stack_set)-1]+= f
    return new_stack_set

def wrap(stack_set,f):
    new_stack_set = copystackset(stack_set)
    new_stack_set.append([f])
    return new_stack_set

def unwrap_a(stack_set,f,g):
    new_stack_set = copystackset(stack_set)
    new_stack_set = new_stack_set[0:len(new_stack_set)-1]
    new_stack_set = swap(new_stack_set,f,g)
    return new_stack_set 

def unwrap_b(stack_set,f,g):
    n_s_set = copystackset(stack_set)
    n_s_set = n_s_set[0:len(n_s_set)-2] + [n_s_set[len(n_s_set)-1]]
    n_s_set = swap(n_s_set,f,g)
    return n_s_set

def countleaves(tree1):
    sum = 0
    for tree in tree1.children():
       
        if isinstance(tree,Tree):
           sum += countleaves(tree)
        else:
            sum += 1
        

    if tree1.children() == ():
        return 1
    else:
        return sum
########################################################################

########################################################################
#Given a dotted rule and a list of rules for the tree, these two modules
#will return the rule for the symbol after the dot
def getrule(r,l):
    position = r.pos()
    return getrule1(r,[l],position)

def getrule1(r,l,position):
    
    if len(position)>= 1 :
        t = getrule1(r,l[position[0]],position[1:])
        return TreeRule(t.rule().drule(),t.cat(),t.treeno(),[position[0]]+t.pos())
    else:
        if len(l)> r.rule().pos()+1:
            return TreeRule(l[r.rule().pos()+1][0].drule(),r.cat(),r.treeno(),[r.rule().pos()+1])
        else:
            return TreeRule(Rule('NoRule','NoRule').drule(),'F',0,[])
#######################################################################       
           
#######################################################################

class Bepda:
    """
       This class represents the Bottom up Embedded Push Down Automaton
       which models the parsing strategy. It will be referred to as BEPDA
       henceforth.

       An EPDA is the formalism for a TAG which assigns structure to the set of
       accepted strings based on final state or empty stack similar to the
       PDA's for CFGs. The version of the BEPDA implemented here reconizes
       strings on empty stack. Its is Bottom up in the manner in which the
       adjunctions takes place. The last adjunction is done first and the
       result of this is passed to the previous tree waiting for adjunction.

       Compiling TAG into BEPDA
       ========================
       
       Each tree is represented by a set of ordered context free
       productions a follows::
       
           Node -> Child1 Child2...Childn
           Frontier Node -> Leaf (Remember that fr. nodes are of two
                                  types.  Trees without children for
                                  non terminals and strings for
                                  children. This property is used to
                                  determine whether a node is a
                                  candidate for substitution or
                                  adjoining or comparison with an
                                  input symbol.

       if each tree has a list of context free productions and the index for
       this list is specified in the same manner as the positions for
       subsitution and adjoining

       The methods of the BEPDA model the parsing strategy.

       Each of the methods takes in a state (parse) and returns the possible
       states (parses).

       Ref: A Formal Definition of Bottom-Up Embedded Push-Down Automata and
       Their Tabulation Technique - Alonso, Clergerie, and Vilares

       (The method implemented here is less formal and hopefully more
       easily understood than the one in the paper.)

    """
    def __init__(self,tag):
        if isinstance(tag,Tag):
            self._tag = tag
            
            self._initial = tag.getinitialtrees()
            self._auxiliary = tag.getauxiliarytrees()
            
            self._rulelisti = []
            self._rulelista = []
            for tree in self._initial:
                self._rulelisti += [treetorules(tree)]
                
            for tree in self._auxiliary:
                self._rulelista += [treetorules(tree)]

            self._mode = 0

            
    ##################################################################
            
    def initialise(self,parse,basecat):
            """
               Initialises a parse. That is, for each tree rooted in the
               start symbol is creates a new parse.
            """
            i=0
            parses = []
            
            #Pushes rules rooted in the start symbol onto the stack
            for rule in self._rulelisti:
                newparse = []
                if rule[0].lhs() == basecat:
                    t = TreeRule(rule[0].drule(),'I',i,[0])
                    stack_set = wrap(parse.stack(),t)
                    noleaves = countleaves(self._initial[i])
                    if noleaves <= len(parse.ip()):
                       newparse = ParsingStructure(stack_set,[self._initial[i]],[],[],parse.ip(),noleaves,parse.ops())
                       parses.append(newparse)
                i = i + 1
                
            return parses
        
    ####################################################################
        
    def final(self,parse):
        """
          If a completely consumed tree rooted in the start symbol and
          the initial stack symbol are on the top of the stack and
          the input is totally consumed, stop
        """
          
        parses = []
        stack_set = parse.stack()
        
        #If a completely consumed tree rooted in the start symbol and
        #the initial stack symbol are on the top of the stack and
        #the input is totally consumed, stop
        
        if len(stack_set)==2 and stack_set[0][0]=='$0' and len(parse.ip())==0 and len(parse.pastack())==0:
            
            if isinstance(stack_set[1][0],TreeRule) and stack_set[1][0].pos()==[0]:
                
                if stack_set[1][0].rule().pos() == len(stack_set[1][0].rule()):
                    
                   new_stack_set = unwrap_a(stack_set,['$0'],['$f'])
                   parses.append(ParsingStructure(new_stack_set,parse.treestack(),parse.treeq(),parse.pastack(),parse.ip(),parse.ut(),parse.ops()))
                   
        return(parses)

    ######################################################################

    def call(self,parse):
        """
           Consumes a node. To do this it pushes the rule for the expansion
           of that node on the stack and continues
        """
        
        parses = []
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]

        #If the top element is a TreeRule
        if isinstance(r,TreeRule) and len(parse.ip())>0:
            
            #If the rule is not yet consumed
            if r.rule().pos() < len(r.rule()):
                
                #Consume it by getting the next rules and pushing
                #them onto the stack
                if r.cat() == 'I':
                    new_rule = getrule(r,self._rulelisti[r.treeno()])
                else:
                    new_rule = getrule(r,self._rulelista[r.treeno()])

                #Check if the new rule is valid
                if new_rule.cat() <> 'F':    
                    new_stack_set = wrap(stack_set,new_rule)
                    parses.append(ParsingStructure(new_stack_set,parse.treestack(),parse.treeq(),parse.pastack(),parse.ip(),parse.ut(),parse.ops()))
        return parses

    ################################################################
    
    
    def ret(self,parse):
        """
          When the rule on the top of the stack is completely consumed
          it is popped of the stack and the previous rule is shifted. The
          previous rule is of the same tree in the case of a return from a
          call and is of another tree in the case of a return from adjcall,
          subscall or footcall where this module is run with mode = 1.

     
        """
        
        parses = []
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]
        p = stack_set[len(stack_set)-2][0]
        
        

        #If the top 2 elements on the stack are tree rules
        if isinstance(r,TreeRule) and isinstance(p,TreeRule) :
            if p.cat()=='I':
                l=self._rulelisti
            else:
                l=self._rulelista
            new_rule = getrule(p,l[p.treeno()])
            #Get the lhs of the top element
            if isinstance(r.rule().lhs(),Tree):
                lhs = r.rule().lhs().node()
            else:
                lhs = r.rule().lhs()

            if lhs[-1]=='*':
                lhs = lhs[:-1]
                
            match = 0
            if new_rule.cat() <> 'F':
                if new_rule.cat()== r.cat() and new_rule.pos()==r.pos():
                    if new_rule.treeno()== r.treeno():
                        match = 1
                
            #If the rule is consumed
            if r.rule().pos() == len(r.rule()):
                
                #mode is 1 for adjret or footret
                #Otherwise the lhs of the rule should be the same as the
                #first symbol of the unconsumed portion of the previous
                #rule
                if isinstance(p.rule().lhs(),Tree):
                    lhsp = p.rule()[p.rule().pos()].node()
                else:
                    #Special case for adjunction at the root
                    if p.rule().pos()<len(p.rule()):
                        lhsp = p.rule()[p.rule().pos()]
                    else:
                        lhsp = '*'

                if lhsp[-1]=='*':
                    lhsp = lhsp[:-1]
                
                i=0
                while i<len(p.rule()):
                    i += 1
            
                if self._mode==1 or (lhsp==lhs and match==1):
                    #Pop the consumed rule and shift the previous rule by 1

                    #For adjunction at the root
                    if p.rule().pos() == len(p.rule()):
                        newrule = p.rule()
                    else:
                        newrule =  p.rule().shift()

                    newtreerule = TreeRule(newrule,p.cat(),p.treeno(),p.pos())
                    new_stack_set = unwrap_a(stack_set,[p],[newtreerule])
                    parses.append(ParsingStructure(new_stack_set,parse.treestack(),parse.treeq(),parse.pastack(),parse.ip(),parse.ut(),parse.ops()))
        
        return parses

    ###################################################################

    def scan(self,parse):
        """
          Scans a terminal symbol
        """
        
        parses=[]
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]
        
        #If the top element is a TreeRule object
        if isinstance(r,TreeRule) and len(parse.ip())>0:
            #symb is the next input symbol
            symb = parse.ip()[0].type()
          
            
            #If the rule represents a terminal
            if not(isinstance(r.rule().lhs(),Tree)) and len(r.rule())==1:
                
                #If the symbol matches the terminal consume it
                if r.rule().lhs() == r.rule()[0] and symb==r.rule().lhs():
                    if r.rule().pos()<len(r.rule()) :
                       newrule = r.rule().shift()
                       newtreerule = TreeRule(newrule,r.cat(),r.treeno(),r.pos())
                       new_stack_set = swap(stack_set,[r],[newtreerule])
                       parses.append(ParsingStructure(new_stack_set,parse.treestack(),parse.treeq(),parse.pastack(),parse.ip()[1:],parse.ut()-1,parse.ops()))
                    
        return parses

    ######################################################################

    def adjcall(self,parse):
        """
          Calls for an adjunction if the node being processed is a candidate
          for adjunction. We stop traversing this tree and begin traversing
          the auxiliary tree by:
          a. Pushing the rule on the pastack
          b. Consuming the rule on the top of the stack (moving the dot to
          the end)
          c. Pushing the first rule of the auxiliary tree on the top of the
          stack.

        """
        
        
        parses=[]
        stack_set = parse.stack()
        #The element on the top of the stack
        r = stack_set[len(stack_set)-1][0]

        #If it is a Treerule object
        if isinstance(r,TreeRule) and len(parse.ip())>0:
            #If it is not a frontier node and has not been consumed
            if not(isinstance(r.rule().lhs(),Tree)) and r.rule().pos()==0:
                i = 0
                
                #Find the trees with which it adjoins
                for elt in self._rulelista:
                    #If the root of the auxiliary tree matches with the lhs)
                    if elt[0].lhs()==r.rule().lhs() and (countleaves(self._auxiliary[i]) + parse.ut() - 1)<=len(parse.ip()):
                        tr = TreeRule(elt[0].drule(),'A',i,[0])

                        #Consume the rule on the top of the stack
                        #Push the unconsumed rule on the pastack
                        #Add the rule for the auxiliary tree to the stack
                
    
                         
                        newrule = r.rule()
                        j=0
                        while j<len(r.rule()):
                              newrule = newrule.shift()
                              j=j+1

                        nr = TreeRule(newrule,r.cat(),r.treeno(),r.pos())
                        new_stack_set = wrap(stack_set[0:len(stack_set)-1],nr)
                        new_stack_set = wrap(new_stack_set,tr)
                        
                        #Push the rule just popped on the pending adjunctions
                        #stack
                        pastack = parse.pastack()
                        pastack = [r] + pastack

                        #Add the auxiliary tree to the set of parsetrees
                        #itrees = parse.itrees()
                        #atrees = parse.atrees()

                        #Build the parsing structure
                        
                        ps = ParsingStructure(new_stack_set,[self._auxiliary[i]]+parse.treestack()[1:],parse.treeq()+[parse.treestack()[0]],pastack,parse.ip(),parse.ut()+countleaves(self._auxiliary[i])-1,parse.ops() )
                        parses.append(ps)
                    i+=1

        return parses

    ################################################################

    def adjret(self,parse):
        """
          Returns from an adjunction and draws the derived tree. 
        """
        
        #Save the elements we might need for constructing the new
        #derived tree at the end of a successful adjunction
        #ptrees = parse.ptrees()
        stack_set = parse.stack()
        #fc = parse.fc()

        r = stack_set[len(stack_set)-1][0]
        p = stack_set[len(stack_set)-2][0]
        
        
        
        parses = []
        if isinstance(r,TreeRule) and isinstance(p,TreeRule) :
            if r.cat()=='A' and r.rule().pos()== len(r.rule()) and r.pos()==[0] and (p.rule().pos()==len(p.rule())) and len(parse.treeq()):
                                 
                   position = p.pos()
                   #Set the mode variable which makes the ret method function
                   #for returning from an adjunction
                   self._mode = 1
                   parses = self.ret(parse)
                   self._mode = 0

        #If the ret method was successful
        if parses <> []:

            #Get the new parse trees
            lenq = len(parse.treeq())
            if p.cat()=='I':
                l=self._rulelisti
                tree1 = parse.treeq()[lenq-1]
            else:
                l=self._rulelista
                tree1 = parse.treeq()[lenq-1]



            cat = p.cat()
            no = p.treeno()

            if r.cat()=='I':
                tree2 = parse.treestack()[0]
            else:
                 tree2 = parse.treestack()[0]

            #Special case for adjoining at the root.
            position = p.pos()
                
            
            newop = [tree1,tree2,'A',position]
            
            newtree = self._tag.adjoin(tree1,tree2,position)
            
            newop.append(newtree)
            newop.append(parse.treestack())
            newop.append(parse.treeq())
            op = parse.ops()+[newop]
            
            
        #adjoining(ptrees(1),ptrees(0),position)

        
        newparses = []
 
        #Add the new parse trees to the state
        
        for parse in parses:
            newparses.append(ParsingStructure(parse.stack(),[newtree]+parse.treestack()[1:],parse.treeq()[0:lenq-1],parse.pastack(),parse.ip(),parse.ut(),op))
        return newparses

    #####################################################################

    def footcall(self,parse):
        """
          When the node under consideration is the foot node of an auxiliary
          tree pop an element off the pending adjunctions stack and resume
          traversing the old tree where we left off.
        """
        
        parses = []
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]
        #If it is a TreeRule on the top of the stack set
        if isinstance(r,TreeRule) and isinstance(r.rule().lhs(),Tree) and len(parse.treeq())>0:
            #If the rule is that of a foot node
            if r.rule().lhs().node()[:-1]==self._rulelista[r.treeno()][0].lhs() and r.rule().lhs().node()[-1]=='*':
                #If it is an auxiliary tree
                if r.cat() == 'A' and len(parse.pastack())>0 and len(parse.ip())>0:
                    #Pop the top element from the pending adjunctions stack
                    #Resume parsing on that tree
                    pastack=parse.pastack()
                    new_stack_set = wrap(stack_set,pastack[0])

                    tr = pastack[0]
                    if tr.cat()=='I':
                       tree = self._initial[tr.treeno()]
                    else:
                       tree = self._auxiliary[tr.treeno()]
                    
                    lenq = len(parse.treeq())
                   
                    
                    parses.append(ParsingStructure(new_stack_set,[parse.treeq()[lenq-1]]+parse.treestack(),parse.treeq()[:lenq-1],pastack[1:],parse.ip(),parse.ut(),parse.ops()))

          
        return parses
    
    #####################################################################

    def footret(self,parse):
        """
           If the tree on the pending adjuntions stack which we popped during
           footcall is completely traversed then the foot node is completely
           traversed.
        """
        
        parses = []
        parses = []
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]
        p = stack_set[len(stack_set)-2][0]
        
       
        if isinstance(p,TreeRule) and isinstance(p.rule().lhs(),Tree):
            if isinstance(p,TreeRule) :
                if p.cat()=='A' and p.rule().lhs().node()[:-1]==self._rulelista[p.treeno()][0].lhs() and p.rule().lhs().node()[-1]=='*' and r.rule().pos()==len(r.rule()):
                    #Make the ret method behave appropriately for footret
                    self._mode = 1
                    parses = self.ret(parse)
                    
                    self._mode = 0     

        newparses = []
        for parse in parses:
            newparses.append(ParsingStructure(parse.stack(),parse.treestack()[1:], parse.treeq()+[parse.treestack()[0]] ,parse.pastack(),parse.ip(),parse.ut(),parse.ops()))

        return newparses

    #####################################################################

    def subscall(self,parse):
        """
          A non-terminal on the frontier of any tree is a candidate for
          substitution. It can be substituted with an initial tree which
          is rooted with the same node. So we start traversing the new
          initial tree by pushing it on the top of the stack.
        """
        
        parses = []
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]

        if isinstance(r,TreeRule) and isinstance(r.rule().lhs(),Tree):
            i=0
            for elt in self._rulelisti:
                 #If the root of the auxiliary tree matches with the lhs)
                 if elt[0].lhs()==r.rule().lhs().node() and (countleaves(self._initial[i]) + parse.ut()-1 )<=len(parse.ip()):
                        tr = TreeRule(elt[0].drule(),'I',i,[0])
                        new_stack_set = wrap(stack_set,tr)

                        if r.cat()=='I':
                           tree = self._initial[r.treeno()]
                        else:
                           tree = self._auxiliary[r.treeno()]
                        #ptrees = [self._initial[i]] + parse.ptrees()
                        parses.append(ParsingStructure(new_stack_set,[self._initial[i]]+parse.treestack(),parse.treeq(),parse.pastack(),parse.ip(),parse.ut()+countleaves(self._initial[i])-1,parse.ops()))
                        
                 i+=1
        return parses

    #####################################################################

    def subsret(self,parse):
        """
          Return from a successful substituion.
        """
        
        #Save the elements we might need for constructing the new
        #derived tree at the end of a successful adjunction
        # ptrees = parse.ptrees()
        stack_set = parse.stack()
        r = stack_set[len(stack_set)-1][0]
        p = stack_set[len(stack_set)-2][0]
        
        #fc = parse.fc()
        
        
        parses = []
        if isinstance(r,TreeRule) and isinstance(p,TreeRule) and isinstance(p.rule().lhs(),Tree):
            if r.cat()=='I' and r.rule().pos()== len(r.rule()) and r.pos()==[0]and r.rule().lhs()==p.rule().lhs().node():
                
                   position = p.pos()
                   #Set the mode variable which makes the ret method function
                   #for returning from an adjunction
                   self._mode = 1
                   parses = self.ret(parse)
                   self._mode = 0

        #If the ret method was successful
        if parses <> []:

            #itrees = parse.itrees()
            #atrees = parse.atrees()

            #Get the new parse trees
            if p.cat()=='I':
                l=self._rulelisti
                tree1 = parse.treestack()[1]
            else:
                l=self._rulelista
                tree1 = parse.treestack()[1]
 
            cat = p.cat()
            no = p.treeno()

            if r.cat()=='I':
                tree2 = parse.treestack()[0]
            else:
                tree2 = parse.treestack()[0]
            
            if p.rule().pos()< len(p.rule()):
                if isinstance(p.rule().lhs(),Tree):
                    position = p.pos()
                else:
                    new_rule=getrule(p,l[p.treeno()])
                    position=new_rule.pos()
            else:
                position = [0]
            
            newop = [tree1,tree2,'S',position]
            newtree = self._tag.substitute(tree1,tree2,position)

           
            newop.append(newtree)
            newop.append(parse.treestack())
            newop.append(parse.treeq())
            op = parse.ops()+[newop]
            
        
        
        newparses = []

        #Add the new parse trees to the state
        for parse in parses:
            newparses.append(ParsingStructure(parse.stack(),[newtree]+parse.treestack()[2:],parse.treeq(),parse.pastack(),parse.ip(),parse.ut(),op))
        return newparses


                    
#########################################################################
    
class TagParser(ParserI):
    """
      A parser for Tags which is guided by the automaton. It calls the
      methods of the automaton repeatedly until there is nothing new to
      consider. In addition to the parse method which returns the list of
      parse trees, there is a method called print_derivations. This prints
      the list of operations for each parse.
    """
    
    def __init__(self,tag,basecat):
        self._tag = tag
        self._basecat = basecat
        self._bepda = Bepda(tag)
        self._deriv = 0

    def initialise(self,ip):
        return self._bepda.initialise(ParsingStructure([['$0']],[],[],[],ip,0,[]),self._basecat)

    def parse(self,tokens):
        parses = []
        parses = self.initialise(tokens)
        finalparses = []
        newparses = []
        ipsize = len(parses[0].ip())
        
        while len(parses)>0 :
            parse = parses[0]
            parses = parses[1:]
            newparses = []
            
            finalparses.append(self._bepda.final(parse))
            newparses.append(self._bepda.adjcall(parse))
            newparses.append(self._bepda.call(parse))
            newparses.append(self._bepda.subscall(parse))
            newparses.append(self._bepda.scan(parse))
            newparses.append(self._bepda.footcall(parse))
            newparses.append(self._bepda.ret(parse))
            newparses.append(self._bepda.adjret(parse))
            newparses.append(self._bepda.subsret(parse))
            newparses.append(self._bepda.footret(parse))
            
            
            for elt in newparses:
                for ele in elt:
                    if ele<>[]:
                       parses = [ele] + parses

            
            newfinal=[]
            for elt in finalparses:
                if elt <> []:
                    newfinal.append(elt)

           

            finalparses = newfinal

        
        if self._deriv == 0:
            parsetrees = []
            for elt in finalparses:
                for ele in elt:
                    parsetrees.append(ele.treestack()[0])
            return parsetrees
        else:
            ops = []
            for elt in finalparses:
                for ele in elt:
                    ops.append(ele.ops())
            return ops


    def print_derivations(self,tokens):
        self._deriv = 1
        ops = self.parse(tokens)
        self._deriv = 0

        i=1

        for elt in ops:
            print "**** For Parse ",i," ****"
            j=1
            
            for ele in elt:
                print "    **** Operation ",j," ****" 
                print "         Tree1 = ",ele[0]
                print "         Tree2 = ",ele[1]
                print "         op (S or A) = ",ele[2]
                print "         Position = ",ele[3]
                print "         Result = ",ele[4]
                j+=1
            print "*************************"
            i+=1



def demo():
      # Demonstration code

      # Defining the grammar

      initial_trees = [Tree('S',Tree('NP'),Tree('VP',Tree('VP',Tree('V','had'),Tree('NP')),Tree('PP'))),Tree('NP',Tree('N','I')),Tree('NP',Tree('N','map')),Tree('NP',Tree('N','desk')),Tree('PP',Tree('P','on'),Tree('NP'))]

      auxiliary_trees = [Tree('NP',Tree('D','my'),Tree('NP*')),Tree('NP',Tree('D','a'),Tree('NP*'))]


      tag = Tag(initial_trees,auxiliary_trees)

     
      # Constructing the parser
      basecat = 'S'
      parser = TagParser(tag,basecat)
      

      # Tokenizing the sentence

      sent = 'I had a map on my desk'
      
     
      tok_sent = WSTokenizer().tokenize(sent)
      

      #Parse and print derivations.
    

      parses = parser.parse(tok_sent)   

      parses[0].draw()

      parser.print_derivations(tok_sent)



if __name__ == '__main__': demo()
