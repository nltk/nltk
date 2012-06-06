from nltk.metrics.maltevalconstans import Malteval_metric

__author__ = 'kacper'
from xml.dom.minidom import Document

class Parameter(object):
    def __init__(self, parameterName, command, evaluation, constans):
        self.parameterName = parameterName
        self.command = command
        self.evaluation = evaluation
        self.constans = constans
        self.parameter = None


    def addValue(self, valueName):
        if not self.parameter:
            self.parameter = self.command.createElement("parameter")
            self.parameter.setAttribute("name", self.parameterName)
            self.evaluation.appendChild(self.parameter)
            self.valuesDict = {}

        if not valueName in [name for name in dir(self.constans) if not name.startswith('__')]:
            raise AttributeError("type :" + valueName + " is not applicable. Consult " + self.constans)

        if valueName in self.valuesDict:
            self.parameter.removeChild(self.valuesDict[valueName])

        valueNode = self.command.createElement("value")
        self.parameter.appendChild(valueNode)

        textNode = self.command.createTextNode(valueName)
        valueNode.appendChild(textNode)
        self.valuesDict[valueName] = valueNode

    def deleteValue(self, value):
        if not self.parameter:
            raise AttributeError(value)

        if not value in self.valuesDict:
            raise AttributeError(value)

        self.parameter.removeChild(self.valuesDict[value])
        self.valuesDict.pop(value)

        if not self.valuesDict:
            self.evaluation.removeChild(self.parameter)
            self.parameter = None


class Malteval_xml_commands(object):
    def __init__(self):
        self.command = Document()
        self.evaluation = self.command.createElement("evaluation")
        self.command.appendChild(self.evaluation)
        self.parameters = {}
        self._constans = {
            'metric': Malteval_metric
        }

    def toprettyxml(self, ident=" "):
        return  self.command.toprettyxml(ident)

    def addValue(self, parameterName, valueName):
        #TODO paramteres names as const
        if not parameterName in self.parameters:
            parameter = Parameter(parameterName,
                self.command,
                self.evaluation,
                self._constans[parameterName])
            self.parameters[parameterName] = parameter

        self.parameters[parameterName].addValue(valueName)

    def deleteValue(self, parameterName, valueName):
        #TODO parameters names as consts
        if not parameterName in self.parameters:
            raise AttributeError(type)
        self.parameters[parameterName].deleteValue(valueName)


#    def addMetrics(self, type):
#        if not hasattr(self, 'metric'):
#            self.metric = self.command.createElement("parameter")
#            self.metric.setAttribute("name", "metric")
#            self.evaluation.appendChild(self.metric)
#            self._metricDict = {}
#
#        if not type in [name for name in dir(Malteval_metric) if not name.startswith('__')]:
#            raise AttributeError("type :" + type + " is not applicable. Consult Malteval_metric")
#
#        value = self.command.createElement("value")
#        if type in self._metricDict:
#            self.metric.removeChild(self._metricDict[type])
#
#        self.metric.appendChild(value)
#
#        type_text = self.command.createTextNode(type)
#        value.appendChild(type_text)
#        self._metricDict[type] = value
#
#
#    def deleteMetrics(self, type):
#        if not hasattr(self, 'metric'):
#            raise AttributeError(type)
#        if not type in self._metricDict:
#            raise AttributeError(type)
#        self.metric.removeChild(self._metricDict[type])
#        self._metricDict.pop(type)
#        if not self._metricDict:
#            self.evaluation.removeChild(self.metric)
#            delattr(self, "metric")


maleval_cmd = Malteval_xml_commands()
print maleval_cmd.toprettyxml()
maleval_cmd.addValue('metric', 'LAS')
print maleval_cmd.toprettyxml()
maleval_cmd.addValue('metric', 'LAS')
print maleval_cmd.toprettyxml()
maleval_cmd.deleteValue('metric', 'LAS')
print maleval_cmd.toprettyxml()
maleval_cmd.addValue('metric', 'LAS')
print maleval_cmd.toprettyxml()

