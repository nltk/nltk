LATEX = latex
PDF_LATEX = pdflatex
BIBTEX = bibtex8

DVIPS = dvips

usage:
	@echo "make pdf -- Build the manual from LaTex source"
	@echo "make ps -- Build the manual from LaTex source"
	@echo "make dvi -- Build the manual from LaTex source"
	@echo "make clean -- Remove all built files and temporary files"
	@echo "make clean_up -- Remove temporary files"

pdf: 
	${PDF_LATEX} manual.tex
	${PDF_LATEX} manual.tex
	${BIBTEX} manual
	${PDF_LATEX} manual.tex
	${PDF_LATEX} manual.tex

ps: dvi
	${DVIPS} manual.dvi

dvi:
	${LATEX} manual.tex
	${LATEX} manual.tex
	${BIBTEX} manual
	${LATEX} manual.tex
	${LATEX} manual.tex

clean: clean_up
	rm -f manual.pdf manual.ps manual.dvi

clean_up:
	rm -f manual.aux manual.bbl manual.blg manual.lof manual.log manual.pdfsync manual.toc
	
