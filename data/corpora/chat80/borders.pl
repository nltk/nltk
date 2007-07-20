/*

 _________________________________________________________________________
|	Copyright (C) 1982						  |
|									  |
|	David Warren,							  |
|		SRI International, 333 Ravenswood Ave., Menlo Park,	  |
|		California 94025, USA;					  |
|									  |
|	Fernando Pereira,						  |
|		Dept. of Architecture, University of Edinburgh,		  |
|		20 Chambers St., Edinburgh EH1 1JZ, Scotland		  |
|									  |
|	This program may be used, copied, altered or included in other	  |
|	programs only for academic purposes and provided that the	  |
|	authorship of the initial program is aknowledged.		  |
|	Use for commercial purposes without the previous written 	  |
|	agreement of the authors is forbidden.				  |
|_________________________________________________________________________|

*/

% Facts about Europe.
% ------------------

% borders(X,C) :- var(X), nonvar(C), !, borders(C,X).

borders(albania,greece).
borders(albania,yugoslavia).
borders(albania,mediterranean).

borders(andorra,france).
borders(andorra,spain).

borders(austria,czechoslovakia).
borders(austria,hungary).
borders(austria,italy).
borders(austria,liechtenstein).
borders(austria,switzerland).
borders(austria,west_germany).
borders(austria,yugoslavia).

borders(belgium,france).
borders(belgium,luxembourg).
borders(belgium,netherlands).
borders(belgium,west_germany).
borders(belgium,atlantic).

borders(bulgaria,greece).
borders(bulgaria,romania).
borders(bulgaria,turkey).
borders(bulgaria,yugoslavia).
borders(bulgaria,black_sea).

borders(cyprus,mediterranean).

borders(czechoslovakia,austria).
borders(czechoslovakia,east_germany).
borders(czechoslovakia,hungary).
borders(czechoslovakia,poland).
borders(czechoslovakia,soviet_union).
borders(czechoslovakia,west_germany).

borders(denmark,west_germany).
borders(denmark,atlantic).
borders(denmark,baltic).

borders(eire,united_kingdom).
borders(eire,atlantic).

borders(finland,norway).
borders(finland,soviet_union).
borders(finland,sweden).
borders(finland,baltic).

borders(france,andorra).
borders(france,belgium).
borders(france,italy).
borders(france,luxembourg).
borders(france,monaco).
borders(france,spain).
borders(france,switzerland).
borders(france,west_germany).
borders(france,atlantic).
borders(france,mediterranean).

borders(east_germany,czechoslovakia).
borders(east_germany,poland).
borders(east_germany,west_germany).
borders(east_germany,baltic).

borders(greece,albania).
borders(greece,bulgaria).
borders(greece,turkey).
borders(greece,yugoslavia).
borders(greece,mediterranean).

borders(hungary,austria).
borders(hungary,czechoslovakia).
borders(hungary,romania).
borders(hungary,soviet_union).
borders(hungary,yugoslavia).

borders(iceland,atlantic).

borders(italy,austria).
borders(italy,france).
borders(italy,san_marino).
borders(italy,switzerland).
borders(italy,yugoslavia).
borders(italy,mediterranean).

borders(liechtenstein,austria).
borders(liechtenstein,switzerland).

borders(luxembourg,belgium).
borders(luxembourg,france).
borders(luxembourg,west_germany).

borders(malta,mediterranean).

borders(monaco,france).
borders(monaco,mediterranean).

borders(netherlands,belgium).
borders(netherlands,west_germany).
borders(netherlands,atlantic).

borders(norway,finland).
borders(norway,sweden).
borders(norway,soviet_union).
borders(norway,arctic_ocean).
borders(norway,atlantic).

borders(poland,czechoslovakia).
borders(poland,east_germany).
borders(poland,soviet_union).
borders(poland,baltic).

borders(portugal,spain).
borders(portugal,atlantic).

borders(romania,bulgaria).
borders(romania,hungary).
borders(romania,soviet_union).
borders(romania,yugoslavia).
borders(romania,black_sea).

borders(san_marino,italy).
borders(san_marino,mediterranean).

borders(spain,andorra).
borders(spain,france).
borders(spain,portugal).
borders(spain,atlantic).
borders(spain,mediterranean).

borders(sweden,finland).
borders(sweden,norway).
borders(sweden,atlantic).
borders(sweden,baltic).

borders(switzerland,austria).
borders(switzerland,france).
borders(switzerland,italy).
borders(switzerland,liechtenstein).
borders(switzerland,west_germany).

borders(west_germany,austria).
borders(west_germany,belgium).
borders(west_germany,czechoslovakia).
borders(west_germany,denmark).
borders(west_germany,east_germany).
borders(west_germany,france).
borders(west_germany,luxembourg).
borders(west_germany,netherlands).
borders(west_germany,switzerland).
borders(west_germany,atlantic).
borders(west_germany,baltic).

borders(united_kingdom,eire).
borders(united_kingdom,atlantic).

borders(yugoslavia,albania).
borders(yugoslavia,austria).
borders(yugoslavia,bulgaria).
borders(yugoslavia,greece).
borders(yugoslavia,hungary).
borders(yugoslavia,italy).
borders(yugoslavia,romania).
borders(yugoslavia,mediterranean).

% Facts about Asia.
% ----------------

borders(afghanistan,china).
borders(afghanistan,iran).
borders(afghanistan,pakistan).
borders(afghanistan,soviet_union).

borders(bahrain,persian_gulf).

borders(bangladesh,burma).
borders(bangladesh,india).
borders(bangladesh,indian_ocean).

borders(bhutan,china).
borders(bhutan,india).

borders(burma,bangladesh).
borders(burma,china).
borders(burma,india).
borders(burma,laos).
borders(burma,thailand).
borders(burma,indian_ocean).

borders(cambodia,laos).
borders(cambodia,thailand).
borders(cambodia,vietnam).
borders(cambodia,pacific).

borders(china,afghanistan).
borders(china,bhutan).
borders(china,burma).
borders(china,india).
borders(china,laos).
borders(china,mongolia).
borders(china,nepal).
borders(china,north_korea).
borders(china,pakistan).
borders(china,soviet_union).
borders(china,vietnam).
borders(china,pacific).

borders(india,bangladesh).
borders(india,bhutan).
borders(india,burma).
borders(india,china).
borders(india,nepal).
borders(india,pakistan).
borders(india,indian_ocean).

borders(indonesia,malaysia).
borders(indonesia,papua_new_guinea).
borders(indonesia,indian_ocean).
borders(indonesia,pacific).

borders(iran,afghanistan).
borders(iran,iraq).
borders(iran,pakistan).
borders(iran,soviet_union).
borders(iran,turkey).
borders(iran,caspian).
borders(iran,persian_gulf).
borders(iran,indian_ocean).

borders(iraq,iran).
borders(iraq,jordan).
borders(iraq,kuwait).
borders(iraq,saudi_arabia).
borders(iraq,syria).
borders(iraq,turkey).
borders(iraq,persian_gulf).

borders(israel,egypt).
borders(israel,jordan).
borders(laos,burma).
borders(laos,cambodia).
borders(laos,china).
borders(laos,thailand).
borders(laos,vietnam).

borders(israel,lebanon).
borders(israel,syria).
borders(israel,mediterranean).
borders(israel,red_sea).

borders(japan,pacific).

borders(jordan,iraq).
borders(jordan,israel).
borders(jordan,saudi_arabia).
borders(jordan,syria).
borders(jordan,red_sea).

borders(kuwait,iraq).
borders(kuwait,saudi_arabia).
borders(kuwait,persian_gulf).

borders(lebanon,israel).
borders(lebanon,syria).
borders(lebanon,mediterranean).

borders(malaysia,indonesia).
borders(malaysia,singapore).
borders(malaysia,thailand).
borders(malaysia,indian_ocean).
borders(malaysia,pacific).

borders(maldives,indian_ocean).

borders(mongolia,china).
borders(mongolia,soviet_union).

borders(nepal,china).
borders(nepal,india).

borders(north_korea,china).
borders(north_korea,south_korea).
borders(north_korea,soviet_union).
borders(north_korea,pacific).

borders(oman,saudi_arabia).
borders(oman,united_arab_emirates).
borders(oman,south_yemen).
borders(oman,indian_ocean).

borders(pakistan,afghanistan).
borders(pakistan,china).
borders(pakistan,india).
borders(pakistan,iran).
borders(pakistan,indian_ocean).

borders(philippines,pacific).

borders(qatar,saudi_arabia).
borders(qatar,united_arab_emirates).
borders(qatar,persian_gulf).

borders(saudi_arabia,iraq).
borders(saudi_arabia,jordan).
borders(saudi_arabia,kuwait).
borders(saudi_arabia,oman).
borders(saudi_arabia,qatar).
borders(saudi_arabia,south_yemen).
borders(saudi_arabia,united_arab_emirates).
borders(saudi_arabia,yemen).
borders(saudi_arabia,persian_gulf).
borders(saudi_arabia,red_sea).

borders(singapore,malaysia).
borders(singapore,pacific).

borders(south_korea,north_korea).
borders(south_korea,pacific).

borders(south_yemen,oman).
borders(south_yemen,saudi_arabia).
borders(south_yemen,yemen).
borders(south_yemen,indian_ocean).

borders(soviet_union,afghanistan).
borders(soviet_union,china).
borders(soviet_union,czechoslovakia).
borders(soviet_union,finland).
borders(soviet_union,hungary).
borders(soviet_union,iran).
borders(soviet_union,mongolia).
borders(soviet_union,north_korea).
borders(soviet_union,norway).
borders(soviet_union,poland).
borders(soviet_union,romania).
borders(soviet_union,turkey).
borders(soviet_union,arctic_ocean).
borders(soviet_union,baltic).
borders(soviet_union,black_sea).
borders(soviet_union,caspian).
borders(soviet_union,pacific).

borders(sri_lanka,indian_ocean).

borders(syria,iraq).
borders(syria,israel).
borders(syria,jordan).
borders(syria,lebanon).
borders(syria,turkey).
borders(syria,mediterranean).

borders(taiwan,pacific).

borders(thailand,burma).
borders(thailand,cambodia).
borders(thailand,laos).
borders(thailand,malaysia).
borders(thailand,indian_ocean).
borders(thailand,pacific).

borders(turkey,bulgaria).
borders(turkey,greece).
borders(turkey,iran).
borders(turkey,iraq).
borders(turkey,soviet_union).
borders(turkey,syria).
borders(turkey,black_sea).
borders(turkey,mediterranean).

borders(united_arab_emirates,oman).
borders(united_arab_emirates,qatar).
borders(united_arab_emirates,saudi_arabia).
borders(united_arab_emirates,persian_gulf).

borders(vietnam,cambodia).
borders(vietnam,china).
borders(vietnam,laos).
borders(vietnam,pacific).

borders(yemen,south_yemen).
borders(yemen,saudi_arabia).
borders(yemen,red_sea).

% Facts about Africa.
% ------------------

borders(algeria,libya).
borders(algeria,mali).
borders(algeria,mauritania).
borders(algeria,morocco).
borders(algeria,niger).
borders(algeria,tunisia).
borders(algeria,mediterranean).

borders(angola,congo).
borders(angola,south_africa).
borders(angola,zaire).
borders(angola,zambia).
borders(angola,atlantic).

borders(botswana,south_africa).
borders(botswana,zimbabwe).

borders(burundi,rwanda).
borders(burundi,tanzania).
borders(burundi,zaire).

borders(cameroon,central_african_republic).
borders(cameroon,chad).
borders(cameroon,congo).
borders(cameroon,equatorial_guinea).
borders(cameroon,gabon).
borders(cameroon,nigeria).
borders(cameroon,atlantic).

borders(central_african_republic,cameroon).
borders(central_african_republic,chad).
borders(central_african_republic,congo).
borders(central_african_republic,sudan).
borders(central_african_republic,zaire).

borders(chad,cameroon).
borders(chad,central_african_republic).
borders(chad,libya).
borders(chad,niger).
borders(chad,nigeria).
borders(chad,sudan).

borders(congo,angola).
borders(congo,cameroon).
borders(congo,central_african_republic).
borders(congo,gabon).
borders(congo,zaire).
borders(congo,atlantic).

borders(dahomey,niger).
borders(dahomey,nigeria).
borders(dahomey,togo).
borders(dahomey,upper_volta).
borders(dahomey,atlantic).

borders(djibouti,ethiopia).
borders(djibouti,somalia).
borders(djibouti,indian_ocean).

borders(egypt,israel).
borders(egypt,libya).
borders(egypt,sudan).
borders(egypt,mediterranean).
borders(egypt,red_sea).

borders(equatorial_guinea,cameroon).
borders(equatorial_guinea,gabon).
borders(equatorial_guinea,atlantic).

borders(ethiopia,djibouti).
borders(ethiopia,kenya).
borders(ethiopia,somalia).
borders(ethiopia,sudan).
borders(ethiopia,red_sea).

borders(gabon,cameroon).
borders(gabon,congo).
borders(gabon,equatorial_guinea).
borders(gabon,atlantic).

borders(gambia,senegal).
borders(gambia,atlantic).

borders(ghana,ivory_coast).
borders(ghana,togo).
borders(ghana,upper_volta).
borders(ghana,atlantic).

borders(guinea,guinea_bissau).
borders(guinea,ivory_coast).
borders(guinea,liberia).
borders(guinea,mali).
borders(guinea,senegal).
borders(guinea,sierra_leone).
borders(guinea,atlantic).

borders(guinea_bissau,guinea).
borders(guinea_bissau,senegal).
borders(guinea_bissau,atlantic).

borders(ivory_coast,ghana).
borders(ivory_coast,guinea).
borders(ivory_coast,liberia).
borders(ivory_coast,mali).
borders(ivory_coast,upper_volta).
borders(ivory_coast,atlantic).

borders(kenya,ethiopia).
borders(kenya,somalia).
borders(kenya,sudan).
borders(kenya,tanzania).
borders(kenya,uganda).
borders(kenya,indian_ocean).

borders(lesotho,south_africa).

borders(liberia,ivory_coast).
borders(liberia,guinea).
borders(liberia,sierra_leone).
borders(liberia,atlantic).

borders(libya,algeria).
borders(libya,chad).
borders(libya,egypt).
borders(libya,niger).
borders(libya,sudan).
borders(libya,tunisia).
borders(libya,mediterranean).

borders(malagasy,indian_ocean).

borders(malawi,mozambique).
borders(malawi,tanzania).
borders(malawi,zambia).

borders(mali,algeria).
borders(mali,guinea).
borders(mali,ivory_coast).
borders(mali,mauritania).
borders(mali,niger).
borders(mali,senegal).
borders(mali,upper_volta).

borders(mauritania,algeria).
borders(mauritania,mali).
borders(mauritania,morocco).
borders(mauritania,senegal).
borders(mauritania,atlantic).

borders(mauritius,indian_ocean).

borders(morocco,algeria).
borders(morocco,mauritania).
borders(morocco,atlantic).
borders(morocco,mediterranean).

borders(mozambique,malawi).
borders(mozambique,south_africa).
borders(mozambique,swaziland).
borders(mozambique,tanzania).
borders(mozambique,zambia).
borders(mozambique,zimbabwe).
borders(mozambique,indian_ocean).

borders(niger,algeria).
borders(niger,chad).
borders(niger,dahomey).
borders(niger,libya).
borders(niger,mali).
borders(niger,nigeria).
borders(niger,upper_volta).

borders(nigeria,cameroon).
borders(nigeria,chad).
borders(nigeria,dahomey).
borders(nigeria,niger).
borders(nigeria,atlantic).

borders(rwanda,burundi).
borders(rwanda,tanzania).
borders(rwanda,uganda).
borders(rwanda,zaire).

borders(senegal,gambia).
borders(senegal,guinea).
borders(senegal,guinea_bissau).
borders(senegal,mali).
borders(senegal,mauritania).
borders(senegal,atlantic).

borders(seychelles,indian_ocean).

borders(sierra_leone,guinea).
borders(sierra_leone,liberia).
borders(sierra_leone,atlantic).

borders(somalia,djibouti).
borders(somalia,ethiopia).
borders(somalia,kenya).
borders(somalia,indian_ocean).

borders(south_africa,angola).
borders(south_africa,botswana).
borders(south_africa,lesotho).
borders(south_africa,mozambique).
borders(south_africa,swaziland).
borders(south_africa,zambia).
borders(south_africa,zimbabwe).
borders(south_africa,atlantic).
borders(south_africa,indian_ocean).

borders(sudan,chad).
borders(sudan,central_african_republic).
borders(sudan,egypt).
borders(sudan,ethiopia).
borders(sudan,kenya).
borders(sudan,libya).
borders(sudan,uganda).
borders(sudan,zaire).
borders(sudan,red_sea).

borders(swaziland,mozambique).
borders(swaziland,south_africa).

borders(tanzania,burundi).
borders(tanzania,kenya).
borders(tanzania,malawi).
borders(tanzania,mozambique).
borders(tanzania,rwanda).
borders(tanzania,uganda).
borders(tanzania,zaire).
borders(tanzania,zambia).
borders(tanzania,indian_ocean).

borders(togo,dahomey).
borders(togo,ghana).
borders(togo,upper_volta).
borders(togo,atlantic).

borders(tunisia,algeria).
borders(tunisia,libya).
borders(tunisia,mediterranean).

borders(uganda,kenya).
borders(uganda,rwanda).
borders(uganda,sudan).
borders(uganda,tanzania).
borders(uganda,zaire).

borders(upper_volta,dahomey).
borders(upper_volta,ghana).
borders(upper_volta,ivory_coast).
borders(upper_volta,mali).
borders(upper_volta,niger).
borders(upper_volta,togo).

borders(zaire,angola).
borders(zaire,burundi).
borders(zaire,central_african_republic).
borders(zaire,congo).
borders(zaire,rwanda).
borders(zaire,sudan).
borders(zaire,tanzania).
borders(zaire,uganda).
borders(zaire,zambia).
borders(zaire,atlantic).

borders(zambia,angola).
borders(zambia,malawi).
borders(zambia,mozambique).
borders(zambia,south_africa).
borders(zambia,tanzania).
borders(zambia,zaire).
borders(zambia,zimbabwe).

borders(zimbabwe,botswana).
borders(zimbabwe,mozambique).
borders(zimbabwe,south_africa).
borders(zimbabwe,zambia).


% Facts about America.
% -------------------

borders(argentina,bolivia).
borders(argentina,brazil).
borders(argentina,chile).
borders(argentina,paraguay).
borders(argentina,uruguay).
borders(argentina,atlantic).

borders(bahamas,atlantic).

borders(barbados,atlantic).

borders(belize,guatemala).
borders(belize,mexico).
borders(belize,atlantic).

borders(bolivia,argentina).
borders(bolivia,brazil).
borders(bolivia,chile).
borders(bolivia,paraguay).
borders(bolivia,peru).

borders(brazil,argentina).
borders(brazil,bolivia).
borders(brazil,colombia).
borders(brazil,french_guiana).
borders(brazil,guyana).
borders(brazil,paraguay).
borders(brazil,peru).
borders(brazil,surinam).
borders(brazil,uruguay).
borders(brazil,venezuela).
borders(brazil,atlantic).

borders(canada,united_states).
borders(canada,arctic_ocean).
borders(canada,atlantic).
borders(canada,pacific).

borders(chile,argentina).
borders(chile,bolivia).
borders(chile,peru).
borders(chile,pacific).

borders(colombia,brazil).
borders(colombia,ecuador).
borders(colombia,panama).
borders(colombia,peru).
borders(colombia,venezuela).
borders(colombia,atlantic).
borders(colombia,pacific).

borders(costa_rica,nicaragua).
borders(costa_rica,panama).
borders(costa_rica,atlantic).
borders(costa_rica,pacific).

borders(cuba,atlantic).

borders(dominican_republic,haiti).
borders(dominican_republic,atlantic).

borders(ecuador,colombia).
borders(ecuador,peru).
borders(ecuador,pacific).

borders(el_salvador,guatemala).
borders(el_salvador,honduras).
borders(el_salvador,pacific).

borders(french_guiana,brazil).
borders(french_guiana,surinam).

borders(greenland,arctic_ocean).
borders(greenland,atlantic).

borders(grenada,atlantic).

borders(guatemala,belize).
borders(guatemala,el_salvador).
borders(guatemala,honduras).
borders(guatemala,mexico).
borders(guatemala,atlantic).
borders(guatemala,pacific).

borders(guyana,brazil).
borders(guyana,surinam).
borders(guyana,venezuela).
borders(guyana,atlantic).

borders(haiti,dominican_republic).
borders(haiti,atlantic).

borders(honduras,el_salvador).
borders(honduras,guatemala).
borders(honduras,nicaragua).
borders(honduras,atlantic).
borders(honduras,pacific).

borders(jamaica,atlantic).

borders(mexico,belize).
borders(mexico,guatemala).
borders(mexico,united_states).
borders(mexico,atlantic).
borders(mexico,pacific).

borders(nicaragua,costa_rica).
borders(nicaragua,honduras).
borders(nicaragua,atlantic).
borders(nicaragua,pacific).

borders(panama,colombia).
borders(panama,costa_rica).
borders(panama,atlantic).
borders(panama,pacific).

borders(paraguay,argentina).
borders(paraguay,bolivia).
borders(paraguay,brazil).

borders(peru,bolivia).
borders(peru,brazil).
borders(peru,chile).
borders(peru,colombia).
borders(peru,ecuador).
borders(peru,pacific).

borders(surinam,brazil).
borders(surinam,french_guiana).
borders(surinam,guyana).

borders(trinidad_and_tobago,atlantic).

borders(united_states,canada).
borders(united_states,mexico).
borders(united_states,arctic_ocean).
borders(united_states,atlantic).
borders(united_states,pacific).

borders(uruguay,argentina).
borders(uruguay,brazil).
borders(uruguay,atlantic).

borders(venezuela,brazil).
borders(venezuela,colombia).
borders(venezuela,guyana).
borders(venezuela,atlantic).

% Facts about Australasia.
% -----------------------

borders(australia,indian_ocean).
borders(australia,pacific).

borders(fiji,pacific).

borders(new_zealand,pacific).

borders(papua_new_guinea,indonesia).
borders(papua_new_guinea,pacific).

borders(tonga,pacific).

borders(western_samoa,pacific).

borders(antarctica,southern_ocean).

% Facts about oceans and seas.
% ---------------------------

borders(arctic_ocean,atlantic).
borders(arctic_ocean,pacific).

borders(atlantic,arctic_ocean).
borders(atlantic,indian_ocean).
borders(atlantic,pacific).
borders(atlantic,southern_ocean).
borders(atlantic,baltic).
borders(atlantic,mediterranean).

borders(indian_ocean,atlantic).
borders(indian_ocean,pacific).
borders(indian_ocean,southern_ocean).
borders(indian_ocean,persian_gulf).
borders(indian_ocean,red_sea).

borders(pacific,arctic_ocean).
borders(pacific,atlantic).
borders(pacific,indian_ocean).
borders(pacific,southern_ocean).

borders(southern_ocean,atlantic).
borders(southern_ocean,indian_ocean).
borders(southern_ocean,pacific).

borders(baltic,atlantic).

borders(black_sea,mediterranean).

borders(mediterranean,atlantic).
borders(mediterranean,black_sea).

borders(persian_gulf,indian_ocean).

borders(red_sea,indian_ocean).

% Countries bordering each ocean and sea.
% --------------------------------------

borders(arctic_ocean,norway).
borders(arctic_ocean,soviet_union).
borders(arctic_ocean,canada).
borders(arctic_ocean,greenland).
borders(arctic_ocean,united_states).

borders(atlantic,belgium).
borders(atlantic,denmark).
borders(atlantic,eire).
borders(atlantic,france).
borders(atlantic,iceland).
borders(atlantic,netherlands).
borders(atlantic,norway).
borders(atlantic,portugal).
borders(atlantic,spain).
borders(atlantic,sweden).
borders(atlantic,west_germany).
borders(atlantic,united_kingdom).
borders(atlantic,angola).
borders(atlantic,cameroon).
borders(atlantic,congo).
borders(atlantic,dahomey).
borders(atlantic,equatorial_guinea).
borders(atlantic,gabon).
borders(atlantic,gambia).
borders(atlantic,ghana).
borders(atlantic,guinea).
borders(atlantic,guinea_bissau).
borders(atlantic,ivory_coast).
borders(atlantic,liberia).
borders(atlantic,mauritania).
borders(atlantic,morocco).
borders(atlantic,nigeria).
borders(atlantic,senegal).
borders(atlantic,sierra_leone).
borders(atlantic,south_africa).
borders(atlantic,togo).
borders(atlantic,zaire).
borders(atlantic,argentina).
borders(atlantic,bahamas).
borders(atlantic,barbados).
borders(atlantic,belize).
borders(atlantic,brazil).
borders(atlantic,canada).
borders(atlantic,colombia).
borders(atlantic,costa_rica).
borders(atlantic,cuba).
borders(atlantic,dominican_republic).
borders(atlantic,french_guiana).
borders(atlantic,greenland).
borders(atlantic,grenada).
borders(atlantic,guatemala).
borders(atlantic,guyana).
borders(atlantic,haiti).
borders(atlantic,honduras).
borders(atlantic,jamaica).
borders(atlantic,mexico).
borders(atlantic,nicaragua).
borders(atlantic,panama).
borders(atlantic,surinam).
borders(atlantic,trinidad_and_tobago).
borders(atlantic,united_states).
borders(atlantic,uruguay).
borders(atlantic,venezuela).

borders(indian_ocean,bangladesh).
borders(indian_ocean,burma).
borders(indian_ocean,india).
borders(indian_ocean,indonesia).
borders(indian_ocean,iran).
borders(indian_ocean,malaysia).
borders(indian_ocean,maldives).
borders(indian_ocean,oman).
borders(indian_ocean,pakistan).
borders(indian_ocean,south_yemen).
borders(indian_ocean,sri_lanka).
borders(indian_ocean,thailand).
borders(indian_ocean,djibouti).
borders(indian_ocean,kenya).
borders(indian_ocean,malagasy).
borders(indian_ocean,mauritius).
borders(indian_ocean,mozambique).
borders(indian_ocean,seychelles).
borders(indian_ocean,somalia).
borders(indian_ocean,south_africa).
borders(indian_ocean,tanzania).
borders(indian_ocean,australia).

borders(pacific,cambodia).
borders(pacific,china).
borders(pacific,indonesia).
borders(pacific,japan).
borders(pacific,malaysia).
borders(pacific,north_korea).
borders(pacific,philippines).
borders(pacific,singapore).
borders(pacific,south_korea).
borders(pacific,soviet_union).
borders(pacific,taiwan).
borders(pacific,thailand).
borders(pacific,vietnam).
borders(pacific,canada).
borders(pacific,chile).
borders(pacific,colombia).
borders(pacific,costa_rica).
borders(pacific,ecuador).
borders(pacific,el_salvador).
borders(pacific,guatemala).
borders(pacific,honduras).
borders(pacific,mexico).
borders(pacific,nicaragua).
borders(pacific,panama).
borders(pacific,peru).
borders(pacific,united_states).
borders(pacific,australia).
borders(pacific,fiji).
borders(pacific,new_zealand).
borders(pacific,papua_new_guinea).
borders(pacific,tonga).
borders(pacific,western_samoa).

borders(southern_ocean,antarctica).

borders(baltic,denmark).
borders(baltic,finland).
borders(baltic,east_germany).
borders(baltic,poland).
borders(baltic,sweden).
borders(baltic,west_germany).
borders(baltic,soviet_union).

borders(black_sea,bulgaria).
borders(black_sea,romania).
borders(black_sea,soviet_union).
borders(black_sea,turkey).

borders(caspian,iran).
borders(caspian,soviet_union).

borders(mediterranean,albania).
borders(mediterranean,cyprus).
borders(mediterranean,france).
borders(mediterranean,greece).
borders(mediterranean,italy).
borders(mediterranean,malta).
borders(mediterranean,monaco).
borders(mediterranean,san_marino).
borders(mediterranean,spain).
borders(mediterranean,yugoslavia).
borders(mediterranean,israel).
borders(mediterranean,lebanon).
borders(mediterranean,syria).
borders(mediterranean,turkey).
borders(mediterranean,algeria).
borders(mediterranean,egypt).
borders(mediterranean,libya).
borders(mediterranean,morocco).
borders(mediterranean,tunisia).

borders(persian_gulf,bahrain).
borders(persian_gulf,iran).
borders(persian_gulf,iraq).
borders(persian_gulf,kuwait).
borders(persian_gulf,qatar).
borders(persian_gulf,saudi_arabia).
borders(persian_gulf,united_arab_emirates).

borders(red_sea,israel).
borders(red_sea,jordan).
borders(red_sea,saudi_arabia).
borders(red_sea,yemen).
borders(red_sea,egypt).
borders(red_sea,ethiopia).
borders(red_sea,sudan).
