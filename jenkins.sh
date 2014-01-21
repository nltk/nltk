#! /bin/sh

cd `dirname $0`

#download nltk data packages
python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"

#download nltk python dependencies
pip install -r pip-req.txt

#download external dependencies
[[ ! -d 'third' ]] && mkdir 'third'
pushd 'third'

#download nltk stanford dependencies
stanford_parser_package=$(curl 'http://nlp.stanford.edu/software/lex-parser.shtml' | grep -o 'stanford-parser-full-.*\.zip' | head -n1)
wget "http://nlp.stanford.edu/software/$stanford_parser_package"
unzip "$stanford_parser_package"
mv $(echo "$stanford_parser_package" | egrep -o 'stanford-parser-full-[0-9]+-[0-9]+-[0-9]+') 'stanford-parser'

stanford_tagger_package=$(curl 'http://nlp.stanford.edu/downloads/tagger.shtml' | grep -o 'stanford-postagger-.*\.zip' | head -n1)
wget "http://nlp.stanford.edu/downloads/$stanford_tagger_package"
unzip "$stanford_tagger_package"
mv $(echo "$stanford_tagger_package" | egrep -o 'stanford-postagger-[0-9]+-[0-9]+-[0-9]+') 'stanford-postagger'

popd

#coverage
coverage erase
coverage run --source=nltk nltk/test/runtests.py --with-xunit
coverage xml --omit=nltk/test/*
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml
pylint -f parseable nltk > pylintoutput
true   # script always succeeds
