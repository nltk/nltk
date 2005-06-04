# Natural Language Toolkit: Third-Party Contributions
#
# Contributions from: Carlos Rodriguez
#
# Copyright (C) 2001-2005 The original contributors
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
"""
Multilingual Corpus readers and tokenizers for additional data packs,
modeled on NLTK corpus readers.

1. ClicTalp corpora for Spanish and Catalan
   Download corpora from http://turing.iimas.unam.mx/NLTK/
   Universitat Politècnica de Catalunya http://www.talp.upc.es/
   Universitat de Barcelona http://clic.fil.ub.es/

2. 3LB Treebank corpora for Spanish and Catalan.
   Download corpora from http://turing.iimas.unam.mx/NLTK/
   Universitat Politècnica de Catalunya http://www.talp.upc.es/
   Universitat de Barcelona http://clic.fil.ub.es/



USAGE:

1. ClicTalp corpora for Spanish and Catalan

>>> from nltk_contrib.corpora.clictalp import clictalpcas (for castillian Spanish)
>>> from nltk_contrib.corpora.clictalp import clictalpcat  (for Catalan)
>>> from nltk_contrib.corpora.clictalp import clictalpcas
>>> clictalpcas.groups()
['press: suplementosCiencia', 'press: articulistas', 'press: prensa deportiva', 'press: semanarios', 'press: ensayo', 'fiction: narrativa', 'press: noticias']
>>> clictalpcas.items('press: prensa deportiva')
('d1.tag.nou', 'd2.tag.nou')
>>> tks = clictalpcas.read('d1.tag.nou')
>>> tks["WORDS"][:15]
[<LEMMA='este', TAG='DD0MS0', TEXT='Este'>, <LEMMA='a\xf1o', TAG='NCMS000', TEXT='a\xf1o'>, <LEMMA='reci\xe9n', TAG='RG', TEXT='reci\xe9n'>, <LEMMA='concluido', TAG='AQ0MSP', TEXT='concluido'>, <LEMMA='no', TAG='RN', TEXT='no'>, <LEMMA='haber', TAG='VAIP3S0', TEXT='ha'>, <LEMMA='ser', TAG='VSP00SM', TEXT='sido'>, <LEMMA='ni', TAG='CC', TEXT='ni'>, <LEMMA='el', TAG='DA0MS0', TEXT='el'>, <LEMMA='a\xf1o_del_gato', TAG='NP00000', TEXT='A\xf1o_del_Gato'>, <LEMMA=',', TAG='Fc', TEXT=','>, <LEMMA='ni', TAG='CC', TEXT='ni'>, <LEMMA='el', TAG='DA0MS0', TEXT='el'>, <LEMMA='a\xf1o_del_conejo', TAG='NP00000', TEXT='A\xf1o_del_Conejo'>, <LEMMA=',', TAG='Fc', TEXT=','>]
>>> for x in tks["WORDS"][:15]:
	print x.exclude("LEMMA"),

<Este/DD0MS0> <a\xf1o/NCMS000> <reci\xe9n/RG> <concluido/AQ0MSP> <no/RN> <ha/VAIP3S0> <sido/VSP00SM> <ni/CC> <el/DA0MS0> <A\xf1o_del_Gato/NP00000> <,/Fc> <ni/CC> <el/DA0MS0> <A\xf1o_del_Conejo/NP00000> <,/Fc>



2. 3LB Treebank corpora for Spanish and Catalan.

>>> from nltk_contrib.corpora.tree3LB import *

>>> LB
<Corpus: 3LB (contains 489 items; 2 groups)>

>>> LB.groups()
('cas', 'cat')  <- 'cas' Castilian Spanish Treebank, 'cat' Catalan Treebank

>>> LB.items('cas')[:18]
('cas//a1-0.tbf', 'cas//a1-1.tbf', 'cas//a1-2.tbf', 'cas//a1-3.tbf', 'cas//a1-4.tbf',
'cas//a1-5.tbf', 'cas//a1-6.tbf', 'cas//a1-7.tbf', 'cas//a2-0.tbf', 'cas//a12-0.tbf', 'cas//a12-1.tbf',
'cas//a12-2.tbf', 'cas//a12-3.tbf', 'cas//a12-4.tbf', 'cas//a14-0.tbf', 'cas//a14-1.tbf', 'cas//a14-2.tbf',
'cas//a14-3.tbf')

>>> LB.read('cas//a12-1.tbf')[8]
<TREE=(S.co: (S: (sn-SUJ: (espec.fs: <La/da0fs0>) (grup.nom.fs: <rata/ncfs000>)) (gv: <es/vsip3s0>)
(sn-ATR: (espec.ms: <un/di0ms0>) (grup.nom.ms: <animal/ncms000> (s.a.ms: <clasista/aq0cs0>)))
(sp-CC: (prep: <por/sps00>) (sn: (grup.nom.fs: <naturaleza/ncfs000>)))) <,/Fc> (S: (sp-CC: (prep: <hasta/sps00>)
(sp: (prep: <en/sps00>) (sn: (grup.nom.s: <eso/pd0ns000>)))) <\\*-0-\\*/sn.e-SUJ> (gv: <es/vsip3s0>)
(sa-ATR: <asquerosa/aq0fs0>)) <./Fp>), WORDS=[<La/da0fs0>, <rata/ncfs000>, <es/vsip3s0>, <un/di0ms0>,
<animal/ncms000>, <clasista/aq0cs0>, <por/sps00>, <naturaleza/ncfs000>, <,/Fc>, <hasta/sps00>,
<en/sps00>, <eso/pd0ns000>, <\\*-0-\\*/sn.e-SUJ>, <es/vsip3s0>, <asquerosa/aq0fs0>, <./Fp>]>

>>> LB.read_lemma('cas//a12-1.tbf')[8]
<TREE=(S.co: (S: (sn-SUJ: (espec.fs: <LEMMA='el', POS='da0fs0', TEXT='La'>) (grup.nom.fs: <LEMMA='rata',
POS='ncfs000', TEXT='rata'>)) (gv: <LEMMA='ser', POS='vsip3s0', TEXT='es'>) (sn-ATR: (espec.ms: <LEMMA='uno',
POS='di0ms0', TEXT='un'>) (grup.nom.ms: <LEMMA='animal', POS='ncms000', TEXT='animal'> (s.a.ms: <LEMMA='clasista',
POS='aq0cs0', TEXT='clasista'>))) ....
"""
