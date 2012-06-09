from unittest import TestCase
from xml.dom.minidom import Document, parseString
from nltk.metrics.maltevalconstans import MaltevalMetric, MaltevalParameters, MaltevalGroupBy
from nltk.metrics.maltevalxmlcommadns import MaltevalXmlCommands, Parameter

NOT_EXISTING = 'notExisting'

__author__ = 'kacper'



#Failed modules
#Python 2.7.2+ (/usr/bin/python2.7)
#coverage.tracer
#Generation of skeletons for the modules above will be tried again when the modules are updated or a new version of generator is available

class TestParameter(TestCase):
    def setUp(self):
        self.malevalCmd = MaltevalXmlCommands()
        self.command = Document()
        self.evaluation = self.command.createElement("evaluation")
        self.command.appendChild(self.evaluation)
        self.param = Parameter('metric', self.command,
            self.evaluation)

    def _getValue(self, parameterName, valueName, doc):
        dom = parseString(doc)
        for node in dom.getElementsByTagName("parameter"):
            if node.getAttribute('name') == parameterName:
                lst = [vals.childNodes[0].data.rstrip().lstrip()
                       for vals in node.getElementsByTagName("value")]
                if valueName in lst:
                    return True

        return False

    def _getValueSelf(self, parameterName, valueName):
        return self._getValue(parameterName, valueName, self.malevalCmd.toPrettyXml())

    def _hasParameter(self, parameterName, doc):
        dom = parseString(doc)
        for node in dom.getElementsByTagName("parameter"):
            if node.getAttribute('name') == parameterName:
                return True
        return False

    def _hasParameterSelf(self, parameterName):
        return self._hasParameter(parameterName, self.malevalCmd.toPrettyXml())

    ###TESTS



    def testParameterDeleteNotAddedValue(self):
        self.assertRaises(AttributeError, self.param.deleteValue, NOT_EXISTING)

    def testAddValue(self):
        self.param.addValue(MaltevalMetric.LAS)
        self.assertTrue(MaltevalMetric.LAS in self.param.valuesDict)

    def testAddDeleteProperty(self):
        self.param.addValue(MaltevalMetric.LAS)
        self.param.deleteValue(MaltevalMetric.LAS)
        self.assertFalse(MaltevalMetric.LAS in self.param.valuesDict)

    def testAddNonExistingCommandParameter(self):
        self.assertRaises(AttributeError, self.malevalCmd.addValue, NOT_EXISTING, MaltevalMetric.LAS)

    def testAddNonExistingEverything(self):
        self.assertRaises(AttributeError, self.malevalCmd.addValue, NOT_EXISTING, NOT_EXISTING)

    def testAddCorrectParameterAndAnyValue(self):
        self.malevalCmd.addValue(MaltevalParameters.Metric, NOT_EXISTING)
        self.assertTrue(MaltevalParameters.Metric in self.malevalCmd.parameters)

    def testDoubleAdd(self):
        self.malevalCmd.addValue(MaltevalParameters.Metric, MaltevalMetric.LAS)
        self.malevalCmd.addValue(MaltevalParameters.Metric, MaltevalMetric.LAS)
        res = self.malevalCmd.toPrettyXml()
        splits = str(res).split(MaltevalParameters.Metric)
        self.assertEqual(len(splits), 2);

    def testRemove(self):
        self.malevalCmd.addValue(MaltevalParameters.Metric, MaltevalMetric.LAS)
        self.malevalCmd.deleteValue(MaltevalParameters.Metric, MaltevalMetric.LAS)
        self.assertFalse(self.malevalCmd.parameters is {})


    def testAddMaxSentenceLength(self):
        self.malevalCmd.maxSentenceLength(10);
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.MaxSentenceLength, "10"))

    def testDeleteMaxSentenceLength(self):
        self.malevalCmd.maxSentenceLength(10);
        self.malevalCmd.deleteMaxSentenceLength()
        self.assertFalse(
            self._hasParameterSelf(MaltevalParameters.MaxSentenceLength)
        )

    def testAddMinusSentenceLength(self):
        self.assertRaises(AttributeError, self.malevalCmd.maxSentenceLength, -1)


    def testAddMinSentenceLength(self):
        self.malevalCmd.minSentenceLength(10)
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.MinSentenceLength, "10"))

    def testDeleteMinSentenceLength(self):
        self.malevalCmd.minSentenceLength(10)
        self.malevalCmd.deleteMinSentenceLength()
        self.assertFalse(
            self._hasParameterSelf(MaltevalParameters.MinSentenceLength)
        )

    def testAddMinusMinSentenceLength(self):
        self.assertRaises(AttributeError, self.malevalCmd.minSentenceLength, -1)


    def testAddGroupBy(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.Lemma)
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.GroupBy, MaltevalGroupBy.Lemma)
        )

    def testAddMultiple(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.Lemma)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcDepth)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcProjectivity)
        self.assertEqual(len(self.malevalCmd.parameters[MaltevalParameters.GroupBy].valuesDict), 3)

    def testAddMultipleLemma(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.Lemma)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcDepth)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcProjectivity)
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.GroupBy, MaltevalGroupBy.Lemma)
        )

    def testAddMultipleArcDepth(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.Lemma)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcDepth)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcProjectivity)
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.GroupBy, MaltevalGroupBy.ArcDepth)
        )

    def testAddMultipleArcArcProjectivity(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.Lemma)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcDepth)
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcProjectivity)
        self.assertTrue(
            self._getValueSelf(MaltevalParameters.GroupBy, MaltevalGroupBy.ArcProjectivity)
        )

    def testDeleteGroupBy(self):
        self.malevalCmd.deleteGroupBy(MaltevalGroupBy.ArcDepth)
        self.assertFalse(
            self._hasParameterSelf(MaltevalParameters.GroupBy)
        )

    def testDeleteAfterAditionGroupBy(self):
        self.malevalCmd.addGroupBy(MaltevalGroupBy.ArcDepth)
        self.malevalCmd.deleteGroupBy(MaltevalGroupBy.ArcDepth)
        self.assertFalse(
            self._hasParameterSelf(MaltevalParameters.GroupBy)
        )


    def testAddMetricNonExisting(self):
        self.assertRaises(AttributeError, self.malevalCmd.addMetric, NOT_EXISTING)

    def testDeleteMetrics(self):
        self.malevalCmd.deleteMetric(NOT_EXISTING)

