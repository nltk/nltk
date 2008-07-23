#!/bin/sh

streamer="/usr/local/hadoop/contrib/streaming/hadoop-*-streaming.jar"
hadoop="/usr/local/hadoop/bin/hadoop"

$hadoop dfs -rmr tf_out
$hadoop jar $streamer -mapper tf_map.py  -reducer tf_reduce.py  -input filelist -output tf_out -file tf_map.py -file tf_reduce.py -file ../../../data/corpora/gutenberg/austen-emma.txt -file ../../../data/corpora/gutenberg/austen-persuasion.txt -file ../../../data/corpora/gutenberg/austen-sense.txt

$hadoop dfs -rmr idf_out
$hadoop jar $streamer -mapper idf_map.py -reducer idf_reduce.py -input tf_out  -output idf_out -file idf_map.py -file idf_reduce.py 

$hadoop dfs -rmr tf_idf
$hadoop jar $streamer -mapper tfidf_map1.py -reducer tfidf_reduce1.py -input tf_out -input idf_out -output tf_idf -file tfidf_map1.py -file tfidf_reduce1.py

$hadoop dfs -rmr tf_idf_final
$hadoop jar $streamer -mapper tfidf_map2.py -reducer /bin/cat -input tf_idf -output tf_idf_final -file tfidf_map2.py -file tfidf_reduce1.py
