all: ps pdf
pdf: exercises-002.pdf exercises-001.pdf
ps: exercises-002.ps exercises-001.ps
dvi:
clean:
	rm -f *.eps *.log *.aux *.dvi *.ps *.toc *.pdf

# General rules
%.dvi: %.tex
	latex $<
	latex $<

%.ps: %.dvi
	dvips -t letter -o $@ $<

%.eps: %.dot
	dot -Tps -o $@ $<

%.eps: %.obj
	tgif -print -eps $<

%.pdf: %.ps
	ps2pdf $< $@

