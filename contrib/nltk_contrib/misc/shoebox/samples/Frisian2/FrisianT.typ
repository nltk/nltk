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

\+mkr id
\nam Identifier
\lng Default
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
\+filset 

\-filset
\+jmpset 
\+jmp default
\+drflst 
\+drf 
\File C:\xxxx\Samples\FRISIAN2\FRIRT.DIC
\mkr fri
\-drf
\+drf 
\File C:\xxxx\Samples\FRISIAN2\FRIRT.DIC
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
