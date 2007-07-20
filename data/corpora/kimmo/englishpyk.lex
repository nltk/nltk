Begin:          N_ROOT ADJ_PREFIX V_PREFIX End
N_Root1:        N_SUFFIX NUMBER
N_Root2:        GENITIVE
N_Root3:	PLUR_SING
N_Suffix:        ADJ_SUFFIX3
Number:          GENITIVE
Genitive:        End


Adj_Prefix1:     ADJ_ROOT1 ADJ_ROOT2
Adj_Prefix2:     ADJ_ROOT1 ADJ_ROOT2
Adj_Root1:       ADJ_SUFFIX1 ADJ_SUFFIX2 ADJ_SUFFIX3
Adj_Root2:       ADJ_SUFFIX2 ADJ_SUFFIX3
Adj_Suffix1:     End
Adj_Suffix2:     ADJ_SUFFIX3


V_Pref_Non:      V_ROOT_NO_PREF V_ROOT_REVERSE V_ROOT_REPEAT V_ROOT_NEG
V_Pref_Reverse:  V_ROOT_REVERSE
V_Pref_Repeat:  V_ROOT_REPEAT
V_Pref_Neg:     V_ROOT_NEG


V_Root1:         End
V_Root2:         V_SUFFIX1
V_Root3:         V_SUFFIX1 V_SUFFIX3
V_Root4:         V_SUFFIX1 V_SUFFIX2 V_SUFFIX3

V_Suffix1:       End
V_Suffix2:       NUMBER


NUMBER:
+s Number +PL
''  Number .SG

# case where the noun is both plural and singular
PLUR_SING:
'' Number +PL


GENITIVE:
+'s  Genitive +GEN
''   Genitive None

N_SUFFIX:
+ish Adj_Suffix2 +ADJR1
+ly  Adj_Suffix2 +ADJR2
+y   Adj_Suffix2 +ADJR3

ADJ_PREFIX:
un+  Adj_Prefix1 NEG1+
''   Adj_Prefix1 None

ADJ_ROOT1:
clear Adj_Root1 Adj(clear)
happy Adj_Root1 Adj(happy)
real  Adj_Root1 Adj(real)

ADJ_ROOT2:
`big   Adj_Root2 Adj(big)
cool  Adj_Root2 Adj(cool)
`red   Adj_Root2 Adj(red)

ADJ_SUFFIX1:
+ly    Adj_Suffix1 +ADVR

ADJ_SUFFIX2:
+er    Adj_Suffix1 +COMP
+est   Adj_Suffix1 +SUPER
''	''

ADJ_SUFFIX3:
+ness  Adj_Suffix1 +NOMR
''     Adj_Suffix1 None

V_PREFIX:
re-  V_Pref_Repeat REP+
un+  V_Pref_Reverse REV+
dis+ V_Pref_Neg NEG2+
''   V_Pref_Non None

V_SUFFIX1:
+able V_Suffix1 +ADJR
+ing  V_Suffix1 +PROG
+er   V_Suffix2 +AGENT
''    V_Suffix1 .INF

V_SUFFIX2:
+ed   V_Suffix1 +PAST
+ed   V_Suffix1 +PAST.PRTC

V_SUFFIX3:
+s    V_Suffix1 +3sg.PRES

N_ROOT:
`cat    N_Root1 Noun(cat)
`dog    N_Root1 Noun(dog)
`fox    N_Root1 Noun(fox)
`fly    N_Root1 Noun(fly)
`axe    N_Root1 Noun(axe)
`spot   N_Root1 Noun(spot)
`spy   N_Root1 Noun(spy)
person  N_Root2 Noun(person)
bob  N_Root2 "Noun(person - Bob)"
rob  N_Root2 "Noun(person - Rob)"
catherine  N_Root2 "Noun(person - Catherine)"
beracah  N_Root2 "Noun(person - Beracah)"
sheep  N_Root3 Noun(sheep)




V_ROOT_NO_PREF:
`axe  V_Root4 Verb(axe)
`move V_Root4 Verb(move)
`spy  V_Root4 Verb(spy)
`tie  V_Root4 Verb(tie)
`slip V_Root4 Verb(slip)
`fly  V_Root4 Verb(fly)

End:
'#' Begin None
