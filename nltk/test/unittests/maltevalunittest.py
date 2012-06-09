# coding: utf-8
import os
import tempfile
import unittest
from nltk.metrics.malteval import Malteval
from nltk.parse.dependencygraph import DependencyGraph
from stat import *
from nltk.metrics.maltevalxmlcommadns import MaltevalXmlCommands


class TestMalteval(unittest.TestCase):
    def setUp(self):
        dg1 = DependencyGraph(
            """1	Na	na	prep	prep	loc	4	pobl	_	_
            2	tym	to	psubst	psubst	sg|loc|n	1	pobj	_	_
            3	nie	nie	qub	qub	_	4	neg	_	_
            4	koncza	konczyc	fin	fin	pl|ter|imperf	0	pred	_	_
            5	sie	się	qub	qub	_	4	refl	_	_
            6	ich	on	ppron3	ppron3	pl|gen|m1|ter|akc|npraep	7	adj	_	_
            7	problemy	problem	subst	subst	pl|nom|m3	4	subj	_	_
            8	.	.	interp	interp	_	4	punct	_	_
            """)
        dg2 = DependencyGraph(
            """1       Zakonczyly      zakonczyc       praet   praet   pl|f|perf       0       pred    _       _
            2       sie     sie     qub     qub     _       1       refl    _       _
            3       sukcesem        sukces  subst   subst   sg|inst|m3      1       obl     _       _
            4       .       .       interp  interp  _       1       punct   _       _
            """)
        self.dg = [dg1, dg2]

    def setSampleFile(self, maltEval):
        gold_file = '/tmp/me/gold.conll'
        maltEval.setGoldFile(gold_file)
        test_file = '/tmp/me/test.conll'
        maltEval.setEvalFile(test_file)

    def mockedExecute(self, cmd):
        s = 'Evaluation arguments: -g gold.conll -s out.conll'\
            '\n====================================================\n'\
            'Gold:   /home/kacper/dev/nltkNewDev/nltk/gold.conll\nParsed:'\
            ' /home/kacper/dev/nltkNewDev/nltk/out.conll'\
            '\n====================================================\n'\
            'Metric-> LAS\nGroupBy-> Token\n'\
            '\n====================================================\n'\
            '\naccuracy /    Token\n-----------------------\n0.885         '\
            'Row mean\n4537          Row count\n-----------------------\n\n'
        return s

    def mockSetUp(self):
        maltEval = Malteval(malteval_jar=None, look_for_jar=False)
        maltEval.setJar(malteval_jar='MaltEval.jar',
            check_jar_correctness=False)
        self.setSampleFile(maltEval)
        return maltEval

        ### TESTS

    def test_constructor(self):
        jar = '/x/y/z/1221526/y/'
        maltEval = Malteval(jar, look_for_jar=False)
        self.assertEquals(maltEval._malteval_bin, jar)

    def test_set_Gold(self):
        maltEval = Malteval(None, False)
        gold_file = '/tmp/me/gold.conll'
        maltEval.setGoldFile(gold_file)
        self.assertEqual(maltEval.goldFile, gold_file)

    def test_set_Eval_File(self):
        maltEval = Malteval(None, False)
        eval_file = '/tmp/me/test.conll'
        maltEval.setEvalFile(eval_file)
        self.assertEqual(maltEval.evalFile, eval_file)

    def test_run_default_evaluation(self):
        maltEval = Malteval(malteval_jar=None, look_for_jar=False)
        maltEval.setJar(malteval_jar='MaltEval.jar',
            check_jar_correctness=False)
        self.setSampleFile(maltEval)
        cmd = maltEval.getCommand()
        properCmd = 'java -jar MaltEval.jar '\
                    '-g /tmp/me/gold.conll -s /tmp/me/test.conll'
        self.assertEqual(properCmd, cmd)

    #    TODO: Figure out right encoding
    def test_to_file(self):
        maltEval = Malteval(malteval_jar=None, look_for_jar=False)
        f = maltEval._toFile(self.dg, 'tst')
        self.assertNotEqual(f, None)
        self.assertNotEqual(os.stat(f.name)[ST_SIZE], 0)

    def test_create_gold_file(self):
        maltEval = Malteval(malteval_jar=None, look_for_jar=False)
        maltEval.createGoldFile(self.dg)
        self.assertTrue(os.path.exists(os.path.join(tempfile.gettempdir(),
            'gold_malteval')))

    def test_create_eval_file(self):
        maltEval = Malteval(malteval_jar=None, look_for_jar=False)
        maltEval.createEvalFile(self.dg)
        self.assertTrue(os.path.exists(os.path.join(
            tempfile.gettempdir(),
            'eval_malteval')))

    @unittest.skipIf(Malteval.canConfigureProperly() == False,
        "MaltEval.jar could not be found automatically. Set MALTEVALHOME ")
    def test_run_default_cmd(self):
        maltEval = Malteval()
        maltEval.createGoldFile(self.dg)
        maltEval.createEvalFile(self.dg)
        res = maltEval.execute()
        pratial_result = ['1             Row mean', '12            Row count']
        self.assertEquals(res.split("\n")[12:14], pratial_result)

    def testCmdWithEvalFile(self):
        maltEval = self.mockSetUp()
        maltEvalCmd = MaltevalXmlCommands()
        maltEval.setCommandFile(maltEvalCmd)
        location = maltEval.commandFilePath
        cmd = maltEval.getCommand()
        properCmd = 'java -jar MaltEval.jar '\
                    '-g /tmp/me/gold.conll -s /tmp/me/test.conll '\
                    '-e ' + location
        self.assertEqual(properCmd, cmd)

    def testDeleteCommandFile(self):
        maltEval = self.mockSetUp()
        maltEvalCmd = MaltevalXmlCommands()
        maltEval.setCommandFile(maltEvalCmd)
        maltEval.deleteCommandFile()
        cmd = maltEval.getCommand()
        self.assertEquals(len(cmd.split("-e")), 1)

    #TODO consider library for mocking
    def testUASlikeExceution(self):
        maltEval = self.mockSetUp()
        functype = type(Malteval.execute)
        maltEval.execute = functype(self.mockedExecute, maltEval, Malteval)
        self.assertEqual(maltEval.uas(), 0.885)

    def testLASlikeExceution(self):
        maltEval = self.mockSetUp()
        functype = type(Malteval.execute)
        maltEval.execute = functype(self.mockedExecute, maltEval, Malteval)
        self.assertEqual(maltEval.las(), 0.885)

if __name__ == '__main__':
    unittest.main()
