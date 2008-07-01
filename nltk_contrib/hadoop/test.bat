@echo off
python wordCountMapper.py < brown-ca01 | sort.exe | python wordCountReducer.py > testresult
fc testresult testcase-brown-ca01 | head
