@echo off

cat filelist.txt | python tf_map.py | python sort.py | python tf_reduce.py > ntcir_gb_tf_out.txt

cat ntcir_gb_tf_out.txt | python idf_map.py |  python sort.py | python idf_reduce.py > ntcir_gb_idf_out.txt

cat ntcir_gb_tf_out.txt ntcir_gb_idf_out.txt | python tfidf_map1.py|  python sort.py | python tfidf_reduce1.py | python tfidf_map2.py 
