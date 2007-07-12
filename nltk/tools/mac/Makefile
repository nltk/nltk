PM = /Developer/Tools/packagemaker

pkg:
	./buildroots $(VER)
	$(PM) -build -proj ./Corpus_installer/nltk_corpora.pmproj -p ./pkgs/nltk_corpora.pkg
	$(PM) -build -proj ./NLTKLibrary_installer/NLTKLibrary.pmproj -p ./pkgs/NLTKLibrary.pkg
	$(PM) -build -proj ./NLTK.pmproj -p ../../../dist/nltk-$(VER).mpkg
