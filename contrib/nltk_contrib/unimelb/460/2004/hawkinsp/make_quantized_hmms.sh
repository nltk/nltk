#!/bin/sh

TRAINING_DATA="data/ti20-pwav/train"

if [ "$#" != 1 ] ; then
    echo "Usage: $0 <code book size>"
    exit 1
fi


for I in 00 01 02 03 04 05 06 07 08 09 en er go hp no rb rp sp st ys ; do
    echo $I
    rm -f q$1_$I.vec
    find $TRAINING_DATA -name $I*.wav | \
        xargs ./extract_mfcc.py -q code$1.txt >> q$1_$I.vec
done

java -classpath java/jahmm-0.2.6.jar:java/ QuantizedLearner $1 > q$1_data.py

