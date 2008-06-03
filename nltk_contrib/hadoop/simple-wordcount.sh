#!/bin/sh
# Usage: sh simple-wordcount.sh <CORPUSDIR>
#
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python
#
sh runStreaming.sh m_wordcount.py r_wordcount.py $1 counts compute-counts


