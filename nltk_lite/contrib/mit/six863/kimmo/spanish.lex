; Alex Gruenstein
; 6.863
; Lab 1b
; spanish.lex

;-----------
;State_Name   Arc_transition_label_abbreviation

Begin:    V_ROOT_AR V_ROOT_ER  V_ROOT_IR N_ROOT End
v_root_ar: V_SUFFIX_AR
v_root_er: V_SUFFIX_ER
v_root_ir: V_SUFFIX_IR
v_suffix: End
n_root: NUMBER
number: End

;-----------
; Label_name  Next_state  Output_on_making_this_arc_transition
V_ROOT_AR:
lleg v_root_ar Verb(llegar-"arrive")
pag v_root_ar Verb(pagar-"pay")
cruz v_root_ar Verb(cruzar-"cross" )

V_ROOT_ER:
coJ v_root_er Verb(coger)
conoC v_root_er Verb(conocer-"know")
pareC v_root_er Verb(paracer-"seem")
venz v_root_er Verb(vencer-"conquer/defeat")
ejerz v_root_er Verb(ejercer-"exercise/practice")
cuez v_root_er Verb(cocer-"cook")


V_ROOT_IR:


V_SUFFIX_ER:
+er    v_suffix inf
+o     v_suffix 1p,sg,ind,pres
+es    v_suffix 2p,sg,ind,pres
+e     v_suffix 3p,sg,ind,pres
+emos  v_suffix 1p,pl,ind,pres
+en    v_suffix 3p,pl,ind,pres
+a     v_suffix 1p,sg,subj,pres
+as    v_suffix 2p,sg,subj,pres
+a     v_suffix 3p,sg,subj,pres
+amos  v_suffix 1p,pl,subj,pres
+an    v_suffix 3p,pl,subj,pres

V_SUFFIX_IR:
+ir    v_suffix inf
+o     v_suffix 1p,sg,ind,pres
+es    v_suffix 2p,sg,ind,pres
+e     v_suffix 3p,sg,ind,pres
+imos  v_suffix 1p,pl,ind,pres
+en    v_suffix 3p,pl,ind,pres
+a     v_suffix 1p,sg,subj,pres
+as    v_suffix 2p,sg,subj,pres
+a     v_suffix 3p,sg,subj,pres
+amos  v_suffix 1p,pl,subj,pres
+an    v_suffix 3p,pl,subj,pres

V_SUFFIX_AR:
+ar    v_suffix inf
+o     v_suffix 1p,sg,ind,pres
+as    v_suffix 2p,sg,ind,pres
+a     v_suffix 3p,sg,ind,pres
+amos  v_suffix 1p,pl,ind,pres
+an    v_suffix 3p,pl,ind,pres
+e     v_suffix 1p,sg,subj,pres
+es    v_suffix 2p,sg,subj,pres
+e     v_suffix 3p,sg,subj,pres
+emos  v_suffix 1p,pl,subj,pres
+en    v_suffix 3p,pl,subj,pres


N_ROOT:
l^piz n_root Noun(l^piz-"pencil")
ciudad n_root Noun(cuidad-"city")
bota n_root Noun(bota-"boat")
cosa n_root Noun(cosa-"thing")

NUMBER:
+s number ,plural
'' number ,singular

End:
'#' Begin None
