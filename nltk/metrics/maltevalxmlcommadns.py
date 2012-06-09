from nltk.metrics.maltevalconstans import MaltevalMetric, MaltevalParameters
from xml.dom.minidom import Document

__author__ = 'kacper'


class Parameter(object):
    '''
    Each parameter has a default value which is overridden if it is
    specified in the evaluation file. New values for a parameter are
    added using zero or more value elements located under the parameter
    element.E.g
    <parameter name="par1">
        <value>par1_val1</value>
        <value>par1_val2</value>
        <value>...</value>
    </parameter>
    This class is representing such single parameter.
    '''

    def __init__(self, parameterName, command, evaluation):
        '''
        :param parameterName: the available parameters are: Metric, GroupBy,
        MinSentenceLength,MaxSentenceLength, ExcludeWordforms, ExcludeLemmas,
        ExcludeCpostags, ExcludePostags, ExcludeFeats, ExcludeDeprels,
        ExcludePdeprels and ExcludeUnicodePunc. They can be all achieved via
        MaltevalParameter as consts.
        :type parameterName:string
        :param command: object representing created command
        :type command: xml.dom.minidom.Document
        :param evaluation: object representing body of created command.
         Name taken form malteval naming convention
        :type evaluation: xml.dom.minidom.Element
        :param consts: appropriate const class from maltevalconstans.py
        '''
        self.parameterName = parameterName
        self.command = command
        self.evaluation = evaluation
        self.parameter = None


    def addValue(self, valueName):
        '''
        Adding single value to this Parameter values list. If
        same value is added several times old value is erased
        which might make a difference when formatter is used.
        :param valueName: name of value to be added.
        :type valueName: string
        '''
        if not self.parameter:
            self.parameter = self.command.createElement("parameter")
            self.parameter.setAttribute("name", self.parameterName)
            self.evaluation.appendChild(self.parameter)
            self.valuesDict = {}

        if valueName in self.valuesDict:
            self.parameter.removeChild(self.valuesDict[valueName])

        valueNode = self.command.createElement("value")
        self.parameter.appendChild(valueNode)

        textNode = self.command.createTextNode(valueName)
        valueNode.appendChild(textNode)
        self.valuesDict[valueName] = valueNode

    def deleteValue(self, valueName):
        '''
        Deletes value from this Parameter values list.
        If this parameter was not added or is not
        specified in Maleteval documentation AttributeError
        is raised
        :param valueName: value to be deleted
        :type valueName: string
        '''

        if not self.parameter:
            raise AttributeError(valueName)

        if not valueName in self.valuesDict:
            raise AttributeError(valueName)

        self.parameter.removeChild(self.valuesDict[valueName])
        self.valuesDict.pop(valueName)

        if not self.valuesDict:
            self.delete()

    def delete(self):
        self.evaluation.removeChild(self.parameter)
        self.parameter = None


class MaltevalXmlCommands(object):
    '''
    A simple evaluation file (default.xml) could look like this:

    <evaluation>
        <parameter name="Metric">
            <value>LAS</value>
        </parameter>
    <parameter name="GroupBy">
        <value>Token</value>
    </parameter>
    </evaluation>

    The root element is named evaluation and contains a list of zero or more
    parameter elements. Each parameter element has a required name attribute,
    containing the name of the parameter to set.Each parameter has a default
    value which is overridden if it is specified in the evaluation file. New
    values for a parameter are added using zero or more value elements located
    under the parameter element. In the example we can see that LAS is added
    to Metric and that Token is added to GroupBy, which corresponds to the
    default settings. As the evaluation element consists of a list of
    parameters and each parameter consists of a list of value elements, the
    generic evaluation file format looks like this:

    <evaluation>
        <parameter name="par1">
            <value>par1_val1</value>
            <value>par1_val2</value>
            <value>...</value>
        </parameter>
        <parameter name="par2">
            <value>par2_val1</value>
            <value>par2_val2</value>
            <value>...</value>
        </parameter>
      ...
    </evaluation>

    The parameter list is treated as a set with the name attribute as the
    key, where the last parameter element with a distinct key overrides
    all previous parameter elements with the same key. Each list of value
    elements is also treated as a set. MaltEval then performs one evaluation
    for every possible combination of values for all parameters. For instance,
    with two parameters having three and four values,respectively, twelve
    evaluations will be computed by MaltEval by combining every value of the
    first parameter with every value of the second parameter.
    '''

    def __init__(self):
        self.command = Document()
        self.evaluation = self.command.createElement("evaluation")
        self.command.appendChild(self.evaluation)
        self.parameters = {}


    def toprettyxml(self, ident=" "):
        '''
        Print xml prettily.
        :param ident:   specify ident
        '''
        return self.command.toprettyxml(ident)

    def addValue(self, parameterName, valueName):
        '''
        Generic function for adding parameter value to this command.
        If either parameterName or valueName will not match
        MaltEval documentation AttributeError will be raised
        :param parameterName: name of the parameter to be modified
        :type parameterName: string
        :param valueName: name of the value to be added to parameter
        :type valueName:String
        '''
        if not parameterName in [name for name in
                                 dir(MaltevalParameters) if not name.startswith('__')]:
            raise AttributeError(parameterName)
        if not parameterName in self.parameters:
            parameter = Parameter(parameterName, self.command, self.evaluation)
            self.parameters[parameterName] = parameter

        self.parameters[parameterName].addValue(valueName)

    def deleteValue(self, parameterName, valueName):
        '''
        Generic function for deleting  parameter value form this command.
        If one tries to delete non existing value or parameter
        nothing will happen.
        :param parameterName: name of the parameter to be modified
        :type parameterName: string
        :param valueName: name of the value to be deleted from parameter
        :type valueName:String
        '''
        if parameterName in self.parameters:
            self.parameters[parameterName].deleteValue(valueName)


    def deleteParam(self, parameterName):
        if parameterName in self.parameters:
            self.parameters[parameterName].delete()
            self.parameters.pop(parameterName)

    def maxSentenceLength(self, maxLength):
        if maxLength < 1:
            raise AttributeError("maxLength smaller then 1")
        self.addValue(MaltevalParameters.MaxSentenceLength, str(maxLength))

    def deleteMaxSentenceLength(self):
        self.deleteParam(MaltevalParameters.MaxSentenceLength)

    def minSentenceLength(self, minLength):
        if minLength < 1:
            raise AttributeError("minLength smaller then 1")
        self.addValue(MaltevalParameters.MinSentenceLength, str(minLength))

    def deleteMinSentenceLength(self):
        self.deleteParam(MaltevalParameters.MinSentenceLength)

    def addGroupBy(self, valueName):
        self.addValue(MaltevalParameters.GroupBy, valueName)

    def deleteGroupBy(self, valueName):
        self.deleteValue(MaltevalParameters.GroupBy, valueName)

    def deleteMetric(self, valueName):
        self.deleteValue(MaltevalParameters.Metric, valueName)

    def addMetric(self, valueName):
        if not valueName in [name for name in
                             dir(MaltevalMetric) if not name.startswith('__')]:
            raise AttributeError
        self.addValue(MaltevalParameters.Metric, valueName)









