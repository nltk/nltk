#!/bin/sh

cat brown-ca01 | ./wordcount_mapper.py | sort | ./wordcount_reducer.py
