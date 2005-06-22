\+DatabaseType Asy Scrip
\ver 5.0
\desc Assyrian Scripture text for editing and import to word for printing
\+mkrset 
\lngDefault Default
\mkrRecord id

\+mkr c
\nam chapter
\lng Aramaic
\mkrOverThis id
\CharStyle
\-mkr

\+mkr cp
\nam Chapter Paragraph
\lng Aramaic
\mkrOverThis c
\-mkr

\+mkr ct
\nam Chapter Title
\lng Aramaic
\mkrOverThis id
\CharStyle
\-mkr

\+mkr id
\nam Identification
\lng Default
\-mkr

\+mkr p
\nam paragraph
\lng Aramaic
\mkrOverThis c
\CharStyle
\-mkr

\+mkr pp
\nam Para Paragraph
\lng Aramaic
\mkrOverThis c
\-mkr

\+mkr s
\nam section
\lng Aramaic
\mkrOverThis c
\CharStyle
\-mkr

\+mkr sp
\nam Section Paragraph
\lng Aramaic
\mkrOverThis c
\-mkr

\+mkr v
\nam verse
\lng Aramaic
\mkrOverThis c
\CharStyle
\-mkr

\+mkr vp
\nam Verse Paragraph
\lng Aramaic
\mkrOverThis c
\-mkr

\+mkr vt
\nam Verse Text
\lng Aramaic
\mkrOverThis c
\CharStyle
\-mkr

\-mkrset
\iInterlinCharWd 8
\+filset 

\-filset
\+drflst 
\-drflst
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
\recordsspace 10
\-PrintProperties
\+expset 

\+expRTF Asy NT RTF
\cctFile Asyout.cct
\dotFile Asynt6.dot
\exportedFile phil1.rtf
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

\+expSF Asy NT SF
\cctFile Asyout.cct
\exportedFile phil1.txt
\-expSF

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

\expDefault Asy NT RTF
\AutoOpen
\-expset
\-DatabaseType
