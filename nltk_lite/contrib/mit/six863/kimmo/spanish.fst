subset BACK u o a > * ^
subset FRONT e i < {
subset CONSONANTS b c d f g h j k l m n ~ p q r s t v w x y z J C
subset C_NOT_S b c d f g h j k l m n ~ p q r t v w x y z 


machine "other defaults"
state start
+:0 start
#:# start
+:+ reject
others start


machine "g-j mutation"
state start
J:J reject
J:g front
J:j back
others start

rejecting state front
@:0 front
@:FRONT start
others reject

rejecting state back
@:BACK start
@:0 back
others reject


machine "z-c mutation"
state start
z:c front
z:z nonfront
others start

rejecting state front
@:FRONT start
@:0 front
others reject

state nonfront
@:FRONT reject
z:c front
z:z nonfront
@:0 nonfront
others start

machine "pluralization"
state start
@:C_NOT_S consonant
s:s consonant
0:e reject
others start

state consonant
@:C_NOT_S consonant
s:s consonant
0:e reject
+:0 guess_e
others start

state guess_e
0:e require_s
@:C_NOT_S consonant
s:s reject
others start

rejecting state require_s
s:s start
others reject



machine "c-zc irregularity pattern in -cer and -cir verbs"
state start
C:C reject
C:c front_1
C:z back_1
0:c reject
others start

rejecting state front_1
+:0 front_2
others reject

rejecting state front_2
@:FRONT start
others reject

rejecting state back_1
0:c back_2
others reject

rejecting state back_2
+:0 back_3
others reject

rejecting state back_3
@:BACK start
others reject



