.. -*- mode: rst -*-
.. include:: ../definitions.rst
.. |bdquo| unicode:: 8222 .. opening quotation marks (Polish style)
   :rtrim:
.. |rdquo| unicode:: 8221 .. closing quotation marks (Polish style)
   :ltrim:
.. preface::

=========
Przedmowa
=========

|nopar|
Tematem niniejszego podręcznika jest analiza języka naturalnego (ang. *Natural Language Processing* |mdash| *NLP*).
Określenie |bdquo| język naturalny |rdquo| odnosi się do dowolnego języka, np. angielskiego, hindi czy portugalskiego,
służącego ludziom w procesie komunikacji. W przeciwieństwie do języków sztucznych,
takich jak choćby języki programowania czy zapisy matematyczne, języki naturalne ewoluują
z każdym, kolejnym pokoleniem władających nimi osób, przez co trudno jest m.in. w sposób jednoznaczny uchwycić rządzące nimi zasady.
Analizę języka naturalnego (oznaczaną skrótem |NLP|) będziemy w tym podręczniku rozumieć jako ogół technik komputerowych
mających na celu manipulację i operowanie danymi opartymi na języku naturalnym (mówionym lub pisanym).
NLP może służyć realizacji prostych zadań, jak zliczanie częstotliwości słów
mające na celu porównanie różnorodnych stylów. Z drugiej strony w ramach dziedziny jaką jest |NLP| podejmowane są także złożone wyzwania,
np. |bdquo| rozumienie |rdquo| kompletnych, autentycznych wypowiedzi celem udzielenia użytecznych odpowiedzi na zadawane przez użytkownika pytania.

Technologie oparte na analizie języka naturalnego
stają się coraz bardziej obecne. Przykładowo telefony komórkowe oraz przenośne komputery (smartfony, urządzenia typu PDA tudzież palmtopy)
wyposaża się w funkcje przewidywania wprowadzanego tekstu (np. tzw. słowniki T9 |mdash| przyp. tłum.) oraz rozpoznawania pisma odręcznego;
wyszukiwarki internetowe umożliwiają dostęp do informacji zagnieżdżonych w teście nieustrukturyzowanym;
tłumaczenie maszynowe pozwala na wyszukiwanie tekstów napisanych w języku chińskim, a następnie odczytanie ich po hiszpańsku.
Dzięki zastosowaniu bardziej naturalnych interfejsów człowiek-maszyna (ang. *human-machine interface*, *HMI*) oraz zaawansowanych
metod dostępu do zapisanych informacji, przetwarzanie danych językowych zaczęło pełnić kluczową rolę w wielokulturowym społeczeństwie informacyjnym.

Niniejszy książka stanowi wprowadzenie do świata analizy języka naturalnego.
Może być z powodzeniem stosowana do samodzielnej nauki, jako podręcznik podczas kursu/zajęć
związanych z tematyką |NLP| lub lingwistyką komputerową, ewentualnie jako źródło uzupełniające
do zajęć ze sztucznej inteligencji, analizy zawartości dokumentów tekstowych (ang. *text mining*) czy językoznawstwa korpusowego.
Książka skupia się na praktycznym wykorzystaniu zdobywanej wiedzy, oferując setki w pełni funkcjonalnych przykładów oraz ćwiczeń o różnym stopniu trudności.

Prezentowana treść opiera się na języku programowania Python oraz rozprowadzanym na licencji open-source pakiecie *Natural Language Toolkit* (|NLTK|). 
W ramach |NLTK| dostępny jest obszerny wybór bibliotek programistycznych oraz bogate towarzyszące zasoby danych |mdash| wszystko opatrzone stosowną dokumentacją
i dostępne bezpłatnie pod adresem internetowym |NLTK-URL|.
Na stronie znajdują się dystrybucje dla systemów Windows, Macintosh i platform Unixowych.
Gorąco zachęcamy do pobrania języka programowania Python i pakietu |NLTK| oraz wypróbowania przykładów i ćwiczeń towarzyszących poszczególnym partiom materiału.

--------------------------------------
Dla kogo przeznaczona jest ta książka?
--------------------------------------

Analiza języka naturalnego jest dziedziną istotną ze względów naukowych, ekonomicznych, społecznych oraz kulturowych.
|NLP| przeżywa aktualnie gwałtowny rozwój |mdash| powiązane teorie i metody znajdują zastosowanie w ramach różnorodnych technologii językowych.
Z tego względu praktyczna znajomość podstaw |NLP| ma zasadnicze znaczenie dla szerokiego spektrum odbiorców.
W sektorze komercyjnym wiedza ta przyda się osobom zaangażowanym w projektowanie systemów interakcji człowiek-maszyna, analizę informacji biznesowych,
oraz rozwój oprogramowania i technologii internetowych.
Natomiast w środowisku akademickim krąg odbiorców będzie obejmował osoby zajmujące się naukami humanistycznymi w kontekście informatycznym (ang. *humanities computing*) i językoznawstwem korpusowym, jak również informatyków i badaczy sztucznej inteligencji. 
Dla wielu osób z kręgów akademickich, |NLP| funkcjonuje jako lingwistyka informatyczna (ang. |bdquo| computational linguistics |rdquo|).

Podręcznik skierowany jest do szerokiego grona osób, które chcą
nauczyć się pisać programy analizujące język pisany,
bez wględu na ich wcześniejsze doświadczenie związane z programowaniem.

:Brak doświadczenia w programowaniu?:  Wczesne rozdziały książki są przeznaczone
    dla czytelników nieposiadających wiedzy programistycznej, otwartych na poznawanie
    nowych koncepcji i pragnących rozwijać swoje umiejętności programistyczne.
    Podręcznik zawiera dużo przykładów, które można powielać i wypróbować samodzielnie,
    a poszczególnym partiom materiału towarzyszą ćwiczenia o zróżnicowanym poziomie zaawansowania.
    Czytelnikom potrzebującym bardziej ogólnego wprowadzenia do programowania w Pythonie
    polecamy materiały dostępnyme na stronie internetowej ``http://docs.python.org/``.

:Pierwszy kontakt z Pythonem?:  Doświadczeni programiści mogą dzięki tej książce szybko poznać
    podstawy Pythona, aby rozpocząć prace związane z przetwarzaniem języka naturalnego.
    Podręcznik tłumaczy wszystkie istotne elementy języka programowania, bogato ilustrując je przykładami.
    Dzięki temu można docenić przystępność Pythona w zastosowaniach NLP.
    Załączony indeks rzeczowy pomoże odnaleźć fragmenty zawierające omówienia poszukiwanych pojęć.

:Programujesz w Pythonie?:  Pomiń przykłady wprowadzające do Pythona
    i rozpocznij czytanie od materiału otwierającego tematykę analizy językowej,
    który znajduje się w rozdziale chap-introduction_.
    Wkrótce będziesz mógł wykorzystać swoje umiejętności w tej nowej, fascynującej dziedzinie.

-----------
Cel książki
-----------

Niniejszy podręcznik stanowi przede wszystkim *praktyczne* wprowadzenie do tematyki |NLP|.
Nauka następuje poprzez prezentację przykładów i pisanie praktycznych programów, dzięki czemu użytkownik uczy się, jak
przetestować pomysł poprzez jego implementację. Jeżeli wcześniej dostatecznie tego nie podkreślono,
zadaniem książki jest nauka *programowania*.  Jednakże w przeciwieństwie do innych podręczników
przedstawione przykłady ilustrujące oraz ćwiczenia skupiają się na zadaniach związanych z |NLP|.
Książka przedstawia *teorie* zasadnicze dla omawianej partii materiału, nie unikając
szczegółowych analiz lingwistycznych czy informatycznych poszczególnych kwestii.
Autorzy starali się zachować *praktyczny* charakter podręcznika,
utrzymując równowagę pomiędzy wiedzą teoretyczną a jej zastosowaniem, przedstawiając istniejące
zbieżności i problemy. Co jednak najważniejsze, trudno byłoby przebrnąć przez cały materiał,
gdyby nie był on dostatecznie *atrakcyjny*, dlatego też
w treści przedstawiono wiele zastosowań i przykładów, które są interesujące, zabawne, czasem wręcz dziwaczne.

Warto podkreślić, iż opracowanie nie ma charakteru encyklopedycznego. Zarówno omówienie programowania w Pythonie, jak i tematyki związanej z |NLP|
jest wybiórcze i przedstawione w formie podręcznika do samodzielnej nauki. Szczegółową dokumentację można odnaleźć przeszukując materiały dostępne odpowiednio na |PYTHON-URL| oraz |NLTK-URL|.

Książka nie stanowi też zaawansowanego podręcznika z zakresu informatyki.
Poziom prezentowanego materiału waha się pomiędzy etapem początkującym a średniozaawansowanym, z racji iż
jest on skierowany do czytelników pragnących nauczyć się, jak analizować
tekst przy użyciu języka programowania Python oraz pakietu Natural Language Toolkit.
Zainteresowanym bardziej zaawansowanym poznaniem algorytmów wykorzystanych w |NLTK|,
proponujemy przestudiowanie sekcji dotyczącej kodu na stronie |NLTK-URL|.
Warto również zapoznać się z pozostałym materiałami i źródłami cytowanymi w podręczniku.

-----------------------
Czego można się nauczyć
-----------------------

Studiując przedstawiony materiał, czytelnik dowiaduje się:

* w jaki sposób proste programy pomagają w manipulacji i analizie
  danych językowych oraz, co najważniejsze, jak samodzielnie pisać takie aplikacje;
* jak koncepcje lingwistyczne oraz związane z dziedziną |NLP| mogą posłużyć w opisie
  i badaniu języka;
* jak korzystać z algorytmów i struktur danych w zadaniach związanych z |NLP|;
* w jaki sposób zapisywać informacje językowe w standardowych formatach oraz jak wykorzystać dane
  do oszacowania skuteczności technik |NLP|.

W zależności od wcześniejszych doświadczeń, charakteru nabytego wykształcenia oraz rodzaju motywacji związanej z poznaniem dziedziny, jaką jest |NLP|,
czytelnik może z pomocą tej książki rozwinąć różne umiejętności oraz zyskać adekwatną wiedzę teoretyczną, co przedstawiono szczegółowo w tab-goals_.

.. table:: tab-goals

    ====================  ==================================  =============================================================================
    Cel nauki             Wykształcenie humanistyczne         Wykształcenie ścisłe/techniczne
    ====================  ==================================  =============================================================================
    Analiza językowa      Operacje na dużych korpusach,       Wykorzystanie technik z zakresu modelowania danych,
                          badanie modeli lingwistycznych,     eksploracji danych (ang. *data mining*) czy
                          testowanie założeń empirycznych.    odkrywania wiedzy (ang. *knowledge discovery*) w analizie języka naturalnego.
    --------------------  ----------------------------------  -----------------------------------------------------------------------------
    Technologie językowe  Budowanie efektywnych systemów      Wykorzystanie algorytmów lingwistycznych
                          wykonujących zadania lingwistyczne  oraz struktur danych w projektowaniu efektywnego
                          za pomocą aplikacji komputerowych.  oprogramowania służącego do przetwarzania języka naturalnego.
    ====================  ==================================  =============================================================================

    Umiejętności i wiedza, które czytelnik nabywa wraz lekturą książki zależą od wyznaczonych celów i kierunku kształcenia.

-----------------
Struktura książki
-----------------

Wczesne rozdziały uporządkowano według skali trudności wprowadzanych pojęć,
zaczynając od praktycznego wprowadzenia do |NLP|, w ramach którego
przedstawiono jak za pomocą niewielkich programów napisanych Pythonie łatwo
wykonać proste zadania analityczne oparte na ciekawych materiałach tekstowych (rozdziały 1-3).
Rozdział czwarty omawia podstawy programowania strukturalnego,
co ma na celu zebranie tematów i pojęć związanych z programowaniem
rozproszonych w trzech poprzedzających rozdziałach.
W dalszej części podręcznika ilość wprowadzanego materiału wzrasta, a kolejne rozdziały
poświęcone są omówieniu zasadniczych kwestii związanych z przetwarzaniem danych językowych:
oznaczaniu części mowy (tagowaniu), klasyfikacji tekstu oraz ekstrakcji informacji (rozdziały 5-7).
Kolejne trzy rozdziały przedstawiają techniki parsowania (rozbioru gramatycznego) zdań,
rozpoznawania ich budowy składniowej oraz konstruowania reprezentacji semantycznych (znaczeniowych)(rozdziały 8-10).
Ostatni rozdział skupia się na efektywnym zarządzaniu danymi językowymi (rozdział 11).
Podręcznik zawiera również posłowie rozważające rozwój historyczny oraz przyszłość |NLP|.

W treści poszczególnych rozdziałów na przemian występują dwa style prezentacji.
W pierwszym z nich centrum stanowi język naturalny. Jest on poddawany analizie;
badane są różne koncepcje lingwistyczne, a przykładowe programy funkcjonują jako narzędzia pomocne w dyskusji.
Pojawiają się elementy Pythona, które nie zostały uprzednio wprowadzone w sposób systematyczny, aby czytelnik
mógł zrozumieć cel ich zastosowania, zanim zagłębi się w szczegóły techniczne.
Przypomina to naukę formułek w języku obcym |mdash| można np. skutecznie spytać obcokrajowca o drogę, nie znając teoretycznych zasad rządzących tworzeniem zdań pytających.
Drugi styl prezentacji skupia się na zasadach rządzących językiem programowania.
Analizujemy programy, badamy algorytmy, natomiast przykłady językowe odgrywają rolę pomocniczą.

Każdy rozdział zawiera zestaw ćwiczeń o zróżnicowanym poziomie zaawansowania,
które służą jako podsumowanie materiału.
Zastosowano następujący podział zadań ze względu na ich poziom trudności:
|easy| łatwe ćwiczenia wymagające drobnych modyfikacji przedstawionych przykładów lub inne proste zadania;
|soso| ćwiczenia o średnim stopniu trudności, w których materiał jest badany dokładniej |mdash| wymagają one uważnej analizy i przemyślanych rozwiązań;
|hard| ćwiczenia zaawansowane o charakterze otwartym, stanowiące wyzwanie dla czytelnika, weryfikują pełne zrozumienie przedstawianej treści oraz wymagają nieszablonowego myślenia.
(niezalecane dla rozpoczynających przygodę z programowaniem).

Ponadto każdy z rozdziałów zawiera listę polecanych publikacji oraz internetową sekcję |bdquo|materiały uzupełniające|rdquo|,
dostępną na stronie |NLTK-URL|, przedstawiającą bardziej zaawansowane źródła wiedzy oraz powiązane witryny internetowe. W witrynie można również znaleźć wszystkie fragmenty kodu przedstawione w danym rozdziale.

----------------
Dlaczego Python?
----------------

Python jest prostym w nauce, potężnym językiem programowania, oferującym duże możliwości
w zakresie przetwarzania danych językowych. 
Jest on dostępny bezpłatnie na stronie internetowej ``http://www.python.org/``.
Wersje instalacyjne są dostępne dla wszystkich popularnych systemów operacyjnych.

Poniżej przedstawiono kilkuwierszowy program w Pythonie, który przetwarza plik ``file.txt``,
a następnie wypisuje wszystkie słowa zakończone końcówką ``ing``:

.. doctest-ignore::
    >>> for line in open("file.txt"):
    ...     for word in line.split():
    ...         if word.endswith('ing'):
    ...             print word

Powyższy przykład ilustruje kilka podstawowych elementów programowania w Pythonie.
Odstępy służą *zagnieżdżaniu* fragmentów kodu, dlatego wiersz rozpoczynający się od ``if``
znajduje się w obszarze działania instrukcji wyrażonej w poprzedniej linii zaczynającej się od ``for``.
W tym wypadku gwarantuje to, iż test na obecność końcówki ``ing`` zostanie wykonany dla każdego słowa.
Po drugie Python jest językiem *zorientowanym obiektowo* |mdash| każda zmienna stanowi obiekt
posiadający określone atrybuty (właśności) i metody. Przykładowo wartość zmiennej ``line``
jest czymś więcej niż tylko sekwencją znaków. W istocie reprezentuje ona obiekt typu string (łańcuch),
który posiada m.in. metodę (operację) ``split()``, która wyodrębnia słowa z linii tekstu.
Chcąc zastosować metodę dla danego obiektu, należy wpisać nazwę obiektu, a następnie nazwę metody poprzedzoną kropką, np. ``line.split()``.
Po trzecie metody mogą posiadać *argumenty* wyrażane w nawiasach. Na przykład w przedstawionym programie metoda  ``endswith`` zawiera argument ``'ing'``
wskazujący, że poszukiwane są tylko słowa zakończone na `ing`:lx:. 
Co jednak najważniejsze, Python jest językiem o czytelnym zapisie,
w związku z czym nietrudno domyślić się, jakie zadanie pełni dany ciąg instrukcji,
nawet bez doświadczenia w programowaniu.

Wybraliśmy język programowania Python ze względu na łatwość przyswajania obowiązujących w nim zasad,
nieskomplikowaną składnię i semantykę, jak również szerokie możliwości przetwarzania łańcuchów tekstowych.
Jako język interpretowany, Python ułatwia interaktywne eksperymentowanie.
Będąc językiem zorientowanym obiektowo, pozwala on na prostą hermetyzację
i wielokrotne wykorzystanie danych i metod. Python jest również dynamiczny |mdash|
umożliwia dodawanie właściwości do obiektów na bieżąco, natomiast typy zmiennych są
przydzielane dynamicznie, ułatwiając szybki rozwój aplikacji.
Warto także nadmienić, że język ten zawiera obszerny zestaw bibliotek standardowych,
w tym komponenty umożliwiające programowanie elementów graficznych, przetwarzanie danych numerycznych
oraz łączność z siecią internet.

Python jest szeroko wykorzystywany w sektorze komercyjnym i badaniach naukowych, a w edukacji jego popularność ma skalę międzynarodową.
Programiści często chwalą go jako środek do osiągnięcia zwiększonej produktywności, jakości oraz obsługiwalności projektowanego oprogramowania.
O historiach udanych projektów opartych na Pythonie można poczytać na stronie internetowej ``http://www.python.org/about/success/``.

Pakiet |NLTK| stanowi infrastrukturę, która może posłużyć do konstruowania programów związanych z |NLP|
w Pythonie. Zawiera on podstawowe klasy dla reprezentacji danych związanych z przetwarzaniem języka naturalnego;
standardowe interfejsy umożliwiające wykonywanie zadań, takich jak: oznaczanie części mowy (ang. *part-of-speech tagging*),
parsowanie (rozbiór) składniowe, czy klasyfikację tekstu; a także standardowe implementacje dla każdego typu zadań.
Łącząc wymienione elementy, można efektywnie rozwiązać nawet bardzo złożone problemy.

|NLTK| zawiera obszerną dokumentację. Poza niniejszym podręcznikiem
można skorzystać ze strony internetowej |NLTK-URL|, na której dostępna jest dokumentacja API
szczegółowo opisująca każdy moduł, klasę oraz funkję stanowiące elementy pakietu, wyszczególniając
odpowiednie parametry oraz przedstawiając przykłady ich użycia.
W witrynie można również odnaleźć wiele samouczków popartych licznymi przykładami i zadaniami przeznaczonymi dla
użytkowników, programistów i instruktorów.

-----------------------
Wymagane oprogramowanie
-----------------------

Chcąc w pełni korzystać z możliwości opisanych w podręczniku, należy zainstalować kilka bezpłatnych pakietów oprogramowania.
Aktualne odnośniki do plików instalacyjnych oraz odpowiednie instrukcje znajdują się na stronie |NLTK-URL|.

:Python:
    Materiał prezentowany w książce zakłada, że czytelnik posiada zainstalowany język programowania Python w wersji 2.4 lub 2.5.
    Postaramy się dostosować |NLTK| do Pythona w wersji 3.0, jak tylko powiązane biblioteki zostaną stosownie zmodyfikowane.

:NLTK:
    Przykłady zawarte w podręczniku opierają się na pakiecie |NLTK| w wersji 2.0.  Późniejsze edycje |NLTK| są zgodne z poprzednimi wersjami.

:NLTK-Data:
    Korpusy językowe analizowane i przetwarzane w podręczniku.

:NumPy: (zalecane)
    Biblioteka wykorzystywana do wykonywania obliczeń naukowych, wspierająca tablice wielowymiarowe i algebrę liniową,
    wymagana przy niektórych zadaniach związanych z obliczaniem prawdopodobieństwa, oznaczaniem części mowy, grupowaniem (analizą skupień, ang. *clustering*) czy klasyfikacją tekstu.

:Matplotlib: (zalecane)
    Biblioteka wspomagająca tworzenie dwuwymiarowych obrazów służących do wizualizacji danych,
    wykorzystywana w niektórych fragmentach kodu wyświetlających wykresy liniowe lub słupkowe.

:NetworkX: (opcjonalne)
    Biblioteka służąca do przechowywania i wykonywania operacji na grafach, składających się z
    węzłów i krawędzi. Dla wizualizacji sieci semantycznych, warto również zainstalować bibliotekę *Graphviz*.

:Prover9: (opcjonalne)
    Biblioteka zajmująca się automatycznym dowodzeniem twierdzeń dla logiki pierwszego rzędu oraz logiki równościowej, wykorzystywana
    do wnioskowania w analizie językowej.


-------------------------------
Natural Language Toolkit (NLTK)
-------------------------------

|NLTK| powstał w 2001 roku jako element zajęć z lingwistyki informatycznej
na wydziale informatyki Uniwersytetu Pensylwanii.
Od tego czasu jest on stale rozwijany i wzbogacany przy współpracy kilkudziesięciu osób.
Pakiet został wdrożony w programach ćwiczeń na wielu uczelniach wyższych i stanowi podstawę
wielu projektów badawczych. W tab-modules_ zawarto listę najważniejszych modułów wchodzących w skład pakietu |NLTK|.

.. table:: tab-modules

   ================================  ===========================  =================================================================================================
   Rodzaj zadania                    Moduł NLTK                   Funkcje
   ================================  ===========================  =================================================================================================
   dostęp do korpusów                nltk.corpus                  ujednolicone interfejsy dla korpusów i zasobów leksykalnych
   przetwarzanie łańcuchów           nltk.tokenize, nltk.stem     tokenizery, tokenizery zdaniowe, stemmery
   znajdowanie kolokacji             nltk.collocations            test t Welcha, test zgodności chi-kwadrat, punktowa informacja wzajemna 
   oznaczanie części mowy            nltk.tag                     tagery: n-gram, backoff, Brill; ukryte modele Markowa (HMM), TnT
   klasyfikacja tekstu               nltk.classify, nltk.cluster  drzewa decyzyjne, maksymalna entropia, naiwny klasyfikator Bayesa, algorytm EM, metoda k-średnich
   chunking                          nltk.chunk                   wyrażenia regularne, n-gramy, jednostki nazewnicze
   parsowanie                        nltk.parse                   tablicowe, oparte na atrybutach, unifikacyjne, probabilistyczne, zależnościowe
   interpretacja semantyczna         nltk.sem, nltk.inference     rachunek lambda, logika pierwszego rzędu, weryfikacja modelu
   ocena efektywności przetwarzania  nltk.metrics                 dokładność, pełność, współczynniki zgodności
   prawdopodobieństwo i szacowanie   nltk.probability             rozkład częstości, wygładzony rozkład probabilistyczny
   aplikacje                         nltk.app, nltk.chat          graficzny interfejs konkordacyjny, parsery, przeglądarka bazy WordNet, chatboty
   badania lingwistyczne             nltk.toolbox                 manipulacja danymi zapisanymi w formacie SIL Toolbox
   ================================  ===========================  =================================================================================================

   Zadania związane z przetwarzaniem języka, odpowiadające im moduły pakietu NLTK oraz przykładowe funkcje

Pakiet |NLTK| zaprojektowano pod kątem realizacji czterech podstawowych założeń:

:Prostota: Intuicyjna struktura wraz z licznymi
    elementami konstrukcyjnymi, zapewniająca użytkownikom nabycie praktycznej
    wiedzy w zakresie |NLP| bez niepotrzebnego angażowania się w monotonne rutyny
    typowe dla przetwarzania oznaczonych danych językowych.
:Konsekwencja: Ujednolicona platforma z konsekwentnie zaprojektowanymi
    interfejsami i strukturami danych oraz łatwymi do odgadnięcia i przyswojenia nazwami metod.
:Możliwości rozbudowy: Struktura, do której łatwo dołączyć nowe moduły programowe, łącznie z
    alternatywnymi implementacjami i konkurencyjnymi rozwiązaniami tych samych problemów.
:Modułowość: Komponenty umożliwiające ich niezależne wykorzystanie bez potrzeby zrozumienia
    pozostałych elementów pakietu

Powyższe cele są w opozycji do trzech potencjalnie użytecznych cech, których
celowo starano się unikać podczas projektowania i rozwoju elementów |NLTK|.
Po pierwsze pomimo, iż pakiet oferuje szeroki zakres funkcji, nie ma on
natury encyklopedycznej |mdash| |NLTK| jest pakietem narzędzi, a nie systemem;
jego dalszy rozwój będzie zależał od ewolucji dziedziny, jaką jest |NLP|. 
Po drugie, pakiet jest wystarczająco wydajny, aby radzić sobie z autentycznymi zadaniami,
jednakże nie został on zoptymalizowany pod kątem szybkości działania,
co wymagałoby zastosowania dużo bardziej złożonych algorytmów lub
implementacji w językach programowania niskiego poziomu, np. C czy C++.
W efekcie kod stałby się mniej czytelny, a oprogramowanie trudniejsze w instalacji.
Po trzecie, autorzy starali się unikać wyszukanych sztuczek programistycznych,
kierując się przekonaniem, że jasne implementacje mają przewagę nad
tymi bardziej efektywnymi lecz trudnymi do odszyfrowania.


---------------
Dla nauczycieli
---------------

Analiza języka naturalnego stanowi najczęściej przedmiot zajęć prowadzonych
w ramach jednego semestru studiów licencjackich, inżynierskich lub uzupełniających magisterskich.
Wielu wykładowców zauważa, iż trudno jest omówić zarówno teoretyczne, jak i praktyczne elementy
związane z tematem w tak krótkim czasie. Niektóre zajęcia skupiają się na teorii, wykluczając tym samym
elementy praktyczne i pozbawiając studentów wyzwań płynących z samodzielnego pisania programów
służących do przetwarzania języka. W innych przypadkach, program nauczania ma na celu jedynie przedstawienie
elementów programowania dla lingwistów, bez przykładania uwagi do treści związanych z |NLP|.
Pakiet |NLTK| powstał, aby zaradzić tego typu problemom i umożliwić omówienie znacznej ilości teorii oraz
materiału praktycznego w ramach jednosemestralnego kursu, nawet jeśli studenci nie posiadają doświadczenia w programowaniu.
    
Znaczna część dowolnego programu nauczania związanego z |NLP| przedstawia
zwykle różne algorytmy i struktury danych. Same w sobie stanowią nieatrakcyjną teorię,
natomiast z pomocą pakietu |NLTK| |bdquo|nabierają życia|rdquo| dzięki
interaktywnym interfejsom użytkownika, umożliwiającym podgląd działania algorytmów krok po kroku.
Większość komponentów |NLTK| zawiera demonstracje przedstawiające wykonanie interesującego zadania
bez potrzeby wprowadzania danych przez użytkownika.
Interaktywna prezentacja oparta na przykładach z podręcznika stanowi efektowny sposób prezentacji materiału.
Demonstracje można uruchomić w środowisku Pythona, zaobserwować czym się one zajmują, a następnie zmodyfikować je, aby
dogłębniej zbadać dany temat praktyczny lub teoretyczny.

Podręcznik zawiera setki ćwiczeń, które mogą posłużyć
jako podstawa oceny pracy studentów. Najprostsze z nich wymagają jedynie
zmodyfikowania przedstawionego w części teoretycznej programu, aby móc
odpowiedzieć na zadane pytanie. Z drugiej strony pakiet |NLTK|
może posłużyć jako elastyczna platforma programistyczna dla wielu projektów dyplomowych,
dzięki przygotowanym, standardowym implementacjom wszystkich podstawowych struktur danych
i algorytmów, interfejsom dla kilkudziesięciu popularnych zbiorów danych (korpusów), a także
elastycznej architekturze umożliwiającej wprowadzanie dalszych rozszerzeń. Dodatkowe informacje
dla nauczycieli posługujących się |NLTK| są dostępne na stronie internetowej pakietu.

|nopar|  
Autorzy wyrażają przekonanie, iż wyjątkowość książki przejawia się w tym, iż umożliwia ona studentom
pozyskanie spójnej architektury do nauki przetwarzania języka naturalnego w kontekście programistycznym.
To co wyróżnia przedstawiony materiał, to silne zespolenie treści i ćwiczeń z elementami pakietu |NLTK|,
zapewniające studentom |mdash| nawet tym bez doświadczenia w programowaniu |mdash|
praktyczny wstęp do dziedziny, jaką jest |NLP|.
Po ukończeniu całego kursu studenci będą przygotowani, aby przejść
do bardziej zaawansowanych podręczników, np. *Speech and
Language Processing* autorstwa Jurafsky'ego i Martina (wydawn. Prentice Hall, 2008).

Niniejsza książka przedstawia koncepcje związane z programowaniem w dość nietypowej kolejności, zaczynając
od nietrywialnego typu danych, jakim są listy łańcuchów, a następnie wprowadzając
nietrywialne struktury sterujące wykonaniem programu, takie jak wyrażenia listowe oraz instrukcje warunkowe.
Dzięki znajomości tych wyrażeń można od razu zająć się praktycznym przetwarzaniem języka.
Dopiero kiedy jest to konieczne, powracamy do systematycznej prezentacji
podstawowych pojęć, jak łańcuchy, pętle, pliki itd.
W ten sposób omawiamy taką samą porcję materiału jak ma to miejsce w bardziej konwencjonalnych podręcznikach,
nie stawiając jednak wymogu, aby czytelnicy byli przede wszystkim zainteresowani nauką języka programowania Python.

Poniższa tabela przedstawia dwa przykładowe, możliwe rozkłady zajęć dydaktycznych.
Pierwszy z nich skonstruowano pod kątem studentów kierunków humanistycznych, natomiast drugi
pasuje bardziej do kierunków ścisłych i technicznych. Można przygotować własny plan, omawiający pierwszych pięć
tematów, a następnie poświęcić pozostały, dostępny czas na omówienie wybranej tematyki, np.
klasyfikacji tekstu (rozdziały 6-7), składni (rozdziału 8-9),
semantyki (rozdział 10) czy zarządzania danymi językowymi (rozdział 11).

.. table:: tab-course-plans

   ===============================================  ====================  =========================
   Rozdział                                         Profil humanistyczny  Nauki ścisłe i techniczne
   ===============================================  ====================  =========================
   1  Przetwarzanie języka w Pythonie               2-4                   2
   2  Dostęp do korpusów i zasobów leksykalnych     2-4                   2
   3  Przetwarzanie tekstu niesformatowanego        2-4                   2
   4  Programowanie strukturalne                    2-4                   1-2
   5  Kategoryzacja i oznaczanie słów               2-4                   2-4
   6  Nauka klasyfikacji tekstu                     0-2                   2-4
   7  Ekstrakcja informacji z tekstu                2                     2-4
   8  Analiza składniowa zdań                       2-4                   2-4
   9  Budowanie gramatyk opartych na atrybutach     2-4                   1-4
   10 Analiza znaczeniowa zdań                      1-2                   1-4
   11 Zarządzanie danymi językowymi                 1-2                   1-4
   Razem                                            18-36                 18-36
   ===============================================  ====================  =========================

   Sugerowany rozkład zajęć dydaktycznych; szacunkowa liczba godzin przypadająca na rozdział

-----------------------------
Konwencje użyte w podręczniku
-----------------------------
 
W podręczniku obowiązują następujące konwencje związane z prezentacją materiału: 

`Pogrubienie`:dt: -- oznacza nowy termin. 

*Kursywa* -- w treści odnosi się do przykładów językowych,
tytułów tekstów i adresów internetowych; stosowana także przy podawaniu nazw i rozszerzeń plików. 

``Test o stałej szerokości`` -- w listingach programów,
a także w treści, odnosząc się do elementów programistycznych, 
jak np. nazwy funkcji lub zmiennych, deklaracji lub słów kluczowych Pythona;
stosowany także w odniesieniu do nazw programów.
 
``Tekst pogrubiony o stałej szerokości`` -- polecenia lub inny tekst, który wymaga ręcznego
wprowadzenia przez użytkownika.
 
``Kursywa o stałej szerokości`` -- tekst, który powinien zostać zastąpiony wartościami
wprowadzonymi przez użytkownika lub określonymi z kontekstu; używana także dla metazmiennych w przykładowych programach.

.. note:: Ta ikona oznacza poradę, sugestię lub ogólną uwagę.

.. caution:: Ta ikona oznacza ostrzeżenie lub sugeruje zachowanie ostrożności.

------------------------------
Wykorzystanie załączonego kodu
------------------------------

Podręcznik ma służyć jako narzędzie w realizacji założonych celów. Dlatego też, generalnie można
wykorzystywać fragmenty kodu zawartego w książce we własnych programach i dokumentach. Nie jest w tym celu wymagana
specjalna zgoda, z wyjątkiem sytuacji, kiedy wykorzystane są znaczne ilości kodu. Na przykład,
pisząc program, który zawiera kilka fragmentów kodu z tego podręcznika, pozwolenie nie jest konieczne.
Natomiast sprzedaż lub rozprowadzanie płyt CD-ROM z przykładami z tej książki lub innych publikacji wydawnictwa
O'Reilly wymaga stosownej zgody. Odpowiedź na pytanie wyrażona cytatem z podręcznika i fragmentem kodu
nie wymaga pozwolenia, podczas gdy załączenie znacznej liczby przykładów z książki we własnych produktach
lub dokumentacji wymaga otrzymania zgody.

Jesteśmy wdzięczni za podawanie źródeł, choć nie jest to konieczne. Odnośnik powinien zwykle zawierać tytuł źródła,
autorów, wydawcę oraz numer ISBN. Na przykład: Przetwarzanie języka naturalnego w Pythonie,
Steven Bird, Ewan Klein i Edward Loper.  Wydawn. O'Reilly Media, 978-0-596-51649-9.Ó
Jeżeli uważasz, że sposób wykorzystania przykładów wykracza poza udzielone pozwolenie,
skontaktuj się z wydawcą pod adresem e-mail *permissions@oreilly.com*.

--------------
Wyrazy uznania
--------------

Autorzy składają podziękowania następującym osobom za okazane wsparcie i wyrażone opinie dotyczące wcześniejszych wersji dokumentu:
Doug Arnold,
Michaela Atterer,
Greg Aumann,
Kenneth Beesley,
Steven Bethard,
Ondrej Bojar,
Chris Cieri,
Robin Cooper,
Grev Corbett,
James Curran,
Dan Garrette,
Jean Mark Gawron,
Doug Hellmann,
Nitin Indurkhya,
Mark Liberman,
Peter Ljunglöf, 
Stefan M\ |uumlaut|\ ller,
Robin Munn,
Joel Nothman,
Adam Przepiórkowski,
Brandon Rhodes,
Stuart Robinson,
Jussi Salmela,
Kyle Schlansker,
Rob Speer
Richard Sproat.
Dziękujemy również za komentarze studentom i współpracownikom,
a szczególnie uczestnikom letnich kursów |NLP| i lingwistyki w Brazylii, Indiach i Stanach zjednoczonych,
dzięki którym materiały dydaktyczne mogły rozwinąć się do postaci pełnych rozdziałów.
Ta książka nie mogłaby powstać bez udziału członków społeczności ``nltk-dev``,
wymienionej na stronie internetowej pakietu |NLTK|;
którzy poświęcili swoją wiedzę oraz czas dla budowy i rozwoju modułów |NLTK|. 

Przekazujemy wyrazy wdzięczności dla Narodowej Fundacji na rzecz Nauki w USA, Konsorcjum Danych Lingwistycznych i
Edward Clarence Dyason Fellowship, jak również dla Uniwersytetów Pensylwanii, Edynburga i Melbourne za wspieranie prac nad rozwojem podręcznika.

Dziękujemy Julie Steele, Abby Fox, Loranah Dimant oraz pozostałym osobom z zespołu wydawnictwa O'Reilly za organizację
kompleksowej edycji i korekty wstępnych szkiców podręcznika przeprowadzone przez osoby związane ze środowiskami
|NLP| i Pythonem, a także za sprawne dostosowanie narzędzi wydawniczych O'Reilly oraz za precyzyjne wykonanie prac edytorskich

Na koniec przekazujemy wyrazy niezmiernej wdzięczności naszym małżonkom: Kay, Mimo i Jee, za ich
miłość, cierpliwość i wsparcie na przestrzeni lat, podczas których pracowaliśmy nad tą książką.
Mamy nadzieję, że nasze dzieci |mdash| Andrew, Alison, Kirsten, Leonie i Maaike |mdash|
podzielą nasz entuzjazm związany z językiem i informatyką. 

.. LSA 325: Anna Asbury, Dustin Bowers

----------
O autorach
----------

**Steven Bird** jest profesorem nadzwyczajnym
na wydziale informatyki i inżynierii oprogramowania
Uniwersytetu Melbourne oraz adiunktem w 
Konsorcjum Danych Lingwistycznych przy Uniwesytecia Pensylwanii.
Obronił tytuł doktora z fonologii informatycznej na Uniwersytecie w Edynburgu
w roku 1990; jego promotorem był Ewan Klein (współautor podręcznika |mdash| przyp. tłum.).
W późniejszym czasie przeniósł się do Kamerunu, aby prowadzić terenowe badania lingwistyczne związane z
językami plemion Bantu pod patronatem Summer Institute
of Linguistics. Spędził kilka lat
jako wicedyrektor Konsorcjum Danych Lingwistycznych,
gdzie prowadził zespół badawczo-rozwojowy tworzący modele i narzędzia
dla rozbudowanych baz danych zawierających oznaczone dane tekstowe.
Utworzył grupę badawczą zajmującą się technologią badań językowych na Uniwesytecie Melbourne,
gdzie prowadzi również zajęcia na wszystkich poziomach studiów informatycznych pierwszego stopnia.
W roku 2009 Steven pełnił rolę prezesa Stowarzyszenia Lingwistyki Informatycznej (Association for Computational Linguistics, ACL |mdash|).

**Ewan Klein** jest profesorem technologii językowych w Instytucie Informatyki
na Uniwesytecie w Edynburgu. Obronił rozprawę doktorską
z semantyki formalnej na Uniwersytecie Cambridge w roku 1978. Po kilku latach
pracy na Uniwersytetach Sussex i Newcastle upon Tyne, Ewan objął pozycję wykładowcy
w Edynburgu. W 19993 współuczestniczył w tworzeniu grupy badawczej Language Technology Group w Edynburgu, z którą
jest związany do dziś. W latach 2000\ |ndash|\ 2002 
pracował poza uniwersytetem jako kierownik badań dla Edify Corporation z siedzibą w Santa Clara w Kalifornii
w ramach działającej w Edynburgu Natural Language Research Group, gdzie był odpowiedzialny za przetwarzania dialogów ustnych.
Ewan jest byłym prezesem Europejskiej Sekcji Stowarzyszenia Lingwistyki Informatycznej (European Chapter of the Association for
Computational Linguistics) oraz współzałożycielem i koordynatorem projektu European Network of Excellence in Human Language Technologies
(ELSNET).

**Edward Loper** niedawno obronił rozprawę doktorską na Uniwersytecie Pensylwanii związaną z
tematyką uczenia maszynowego (ang. machine learning) w kontekście
przetwarzania języka naturalnego.
Wcześniej, w trakcie studiów magisterskich Edward był studentem w grupie Stevena Birda
na zajęciach z lingwistyki informatycznej w semestrze zimowym 2000;
pozostał na uczelni jako asystent, biorąc czynny udział w rozwoju pakietu |NLTK|. Ponadto pomógł w tworzeniu
dwóch pakietów służacych do dokumentacji i testowania
programów w Pythonie: ``epydoc`` oraz ``doctest``.

--------
Tantiemy
--------

Zysk ze sprzedaży książki zostanie wykorzystany do dalszego rozwoju
pakietu Natural Language Toolkit.

.. figure:: ../images/authors.png
   :scale: 250:100:330

   Edward Loper, Ewan Klein i Steven Bird; Stanford, lipiec 2007 

--------------------------------------------------------------------------


.. include:: footer.rst
.. include:: footer-pl.rst
