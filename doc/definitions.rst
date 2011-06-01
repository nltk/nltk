.. -*- mode: rst -*-

.. ifndef:: definitions

  .. def:: definitions

  .. |version| replace:: 2.0.1rc1
  .. |copyrightinfo| replace:: 2001-2011 the authors
  .. |license| replace:: Creative Commons Attribution-Noncommercial-No Derivative Works 3.0 United States License

  .. CAP abbreviations (map to small caps in LaTeX)
  
  .. |CFG| replace:: CFG
  .. |DRT| replace:: DRT
  .. |DRS| replace:: DRS
  .. |CoNLL| replace:: CoNLL
  .. |CYK| replace:: CYK
  .. |FOL| replace:: first-order logic
  .. |FSRL| replace:: FSRL
  .. |HTML| replace:: HTML
  .. |IDLE| replace:: IDLE
  .. |LF| replace:: LF
  .. |NE|  replace:: NE
  .. |NLP|  replace:: NLP
  .. |NLTK| replace:: NLTK
  .. |URL| replace:: URL
  .. |WFST| replace:: WFST
  .. |XML| replace:: XML
  
  .. Other candidates for global consistency
  
  .. |fol| replace:: first-order logic
  .. |Fol| replace:: First-order logic
  .. PTB removed since it must be indexed
  .. WN removed since it must be indexed
  .. |TRY| replace:: **Your Turn:**
  .. |IMPORTANT| replace:: **Important:**
  
  .. misc & punctuation
  .. cdots was unicode U+22EF but not working
  .. |dots| unicode:: U+2026 .. horizontal dots, ellipsis
  .. |copy| unicode:: 0xA9 .. copyright sign
  .. |dot| unicode:: U+2022 .. bullet
  .. |mdash| unicode:: U+02014 .. em dash (for between words)
  .. |ndash| unicode:: U+02013 .. en dash (for numeric ranges)
  .. |tilde| unicode:: U+007E
  
  .. exercise meta-tags
  
  .. |easy| unicode:: U+263C .. sun
  .. |soso| unicode:: U+25D1 .. "moon"
  .. |hard| unicode:: U+2605 .. black star
  .. |talk| unicode:: U+263A .. smiley face

  .. |blackstar| unicode:: U+2605
  .. |whitestar| unicode:: U+2606
  .. |blacksmiley| unicode:: U+263B
  .. |blackdiamond| unicode:: U+25C6

  .. Unicode tests
  .. |test0| unicode:: U+2690
  .. |test1| unicode:: U+2691
  .. |test2| unicode:: U+2692
  .. |test3| unicode:: U+2693
  .. |test4| unicode:: U+2694
  .. |test5| unicode:: U+2695
  .. |test6| unicode:: U+2696
  .. |test7| unicode:: U+2697
  .. |test8| unicode:: U+2698
  .. |test9| unicode:: U+2699
  .. |testa| unicode:: U+269A
  .. |testb| unicode:: U+269B
  .. |testc| unicode:: U+269C
  .. |testd| unicode:: U+269D
  .. |teste| unicode:: U+269E
  .. |testf| unicode:: U+269F
  
  .. phonetic
  .. |ae| unicode:: U+00E6 ..  small ae digraph
  .. |schwa| unicode:: U+0259 ..  schwa
  .. |eth| unicode:: U+00F0 ..  eth
  .. |length| unicode:: U+02D0 ..  length
  
  .. misc
  .. |aumlaut| unicode:: U+00E4 .. a umlaut
  .. |eacute| unicode:: U+00E9 .. e acute
  .. |eogonek| unicode:: U+1119 .. e ogonek
  .. |ncaron| unicode:: U+0148 .. n caron
  .. |ntilde| unicode:: U+00F1 .. n tilde
  .. |odacute| unicode:: U+0151 .. o double acute
  .. |oslash| unicode:: U+00F8 .. o slash
  .. |uumlaut| unicode:: U+00FC .. u umlaut
  .. |ecircumflex| unicode:: U+00EA .. e circumflex
  .. |space| unicode:: U+23E1 .. bottom tortoise shell bracket

  .. used in Unicode section
  .. |nacute| unicode:: U+0144 
  .. |oacute| unicode:: U+00f3
  .. |sacute| unicode:: U+015b
  .. |Sacute| unicode:: U+015a
  .. |aogonek| unicode:: U+0105
  .. |lstroke| unicode:: U+0142

  .. |CJK-4EBA| unicode:: U+4eba
  .. |CJK-4EE5| unicode:: U+4ee5
  .. |CJK-732B| unicode:: U+732b
  .. |CJK-751A| unicode:: U+751a
  .. |CJK-81F3| unicode:: U+81f3
  .. |CJK-8D35| unicode:: U+8d35
  
  .. arrows
  .. |DoubleRightArrow| unicode:: U+021D2 .. rightwards double arrow
  .. |rarr| unicode:: U+2192 .. right arrow
  .. |rdarr| unicode:: U+21D2 .. right double arrow
  .. |reduce| unicode:: U+219D .. curly right arrow
  .. |lrarr| unicode:: U+2194 .. left-right arrow
  .. |larr| unicode:: U+2190 .. left arrow
  
  
  .. unification stuff
  .. |SquareIntersectionX| unicode:: U+02293 .. square cap
  .. |SquareSubsetEqual| unicode:: U+02291 .. square image of or equal to
  .. |SquareSubset| unicode:: U+0228F .. square image of
  .. |SquareSupersetEqual| unicode:: U+02292 .. square original of or equal to
  .. |SquareSuperset| unicode:: U+02290 .. square original of
  .. |SquareUnion| unicode:: U+02294 .. square cup   

  .. Math & Logic
  .. |tf| replace:: {*True*, *False*}
  
  .. |exists| unicode:: U+2203 .. existential quantifier
  .. |forall| unicode:: U+2200 .. universal quantifier
  .. |geq| unicode:: U+2265 .. greater than or equal
  .. |iff| unicode:: U+2261 .. triple bars
  .. |langle| unicode:: U+02329 .. left angle-bracket
  .. |leq| unicode:: U+2264 .. less than or equals
  .. |l| unicode:: U+00AB .. left chevron
  .. |neg| unicode:: U+00AC .. negation symbol
  .. |rangle| unicode:: U+0232A .. right angle-bracket
  .. |r| unicode:: U+00BB .. right chevron
  .. |times| unicode:: U+00D7 .. multiplication
  .. |vee| unicode:: U+2228 .. or
  .. |wedge| unicode:: U+2227 .. and
  .. |prod| replace:: Prod
  .. |minus| unicode:: U+2212 .. minus
  
  .. sets
  .. |cup| unicode:: U+0222A .. union 
  .. |diff| unicode:: U+2212 .. set-theoretical complement
  .. |element| unicode:: U+2208 .. set-theoretical membership
  .. |empty| unicode:: U+2205 .. empty set
  .. |intersect| unicode:: U+2229 .. set-theoretical intersection
  .. |in| unicode:: U+2208 .. element of
  .. |mapsto| unicode:: U+2192 .. maps to
  .. |nelement| unicode:: U+2209 .. set-theoretical membership
  .. |pipe| unicode:: U+2223 .. vertical pipe
  .. |power| unicode:: U+2118 .. powerset
  .. |propsubset| unicode:: U+2282 .. proper subset
  .. |subset| unicode:: U+2286 .. subset
  .. |union| unicode:: U+222A .. set-theoretical union
  
  
  .. Greek
  .. |alpha| unicode:: U+03B1
  .. |beta| unicode:: U+03B2
  .. |gamma| unicode:: U+03B3
  .. |Gamma| unicode:: U+0393
  .. |kappaX| unicode:: U+03BA
  .. |kappa| replace:: K
  .. |lambda| unicode:: U+03BB
  .. |mu| unicode:: U+03BC 
  .. |pi| unicode:: U+03C0 
  .. |phi| unicode:: U+03C6
  .. |psi| unicode:: U+03C8
  .. |sigma| unicode:: U+03C3
  .. |tau| unicode:: U+03C4
  .. |rho| unicode:: U+03C1
  .. |Sigma| unicode:: U+03A3
  .. |sum| unicode:: U+03A3
  .. |Omega| unicode:: U+03A9
  
  .. Chinese
  .. |ai4| unicode:: U+7231 .. zh ai (love)
  .. |guo3| unicode:: U+56FD .. zh guo (country)
  .. |ren2| unicode:: U+4EBA .. zh ren (person)
  
  .. URLs
  .. |StevenBird| replace:: `Steven Bird <http://www.csse.unimelb.edu.au/~sb/>`__
  .. |EwanKlein| replace:: `Ewan Klein <http://www.ltg.ed.ac.uk/~ewan/>`__
  .. |EdwardLoper| replace:: `Edward Loper <http://www.cis.upenn.edu/~edloper/>`__
  .. |PYTHON-URL| replace:: ``http://python.org/``
  .. |PYTHON-DOCS| replace:: ``http://docs.python.org/``
  .. |NLTK-URL| replace:: ``http://www.nltk.org/``
  .. |NLTK-HOWTO-URL| replace:: ``http://www.nltk.org/howto``
  .. |OLAC-URL| replace:: ``http://www.language-archives.org/``
  
  .. Python example - a snippet of code in running text
  .. role:: py
     :class: python
  
  .. PlaceHolder example -  something that should be replaced by actual code
  .. role:: ph
     :class: placeholder
   
  .. Linguistic eXample - cited form in running text
  .. role:: lx
     :class: example
    
  .. Emphasized (more declarative than just using *)
  .. role:: em
     :class: emphasis
  
  .. Grammatical Category - e.g. NP and verb as technical terms
     .. role:: gc
        :class: category
    
  .. Math expression - e.g. especially for variables
  .. role:: math
     :class: math
  
  .. Textual Math expression - for words 'inside' a math environment
  .. role:: mathit
     :class: mathit
  
  .. Feature (or attribute)
  .. role:: feat
     :class: feature
  
  .. Raw LaTeX
  .. role:: raw-latex(raw)
     :format: latex
  
  .. Raw HTML
  .. role:: raw-html(raw)
     :format: html
  
  .. Feature-value
  .. role:: fval
     :class: fval
  
  .. Lexemes
  .. role:: lex
     :class: lex
  
  .. Replacements that rely on previous definitions :-)
  
  .. |nopar| replace:: :raw-latex:`{\noindent}`
  .. |seef| replace:: `see`:mathit:\ :sub:`f`
  .. |seeR| replace:: `see`:mathit:\ :sub:`R`
  .. |walkf| replace:: `walk`:mathit:\ :sub:`f`
  .. |walkR| replace:: `walk`:mathit:\ :sub:`R`
  

  .. |SquareIntersection| replace:: :raw-latex:`$\sqcap$`:raw-html:`&#8851;`
  
