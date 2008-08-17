#!/bin/sh

streamer="/usr/local/hadoop/contrib/streaming/hadoop-*-streaming.jar"
hadoop="/usr/local/hadoop/bin/hadoop"

$hadoop dfs -rmr wordcount-out
$hadoop jar $streamer -mapper wordcount_mapper.py -reducer wordcount_reducer.py -input wordcount-input  -output wordcount-out -file EM_mapper.py  -file EM_reducer.py 
