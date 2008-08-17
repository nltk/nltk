#!/bin/sh

streamer="/usr/local/hadoop/contrib/streaming/hadoop-*-streaming.jar"
hadoop="/usr/local/hadoop/bin/hadoop"

$hadoop dfs -rmr EM-out
$hadoop jar $streamer -mapper EM_mapper.py -reducer EM_reducer.py -input EM-input  -output EM-out -file EM_mapper.py  -file EM_reducer.py -file hmm_parameter
