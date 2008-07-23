#!/bin/sh

export LC_ALL=C

cat male.txt | ./name_mapper1.py |sort | /bin/cat | ./swap_mapper.py | sort | ./value_aggregater.py | ./name_mapper2.py | sort | ./similiar_name_reducer.py
