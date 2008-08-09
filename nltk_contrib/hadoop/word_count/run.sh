#!/bin/sh

export LC_ALL=C
cat brown-ca01 | ./wordcount_mapper.py | sort | ./wordcount_reducer.py

