; Words with lowercase letters in them represent 'alternations', or states
; whose purpose is to allow transitions (without reading any input) to one or
; other states. Words with capital letters are lexical states; they require
; reading a certain word in the lexical form to proceed.

; Alternations are the only place that the lexical FSA can branch into multiple
; options.

Begin:  Prefix Root
Prefix: ADJ_PREFIX V_PREFIX
Root: N_ROOT ADJ_ROOT V_ROOT_PREF V_ROOT_NO_PREF
AfterNoun: NounSuffix
NounSuffix: End GENITIVE PLURAL N_TO_ADJ
AfterPlural: End GENITIVE
AfterGenitive: End

AfterAdj: ADVERB ADJ_SUFFIX End
Adj-NoAdverb: ADJ_SUFFIX End
AfterAdjSuffix: End

AfterVerb: VerbSuffix
VerbSuffix: V_SUFFIX
; V_SUFFIX is not optional -- you can't go to 'End' from here.
AfterVerbSuffix: End

ADJ_PREFIX:
un+  ADJ_ROOT Not+

ADJ_ROOT:
`clear AfterAdj Adj(clear)
`happy AfterAdj Adj(happy)
`real  AfterAdj Adj(real)
`cool  AfterAdj Adj(cool)
`big   Adj-NoAdverb  Adj(big)
`red   Adj-NoAdverb  Adj(red)

ADVERB:
+ly    AdjSuffix +ADVERB

ADJ_SUFFIX:
+er    AfterAdjSuffix +COMP
+est   AfterAdjSuffix +SUPER
+ness  AfterAdjSuffix +NOM


N_ROOT:
`cat    AfterNoun Noun(cat)
`dog    AfterNoun Noun(dog)
`fox    AfterNoun Noun(foxes)
`axe    AfterNoun Noun(axe)
`spot   AfterNoun Noun(spot)
`spy    AfterNoun Noun(spy)
`fly    AfterNoun Noun(fly)
`tie    AfterNoun Noun(tie)

GENITIVE:
+'s  AfterGenitive +GEN

PLURAL:
+s   AfterPlural   +PL

N_TO_ADJ:
+ish AfterAdj +ADJR1
+y AfterAdj +ADJR1


V_PREFIX:
re+   V_ROOT_PREF REP+
un+   V_ROOT_PREF REV+

V_ROOT_PREF:
`tie    AfterVerb Verb(tie)
se`lect AfterVerb Verb(select)
`do     AfterVerb Verb(do)

V_ROOT_NO_PREF:
`axe    AfterVerb Verb(axe)
`move   AfterVerb Verb(move)
`have   AfterVerb Verb(have)
`spy    AfterVerb Verb(spy)
`tie    AfterVerb Verb(tie)
`slip   AfterVerb Verb(slip)
`fly    AfterVerb Verb(fly)
`ponder AfterVerb Verb(select)

V_SUFFIX:
+able AfterVerbSuffix +ADJR
+ing  AfterAdj        +PROG
+er   AfterNoun       +AGENT
""    AfterVerbSuffix .INF
; The empty suffix indicates the infinitive.
+ed   AfterVerbSuffix +PAST
+ed   AfterAdj        +PAST.PRTC
+s    AfterVerbSuffix +3sg.PRES

; This part is required to deal gracefully with the boundary symbol.
End:
'#' End None

