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

% Inversion of the 'in' relation.
% ------------------------------

contains(X,Y) :- contains0(X,Y).
contains(X,Y) :- contains0(X,W), contains(W,Y).

contains0(africa,central_africa).
contains0(africa,east_africa).
contains0(africa,north_africa).
contains0(africa,southern_africa).
contains0(africa,west_africa).

contains0(america,caribbean).
contains0(america,central_america).
contains0(america,north_america).
contains0(america,south_america).

contains0(asia,far_east).
contains0(asia,indian_subcontinent).
contains0(asia,middle_east).
contains0(asia,northern_asia).
contains0(asia,southeast_east).

contains0(australasia,australia).
contains0(australasia,fiji).
contains0(australasia,new_zealand).
contains0(australasia,papua_new_guinea).
contains0(australasia,tonga).
contains0(australasia,western_samoa).

contains0(europe,eastern_europe).
contains0(europe,scandinavia).
contains0(europe,southern_europe).
contains0(europe,western_europe).

contains0(scandinavia,denmark).
contains0(scandinavia,finland).
contains0(scandinavia,norway).
contains0(scandinavia,sweden).

contains0(western_europe,austria).
contains0(western_europe,belgium).
contains0(western_europe,eire).
contains0(western_europe,france).
contains0(western_europe,iceland).
contains0(western_europe,liechtenstein).
contains0(western_europe,luxembourg).
contains0(western_europe,netherlands).
contains0(western_europe,switzerland).
contains0(western_europe,united_kingdom).
contains0(western_europe,west_germany).

contains0(eastern_europe,bulgaria).
contains0(eastern_europe,czechoslovakia).
contains0(eastern_europe,east_germany).
contains0(eastern_europe,hungary).
contains0(eastern_europe,poland).
contains0(eastern_europe,romania).

contains0(southern_europe,albania).
contains0(southern_europe,andorra).
contains0(southern_europe,cyprus).
contains0(southern_europe,greece).
contains0(southern_europe,italy).
contains0(southern_europe,malta).
contains0(southern_europe,monaco).
contains0(southern_europe,portugal).
contains0(southern_europe,san_marino).
contains0(southern_europe,spain).
contains0(southern_europe,yugoslavia).

contains0(north_america,canada).
contains0(north_america,united_states).

contains0(central_america,belize).
contains0(central_america,costa_rica).
contains0(central_america,el_salvador).
contains0(central_america,guatemala).
contains0(central_america,honduras).
contains0(central_america,mexico).
contains0(central_america,nicaragua).
contains0(central_america,panama).

contains0(caribbean,bahamas).
contains0(caribbean,barbados).
contains0(caribbean,cuba).
contains0(caribbean,dominican_republic).
contains0(caribbean,grenada).
contains0(caribbean,haiti).
contains0(caribbean,jamaica).
contains0(caribbean,trinidad_and_tobago).

contains0(south_america,argentina).
contains0(south_america,bolivia).
contains0(south_america,brazil).
contains0(south_america,chile).
contains0(south_america,colombia).
contains0(south_america,ecuador).
contains0(south_america,french_guiana).
contains0(south_america,guyana).
contains0(south_america,paraguay).
contains0(south_america,peru).
contains0(south_america,surinam).
contains0(south_america,uruguay).
contains0(south_america,venezuela).

contains0(north_africa,algeria).
contains0(north_africa,egypt).
contains0(north_africa,libya).
contains0(north_africa,morocco).
contains0(north_africa,tunisia).

contains0(west_africa,cameroon).
contains0(west_africa,dahomey).
contains0(west_africa,equatorial_guinea).
contains0(west_africa,gambia).
contains0(west_africa,ghana).
contains0(west_africa,guinea).
contains0(west_africa,guinea_bissau).
contains0(west_africa,ivory_coast).
contains0(west_africa,liberia).
contains0(west_africa,mali).
contains0(west_africa,mauritania).
contains0(west_africa,niger).
contains0(west_africa,nigeria).
contains0(west_africa,senegal).
contains0(west_africa,sierra_leone).
contains0(west_africa,togo).
contains0(west_africa,upper_volta).

contains0(central_africa,burundi).
contains0(central_africa,central_african_republic).
contains0(central_africa,chad).
contains0(central_africa,congo).
contains0(central_africa,gabon).
contains0(central_africa,rwanda).
contains0(central_africa,sudan).
contains0(central_africa,zaire).

contains0(east_africa,djibouti).
contains0(east_africa,ethiopia).
contains0(east_africa,kenya).
contains0(east_africa,seychelles).
contains0(east_africa,somalia).
contains0(east_africa,tanzania).
contains0(east_africa,uganda).

contains0(southern_africa,angola).
contains0(southern_africa,botswana).
contains0(southern_africa,lesotho).
contains0(southern_africa,malagasy).
contains0(southern_africa,malawi).
contains0(southern_africa,mauritius).
contains0(southern_africa,mozambique).
contains0(southern_africa,south_africa).
contains0(southern_africa,swaziland).
contains0(southern_africa,zambia).
contains0(southern_africa,zimbabwe).

contains0(middle_east,bahrain).
contains0(middle_east,iran).
contains0(middle_east,iraq).
contains0(middle_east,israel).
contains0(middle_east,jordan).
contains0(middle_east,kuwait).
contains0(middle_east,lebanon).
contains0(middle_east,oman).
contains0(middle_east,qatar).
contains0(middle_east,saudi_arabia).
contains0(middle_east,south_yemen).
contains0(middle_east,syria).
contains0(middle_east,turkey).
contains0(middle_east,united_arab_emirates).
contains0(middle_east,yemen).

contains0(indian_subcontinent,afghanistan).
contains0(indian_subcontinent,bangladesh).
contains0(indian_subcontinent,bhutan).
contains0(indian_subcontinent,india).
contains0(indian_subcontinent,maldives).
contains0(indian_subcontinent,nepal).
contains0(indian_subcontinent,pakistan).
contains0(indian_subcontinent,sri_lanka).

contains0(southeast_east,burma).
contains0(southeast_east,cambodia).
contains0(southeast_east,indonesia).
contains0(southeast_east,laos).
contains0(southeast_east,malaysia).
contains0(southeast_east,philippines).
contains0(southeast_east,singapore).
contains0(southeast_east,thailand).
contains0(southeast_east,vietnam).

contains0(far_east,china).
contains0(far_east,japan).
contains0(far_east,north_korea).
contains0(far_east,south_korea).
contains0(far_east,taiwan).

contains0(northern_asia,mongolia).
contains0(northern_asia,soviet_union).

contains0(afghanistan,amu_darya).

contains0(angola,cubango).
contains0(angola,zambesi).

contains0(argentina,buenos_aires).
contains0(argentina,parana).

contains0(australia,melbourne).
contains0(australia,murray).
contains0(australia,sydney).

contains0(austria,danube).
contains0(austria,vienna).

contains0(bangladesh,brahmaputra).

contains0(belgium,brussels).

contains0(brazil,amazon).
contains0(brazil,parana).
contains0(brazil,rio_de_janeiro).
contains0(brazil,sao_paulo).

contains0(burma,irrawaddy).
contains0(burma,salween).

contains0(cambodia,mekong).

contains0(canada,mackenzie).
contains0(canada,montreal).
contains0(canada,toronto).
contains0(canada,yukon).

contains0(chile,santiago).

contains0(china,amur).
contains0(china,brahmaputra).
contains0(china,canton).
contains0(china,chungking).
contains0(china,dairen).
contains0(china,ganges).
contains0(china,harbin).
contains0(china,hwang_ho).
contains0(china,indus).
contains0(china,kowloon).
contains0(china,mekong).
contains0(china,mukden).
contains0(china,peking).
contains0(china,salween).
contains0(china,shanghai).
contains0(china,sian).
contains0(china,tientsin).
contains0(china,yangtze).

contains0(colombia,orinoco).

contains0(czechoslovakia,danube).
contains0(czechoslovakia,elbe).
contains0(czechoslovakia,oder).

contains0(east_germany,berlin).
contains0(east_germany,elbe).

contains0(egypt,cairo).
contains0(egypt,nile).

contains0(france,paris).
contains0(france,rhone).

contains0(ghana,volta).

contains0(greece,athens).

contains0(guinea,niger_river).
contains0(guinea,senegal_river).

contains0(hungary,budapest).
contains0(hungary,danube).

contains0(india,bombay).
contains0(india,calcutta).
contains0(india,delhi).
contains0(india,ganges).
contains0(india,hyderabad).
contains0(india,indus).
contains0(india,madras).

contains0(indonesia,jakarta).

contains0(iran,tehran).

contains0(iraq,euphrates).

contains0(italy,milan).
contains0(italy,naples).
contains0(italy,rome).

contains0(japan,kobe).
contains0(japan,kyoto).
contains0(japan,nagoya).
contains0(japan,nanking).
contains0(japan,osaka).
contains0(japan,tokyo).
contains0(japan,yokohama).

contains0(laos,mekong).

contains0(lesotho,orange).

contains0(mali,niger_river).
contains0(mali,senegal_river).

contains0(mexico,colorado).
contains0(mexico,mexico_city).
contains0(mexico,rio_grande).

contains0(mongolia,amur).
contains0(mongolia,yenisei).

contains0(mozambique,limpopo).
contains0(mozambique,zambesi).

contains0(netherlands,rhine).

contains0(niger,niger_river).

contains0(nigeria,niger_river).

contains0(pakistan,indus).
contains0(pakistan,karachi).

contains0(paraguay,parana).

contains0(peru,amazon).
contains0(peru,lima).

contains0(philippines,manila).

contains0(poland,oder).
contains0(poland,vistula).
contains0(poland,warsaw).

contains0(portugal,tagus).

contains0(romania,bucharest).
contains0(romania,danube).

contains0(senegal,senegal_river).

contains0(singapore,singapore_city).

contains0(south_africa,cubango).
contains0(south_africa,johannesburg).
contains0(south_africa,limpopo).
contains0(south_africa,orange).

contains0(south_korea,pusan).
contains0(south_korea,seoul).

contains0(soviet_union,amu_darya).
contains0(soviet_union,amur).
contains0(soviet_union,don).
contains0(soviet_union,kiev).
contains0(soviet_union,lena).
contains0(soviet_union,leningrad).
contains0(soviet_union,moscow).
contains0(soviet_union,ob).
contains0(soviet_union,volga).
contains0(soviet_union,yenisei).

contains0(spain,barcelona).
contains0(spain,madrid).
contains0(spain,tagus).

contains0(sudan,nile).

contains0(switzerland,rhine).
contains0(switzerland,rhone).

contains0(syria,euphrates).

contains0(thailand,bangkok).

contains0(turkey,euphrates).
contains0(turkey,istanbul).

contains0(uganda,nile).

contains0(united_kingdom,birmingham).
contains0(united_kingdom,glasgow).
contains0(united_kingdom,london).

contains0(united_states,chicago).
contains0(united_states,colorado).
contains0(united_states,detroit).
contains0(united_states,los_angeles).
contains0(united_states,mississippi).
contains0(united_states,new_york).
contains0(united_states,philadelphia).
contains0(united_states,rio_grande).
contains0(united_states,yukon).

contains0(upper_volta,volta).

contains0(venezuela,caracas).
contains0(venezuela,orinoco).

contains0(vietnam,mekong).
contains0(vietnam,saigon).

contains0(west_germany,danube).
contains0(west_germany,elbe).
contains0(west_germany,hamburg).
contains0(west_germany,rhine).

contains0(yugoslavia,danube).

contains0(zaire,congo_river).

contains0(zambia,congo_river).
contains0(zambia,zambesi).

