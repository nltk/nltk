; Words with lowercase letters in them represent 'alternations', or states
; whose purpose is to allow transitions (without reading any input) to one or
; other states. Words with capital letters are lexical states; they require
; reading a certain word in the lexical form to proceed.

; Alternations are the only place that the lexical FSA can branch into multiple
; options.

Begin:  Prefix Root
Prefix: ADJ_PREFIX
Root: N_ROOT ADJ_ROOT V_ROOT PARTICLE NAME
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
sus`picious AfterAdj    {pos: A, compar: false}
`still      AfterAdj    {pos: A, compar: false}
`similar    AfterAdj    {pos: A, compar: false}
`same       AfterAdj    {pos: A, compar: false}
`raw        AfterAdj    {pos: A, compar: false}
`rabid      AfterAdj    {pos: A, compar: false}
`new        AfterAdj    {pos: A, compar: false}
`more       AfterAdj    {pos: A, compar: true}
`less       AfterAdj    {pos: A, compar: true}
`ill        AfterAdj    {pos: A, compar: false}
`great      AfterAdj    {pos: A, compar: false}
`further    AfterAdj    {pos: A, compar: true}
`fewer      AfterAdj    {pos: A, compar: true}
`equal      AfterAdj    {pos: A, compar: false}
`easy       AfterAdj    {pos: A, compar: false}
`close      AfterAdj    {pos: A, compar: false}
cor`rect    AfterAdj    {pos: A, compar: false}

ADVERB:
+ly    AdjSuffix {pos: ADV}

ADJ_SUFFIX:
+er    AfterAdjSuffix {compar: true}
+est   AfterAdjSuffix {compar: true}
+ness  AfterAdjSuffix {pos: N}


N_ROOT:
`wonder     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`woman      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`women      AfterNoun   {pos: N, agr: {person: 3, plural: true}}
`volume     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`werewolf   AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`visit      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`tune       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`theory     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`theory     AfterNoun   {pos: FACT, agr: {person: 3, plural: false}}
`tax        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`table      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`state      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`state      AfterNoun   {pos: FACT, agr: {person: 3, plural: false}}
`pot        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`pencil     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`matter     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`man        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`men        AfterNoun   {pos: N, agr: {person: 3, plural: true}}
`love       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`keys       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`kennel     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`horse      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`guy        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`flower     AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`fact       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`fact       AfterNoun   {pos: FACT, agr: {person: 3, plural: false}}
`exam       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`eggplant   AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`drugs      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`dog        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`cows       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`conference AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`communist  AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`city       AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`chase      AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`cat        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`car        AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`cadillac   AfterNoun   {pos: N, agr: {person: 3, plural: false}}
`book       AfterNoun   {pos: N, agr: {person: 3, plural: false}}

GENITIVE:
+'s  AfterGenitive {gen: true}

PLURAL:
+s   AfterPlural   {plural: true}

N_TO_ADJ:
+ish AfterAdj {pos: A, compar: false}
+y AfterAdj {pos: A, compar: false}


V_ROOT:
`wonder     AfterVerb {pos: V, class: 10}
`want       AfterVerb {pos: V, class: 14}
`want       AfterVerb {pos: V, class: 15}
`think      AfterVerb {pos: V, class: 8}
`think      AfterVerb {pos: V, class: 9}
`state      AfterVerb {pos: V, class: 8}
`said       End       {pos: V, class: 8, agr: {tense: past}}
`said       End       {pos: V, class: 9, agr: {tense: past}}
`say        AfterVerb {pos: V, class: 8}
`say        AfterVerb {pos: V, class: 9}
`put        AfterVerb {pos: V, class: 6}
`put        AfterVerb {pos: V, class: 17}
`offer      AfterVerb {pos: V, class: 18}
`matter     AfterVerb {pos: V, class: 12}
`know       AfterVerb {pos: V, class: 8}
`know       AfterVerb {pos: V, class: 9}
`hope       AfterVerb {pos: V, class: 8}
`hope       AfterVerb {pos: V, class: 9}
`hope       AfterVerb {pos: V, class: 15}
`hope       AfterVerb {pos: V, class: 16}
`claim      AfterVerb {pos: V, class: 8}
`claim      AfterVerb {pos: V, class: 9}
be`lieve    AfterVerb {pos: V, class: 8}
be`lieve    AfterVerb {pos: V, class: 9}
re`gret     AfterVerb {pos: V, class: 8}
`ask        AfterVerb {pos: V, class: 10}
`ask        AfterVerb {pos: V, class: 11}
ar`range    AfterVerb {pos: V, class: 6}
ar`range    AfterVerb {pos: V, class: 8}
`offer      AfterVerb {pos: V, class: 6}
`offer      AfterVerb {pos: V, class: 7}
`give       AfterVerb {pos: V, class: 6}
`give       AfterVerb {pos: V, class: 7}
`win        AfterVerb {pos: V, class: A}
`want       AfterVerb {pos: V, class: A}
`visit      AfterVerb {pos: V, class: A}
`use        AfterVerb {pos: V, class: A}
`tell       AfterVerb {pos: V, class: A}
`tax        AfterVerb {pos: V, class: A}
sur`prise   AfterVerb {pos: V, class: A}
sur`prise   AfterVerb {pos: V, class: 13}
sup`port    AfterVerb {pos: V, class: A}
`state      AfterVerb {pos: V, class: A}
`sing       AfterVerb {pos: V, class: A}
`sang       End       {pos: V, class: A, fin: true, agr: {tense: past}}
`sung       End       {pos: V, class: A, fin: true, agr: {tense: past}}
`see        AfterVerb {pos: V, class: B}
`saw        End       {pos: V, class: B, fin: true, agr: {tense: past}}
`seen       End       {pos: V, class: B, fin: true, agr: {tense: past}}
`please     AfterVerb {pos: V, class: A}
`pass       AfterVerb {pos: V, class: A}
`make       AfterVerb {pos: V, class: A}
`made       End       {pos: V, class: A, fin: true, agr: {tense: past}}
`love       AfterVerb {pos: V, class: A}
`like       AfterVerb {pos: V, class: B}
`left       End       {pos: V, class: A, fin: true, agr: {tense: past}}
`leave      AfterVerb {pos: V, class: A}
`know       AfterVerb {pos: V, class: A}
`kill       AfterVerb {pos: V, class: A}
`keep       AfterVerb {pos: V, class: A}
`kept       End       {pos: V, class: A, fin: true, agr: {tense: past}}
`hum        AfterVerb {pos: V, class: A}
`hate       AfterVerb {pos: V, class: A}
`eat        AfterVerb {pos: V, class: A}
`drive      AfterVerb {pos: V, class: A}
`drove      End       {pos: V, class: A, fin: true, agr: {tense: past}}
`driven     End       {pos: V, class: A, fin: true, agr: {tense: past}}
cor`rect    AfterVerb {pos: V, class: A}
com`pute    AfterVerb {pos: V, class: A}
`chase      AfterVerb {pos: V, class: A}
`catch      AfterVerb {pos: V, class: B}
`caught     End       {pos: V, class: B, fin: true, agr: {tense: past}}
`buy        AfterVerb {pos: V, class: B}
`bought     End       {pos: V, class: B, fin: true, agr: {tense: past}}
`talk       AfterVerb {pos: V, class: C}
`steal      AfterVerb {pos: V, class: C}
`stole      End       {pos: V, class: C, fin: true, agr: {tense: past}}
`stolen     End       {pos: V, class: C, fin: true, agr: {tense: past}}
`sleep      AfterVerb {pos: V, class: C}
`slept      End       {pos: V, class: C, fin: true, agr: {tense: past}}
re`turn     AfterVerb {pos: V, class: C}
`look       AfterVerb {pos: V, class: C}
`go         AfterVerb {pos: V, class: C}
`come       AfterVerb {pos: V, class: C}
`came       End       {pos: V, class: C, fin: true, agr: {tense: past}}

V_SUFFIX:
+able AfterVerbSuffix {pos: A, compar: false}
+ing  AfterAdj        {pos: A, compar: false}
+ing  AfterVerbSuffix {fin: false, agr: {tense: present}}
+er   AfterNoun       {pos: N}
""    AfterVerbSuffix {fin: false}
""    AfterVerbSuffix {fin: true, agr: {tense: present, person: 1, plural: false}}
""    AfterVerbSuffix {fin: true, agr: {tense: present, person: 2, plural: false}}
""    AfterVerbSuffix {fin: true, agr: {tense: present, plural: true}}
; The empty suffix indicates the infinitive.
+ed   AfterVerbSuffix {fin: true, agr: {tense: past}}
+ed   AfterAdj        {pos: A, compar: false}
+s    AfterVerbSuffix {fin: true, agr: {tense: present, person: 3, plural: false}}

NAME:
mary    End {pos: NAME, agr: {person: 3, plural: false}}
john    End {pos: NAME, agr: {person: 3, plural: false}}
fred    End {pos: NAME, agr: {person: 3, plural: false}}
fido    End {pos: NAME, agr: {person: 3, plural: false}}
bill    End {pos: NAME, agr: {person: 3, plural: false}}

PARTICLE:
i     End  {pos: PRO, agr: {person: 1, plural: false}, wh: false}
me    End  {pos: PRO, agr: {person: 1, plural: false}, wh: false}
my    End  {pos: DET, wh: false, agr: {person: 1, plural: false}, wh: false}
mine  End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
you   End  {pos: PRO, agr: {person: 2}, wh: false}
your  End  {pos: DET, wh: false, agr: {person: 2}, wh: false}
yours End  {pos: PRO, agr: {person: 3}, wh: false}
he    End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
him   End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
his   End  {pos: DET, wh: false, agr: {person: 3, plural: false}, wh: false}
she   End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
her   End  {pos: DET, wh: false, agr: {person: 3, plural: false}, wh: false}
hers  End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
it    End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
its   End  {pos: PRO, agr: {person: 3, plural: false}, wh: false}
we    End  {pos: PRO, agr: {person: 1, plural: true}, wh: false}
us    End  {pos: PRO, agr: {person: 1, plural: true}, wh: false}
our   End  {pos: DET, wh: false, agr: {person: 1, plural: true}, wh: false}
ours  End  {pos: PRO, agr: {person: 1, plural: true}, wh: false}
they  End  {pos: PRO, agr: {person: 3, plural: true}, wh: false}
them  End  {pos: PRO, agr: {person: 3, plural: true}, wh: false}
them  End  {pos: PRO, agr: {person: 3, plural: true}, wh: false}
their End  {pos: DET, wh: false, agr: {person: 3, plural: true}, wh: false}
theirs End  {pos: PRO, agr: {person: 3, plural: true}, wh: false}
here  End  {pos: PRO, wh: false}
there End  {pos: PRO, wh: false}
the   End  {pos: DET, wh: false}
this  End  {pos: DET, wh: false, agr: {plural: false}}
these End  {pos: DET, wh: false, agr: {plural: true}}
that  End  {pos: DET, wh: false, agr: {plural: false}}
those End  {pos: DET, wh: false, agr: {plural: true}}
a     End  {pos: DET, wh: false, agr: {plural: false}}
an    End  {pos: DET, wh: false, agr: {plural: false}}
some  End  {pos: DET, wh: false, agr: {plural: true}}
and   End  {pos: CONJ}
but   End  {pos: CONJ}
or    End  {pos: CONJ}
if    End  {pos: CONJ}
that  End  {pos: RCOMP, wh: false}
that  End  {pos: COMP, wh: false}
how   End  {pos: SPEC, wh: true}
if    End  {pos: SPEC, wh: true}
why   End  {pos: SPEC, wh: true}
whether End  {pos: SPEC, wh: true}
when  End  {pos: '*ADVP', wh: true}
where End  {pos: '*ADVP', wh: true}
which End  {pos: RCOMP, wh: true}
which End  {pos: PRO, wh: true}
which End  {pos: DET, wh: true}
what  End  {pos: DET, wh: true}
what  End  {pos: PRO, wh: true}
whom  End  {pos: PRO, wh: true}
who   End  {pos: PRO, wh: true}
who   End  {pos: RCOMP, wh: true}
not   End  {pos: '*NOT'}
than  End  {pos: '*THAN'}
for   End  {pos: '*FOR'}
do    End  {pos: DO, fin: false}
do    End  {pos: DO, fin: true, agr: {tense: present, person: 1, plural: false}}
do    End  {pos: DO, fin: true, agr: {tense: present, person: 2, plural: false}}
does  End  {pos: DO, fin: true, agr: {tense: present, person: 3, plural: false}}
do    End  {pos: DO, fin: true, agr: {tense: present, plural: true}}
did   End  {pos: DO, fin: true, agr: {tense: past}}
done  End  {pos: DO, fin: true, agr: {tense: past}}
doing End  {pos: DO, fin: true, agr: {tense: present}}
be    End  {pos: BE, fin: false}
am    End  {pos: BE, fin: true, agr: {tense: present, person: 1, plural: false}}
are   End  {pos: BE, fin: true, agr: {tense: present, person: 2, plural: false}}
is    End  {pos: BE, fin: true, agr: {tense: present, person: 3, plural: false}}
are   End  {pos: BE, fin: true, agr: {tense: present, plural: true}}
was   End  {pos: BE, fin: true, agr: {tense: past}}
been  End  {pos: BE, fin: true, agr: {tense: past}}
being End  {pos: BE, fin: true, agr: {tense: present}}
should End {pos: MODAL, fin: true}
shall End {pos: MODAL, fin: true}
could End {pos: MODAL, fin: true}
can   End {pos: MODAL, fin: true}
might End {pos: MODAL, fin: true}
may   End {pos: MODAL, fin: true}
would End {pos: MODAL, fin: true}
will  End {pos: MODAL, fin: true}
to    End {pos: MODAL, fin: false}
have  End  {pos: BE, fin: false}
have  End  {pos: BE, fin: true, agr: {tense: present, person: 1, plural: false}}
have  End  {pos: BE, fin: true, agr: {tense: present, person: 2, plural: false}}
has   End  {pos: BE, fin: true, agr: {tense: present, person: 3, plural: false}}
have  End  {pos: BE, fin: true, agr: {tense: present, plural: true}}
had   End  {pos: BE, fin: true, agr: {tense: past}}
having End  {pos: BE, fin: true, agr: {tense: present}}
up    End  {pos: '*PP'}
up    End  {pos: P}
underneath End {pos: P}
under End  {pos: '*PP'}
under End  {pos: P}
onto  End  {pos: P}
on    End  {pos: '*PP'}
for   End  {pos: P}
down  End  {pos: P}
down  End  {pos: '*PP'}
into  End  {pos: P}
in    End  {pos: '*PP'}
behind End {pos: P}
behind End {pos: '*PP'}
before End {pos: P}
after End  {pos: P}
very  End  {pos: ADV}
still End  {pos: ADV}
of    End  {pos: P, attach: N}
to    End  {pos: P, attach: V}
in    End  {pos: P}
on    End  {pos: P}
at    End  {pos: P}

End:
'#' End None

