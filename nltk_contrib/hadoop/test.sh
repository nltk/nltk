#!/bin/sh

cat brown-ca01 | ./wordTagCountMapper.py | sort | ./summer.py
