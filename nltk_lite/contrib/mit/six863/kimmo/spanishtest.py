from kimmo import *
k = KimmoRuleSet.load('spanish.yaml')
print list(k.recognize('coger#', TextTrace(3)))
print list(k.generate("la'piz+s#", TextTrace(1)))
