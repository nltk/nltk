Begin:               V_ROOT_ar V_ROOT_ir V_ROOT_er N_ROOT End
V_End:               End

;V_ar:           V_SUFFIX_IN V_SUFFIX_SB V_CLOSE_AR V_CLOSE_IR V_CLOSE_ER End
;V_ir:               V_SUFFIX_IN V_SUFFIX_SB V_CLOSE_AR V_CLOSE_IR V_CLOSE_ER End
V_er:                V_CLOSE_ER V_er_IN V_er_SB End
V_ir:                V_CLOSE_IR V_ir_IN V_ir_SB End
V_ar:                V_CLOSE_AR V_ar_IN V_ar_SB End

N_Suffix1:           N_PLURAL End
N_End:               End

INITIAL:
''                    Begin                   "[ "

N_ROOT:
l^piz          N_Suffix1        "n (pencil)"
ciudad          N_Suffix1        "n (city)"
bota             N_Suffix1        "n (boot)"


N_PLURAL:
+s              N_End         ".plural"


V_ROOT_er:
cog             V_er        "v (to take without asking...)"
conozc          V_er        "v (know)"
parezc          V_er        "v (seem)"
venz             V_er        "v (conquer defeat)"
cuez          V_er        "v (cook bake)"
ejerz          V_er        "v (exercise practice)"

V_ROOT_ar:
lleg            V_ar     "v (arrive)"
habl            V_ar     "v (speak)"
pag             V_ar        "v (pay)"
cruz             V_ar        "v (cross)"

V_ROOT_ir:
test            V_ir        "v (test)"
viv             V_ir     "v (live)"


V_ar_IN:
+o                    V_End           "+1p.sg.PRES - ind"
+as                   V_End           "+2p.sg.PRES - ind"
+a                    V_End           "+3p.sg.PRES - ind"
+amos                 V_End           "+1p.pl.PRES - ind"
+an                   V_End           "+3p.pl.PRES - ind"

V_er_IN:
+o                    V_End           "+1p.sg.PRES - ind"
+es                   V_End           "+2p.sg.PRES - ind"
+e                    V_End           "+3p.sg.PRES - ind"
+emos                 V_End           "+1p.pl.PRES - ind"
+en                   V_End           "+3p.pl.PRES - ind"

V_ir_IN:
+o                 V_End           " +1p.sg.PRES - ind"
+es                 V_End           " +2p.sg.PRES - ind"
+e                 V_End           " +3p.sg.PRES - ind"
+imos                 V_End           "+1p.plural.PRES - ind"
+en                 V_End           "+3p.plural.PRES - ind"


V_ar_SB:
+e                    V_End           "+1p.sg.PRES - sub"
+es                   V_End           "+2p.sg.PRES - sub"
+e                    V_End           "+3p.sg.PRES - sub"
+emos                 V_End           "+1p.pl.PRES - sub"
+en                   V_End           "+3p.pl.PRES - sub"

V_er_SB:
+a                    V_End           "+1p.sg.PRES - sub"
+as                   V_End           "+2p.sg.PRES - sub"
+a                    V_End           "+3p.sg.PRES - sub"
+amos                 V_End           "+1p.pl.PRES - sub"
+an                   V_End           "+3p.pl.PRES - sub"

V_ir_SB:
+a                    V_End           "+1p.sg.PRES - sub"
+as                   V_End           "+2p.sg.PRES - sub"
+a                    V_End           "+3p.sg.PRES - sub"
+amos                 V_End           "+1p.pl.PRES - sub"
+an                   V_End           "+3p.pl.PRES - sub"


V_CLOSE_AR:
+ar                   V_End           " ar-inf "

V_CLOSE_IR:
+ir                   V_End           " ir-inf "

V_CLOSE_ER:
+er                   V_End           " er-inf "


End:
0                     #                        None

