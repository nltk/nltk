\+DatabaseType Rotokas Text
\ver 5.0
\desc Rotokas Interlinear Text for Tutorial
\+mkrset 
\lngDefault Default
\mkrRecord id

\+mkr au
\nam Author
\lng Default
\mkrOverThis id
\-mkr

\+mkr cd
\nam Code
\desc Field for Systematic Tagging
\lng Default
\+fnt 
\Name Bitstream Vera Sans
\Size 12
\charset 00
\rgbColor 0,0,0
\-fnt
\mkrOverThis id
\CharStyle
\-mkr

\+mkr f
\nam Free Translation
\lng Default
\NoWordWrap
\mkrOverThis id
\-mkr

\+mkr fe
\nam English Free Translation
\lng Default
\NoWordWrap
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
\NoWordWrap
\-mkr

\+mkr m
\nam Morphemes
\lng Default
\mkrOverThis id
\-mkr

\+mkr nt
\nam Notes
\lng Default
\NoWordWrap
\mkrOverThis id
\-mkr

\+mkr p
\nam Grammatical Category
\lng Default
\mkrOverThis id
\-mkr

\+mkr ref
\nam Reference
\lng Default
\mkrOverThis id
\-mkr

\+mkr spkr
\nam Speaker
\lng Rotokas
\+fnt 
\Name Times New Roman
\Size 12
\charset 00
\rgbColor 0,0,0
\-fnt
\mkrOverThis id
\-mkr

\+mkr src
\nam Source
\lng Default
\mkrOverThis id
\-mkr

\+mkr syn
\nam Synopsis
\lng Default
\mkrOverThis id
\-mkr

\+mkr t
\nam Text
\lng Rotokas
\NoWordWrap
\mkrOverThis id
\-mkr

\+mkr tAireivu
\nam *
\lng Rotokas
\mkrOverThis id
\-mkr

\+mkr tag
\nam Tagging
\lng Default
\mkrOverThis ref
\-mkr

\-mkrset

\iInterlinCharWd 10

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
\dbtyp Rotokas Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\Shoebox\Rotokas\ROTRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr lx
\mkr alt
\-mrflst
\mkrOut lx
\-triPref

\+triRoot 
\dbtyp Rotokas Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\Shoebox\Rotokas\ROTRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr lx
\mkr alt
\-mrflst
\mkrOut lx
\-triRoot
\GlossSeparator ;
\FailMark *
\bShowFailMark
\bShowRootGuess
\bPreferSuffix
\+wdfset 
\Disabled
\wdfPrimary Word
\+wdf Word
\+wdplst 
\-wdplst
\-wdf
\lngPatterns Default
\-wdfset
\-intprc

\+intprc Lookup
\mkrFrom m
\mkrTo g

\+triLook 
\dbtyp Rotokas Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\Shoebox\Rotokas\ROTRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr lx
\-mrflst
\mkrOut ge
\-triLook
\GlossSeparator ;
\FailMark ***
\bShowFailMark
\-intprc

\+intprc Lookup
\mkrFrom m
\mkrTo p

\+triLook 
\dbtyp Rotokas Dictionary
\+drflst 
\+drf 
\File Z:\home\stuart\workspace\Shoebox\Rotokas\ROTRT.DIC
\-drf
\-drflst
\+mrflst 
\mkr lx
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
