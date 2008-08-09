@echo off
python wordcount_mapper.py < brown-ca01 | sort.exe | python wordcount_reducer.py
