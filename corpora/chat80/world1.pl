/*

Ground clauses derived from Chat-80 file 'worlds0.pl'

*/

% Data for the World Database.
% ---------------------------


circle_of_latitude(equator,0).
circle_of_latitude(tropic_of_cancer,23).
circle_of_latitude(tropic_of_capricorn,-23).
circle_of_latitude(arctic_circle,67).
circle_of_latitude(antarctic_circle,-67).

continent(africa).
continent(america).
continent(antarctica).
continent(asia).
continent(australasia).
continent(europe).

in_continent(scandinavia,europe).
in_continent(western_europe,europe).
in_continent(eastern_europe,europe).
in_continent(southern_europe,europe).
in_continent(north_america,america).
in_continent(central_america,america).
in_continent(caribbean,america).
in_continent(south_america,america).
in_continent(north_africa,africa).
in_continent(west_africa,africa).
in_continent(central_africa,africa).
in_continent(east_africa,africa).
in_continent(southern_africa,africa).
in_continent(middle_east,asia).
in_continent(indian_subcontinent,asia).
in_continent(southeast_east,asia).
in_continent(far_east,asia).
in_continent(northern_asia,asia).

ocean(arctic_ocean).
ocean(atlantic).
ocean(indian_ocean).
ocean(pacific).
ocean(southern_ocean).

sea(baltic).
sea(black_sea).
sea(caspian).
sea(mediterranean).
sea(persian_gulf).
sea(red_sea).
