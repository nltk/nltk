\+DatabaseType Frisian Text
\ver 5.0
\desc Frisian Interlinear Text for Tutorial
\+mkrset 
\lngDefault Default
\mkrRecord id

\+mkr f
\nam Free Translation
\lng Default
\mkrOverThis id
\-mkr

\+mkr g
\nam Gloss
\lng Default
\mkrOverThis id
\-mkr

\+mkr id
\nam Identifier
\lng Default
\-mkr

\+mkr m
\nam Morphemes
\lng Default
\mkrOverThis id
\-mkr

\+mkr p
\nam Part of Spch
\lng Default
\mkrOverThis id
\-mkr

\+mkr ref
\nam Reference
\lng Default
\mkrOverThis id
\-mkr

\+mkr t
\nam Text
\lng Frisian
\mkrOverThis id
\-mkr

\-mkrset

\iInterlinCharWd 8

\+intprclst 
\fglst {
\fglend }
\mbnd +
\mbrks -

\+intprc Lookup
\bParseProc
\mkrFrom t
\mkrTo m

\+triLook 
\+drflst 
\-drflst
\-triLook

\+triPref 
\dbtyp Frisian Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr fri
\mkr a
\-mrflst
\mkrOut u
\-triPref

\+triRoot 
\dbtyp Frisian Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr fri
\mkr a
\-mrflst
\mkrOut u
\-triRoot
\GlossSeparator ;
\FailMark ***
\bShowFailMark
\-intprc

\+intprc Lookup
\mkrFrom m
\mkrTo g

\+triLook 
\dbtyp Frisian Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr fri
\-mrflst
\mkrOut g
\-triLook
\GlossSeparator ;
\FailMark ***
\bShowFailMark
\-intprc

\+intprc Lookup
\mkrFrom m
\mkrTo p

\+triLook 
\dbtyp Frisian Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr fri
\-mrflst
\mkrOut ps
\-triLook
\GlossSeparator ;
\FailMark ***
\bShowFailMark
\-intprc

\-intprclst
\+filset 

\-filset

\+jmpset 
\+jmp default
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\mkr fri
\-drf
\+drf 
\File Z:\home\stuart\workspace\nltk\samples\FRISIAN1\FRIRT.DIC
\mkr a
\-drf
\-drflst
\-jmp
\-jmpset

\+template 
\-template
\mkrRecord id
\+PrintProperties 
\header File: &f, Date: &d
\footer Page &p
\topmargin 1.00 in
\leftmargin 0.25 in
\bottommargin 1.00 in
\rightmargin 0.25 in
\recordsspace 100
\-PrintProperties
\+expset 

\+expRTF Rich Text Format
\InterlinearSpacing 120
\+rtfPageSetup 
\paperSize letter
\topMargin 1
\bottomMargin 1
\leftMargin 1.25
\rightMargin 1.25
\gutter 0
\headerToEdge 0.5
\footerToEdge 0.5
\columns 1
\columnSpacing 0.5
\-rtfPageSetup
\-expRTF

\+expSF Standard Format
\-expSF

\expDefault Standard Format
\SkipProperties
\-expset
\+numbering 
\mkrRef ref
\mkrTxt t
\+subsetTextBreakMarkers 
\+mkrsubsetIncluded 
\-mkrsubsetIncluded
\-subsetTextBreakMarkers
\-numbering
\-DatabaseType
