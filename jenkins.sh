#!/usr/bin/bash

cd `dirname $0`

#download nltk data packages
python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"

#download nltk python dependencies
pip install --upgrade -r pip-req.txt --allow-external matplotlib --allow-unverified matplotlib

#download external dependencies
pushd ${HOME}
[[ ! -d 'third' ]] && mkdir 'third'
pushd 'third'

#download nltk stanford dependencies
stanford_parser_package_zip_name=$(curl 'http://nlp.stanford.edu/software/lex-parser.shtml' | grep -o 'stanford-parser-full-.*\.zip' | head -n1)
[[ ${stanford_parser_package_zip_name} =~ (.+)\.zip ]]
stanford_parser_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_parser_package_name} ]]; then
	wget -nv "http://nlp.stanford.edu/software/$stanford_parser_package_zip_name"
	unzip ${stanford_parser_package_zip_name}
	rm ${stanford_parser_package_name}
	ln -s ${stanford_parser_package_name} 'stanford-parser'
fi

stanford_tagger_package_zip_name=$(curl 'http://nlp.stanford.edu/downloads/tagger.shtml' | grep -o 'stanford-postagger-full-.*\.zip' | head -n1)
[[ ${stanford_tagger_package_zip_name} =~ (.+)\.zip ]]
stanford_tagger_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_tagger_package_name} ]]; then
	wget -nv "http://nlp.stanford.edu/software/$stanford_tagger_package_zip_name"
	unzip ${stanford_tagger_package_zip_name}
	rm ${stanford_tagger_package_name}
	ln -s ${stanford_tagger_package_name} 'stanford-postagger'
fi

popd
popd

#coverage
coverage erase
coverage run --source=nltk nltk/test/runtests.py --with-xunit
coverage xml --omit=nltk/test/*
iconv -c -f utf-8 -t utf-8 nosetests.xml > nosetests_scrubbed.xml
pylint -f parseable nltk > pylintoutput

#script always succeeds
true
