Project: A Tree Adjoining Grammar(TAG) Tool

The Problem:
                 The nltk doesn't have an interface for TAGs and that was a
problem because you would expect any natural language toolkit (especially one
that comes out of UPenn ) to have such an interface !!! 
                 
What the tool does:
                   Enables definition of TAGs and provides a parser for them.

Design:

I will assume that the reader has some knowledge of TAGs .

        The tool consists of three parts:

a.The TAG class which enables the definition of TAGs
  For example,
         
      initial_trees = [Tree('S',Tree('NP'),Tree('VP',Tree('VP',Tree('V','had')
                       ,Tree('NP')),Tree('PP'))),
                       Tree('NP',Tree('N','I')),
                       Tree('NP',Tree('N','map')),
                       Tree('NP',Tree('N','desk')),
                       Tree('PP',Tree('P','on'),Tree('NP'))]

      auxiliary_trees = [Tree('NP',Tree('D','my'),Tree('NP*')),
                         Tree('NP',Tree('D','a'),Tree('NP*'))]

      tag = Tag(initial_trees,auxiliary_trees)

   The class also provides methods for substitution and adjoining which are the
operations by which the elementary trees grow.

Other details:

  Specification:
             The terminals should be on the frontier of the trees because
       all interior nodes are considered non terminals. The nonterminals on the
       frontier of the tree should be trees with only the node and no children.
       
             The foot node of auxiliary trees should have a '*' appended to
       it's label. This is to distinguish it from other nodes on the
       frontier with the same label.

  The position of the node in tree at which the substitution or adjoining 
  takes place is specified as follows:

          1.[0] root node
          2.[0,a,b,c,d...] where a is the ath child of the root,
                            b is the bth child of a ...and so on

    def substitute(self,tree1,tree2,position):
        """
          Substitutes tree2 on the frontier of tree1 at the appropriate
          position.
        """
         Tree1 =  ('S': ('NP':) ('VP': ('VP': ('V': 'had') ('NP':)) ('PP':)))
         Tree2 =  ('NP': ('N': 'I'))
         op (S or A) =  S
         Position =  [0, 1]
         Result =  ('S':
                       ('NP': ('N': 'I'))
                       ('VP': ('VP': ('V': 'had') ('NP':)) ('PP':)))

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

         Tree1 =  ('NP': ('N': 'map'))
         Tree2 =  ('NP': ('D': 'a') ('NP*':))
         op (S or A) =  A
         Position =  [0]
         Result =  ('NP': ('D': 'a') ('NP': ('N': 'map')))  


b.A Bottom-up Embedded Push Down Automaton to model the parsing strategy

       An EPDA is the formalism for a TAG which assigns structure to the set of
       accepted strings based on final state or empty stack similar to the
       PDA's for CFGs. The version of the BEPDA implemented here reconizes
       strings on empty stack. Its is Bottom up in the manner in which the
       adjunction takes place. The last adjunction is done first and the
       result of this is passed to the previous tree waiting for adjunction 
       

       Compiling TAG into BEPDA:
                         Each tree is represented by a set of ordered
       context free productions a follows:
       Node -> Child1 Child2...Childn
       Frontier Node -> Leaf (Remember that fr. nodes are of two types.
                              Trees without children for non terminals and
                              strings for children. This property is used to
                              determine whether a node is a candidate for 
                              substitution or adjoining or comparison with an
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

       The description here will give a fair idea of what is going on. I didn't
       want to include more detail than was necessary. If you really want to
       know what structures are being manipulated etc you might want to take
       a look at the code.
       
       Notation : $0 is the initial stack symbol and $1 is the final stack
       symbol.

       The methods of the BEPDA are as follows:

    def initialise(self,parse,basecat):
            """
               Initialises a parse. That is, for each tree rooted in the
               start symbol is creates a new parse.
            """


    def final(self,parse):
        """
          If a completely consumed tree rooted in the start symbol and
          the initial stack symbol are on the top of the stack and
          the input is totally consumed, stop
        """

    def call(self,parse):
        """
           Consumes a node. To do this it pushes the rule for the expansion
           of that node on the stack and continues
        """


    def ret(self,parse):
        """
          When the rule on the top of the stack is completely consumed
          it is popped of the stack and the previous rule is shifted. The
          previous rule is of the same tree in the case of a return from a
          call and is of another tree in the case of a return from adjcall,
          subscall or footcall where this module is run with mode = 1.

        """

    def scan(self,parse):
        """
          Scans a terminal symbol
        """

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

    def adjret(self,parse):
        """
          Returns from an adjunction and draws the derived tree. 
        """
        

    def footcall(self,parse):
        """
          When the node under consideration is the foot node of an auxiliary
          tree pop an element off the pending adjunctions stack and resume
          traversing the old tree where we left off.
        """


    def footret(self,parse):
        """
           If the tree on the pending adjuntions stack which we popped during
           footcall is completely traversed then the foot node is completely
           traversed.
        """

    def subscall(self,parse):
        """
          A non-terminal on the frontier of any tree is a candidate for
          substitution. It can be substituted with an initial tree which
          is rooted with the same node. So we start traversing the new
          initial tree by pushing it on the top of the stack.
        """


    def subsret(self,parse):
        """
          Return from a successful substituion.
        """

 Each method takes a parse and returns a list of possible parses.

A Parse is represented by the following: (class ParsingStructure)

      1.The stack set - which is a set of stacks. In the simplified
        version of the BEPDA here a single list (not stack) would have
        sufficed. But to keep some semblance with the formalism I have
        used the term stack set. It might be easier to just think of it
        as a stack.
        
      2 and 3. The tree stack and queue. These structures used together
               by the methods of the BEPDA ensure that:
               a. The tree being traversed is on top of the stack
               b. Substitution uses the first two elements of the stack
               c. Adjoining uses the first element of the stack and the
                  last element of the queue.

               Just to draw the parse trees. The final tree will be available
               on the top of the stack. The initialise,adjcall,adjret,footcall
               footret,subscall and subsret method are responsible for these
               structures because the change the tree being traversed. How
               the structures are manipulated is obvious from the code.
               
      4.The pending adjunctions stack
      
      5.The unconsumed input
      
      6.The unconsumed frontier nodes ( which gives us an idea whether
        or not a particular tree could be added to the derivation at this
        state because each unconsumed node will  consume atleast one
        lexical item. That together with the unconsumed input and the
        number of frontier nodes on a tree tells us whether it is worth
        our while to use the tree. Basically reduces the number of
        redundant parses)
      
      7.The operations done so that the steps can be shown.
    


c. A parser which is guided by the automaton

     The parser itself is relatively simple (it ought to be). It offers two
methods. The standard one is the method parse which return a list of parse 
trees. The other one prints the derivation that is the operations that take 
place in each parse.

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
        return self._bepda.initialise(ParsingStructure([['$0']],[],[],[],ip,0,
[]),self._basecat)

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


Sample Output:
              For the sentence 'I had a map on my desk' the derivation of
the parse tree is as follows :

**** For Parse  1  ****
    **** Operation  1  ****
         Tree1 =  ('S': ('NP':) ('VP': ('VP': ('V': 'had') ('NP':)) ('PP':)))
         Tree2 =  ('NP': ('N': 'I'))
         op (S or A) =  S
         Position =  [0, 1]
         Result =  ('S':
  ('NP': ('N': 'I'))
  ('VP': ('VP': ('V': 'had') ('NP':)) ('PP':)))
    **** Operation  2  ****
         Tree1 =  ('NP': ('N': 'map'))
         Tree2 =  ('NP': ('D': 'a') ('NP*':))
         op (S or A) =  A
         Position =  [0]
         Result =  ('NP': ('D': 'a') ('NP': ('N': 'map')))
    **** Operation  3  ****
         Tree1 =  ('S':
  ('NP': ('N': 'I'))
  ('VP': ('VP': ('V': 'had') ('NP':)) ('PP':)))
         Tree2 =  ('NP': ('D': 'a') ('NP': ('N': 'map')))
         op (S or A) =  S
         Position =  [0, 2, 1, 2]
         Result =  ('S':
  ('NP': ('N': 'I'))
  ('VP':
    ('VP': ('V': 'had') ('NP': ('D': 'a') ('NP': ('N': 'map'))))
    ('PP':)))
    **** Operation  4  ****
         Tree1 =  ('NP': ('N': 'desk'))
         Tree2 =  ('NP': ('D': 'my') ('NP*':))
         op (S or A) =  A
         Position =  [0]
         Result =  ('NP': ('D': 'my') ('NP': ('N': 'desk')))
    **** Operation  5  ****
         Tree1 =  ('PP': ('P': 'on') ('NP':))
         Tree2 =  ('NP': ('D': 'my') ('NP': ('N': 'desk')))
         op (S or A) =  S
         Position =  [0, 2]
        Result =  ('PP': ('P': 'on') ('NP': ('D': 'my') ('NP': ('N': 'desk'))))

    **** Operation  6  ****
         Tree1 =  ('S':
  ('NP': ('N': 'I'))
  ('VP':
    ('VP': ('V': 'had') ('NP': ('D': 'a') ('NP': ('N': 'map'))))
    ('PP':)))
         Tree2 =  ('PP': ('P': 'on') ('NP': ('D': 'my') ('NP': ('N': 'desk'))))
         op (S or A) =  S
         Position =  [0, 2, 2]
         Result =  ('S':
  ('NP': ('N': 'I'))
  ('VP':
    ('VP': ('V': 'had') ('NP': ('D': 'a') ('NP': ('N': 'map'))))
    ('PP': ('P': 'on') ('NP': ('D': 'my') ('NP': ('N': 'desk'))))))
************************* 


What could be improved ? 

1. As with the above example it may be seen that a lot of elementary trees 
differ only in their lexical anchor (the terminals on the frontier). It would 
be a good idea to represent them as a list of terminals on the frontier so you
could have one tree.

For example
   Tree('NP',Tree('N',['I','map','desk']))

This should not be too hard and it might become necessary when we have a lot of
trees. The reason I didn't do this is because it becomes harder to see what is
going on an this is intended as a beginners tool.

2. A more efficient parser could be written. 

If this hasn't put you off TAGs for life you might want to check out
www.cis.upenn.edu/~xtag                  




