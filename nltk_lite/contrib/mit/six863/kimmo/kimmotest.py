from kimmo import *
k = KimmoRuleSet.load('simple.yaml')
print list(k.generate('have+ing'))
print list(k.recognize('having'))
