#!/bin/sh -x

TEMP=`mktemp -t dbinfo_out.XXXXXXXX`
OUTPUT="NLTK Wordnet Browser Database Info.html"

python dbinfo_html.py

links -dump "$OUTPUT" > $TEMP

diff -u test-dbinfo.output $TEMP

rm $TEMP
