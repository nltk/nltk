#!/usr/bin/env bash

cd `dirname $0`

# Download nltk python dependencies
pip install --upgrade -r pip-req.txt
pip install --upgrade matplotlib
pip install --upgrade https://github.com/PyCQA/pylint/archive/master.zip

# Download nltk data packages
python -c "import nltk; nltk.download('all')" || echo "NLTK data download failed: $?"

# Download external dependencies
pushd ${HOME}
[[ ! -d 'third' ]] && mkdir 'third'
pushd 'third'

# Download SENNA
senna_file_name=$(curl -s 'https://ronan.collobert.com/senna/download.html' | grep -o 'senna-v.*.tgz' | head -n1)
senna_folder_name='senna'
if [[ ! -d $senna_folder_name ]]; then
        wget -nv "https://ronan.collobert.com/senna/$senna_file_name"
        tar -xvzf ${senna_file_name}
        rm ${senna_file_name}
fi

# Setup the Environment variable
export SENNA=$(pwd)'/senna'

popd
popd

echo "---- CLASSPATH: ----"
echo $CLASSPATH
echo "---- MODELS: ----"
echo $STANFORD_MODELS
echo "---- Running tests ----"

# Coverage
rm -f coverage_scrubbed.xml
pytest --cov=nltk --cov-report xml nltk/test/
iconv -c -f utf-8 -t utf-8 coverage.xml > coverage_scrubbed.xml

# Create a default pylint configuration file.
touch ~/.pylintrc
pylint -f parseable nltk > pylintoutput

# Script always succeeds
true
