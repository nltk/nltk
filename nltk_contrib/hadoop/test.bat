@echo off
python wordcount_mapper.py < brown-ca01 | sort.exe | python wordcount_reducer.py > testresult
fc testresult testcase_wordcount_brown-ca01.txt | head
