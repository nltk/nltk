#!/bin/bash
LOCODES_CSV='/nlptools/loc051cs/UNLOCODE_CodeList_2005-1.csv'
TEXTCAT='/nlptools/textcat/text_cat'
PRED_SAMPLE_SUFF='llp'
GLRESULTS='../results'
GLSTOPWORDS='../stop_words'
TESTNAME="$1"


if [ -e "${TESTNAME}" ]
then
	echo "nup. that test name exists already"
	exit
fi

STOPWORDS="${TESTNAME}.stop_words"
cp "${GLSTOPWORDS}" "${STOPWORDS}"

SWADLIST="${TESTNAME}.swad"
cp "$2" "${SWADLIST}"
EXP_COUNTRIES="$3"

if [ -n $5 ]
then
	OLDURLS=""
else
	OLDURLS=" -u $5"
fi

echo "test-name:${TESTNAME}" >> ${TESTNAME}
echo "stop-word list:${STOPWORDS}" >> ${TESTNAME}
echo "swadesh list:${SWADLIST}" >> ${TESTNAME}
echo "textcat expected output:${TEXTCAT_EXP}" >> ${TESTNAME}
echo "expected countries: " >> ${TESTNAME}
cat ${EXP_COUNTRIES} >> ${TESTNAME}
echo "#########################################################################################" >> ${TESTNAME}

../pull_out_stops.pl ${STOPWORDS} < ${SWADLIST} | ../do_search.py $4 | ../fetch_text.py -p ${TESTNAME} ${OLDURLS}  |\
	../loc_lookup.py -l ${LOCODES_CSV} -c ${EXP_COUNTRIES} -t ${TEXTCAT} -s ${PRED_SAMPLE_SUFF} >> ${TESTNAME}
