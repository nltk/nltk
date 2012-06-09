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


class MaltevalRuntimeException(RuntimeError):
    def __init__(self, value):
        RuntimeError.__init__(self, value)


class Malteval(object):
    def __init__(self, maltevalJar=None, lookForJar=True):
        """
        An interface for malteval an evaluation tool for dependency parsers.

        :param maltevalJar: The full path to the malteval.jar. If not
         provided, the constructor will try to guess location of Malteval.jar.
         It will look at variable MALTEVALHOME. If this fails it will look at
         other typical places (/usr/lib etc). If no binary is found, it will
         raise a ``LookupError`` exception
        :type maltevalJar: str
        :param maltevalJar: Indicator whether to look for jar. If
         maltevalJar is true constructor will look for jar. Otherwise
         it will take whatever was passed as maltevalJar as jar location
         (without checking correctness)
         :type: boolean
        """

        if(lookForJar):
            self.configMalteval(maltevalJar)
        else:
            self._maltevalBin = maltevalJar
        self.visual = False
        self.commandFilePath = None
        self.goldFile = None
        self.evalFile = None
        self.verbose = True

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
        maltevalBinPath = reduce(add, map(glob.glob, _malteval_path))

        # Find the malteval binary.
        self._maltevalBin = find_binary('malteval.jar', bin,
            searchpath=maltevalBinPath, env_vars=['MALTEVALHOME'],
            url='http://w3.msi.vxu.se/~jni/malteval/',
            verbose=verbose)

    def setGoldFile(self, goldFile):
        '''
        This method will set gold  file and will not check if this file exists.
        Gold file is one which sets standards for evaluation. It should be in
        conll format
        :param goldFile: absolute path to gold file
        :type : str
        '''
        self.goldFile = os.path.abspath(goldFile)

    def setEvalFile(self, evalFile):
        '''
        This method will set evaluation file and will
        not check if this file exists. Evaluation file is
        checked against gold file. It should be in
        conll format
        :param evalFile: absolute path to evalFile
        :type : str
        '''
        self.evalFile = os.path.abspath(evalFile)

    def setJar(self, maltevalJar=None, checkJarCorrectness=False):
        '''
        method for changing location of malteval jar.
        :param maltevalJar: absolute path to malteval jar.
        :type: str
        :param checkJarCorrectness: Indicator
        whether to check jar location correctness.
        If False correctness will not be checked
        :type:bool
        '''
        if (checkJarCorrectness):
            self.configMalteval(maltevalJar)
        else:
            self._maltevalBin = maltevalJar

    def _toFile(self, depgraphs, suffix):
        '''
        saving dependency graphs to file
        :param depgraphs: list of ``DependencyGraph``
         objects for training input data
        '''
        inputFile = os.path.join(tempfile.gettempdir(), suffix)
        with open(inputFile, "w") as conllFile:
            conllFile.write('\n'.join([dg.to_conll(10) for dg in depgraphs]))
            return conllFile

    def createGoldFile(self, depgraphs):
        '''
        create gold file from dependency graphs
        :param depgraphs: list of ``DependencyGraph``
        objects for training input data
        '''
        self.setGoldFile(self._toFile(depgraphs, 'goldMalteval').name)

    def createEvalFile(self, depgraphs):
        '''
        create eval file from dependency graphs
        :param depgraphs: list of ``DependencyGraph``
        objects for training input data
        '''
        self.setEvalFile(self._toFile(depgraphs, 'evalMalteval').name)

    def getCommand(self):
        '''
        returns command as string based on set options.
        '''
        if not self.goldFile:
            raise AttributeError("goldFile not set")
        if not self.evalFile:
            raise AttributeError("evalFile not set")
        if not self._maltevalBin:
            raise AttributeError("malt eval bin not configured properly")
        cmd = ['java', '-jar',
               '%s' % self._maltevalBin]
        if self.commandFilePath:
            cmd.append('-e')
            cmd.append('%s' % self.commandFilePath)
        if self.visual:
            cmd.append('-v')
            cmd.append('1')
        cmd += ['-g', '%s' % self.goldFile, '-s', '%s' % self.evalFile]

        self._cmd = cmd
        return ' '.join(cmd)

    def execute(self):
        """
        This method will execute with command starting maltevla binary
        with so far provided parameters. This method may raise
        MaltevalRuntimeException if maltevla bin throws exception.This
        method returns string representing MalteEval output.
        """
        self.getCommand()
        p = subprocess.Popen(self._cmd, shell=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        com, error = p.communicate()
        if self.verbose and error:
            raise MaltevalRuntimeException(error)
        return com

    def setCommand(self, maltevlaCmd):
        """
        Set file with commands for malteval. File is created from
        object representing malteval command.
        :param maltevlaCmd: object representing malteval command xml file
        :type maltevlaCmd: MaltevalXmlCommands
        """
        self.maltevlaCmd = maltevlaCmd
        self.commandFilePath = os.path.join(tempfile.gettempdir(),
            "MaltevalCommandF.xml")
        with open(self.commandFilePath, "w") as cmdFile:
            cmdFile.write(maltevlaCmd.toprettyxml())

    def deleteCommandFile(self):
        self.maltevlaCmd = None
        self.commandFilePath = None

    def setVisual(self, visual):
        """
        This method will turn on visual mode
        in Malteval.jar. In visual mode commands from
        xml file are not executed
        """
        self.visual = visual

    def tryParse(self, maltevalOut):
        """
        This method will try to get metrics aut form result of malteval.
        This method may fail or give inaccurate results so don't use it unless
        you know what your doing.
        """
        return float(maltevalOut.split("\n")[11].split()[0])

    def _singleSimpleMetric(self, metricName):
        maltevalCommands = MaltevalXmlCommands()
        maltevalCommands.addMetric(metricName)
        self.setCommand(maltevalCommands)
        return self.tryParse(self.execute())

    def uas(self):
        """
        Returns UAS measure on eval fil.e
        """
        return self._singleSimpleMetric(MaltevalMetric.UAS)

    def las(self):
        """
        Returns LAS measure on eval fil.e
        """
        return self._singleSimpleMetric(MaltevalMetric.LAS)
