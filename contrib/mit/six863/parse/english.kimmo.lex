; Words with lowercase letters in them represent 'alternations', or states
; whose purpose is to allow transitions (without reading any input) to one or
; other states. Words with capital letters are lexical states; they require
; reading a certain word in the lexical form to proceed.

; Alternations are the only place that the lexical FSA can branch into multiple
; options.

Begin:  Prefix Root
Prefix: ADJ_PREFIX V_PREFIX
Root: N_ROOT ADJ_ROOT V_ROOT_PREF V_ROOT_NO_PREF PARTICLE
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
un+  ADJ_ROOT {}

ADJ_ROOT:
`clear AfterAdj {pos: A, word: clear}
`happy AfterAdj {pos: A, word: happy}
`real  AfterAdj {pos: A, word: real}
`cool  AfterAdj {pos: A, word: cool}
`big   Adj-NoAdverb  {pos: A, word: big}
`red   Adj-NoAdverb  {pos: A, word: red}

ADVERB:
+ly    AdjSuffix {pos: ADV}

ADJ_SUFFIX:
+er    AfterAdjSuffix {}
+est   AfterAdjSuffix {}
+ness  AfterAdjSuffix {pos: N}


N_ROOT:
`cat    AfterNoun {pos: N, word: cat, agr: {plural: false}}
`dog    AfterNoun {pos: N, word: dog, agr: {plural: false}}
`fox    AfterNoun {pos: N, word: fox, agr: {plural: false}}
`axe    AfterNoun {pos: N, word: axe, agr: {plural: false}}
`spot   AfterNoun {pos: N, word: spot, agr: {plural: false}}
`spy    AfterNoun {pos: N, word: spy, agr: {plural: false}}
`fly    AfterNoun {pos: N, word: fly, agr: {plural: false}}
`tie    AfterNoun {pos: N, word: tie, agr: {plural: false}}

GENITIVE:
+'s  AfterGenitive {gen: true}

PLURAL:
+s   AfterPlural   {plural: true}

N_TO_ADJ:
+ish AfterAdj {pos: A}
+y AfterAdj {pos: A}


V_PREFIX:
re+   V_ROOT_PREF {}
un+   V_ROOT_PREF {}

V_ROOT_PREF:
`tie    AfterVerb {pos: V, word: tie}
se`lect AfterVerb {pos: V, word: select}
`do     AfterVerb {pos: V, word: do}

V_ROOT_NO_PREF:
`axe    AfterVerb {pos: V, word: axe}
`move   AfterVerb {pos: V, word: move}
`have   AfterVerb {pos: V, word: have}
`spy    AfterVerb {pos: V, word: spy}
`tie    AfterVerb {pos: V, word: tie}
`slip   AfterVerb {pos: V, word: slip}
`fly    AfterVerb {pos: V, word: fly}
`ponder AfterVerb {pos: V, word: ponder}

V_SUFFIX:
+able AfterVerbSuffix {pos: A}
+ing  AfterAdj        {pos: A}
+er   AfterNoun       {pos: N}
""    AfterVerbSuffix {fin: false}
""    AfterVerbSuffix {fin: true, agr: {tense: present, person: 1, plural: false}}
""    AfterVerbSuffix {fin: true, agr: {tense: present, person: 2, plural: false}}
""    AfterVerbSuffix {fin: true, agr: {tense: present, plural: true}}
; The empty suffix indicates the infinitive.
+ed   AfterVerbSuffix {fin: true, agr: {tense: past}}
+ed   AfterAdj        {pos: A}
+s    AfterVerbSuffix {fin: true, agr: {tense: present, person: 3, plural: false}}

PARTICLE:
of    End  {pos: P, attach: N}
to    End  {pos: P, attach: V}
in    End  {pos: P}
on    End  {pos: P}
at    End  {pos: P}
I     End  {pos: N, agr: {person: 1, plural: false}}
you   End  {pos: N, agr: {person: 2, plural: false}}
the   End  {pos: Det}
this  End  {pos: Det, agr: {plural: false}}
these End  {pos: Det, agr: {plural: true}}
a     End  {pos: Det, agr: {plural: false}}
an    End  {pos: Det, agr: {plural: false}}
some  End  {pos: Det, agr: {plural: true}}

; This part is required to deal gracefully with the boundary symbol.
End:
'#' End None

