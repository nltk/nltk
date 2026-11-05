"""
The sample queries of Warren and Pereira (1982), "An Efficient Easily Adaptable
System for Interpreting Natural Language Queries", AJCL 8(3-4), answered from
NLTK's Chat-80 valuation. Each expected answer is the paper's.

Derived predicates follow Chat-80's own rules in world0.pl: ``in`` is ``contains``
closed transitively, ``northof`` and ``southof`` compare latitudes, an area is
``integer(A0/1000)`` ksqmiles and a city's population is in thousands. Formulas
with one free variable go through NLTK's model; a nested quantifier over this
domain would pass the model's cost limit, so those are read off the relations.
"""

import pytest

from nltk.sem import Assignment, Model, chat80
from nltk.sem.logic import Expression


@pytest.fixture(scope="module")
def world():
    try:
        valuation = chat80.make_valuation(chat80.concepts(), read=True)
    except LookupError:
        pytest.skip("the chat80 corpus is not installed")
    return valuation, Model(valuation.domain, valuation), Assignment(valuation.domain)


@pytest.fixture(scope="module")
def rel(world):
    valuation = world[0]
    return {
        label: set(value) for label, value in valuation.items() if type(value) is list
    }


def _within(rel, region):
    return {inner for outer, inner in rel["contain"] if outer == region}


def _ksqmiles(rel):
    # area(C,A--ksqmiles) :- country(C,_,_,_,A0,_,_,_), A is integer(A0/1000).
    return {country: int(area) // 1000 for country, area in rel["area_of"]}


def _satisfiers(world, formula):
    valuation, model, assignment = world
    return sorted(model.satisfiers(Expression.fromstring(formula), "x", assignment))


def test_does_afghanistan_border_china(world):
    valuation, model, assignment = world
    assert model.evaluate("border(afghanistan, china)", assignment) is True


def test_which_countrys_capital_is_ouagadougou(world):
    assert _satisfiers(world, "country(x) & capital_of(x, ouagadougou)") == [
        "upper_volta"
    ]


def test_the_ocean_bordering_african_and_asian_countries(rel):
    def borders_a_country_in(ocean, continent):
        countries = rel["country"] & _within(rel, continent)
        return any((ocean, c) in rel["border"] for c in countries)

    found = sorted(
        ocean
        for ocean in rel["ocean"]
        if borders_a_country_in(ocean, "africa") and borders_a_country_in(ocean, "asia")
    )
    assert found == ["indian_ocean"]


def test_the_capital_of_each_country_bordering_the_baltic(world, rel):
    capital = dict(rel["capital_of"])
    countries = _satisfiers(world, "country(x) & border(x, baltic)")
    assert [f"{c}-{capital[c]}" for c in countries] == [
        "denmark-copenhagen",
        "east_germany-east_berlin",
        "finland-helsinki",
        "poland-warsaw",
        "soviet_union-moscow",
        "sweden-stockholm",
        "west_germany-bonn",
    ]


def test_the_latitudes_of_the_countries_north_of_the_united_kingdom(rel):
    # northof(X1,X2) :- latitude(X1,L1), latitude(X2,L2), exceeds(L1,L2).
    latitude = {c: int(lat) for c, lat in rel["latitude_of"]}
    north = sorted(
        c for c in rel["country"] if latitude[c] > latitude["united_kingdom"]
    )
    assert [f"{c}-{latitude[c]}" for c in north] == [
        "canada-60",
        "denmark-55",
        "finland-65",
        "iceland-65",
        "norway-64",
        "soviet_union-57",
        "sweden-63",
    ]


def test_the_countries_bordered_by_two_seas(rel):
    found = sorted(
        c
        for c in rel["country"]
        if sum((c, sea) in rel["border"] for sea in rel["sea"]) == 2
    )
    assert found == ["egypt", "iran", "israel", "saudi_arabia", "turkey"]


def test_how_many_countries_the_danube_flows_through(world):
    assert len(_satisfiers(world, "country(x) & flows(danube, x)")) == 6


def test_from_what_country_a_river_flows_into_the_persian_gulf(rel):
    # flows(R,C1,C2) :- river(R,L), links(L,C2,C1): consecutive regions of a course
    found = {
        course[i + 1]
        for course in chat80.river_courses().values()
        for i in range(len(course) - 1)
        if course[i] == "persian_gulf" and course[i + 1] in rel["country"]
    }
    assert sorted(found) == ["iraq"]


def test_the_total_area_of_countries_south_of_the_equator_not_in_australasia(rel):
    # southof(X1,X2) :- latitude(X1,L1), latitude(X2,L2), exceeds(L2,L1).
    equator = dict(rel["degrees_of"])["equator"]
    latitude = dict(rel["latitude_of"])
    area = _ksqmiles(rel)
    south = {c for c in rel["country"] if int(latitude[c]) < int(equator)}
    assert sum(area[c] for c in south - _within(rel, "australasia")) == 10228


def test_the_average_area_of_the_countries_in_each_continent(rel):
    area = _ksqmiles(rel)
    average = {}
    for continent in sorted(rel["continent"]):
        areas = [area[c] for c in rel["country"] & _within(rel, continent)]
        if areas:
            average[continent] = sum(areas) // len(areas)
    assert average == {
        "africa": 233,
        "america": 496,
        "asia": 485,
        "australasia": 543,
        "europe": 58,
    }


def test_how_many_countries_there_are_in_each_continent(rel):
    # also Appendix III, against Quel
    counts = {
        continent: len(rel["country"] & _within(rel, continent))
        for continent in rel["continent"]
    }
    assert {k: v for k, v in counts.items() if v} == {
        "africa": 48,
        "america": 31,
        "asia": 39,
        "australasia": 6,
        "europe": 32,
    }


def _bordering_no_country(rel):
    return [
        ocean
        for ocean in rel["ocean"]
        if not any((ocean, c) in rel["border"] for c in rel["country"])
    ]


def test_some_ocean_borders_no_country(rel):
    assert _bordering_no_country(rel)


def test_what_borders_the_ocean_that_borders_no_country(rel):
    (ocean,) = _bordering_no_country(rel)
    found = sorted(region for region, other in rel["border"] if other == ocean)
    assert found == ["antarctica", "atlantic", "indian_ocean", "pacific"]


def test_the_continents_no_country_in_which_has_three_cities_over_a_million(rel):
    # also Appendix III; population(C,P--thousand) :- city(C,_,P).
    population = dict(rel["population_of"])
    city_country = dict(rel["country_of"])

    def big_cities(country):
        return sum(
            1
            for city in rel["city"]
            if city_country[city] == country and int(population[city]) > 1000
        )

    found = sorted(
        continent
        for continent in rel["continent"]
        if not any(big_cities(c) > 2 for c in rel["country"] & _within(rel, continent))
    )
    assert found == ["africa", "antarctica", "australasia"]


def test_the_mediterranean_country_next_to_a_neighbour_of_a_bigger_one_than_india(rel):
    population = {c: int(p) for c, p in rel["population_of"] if c in rel["country"]}
    bigger = {c for c in rel["country"] if population[c] > population["india"]}
    found = sorted(
        c
        for c in rel["country"]
        if (c, "mediterranean") in rel["border"]
        and any(
            (c, c1) in rel["border"] and any((c2, c1) in rel["border"] for c2 in bigger)
            for c1 in rel["country"]
        )
    )
    assert found == ["turkey"]


def test_the_facts_of_section_2(world, rel):
    valuation, model, assignment = world
    # France is a country; Paris is the capital of France; France borders Spain
    for formula in (
        "country(france)",
        "capital_of(france, paris)",
        "border(france, spain)",
        "city(paris)",
    ):
        assert model.evaluate(formula, assignment) is True, formula
    # France is European; Paris is a European city
    assert {"france", "paris"} <= _within(rel, "europe")
    assert model.evaluate("country(paris)", assignment) is False


def test_three_oceans_border_the_united_states(world):
    # section 2: Chat-80 "simply gives all three answers"
    assert len(_satisfiers(world, "ocean(x) & border(x, united_states)")) == 3


def test_the_drains_relation_of_appendix_ii(world, rel):
    valuation, model, assignment = world
    assert model.evaluate("drains(amazon, atlantic)", assignment) is True
    assert model.evaluate("drains(amu_darya, aral_sea)", assignment) is True
    # predicate statistics(drains,41,41,12): 41 tuples, over 41 rivers
    assert len(rel["drains"]) == 41 and len({r for r, sea in rel["drains"]}) == 41
