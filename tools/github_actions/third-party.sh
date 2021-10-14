#!/bin/bash
# This install script is used in our GitHub Actions CI.
# See .github/workflows/ci.yaml

# Installing the third-party software and the appropriate env variables.
pushd ${HOME}
[[ ! -d 'third' ]] && mkdir 'third'
pushd 'third'

# Download nltk stanford dependencies
# Downloaded to ~/third/stanford-corenlp
# stanford_corenlp_package_zip_name=$(curl -s 'https://stanfordnlp.github.io/CoreNLP/' | grep -o 'stanford-corenlp-full-.*\.zip' | head -n1)
stanford_corenlp_package_zip_name="stanford-corenlp-full-2018-10-05.zip"
[[ ${stanford_corenlp_package_zip_name} =~ (.+)\.zip ]]
stanford_corenlp_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_corenlp_package_name} ]]; then
	curl -L "https://nlp.stanford.edu/software/$stanford_corenlp_package_zip_name" -o ${stanford_corenlp_package_zip_name}
	# wget -nv "https://nlp.stanford.edu/software/$stanford_corenlp_package_zip_name"
	unzip -q ${stanford_corenlp_package_zip_name}
	rm ${stanford_corenlp_package_zip_name}
	mv ${stanford_corenlp_package_name} 'stanford-corenlp'
fi


# Downloaded to ~/third/stanford-parser
#stanford_parser_package_zip_name=$(curl -s 'https://nlp.stanford.edu/software/lex-parser.shtml' | grep -o 'stanford-parser-full-.*\.zip' | head -n1)
stanford_parser_package_zip_name="stanford-parser-full-2018-10-17.zip"
[[ ${stanford_parser_package_zip_name} =~ (.+)\.zip ]]
stanford_parser_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_parser_package_name} ]]; then
	curl -L "https://nlp.stanford.edu/software/$stanford_parser_package_zip_name" -o ${stanford_parser_package_zip_name}
	# wget -nv "https://nlp.stanford.edu/software/$stanford_parser_package_zip_name"
	unzip -q ${stanford_parser_package_zip_name}
	rm ${stanford_parser_package_zip_name}
	mv ${stanford_parser_package_name} 'stanford-parser'
fi

# Downloaded to ~/third/stanford-postagger
#stanford_tagger_package_zip_name=$(curl -s 'https://nlp.stanford.edu/software/tagger.shtml' | grep -o 'stanford-postagger-full-.*\.zip' | head -n1)
stanford_tagger_package_zip_name="stanford-postagger-full-2018-10-16.zip"
[[ ${stanford_tagger_package_zip_name} =~ (.+)\.zip ]]
stanford_tagger_package_name=${BASH_REMATCH[1]}
if [[ ! -d ${stanford_tagger_package_name} ]]; then
	curl -L "https://nlp.stanford.edu/software/$stanford_tagger_package_zip_name" -o ${stanford_tagger_package_zip_name}
	# wget -nv "https://nlp.stanford.edu/software/$stanford_tagger_package_zip_name"
	unzip -q ${stanford_tagger_package_zip_name}
	rm ${stanford_tagger_package_zip_name}
	mv ${stanford_tagger_package_name} 'stanford-postagger'
fi

# Download SENNA to ~/third/senna
senna_file_name=$(curl -s 'https://ronan.collobert.com/senna/download.html' | grep -o 'senna-v.*.tgz' | head -n1)
senna_folder_name='senna'
if [[ ! -d $senna_folder_name ]]; then
	curl -L "https://ronan.collobert.com/senna/$senna_file_name" -o ${senna_file_name}
	# wget -nv "https://ronan.collobert.com/senna/$senna_file_name"
	tar -xzf ${senna_file_name}
	rm ${senna_file_name}
fi

# Download PROVER9 to ~/third/prover9
prover9_file_name="p9m4-v05.tar.gz"
[[ ${prover9_file_name} =~ (.+)\.tar\.gz ]]
prover9_folder_name=${BASH_REMATCH[1]}
if [[ ! -d ${prover9_folder_name} ]]; then
	curl -L "https://www.cs.unm.edu/~mccune/prover9/gui/$prover9_file_name" -o ${prover9_file_name}
	tar -xzf ${prover9_file_name}
	mv ${prover9_folder_name} 'prover9'
	rm ${prover9_file_name}
fi

# Download MEGAM to ~/third/megam
megam_file_name="megam_i686.opt.gz"
[[ ${megam_file_name} =~ (.+)\.gz ]]
megam_folder_name=${BASH_REMATCH[1]}
if [[ ! -d ${megam_folder_name} ]]; then
	curl -L "http://hal3.name/megam/$megam_file_name" -o ${megam_file_name}
	gunzip -vf ${megam_file_name}
	mkdir -p "megam"
	mv ${megam_folder_name} "megam/${megam_folder_name}"
	chmod -R 711 "megam/$megam_folder_name"
fi

# TADM requires `libtaopetsc.so` from PETSc v2.3.3, and likely has more
# tricky to install requirements, so we don't run tests for it.

# Download TADM to ~/third/tadm
# tadm_file_name="tadm-0.9.8.tgz"
# [[ ${tadm_file_name} =~ (.+)\.tgz ]]
# tadm_folder_name=${BASH_REMATCH[1]}
# if [[ ! -d ${tadm_folder_name} ]]; then
# 	curl -L "https://master.dl.sourceforge.net/project/tadm/tadm/tadm%200.9.8/$tadm_file_name?viasf=1" -o ${tadm_file_name}
# 	tar -xvzf ${tadm_file_name}
# 	rm ${tadm_file_name}
#	chmod -R 711 "./tadm/bin/tadm"
# fi

# Download MaltParser to ~/third/maltparser
malt_file_name="maltparser-1.9.2.tar.gz"
[[ ${malt_file_name} =~ (.+)\.tar\.gz ]]
malt_folder_name=${BASH_REMATCH[1]}
if [[ ! -d ${malt_folder_name} ]]; then
	curl -L "http://maltparser.org/dist/$malt_file_name" -o ${malt_file_name}
	tar -xzf ${malt_file_name}
	mv ${malt_folder_name} 'maltparser'
	rm ${malt_file_name}
fi

ls ~/third

popd
popd
