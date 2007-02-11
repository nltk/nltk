from kimmo import *
k = KimmoRuleSet.load('english.yaml')
print list(k.generate('`slip+ed', TextTrace(3)))
print list(k.recognize('slipped', TextTrace(1)))
