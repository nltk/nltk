#!/bin/sh

data="this restaurant serves pizza\n"
file="TESTRESULT1"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this restaurant serves spicy pizza and small noodles\n"
file="TESTRESULT2"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this restaurant serves large spicy pizza and small noodles\n"
file="TESTRESULT3"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this restaurant and chinabar serve pizza and noodles\n"
file="TESTRESULT4"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="how_much does a pizza cost\n"
file="TESTRESULT5"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="does this restaurant serve large pizza\n"
file="TESTRESULT6"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="does this chinese restaurant serve large pizza\n"
file="TESTRESULT7"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="I believe this restaurant serves pizza\n"
file="TESTRESULT8"
echo $data | python semanticProcessor.py grammar.cfg > $file
echo $data
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this chinese restaurant does not serve large pizza\n"
file="TESTRESULT7"
echo $data
echo $data | python semanticProcessor.py grammar.cfg > $file
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this chinese restaurant does not serve large pizza and small sushi\n"
file="TESTRESULT7"
echo $data
echo $data | python semanticProcessor.py grammar.cfg > $file
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="this chinese restaurant serves large pizza and small sushi and noodles and spicy soup\n"
file="TESTRESULT7"
echo $data
echo $data | python semanticProcessor.py grammar.cfg > $file
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1

echo "\n"
data="a pizza costs five  dollars\n"
file="TESTRESULT7"
echo $data
echo $data | python semanticProcessor.py grammar.cfg > $file
file_length=`wc -l $file | cut -c1-8`
#echo $file_length
file_length=`expr $file_length + 0`
#file_length=`expr $file_length  1`
result1=`head -$file_length $file | tail -2`
echo "\n"
echo $result1
