\+DatabaseType Readme Notes
\ver 5.0
\+mkrset 
\lngDefault Default
\mkrRecord id

\+mkr co
\nam Comment
\lng Default
\mkrOverThis id
\-mkr

\+mkr e
\nam English Adaptation
\lng Default
\+fnt 
\Name Times New Roman
\Size 12
\rgbColor 255,0,0
\-fnt
\mkrOverThis id
\-mkr

\+mkr id
\nam File ID
\lng Default
\+fnt 
\Name Times New Roman
\Size 12
\Bold
\Underline
\rgbColor 0,0,128
\-fnt
\-mkr

\+mkr nt
\nam Note
\lng Default
\+fnt 
\Name Times New Roman
\Size 10
\Bold
\rgbColor 255,0,0
\-fnt
\mkrOverThis s
\-mkr

\+mkr p
\nam Paragraph
\lng Default
\mkrOverThis id
\mkrFollowingThis p
\-mkr

\+mkr s
\nam Section
\lng Default
\+fnt 
\Name Times New Roman
\Size 12
\Bold
\rgbColor 0,0,255
\-fnt
\mkrOverThis id
\mkrFollowingThis p
\-mkr

\+mkr s2
\nam Section (2)
\lng Default
\+fnt 
\Name Times New Roman
\Size 11
\Bold
\Italic
\rgbColor 0,0,255
\-fnt
\mkrOverThis s
\-mkr

\+mkr s3
\nam Section (3)
\lng Default
\+fnt 
\Name Times New Roman
\Size 10
\Bold
\rgbColor 0,0,255
\-fnt
\mkrOverThis s2
\-mkr

\+mkr t
\nam Text
\lng Default
\mkrOverThis id
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
\-DatabaseType
