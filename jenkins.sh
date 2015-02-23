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
stanford_parser_package_zip_name=$(curl -s 'http://nlp.stanford.edu/software/lex-parser.shtml' | grep -o 'stanford-parser-full-.*\.zip' | head -n1)
[[ ${stanford_parser_package_zip_name} =~ (.+)\.zip ]]
stanford_parser_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_parser_package_name} ]]; then
	wget -nv "http://nlp.stanford.edu/software/$stanford_parser_package_zip_name"
	unzip ${stanford_parser_package_zip_name}
	rm ${stanford_parser_package_zip_name}
	ln -s ${stanford_parser_package_name} 'stanford-parser'
fi

stanford_tagger_package_zip_name=$(curl -s 'http://nlp.stanford.edu/downloads/tagger.shtml' | grep -o 'stanford-postagger-full-.*\.zip' | head -n1)
[[ ${stanford_tagger_package_zip_name} =~ (.+)\.zip ]]
stanford_tagger_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_tagger_package_name} ]]; then
	wget -nv "http://nlp.stanford.edu/software/$stanford_tagger_package_zip_name"
	unzip ${stanford_tagger_package_zip_name}
	rm ${stanford_tagger_package_zip_name}
	ln -s ${stanford_tagger_package_name} 'stanford-postagger'
fi

# Download SENNA 
senna_file_name=$(curl -s 'http://ml.nec-labs.com/senna/download.html' | grep -o 'senna-v.*.tgz' | head -n1)
senna_folder_name='senna'
if [[ ! -d $senna_folder_name ]]; then
        wget -nv "http://ml.nec-labs.com/senna/$senna_file_name"
        tar -xvzf ${senna_file_name}
        rm ${senna_file_name}       
fi

# Download and Install Liblbfgs 
lbfgs_file_name=$(curl -s 'http://www.chokkan.org/software/liblbfgs/' | grep -o 'liblbfgs-.*\.tar.gz' | head -n1)
[[ ${lbfgs_file_name=} =~ (.+)\.tar.gz ]]
lbfgs_folder_name=${BASH_REMATCH[1]}
if [[ ! -d $lbfgs_folder_name ]]; then
        wget -nv "https://github.com/downloads/chokkan/liblbfgs/$lbfgs_file_name"
        tar -xvzf ${lbfgs_file_name}
        rm ${lbfgs_file_name}
fi
cd $lbfgs_folder_name
./configure --prefix=$HOME/third/liblbfgs
make
make install
cd ..

# Download and install crfsuite 
crfsuite_file_name=$(curl -s 'http://www.chokkan.org/software/crfsuite/' | grep -o 'crfsuite-.*\.tar.gz' | head -n1)
[[ ${crfsuite_file_name=} =~ (.+)\.tar.gz ]]
crfsuite_folder_name=${BASH_REMATCH[1]}
if [[ ! -d $crfsuite_folder_name ]]; then
        wget -nv "https://github.com/downloads/chokkan/crfsuite/$crfsuite_file_name"
        tar -xvzf ${crfsuite_file_name}
        rm ${crfsuite_file_name}
fi
cd $crfsuite_folder_name
./configure --prefix=$HOME/third/crfsuite --with-liblbfgs=$HOME/third/liblbfgs
make
make install
cd ..


# Setup the Enviroment variable 
export CRFSUITE=$(pwd)'/crfsuite/bin'
export STANFORD_PARSER=$(pwd)'/stanford-parser'
export STANFORD_MODELS=$(pwd)'/stanford-parser'
export STANFORD_POSTAGGER=$(pwd)'/stanford-postagger'
export SENNA=$(pwd)'/senna'

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
