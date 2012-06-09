import os
import tempfile
from nltk.metrics.malteval import Malteval
from nltk.metrics.maltevalxmlcommadns import MaltevalXmlCommands
from nltk.metrics.maltevalconstans import MaltevalMetric,\
    MaltevalParameters, MaltevalGroupBy

#make sure you have you MaltEval.jar pointed by MALTEVALHOME
#(or pass jar as argument)
malteval = Malteval()
malteval.setEvalFile("./eval.conll")
malteval.setGoldFile("./gold.conll")

#lets make something simple
print "uas ", malteval.uas()
print "las ", malteval.las()

#let's do it more explicit way
maltevalXmlCommands = MaltevalXmlCommands()
maltevalXmlCommands.addMetric(MaltevalMetric.UAS)
malteval.setCommand(maltevalXmlCommands)
res = malteval.execute()
print res
print "Parsed :", malteval.tryParse(res)

#let's do something more sophisticated
maltevalXmlCommands = MaltevalXmlCommands()
maltevalXmlCommands.addMetric(MaltevalMetric.UAS)
maltevalXmlCommands.addMetric(MaltevalMetric.LAS)
maltevalXmlCommands.addGroupBy(MaltevalGroupBy.Deprel)
maltevalXmlCommands.addGroupBy(MaltevalGroupBy.Postag)
malteval.setCommand(maltevalXmlCommands)
res = malteval.execute()
print res

#let's see how to modify manually commands
maltevalXmlCommands = MaltevalXmlCommands()
maltevalXmlCommands.addMetric(MaltevalMetric.LAS)
maltevalXmlCommands.addGroupBy(MaltevalGroupBy.Deprel)
#sometimes you must add something manually
maltevalXmlCommands.addValue(MaltevalParameters.ExcludePdeprels, "apobl|app")
#this is example of so called complex group by which is
#used rarely but can be specified
maltevalXmlCommands.addGroupBy("Cpostag@-1")
#see if it looks good
print maltevalXmlCommands.toPrettyXml()
malteval.setCommand(maltevalXmlCommands)
print malteval.execute()

#If you prefer to make command file other way you can
cmdString = """<evaluation>
<parameter name="Metric">
<value>LAS</value>
</parameter>
<parameter name="GroupBy">
<value>Token</value>
</parameter>
</evaluation>
"""

pathToCommandFile = os.path.join(tempfile.gettempdir(), "mycmd.xml")
cmdFile = open(pathToCommandFile, 'w')
cmdFile.write(cmdString)
cmdFile.close()
malteval.commandFilePath = pathToCommandFile
print malteval.execute()
os.remove(pathToCommandFile)


#last but not least some nice windows - it's nice of you for coming so far
malteval.deleteCommandFile()
malteval.setVisual(True)
malteval.execute()

#hope its helpful
