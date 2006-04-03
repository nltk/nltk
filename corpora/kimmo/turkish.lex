;Turkish.lex


; ALTERNATION Begin		N_ROOT1 V_ROOT ADJ_ROOT
Begin:		N_ROOT1 V_ROOT ADJ_ROOT

N_root1:		POSSESSIVE NONVERB_SUFFIX TO_ADJ TO_ADVERB PLURAL N_CASE YES_NO End
Adj_root:		NONVERB_SUFFIX PLURAL TO_ADVERB YES_NO End
Possessive:		NONVERB_SUFFIX N_CASE YES_NO End
Nonverb_suffix:	End
To_adverb:		End
Plural:		POSSESSIVE2 N_CASE End
N_case:		End
Possessive2:		N_CASE End
Yes_no:		NONVERB_SUFFIX

V_root:		V_NEGATIVE INFINITIVE TENSE
V_negative:		INFINITIVE TENSE
Infinitive:		End
Tense:		PERSONAL
Progressive:		PROGRESS_PERSONAL
Progress_personal:	End
Personal:		End



; LEXICON INITIAL (old format, make compatible)
INITIAL:
0		Begin		""
; 	0		Begin		"[ "
; notice old '0' format,
; take this into account.

N_ROOT1:
ankara		N_root1		"ProperN(Ankara)"
kol		N_root1		"N(arm)"
kUl		N_root1		"N(ashes)"
top		N_root1		"N(ball)"
sepet		N_root1		"N(basket)"
kitab		N_root1		"N(book)"
otobUs		N_root1		"N(bus)"
kasab		N_root1		"N(butcher)"
^ocug		N_root1		"N(child)"
reng		N_root1		"N(color)"
it		N_root1		"N(dog)"
gOz		N_root1		"N(eye)"
baba		N_root1		"N(father)"
yemek		N_root1		"N(food)"
k!z		N_root1		"N(girl)"
istanbul	N_root1		"ProperN(Istanbul)"
izmir		N_root1		"ProperN(Izmir)"
sa^		N_root1		"N(hair)"
el		N_root1		"N(hand)"
baS		N_root1		"N(head)"
at		N_root1		"N(horse)"
adam		N_root1		"N(man)"
mehmed		N_root1		"ProperN(Mehmed)"
anne		N_root1		"N(mother)"
a>z		N_root1		"N(mouth)"
ism		N_root1		"N(name)"
boyn		N_root1		"N(neck)"
memur		N_root1		"N(official)"
armud		N_root1		"N(pear)"
insan		N_root1		"N(person)"
koyun		N_root1		"N(sheep)"
o>l		N_root1		"N(son)"
kul		N_root1		"N(slave)"
masa		N_root1		"N(table)"
a>ac		N_root1		"N(tree)"
kamyon		N_root1		"N(truck)"
tUrk		N_root1		"N(turk)"

V_ROOT:
gel		V_root		"V(come)"
ye		V_root		"V(eat)"
git		V_root		"V(go)"
gUl		V_root		"V(laugh)"
otur		V_root		"V(live)"
a^		V_root		"V(open)"
oku		V_root		"V(read)"
gOr		V_root		"V(see)"
dur		V_root		"V(stand)"

ADJ_ROOT:
kOtU		Adj_root	"Adj(bad)"
bUyUg		Adj_root	"Adj(big)"
^al!Skan	Adj_root	"Adj(hardworking)"
a^		Adj_root	"Adj(hungry)"
tembel		Adj_root	"Adj(lazy)"
hoS		Adj_root	"Adj(pleasant)"
hasta		Adj_root	"Adj(sick)"
yorgun		Adj_root	"Adj(tired)"
iyi		Adj_root	"Adj(well)"

N_CASE:

+YI		N_case		"+(definite direct object)"
+YE		N_case		"+(indirect object)"
+DE		N_case		"+(locative)"
+DEn		N_case		"+(ablative)"

POSSESSIVE:
+Im		Possessive	"+(1st singular posessive)"
+In		Possessive	"+(2nd singular posessive)"
+ImIz		Possessive	"+(1st plural possessive)"
+InIz		Possessive	"+(2nd plural possessive)"

POSSESSIVE2:
+Im		Possessive2	"+(1st singular posessive)"
+In		Possessive2	"+(2nd singular posessive)"
+ImIz		Possessive2	"+(1st plural possessive)"
+InIz		Possessive2	"+(2nd plural possessive)"

PLURAL:
+lEr		Plural		"+(plural)"

NONVERB_SUFFIX:
+YIm		Nonverb_suffix	"+Nonverbal(1st Singular)"
+sIn		Nonverb_suffix	"+Nonverbal(2nd Singular)"
+DIr		Nonverb_suffix	"+Nonverbal(3rd Singular)"
''		Nonverb_suffix	"+Nonverbal(3rd Singular)"
+YIz		Nonverb_suffix	"+Nonverbal(1st Plural)"
+sInIz		Nonverb_suffix	"+Nonverbal(2nd Plural)"
+DIrlEr		Nonverb_suffix	"+Nonverbal(3rd Plural)"

TO_ADVERB:
+ken		To_adverb	"+(-> progressive adverb)"

TO_ADJ:
+sIz		Adj_root	"+(-> adj, without)"

YES_NO:
+mI		Yes_no		"+(Yes/No ?)"

V_NEGATIVE:
+mE		V_negative	"+(not)"

INFINITIVE:
+mEg		Infinitive	"+(Infinitive Tense)"

TENSE:
+DI		Tense		"+(Definite Past Tense)"
+Iyor		Progressive	"+(Present Progessive Tense)"

PERSONAL:
+m		Personal	"+(1st Person Singular)"
+n		Personal	"+(2nd Person Singular)"
''		Personal	"+(3rd Person Singular)"
+k		Personal	"+(1st Person Plural)"
+nIz		Personal	"+(2nd Person Plural)"
''		Personal	"+(3rd Person Plural)"
+lEr		Personal	"+(3rd Person Plural)"

PROGRESS_PERSONAL:
''		Progress_personal	"+(3rd Person Singular)"
+sInIz		Progress_personal	"+(2nd Person Plural)"

End:
0	#		""
