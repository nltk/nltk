PIX = chart_bottom_up.dot chart_bu_init.dot chart_bu_predict1.dot chart_bu_predict2.dot chart_fr1.dot chart_fr2.dot chart_intro_2edges.dot chart_intro_3edges.dot chart_intro_dottededge.dot chart_intro_empty.dot chart_intro_incomplete.dot chart_intro_parseedge.dot chart_intro_prodedge.dot chart_intro_selfloop.dot chart_td_expand1.dot chart_td_expand2.dot chart_td_init.dot chart_td_match1.dot chart_td_match2.dot chart_top_down.dot chart_useless_edge.dot          

PNG := $(PIX:.dot=.png)

.SUFFIXES: .dot .png

png: $(PNG) 

clean: 
	rm -f $(PNG)

.dot.png:
	dot -Tpng $< > $@
