# Natural Language Toolkit: Spearman Rank Correlation
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Kacper Chwialkowski <kacper.chwialkowski@gmail.com>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
"""
An interface for MaltEval an evaluation tool for dependency parsers.
See more at http://w3.msi.vxu.se/~jni/malteval/
"""
# coding: utf-8

import glob
from operator import add
from nltk.internals import find_binary
import os
import subprocess
import tempfile
from nltk.metrics.maltevalconstans import MaltevalMetric
from nltk.metrics.maltevalxmlcommadns import MaltevalXmlCommands


class Malteval(object):
    def __init__(self, malteval_jar=None, look_for_jar=True):
        """
        An interface for MaltEval an evaluation tool for dependency parsers.

        :param malteval_jar: The full path to the malteval.jar. If not
         provided, the constructor will try to guess location of Malteval.jar.
         It will look at variable MALTEVALHOME. If this fails it will look at
         other typical places (/usr/lib etc). If no binary is found, it will
         raise a ``LookupError`` exception
        :type malteval_jar: str
        :param malteval_jar: Indicator whether to look for jar. If
         malteval_jar is true constructor will look for jar. Otherwise
         it will take whatever was passed as malteval_jar as jar location
         (without checking correctness)
         :type: boolean
        """

        if(look_for_jar):
            self.configMalteval(malteval_jar)
        else:
            self._malteval_bin = malteval_jar
        self.visual = False
        self.commandFilePath = None
        self.goldFile = None
        self.evalFile = None


    @staticmethod
    def canConfigureProperly():
        try:
            Malteval()
        except LookupError:
            return False
        return True

    def configMalteval(self, bin=None, verbose=False):
        """
        Configure NLTK's interface to the ``malteval`` package.  This
        searches for a directory containing the malteval.jar

        :param bin: The full path to the ``malteval`` binary.  If not
            specified, then nltk will search the system for a ``malteval``
            binary; and if one is not found, it will raise a
            ``LookupError`` exception.
        :type bin: str
        """
        # A list of directories that should be searched for the malteval
        # executables.  This list is used by ``config_malteval``
        # when searching for the malteval executables.
        _malteval_path = ['.',
                          '/usr/lib/malteval-1*',
                          '/usr/share/malteval-1*',
                          '/usr/local/bin',
                          '/usr/local/malteval-1*',
                          '/usr/local/bin/malteval-1*',
                          '/usr/local/malteval-1*',
                          '/usr/local/share/malteval-1*']

        # Expand wildcards in _malteval_path:
        malteval_path = reduce(add, map(glob.glob, _malteval_path))

        # Find the malteval binary.
        self._malteval_bin = find_binary('malteval.jar', bin,
            searchpath=malteval_path, env_vars=['MALTEVALHOME'],
            url='http://w3.msi.vxu.se/~jni/malteval/',
            verbose=verbose)

    def setGoldFile(self, gold_file):
        '''
        This method will set gold  file and will not check if this file exists.
        Gold file is one which sets standards for evaluation. It should be in
        conll format
        :param gold_file: absolute path to gold file
        :type : str
        '''
        self.goldFile = gold_file

    def setEvalFile(self, eval_file):
        '''
        This method will set evaluation file and will
        not check if this file exists. Evaluation file is
        checked against gold file. It should be in
        conll format
        :param eval_file: absolute path to eval_file
        :type : str
        '''
        self.evalFile = eval_file

    def setJar(self, malteval_jar=None, check_jar_correctness=False):
        '''
        method for changing location of malteval jar.
        :param malteval_jar: absolute path to malteval jar.
        :type: str
        :param check_jar_correctness: Indicator
        whether to check jar location correctness.
        If False correctness will not be checked
        :type:bool
        '''
        if (check_jar_correctness):
            self.configMalteval(malteval_jar)
        else:
            self._malteval_bin = malteval_jar

    def _toFile(self, depgraphs, suffix):
        '''
        saving dependency graphs to file
        :param depgraphs: list of ``DependencyGraph``
         objects for training input data
        '''
        input_file = os.path.join(tempfile.gettempdir(), suffix)
        with open(input_file, "w") as conll_file:
            conll_file.write('\n'.join([dg.to_conll(10) for dg in depgraphs]))
            return conll_file

    def createGoldFile(self, depgraphs):
        '''
        create gold file from dependency graphs
        :param depgraphs: list of ``DependencyGraph``
        objects for training input data
        '''
        self.setGoldFile(self._toFile(depgraphs, 'gold_malteval').name)

    def createEvalFile(self, depgraphs):
        '''
        create eval file from dependency graphs
        :param depgraphs: list of ``DependencyGraph``
        objects for training input data
        '''
        self.setEvalFile(self._toFile(depgraphs, 'eval_malteval').name)

    def getCommand(self):
        '''
        returns command as string based on set options.
        '''
        if not self.goldFile:
            raise AttributeError("goldFile not set")
        if not self.evalFile:
            raise AttributeError("evalFile not set")
        if not self._malteval_bin:
            raise AttributeError("malt eval bin not configured properly")
        cmd = ['java', '-jar',
               '%s' % self._malteval_bin,
               '-g', '%s' % self.goldFile,
               '-s', '%s' % self.evalFile]
        if self.commandFilePath:
            cmd.append('-e')
            cmd.append('%s' % self.commandFilePath)
        if self.visual:
            cmd.append('-v')
            cmd.append('1')
        self._cmd = cmd
        return ' '.join(cmd)

    def execute(self):
        self.getCommand()
        p = subprocess.Popen(self._cmd, shell=False, stdout=subprocess.PIPE)
        com = p.communicate()
        return com[0]

    def setCommandFile(self, maltEvalCmd):
        """
        Set file with commands for MaltEval. File is created from
        object representing MaltEval command.
        :param maltEvalCmd: object representing MaltEval command xml file
        :type maltEvalCmd: MaltevalXmlCommands
        """
        self.maltEvalCmd = maltEvalCmd
        self.commandFilePath = os.path.join(tempfile.gettempdir(),
            "MaltevalCommandF.xml")
        with open(self.commandFilePath, "w") as cmdFile:
            cmdFile.write(maltEvalCmd.toprettyxml())

    def deleteCommandFile(self):
        self.maltEvalCmd = None
        self.commandFilePath = None


    def setVisual(self, visual):
        self.visual = visual

    def tryParse(self, maltevalOut):
        return float(maltevalOut.split("\n")[12].split()[0])

    def singleSimpleMetric(self, metricName):
        maltevalCommands = MaltevalXmlCommands()
        maltevalCommands.addMetric(metricName)
        self.setCommandFile(maltevalCommands)
        return self.tryParse(self.execute())


    def uas(self):
        return self.singleSimpleMetric(MaltevalMetric.UAS)


    def las(self):
        return self.singleSimpleMetric(MaltevalMetric.LAS)



