#!/bin/bash

# $0 = script path
# $1 = package path
# $2 = default location
# $3 = target volume

TMP=/tmp/nltk-installer/
cd $TMP

MINPYVERMAJOR=2
MINPYVERMINOR=4
PYVER=`python -V 2>&1 | sed 's/Python \([0-9]\.[0-9]\).*/\1/'`
PYMAJOR=`echo $PYVER | sed 's/\([0-9]\)\.\([0-9]\)/\1/'`
PYMINOR=`echo $PYVER | sed 's/\([0-9]\)\.\([0-9]\)/\2/'`

#   if [[ ( "$PYMAJOR" -ge  "$MINPYVERMAJOR"  ) \  permits Python 3

if [[ ( "$PYMAJOR" -eq  "$MINPYVERMAJOR" && "$PYMINOR" -ge  "$MINPYVERMINOR" ) ]]
then 
  /usr/bin/sudo python ./setup.py install
else
  exit -1
fi

# Clean up after ourselves by deleting /tmp/nltk-installer?
# rm -rf $TMP

export NLTK_DATA=/usr/share/nltk
echo export NLTK_DATA=/usr/share/nltk >> /private/etc/bashrc
