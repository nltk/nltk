#!/bin/sh

TRAINING_DATA="data/ti20-pwav/train"


for I in 00 01 02 03 04 05 06 07 08 09 en er go hp no rb rp sp st ys ; do
    echo $I
    rm -f q_$I.vec
    find $TRAINING_DATA -name $I*.wav | \
        xargs ./extract_mfcc.py >> q_$I.vec
done

java -classpath java/jahmm-0.2.6.jar:java/ ContinuousLearner > continuous_data.py

