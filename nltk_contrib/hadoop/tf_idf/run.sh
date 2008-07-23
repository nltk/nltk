#!/bin/sh
export LC_ALL=C

cat filelist.txt | ./tf_map.py | sort | ./tf_reduce.py > tf_out.txt

cat tf_out.txt | ./idf_map.py |  sort | ./idf_reduce.py > idf_out.txt

cat tf_out.txt idf_out.txt | ./tfidf_map1.py|  sort | ./tfidf_reduce1.py | sort | ./tfidf_map2.py 
