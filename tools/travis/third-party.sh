#!/bin/bash
# This install script is used by the "install" step defined in travis.yml
# See https://docs.travis-ci.com/user/installing-dependencies/

# Installing the third-party software and the appropriate env variables.
pushd ${HOME}
[[ ! -d 'third' ]] && mkdir 'third'
pushd 'third'

# Download nltk stanford dependencies
#stanford_corenlp_package_zip_name=$(curl -s 'https://stanfordnlp.github.io/CoreNLP/' | grep -o 'stanford-corenlp-full-.*\.zip' | head -n1)
stanford_corenlp_package_zip_name="stanford-corenlp-full-2017-06-09.zip"
[[ ${stanford_corenlp_package_zip_name} =~ (.+)\.zip ]]
stanford_corenlp_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_corenlp_package_name} ]]; then
	wget -nv "http://nlp.stanford.edu/software/$stanford_corenlp_package_zip_name"
	unzip ${stanford_corenlp_package_zip_name}
	rm ${stanford_corenlp_package_zip_name}
	ln -sf ${stanford_corenlp_package_name} 'stanford-corenlp'
fi


#stanford_parser_package_zip_name=$(curl -s 'https://nlp.stanford.edu/software/lex-parser.shtml' | grep -o 'stanford-parser-full-.*\.zip' | head -n1)
stanford_parser_package_zip_name="stanford-parser-full-2017-06-09.zip"
[[ ${stanford_parser_package_zip_name} =~ (.+)\.zip ]]
stanford_parser_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_parser_package_name} ]]; then
	wget -nv "https://nlp.stanford.edu/software/$stanford_parser_package_zip_name"
	unzip ${stanford_parser_package_zip_name}
	rm ${stanford_parser_package_zip_name}
	ln -sf ${stanford_parser_package_name} 'stanford-parser'
fi

#stanford_tagger_package_zip_name=$(curl -s 'https://nlp.stanford.edu/software/tagger.shtml' | grep -o 'stanford-postagger-full-.*\.zip' | head -n1)
stanford_tagger_package_zip_name="stanford-postagger-full-2017-06-09.zip"
[[ ${stanford_tagger_package_zip_name} =~ (.+)\.zip ]]
stanford_tagger_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_tagger_package_name} ]]; then
	wget -nv "https://nlp.stanford.edu/software/$stanford_tagger_package_zip_name"
	unzip ${stanford_tagger_package_zip_name}
	rm ${stanford_tagger_package_zip_name}
	ln -sf ${stanford_tagger_package_name} 'stanford-postagger'
fi

# Download SENNA
senna_file_name=$(curl -s 'https://ronan.collobert.com/senna/download.html' | grep -o 'senna-v.*.tgz' | head -n1)
senna_folder_name='senna'
if [[ ! -d $senna_folder_name ]]; then
        wget -nv "https://ronan.collobert.com/senna/$senna_file_name"
        tar -xvzf ${senna_file_name}
        rm ${senna_file_name}
fi

# Setup the Enviroment variable
export CLASSPATH=$(pwd)"/${stanford_corenlp_package_name}"
export CLASSPATH=${CLASSPATH}:$(pwd)"/${stanford_parser_package_name}"
export CLASSPATH=${CLASSPATH}:$(pwd)"/${stanford_tagger_package_name}"
export STANFORD_CORENLP=$(pwd)'/stanford-corenlp'
export STANFORD_PARSER=$(pwd)'/stanford-parser'
export STANFORD_MODELS=$(pwd)'/stanford-postagger/models'
export STANFORD_POSTAGGER=$(pwd)'/stanford-postagger'
export SENNA=$(pwd)'/senna'

popd
popd

echo "---- CLASSPATH: ----"
echo $CLASSPATH
echo "---- MODELS: ----"
echo $STANFORD_MODELS
