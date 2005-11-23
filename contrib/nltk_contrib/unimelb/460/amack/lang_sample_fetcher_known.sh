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
TEXTCAT_EXP="$3"
EXP_COUNTRIES="$4"

echo "test-name:${TESTNAME}" >> ${TESTNAME}
echo "stop-word list:${STOPWORDS}" >> ${TESTNAME}
echo "swadesh list:${SWADLIST}" >> ${TESTNAME}
echo "textcat expected output:${TEXTCAT_EXP}" >> ${TESTNAME}
echo "expected countries: " >> ${TESTNAME}
cat ${EXP_COUNTRIES} >> ${TESTNAME}
echo "#########################################################################################" >> ${TESTNAME}

../pull_out_stops.pl ${STOPWORDS} < ${SWADLIST} | ../do_search.pl | ../fetch_text.py -p ${TESTNAME}  |\
	../loc_lookup_known.py -l ${LOCODES_CSV} -c ${EXP_COUNTRIES} -t ${TEXTCAT} -e ${TEXTCAT_EXP} -s ${PRED_SAMPLE_SUFF} >> ${TESTNAME}
