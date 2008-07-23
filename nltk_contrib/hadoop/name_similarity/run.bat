@echo off
type male.txt | python name_mapper1.py | unixsort | cat | python swap_mapper.py | unixsort | python value_aggregater.py | python name_mapper2.py | unixsort | python similiar_name_reducer.py
