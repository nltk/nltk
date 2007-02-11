from kimmo import *
k = KimmoRuleSet.load('spanish.yaml')
# print list(k.generate('`slip+ed', TextTrace(3)))
print list(k.recognize('coger', TextTrace(1)))
