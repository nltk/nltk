This directory contains the data of the UPenn Propbank.  This data is collected
as an additional layer of annotation on the Penn Treebank, representing the predicate
argument structure of verbs.  Below is a list of each file and a description of
its contents.


File                      Description
--------------------------------------------------------------------------------------
prop.txt                  The annotated data, file format described below.
                          This includes the annotations for the entire Wall 
                          Street Journal Section of the Penn TreeBank II.
                          
frames/                   Lexical Guidelines.  The file format for each verb is
                          detailed in frames/frameset.dtd

vloc.txt                  text file containing verb locations in the penn 
                          treebank that have been annotated.
                          
verbs.txt                 verb list for Penn Treebank, Wall Street Journal section.

NOTES.txt                 release notes for PropBank I
--------------------------------------------------------------------------------------

                               Annotation Format.

The prop.txt file contains predicate argument structures of verbs.  Each P-A structure
is represented in a line of space separated columns.  The columns are as follows

  wsj-filename sentence terminal tagger frameset inflection proplabel proplabel ...

The content of each column is described in detail below.

wsj-filename
	the name of the file in merged penn treebank, wsj section
    
sentence
	the number of the sentence in the file (starting with 0)
    
terminal
	the number of the terminal in the sentence that is the location of the
	verb.  note that the terminal number counts empty constituents as
	terminals and starts with 0.  This will hold for all references to
	terminal number in this description.

    An example:  
        (NP-1 (NN John) (VP (VB wants) (S (NP (-NONE- *-1)) (VP (TO to) (V swim)))))
        
    The terminal numbers:
        John 0; wants 1; *-1 2; to 3; swim 4
        
tagger
    the name of the annotator, or "gold" if it's been double annotated and adjudicated.
    
frameset

    The frameset identifier from the frames file of the verb.  For
    example, 'dial.01' refers to the frames file for 'dial', (frames/dial.xml)
    and the roleset element in that frames file whose attribute 'id' is
    'dial.01'.

    There are some instances which have yet to be disambiguated, these
    are marked as 'lemma.XX'.

        
inflection
    The inflection field consists of 5 characters representing
    person, tense, aspect, voice, and form of the verb, respectively.
         
    Each of the characters may be '-', representing 'none.' 

    Otherwise, each of the fields character codes follow:

    form: i=infinitive g=gerund p=participle v=finite
    tense:  f=future p=past n=present
    aspect: p=perfect o=progressive b=both perfect and progressive
    person: 3=3rd person  
    voice: a=active p=passive

proplabel

    A string representing the annotation associated with a particular argument
    or adjunct of the proposition.  Each proplabel is dash '-' delimited and
    has the following columns

  1) column for the 'syntactic relation'
  
    The syntactic relation of the argument label.  This can be in one of 4 forms.
    
    form 1: <terminal number>:<height>
      A single node in the syntax tree of the sentence in question, identified
      by the first terminal the node spans together with the height from that
      terminal to the syntax node (a height of 0 represents a terminal).

      For example,  in the sentence
      
        (S (NP-1 (NN John) (VP (VB wants) (S (NP (-NONE- *-1)) (VP (TO to) (V swim)))))

        A syntactic relation of "2:1" represents the NP immediately dominating
        the terminal "(-NONE- *-1)" and a syntactic relation of "0:2" represents 
        the "S" node.
        
    form 2: terminal number:height*terminal number:height*...
      
      A trace chain identifying coreference within sentence boundaries.

      For example in the sentence

        ((NP-1 (NN John) (VP (VB wants) (S (NP (-NONE- *-1)) (VP (TO to) (V swim)))))

        A syntactic relation of "2:1*0:1" represents the NP immediately dominating
        (-NONE- *-1) and the NP immediately dominating "(NN John)".
      
      
    form 3: terminal number:height,terminal number:height,...
    
      A split argument, where there is no single node that captures the argument
      and the components are not coreferential, eg the utterance in
      "I'm going to", spoke John, "take it with me".  This form is also used
      to denote phrasal variants of verbs.  For example, in the phrase fragment

      (S (NP (NN John)) (VP (VB keeps) (PRT on) (NP ...)).  The phrasal verb 
      "keep_on" would be identified with the syntactic relation  "1:0,2:0".

    form 4: terminal number:height,terminal number:height*terminal number:height...

      This form is a combination of forms 2 and 3.  When this occurs, the ',' operator
      is understood to have precedence over the '*' operator.  For example, in the sentence

       (NP (DT a) (NN series) ) 
           (PP (IN of)(NP (NNS intrigues) ))
              (SBAR
                (WHNP-4 (WDT that) )
                (S
                  (NP-SBJ (-NONE- *T*-4) )
                  (VP (VBZ has)
                    (S
                      (NP-SBJ (NN everyone) )
                      (VP (VBG fearing)

       The proplabel 28:1,30:1*32:1*33:0-ARG0 is to be understood as a trace-chain (form 2), one
       of whose constituents is a split argument (form 3) - i.e. grouped like so: 
       ((28:1,30:1)*32:1*33:0).  The interpretation of this argument is that the "causer of action"
       (ARG0 of have.04) is signified by the following trace-chain:

       *T*-4 --> that --> ([a series][of intrigues])


  2) column for the 'label'
  
    The argument label one of {rel, ARGA, ARGM} + { ARG0, ARG1, ARG2,
    ... }.  The argument labels correspond to the argument labels in the frames
    files (see ./frames).  ARGA is used for causative agents, ARGM for
    adjuncts of various sorts, and 'rel' refers to the surface string of
    the verb.

  3) column for feature (optional for numbered arguments; required for ARGM)

    Argument features can either be a labelled feature, or a preposition.  Labelled 
    features follow:

    EXT - extent
    DIR - direction
    LOC - location
    TMP - temporal
    REC - reciprocal
    PRD - predication
    NEG - negation
    MOD - modal
    ADV - adverbial
    MNR - manner
    CAU - cause
    PNC - purpose not cause.
    DIS - discourse

    Prepositions attached to argument labels occur when the argument is tagged on 
    a PP node.

-------------------------------------------------------------------------------------- 
