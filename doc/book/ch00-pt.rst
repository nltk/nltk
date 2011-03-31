.. -*- mode: rst -*-
.. include:: ../definitions.rst
.. include:: definitions-pt.rst

.. preface::

========
Prefácio
========

|nopar|
Este é um livro sobre Natural Language Processing ou, em português,
Processamento de Linguagem Natural. Por "linguagem natural"
entendemos as linguagens que são utilizadas para comunicações do
dia a dia por seres humanos; línguas como o inglês, o hindi ou o
português. Em contraste com linguagens artificiais como as linguagens
de prograação e notações matemáticas, as linguagens naturais evoluem
à medida que passam de geração em geração, e é difícil descrevê-las por
completo por meio de regras explícitas. Iremos considerar o Natural
Language Processing |mdash| ou, brevemente, |NLP| |mdash| em um sentido
amplo para englobar qualquer tipo de manipulação computacional de
linguagens naturais. Em um extremo, pode ser considerado como
algo tão simples quanto a contagem da frequência de palavras para
comparar diferentes estilos de escrita. No outro extremo, o |NLP|
envolve "compreender" enunciados humanos completos, pelo menos até
o ponto de ser capaz de fornecer respostas úteis a estes.

Tecnologias baseadas em |NLP| estão se tornando cada vez mais difundidas. Por exemplo,
telefones e computadores de mão oferecem suporte a
predição de texto e reconhecimento de escrita; motores de pesquisa para
a web permitem acessar informações contidas em textos não estruturados;
sistemas de tradução automática nos permitem obter textos escritos
em chinês e lê-los em espanhol. Ao disponibilizar interfaces homem-máquina
mais naturais, bem como um acesso mais sofisticado a informações armazenadas,
o prossamento de linguagem tem vindo a desempenhar um papelcentral na
multiliguística sociedade da informação.

Este livro oferece uma introdução bastante acessível ao campo do |PLN|.
Pode ser usado para estudo individual ou como o livro didático para um curso de
processamento de linguagem natural ou de linguística computacional,
ou como um suplemento para cursos de inteligência artificial, text mining ou linguística
de corpora. O livro é intensamente prático, contendo centenas de exemplos detalhados e
exercícios classificados de acordo com as competências.

O livro é baseado na linguagem de programação Python, juntamente com uma biblioteca de código
aberto chamada *Natural Language Toolkit* (|NLTK|). A |NLTK| inclui uma grande quantidade
de código, dados e documentação, todos disponíveis gratuitamente para download em |NLTK-URL|.
Estão disponíveis distribuições para Windows, Macintosh e plataformas Unix.
Recomendamos que você obtenha o Python e a |NLTK|, e que experimente os exemplos e exercícios
ao longo do percurso.

-------
Público
-------

O |NLP| é importante por razões científicas, econômicas, sociais e culturais.
O |NLP| tem sido sujeito a um rápido crescimento decorrência do emprego de suas teorias e métodos
em uma variedade de novas tecnologias de linguagem. 
Por esta razão é importante para uma ampla gama de pessoas ter competências práticas quanto
ao |NLP|. Na indústria, isso inclui as pessoas nos campos da interação homem-máquina, da
análise de informações de negócios e do desenvolvimento de software para a web.
No meio acadêmico, inclui pessoas em áreas que vão da computação em ciências humanas e da lingüística de
corpora aos campos da ciência da computação e da inteligência artificial. (Para muitas pessoas
no meio acadêmico, o |NLP| é conhecido pelo nome de "Lingüística Computacional.")

Este livro destina-se a uma gama diversificada de pessoas que querem aprender a escrever
programas que analisam a linguagem escrita, independente de experiências anteriores em programação:

:Novato no campo da programação?: Os capítulos iniciais do livro são apropriados para leitores
    sem conhecimento prévio de programação, desde que você não tenha medo de enfrentar novos
    conceitos e desenvolver novas habilidades de computação. O livro é replato de exemplos que
    você pode copiar e tentar por si mesmo, juntamente com centenas de exercícios classificados
    de acordo com as competências. Se você precisar de uma introdução mais geral ao Python,
    veja a lista de recursos em ``http://docs.python.org/``.

:Novo no Python?: Programadores experientes podem aprender rapidamente Python suficiente ao utilizar
    este livro para se submergir no Processamento de Linguagem Natural. Todas as características
    relevantes do Python são cuidadosamente explicadas e exemplificadas, e você vai rapidamente começar
    a apreciar a adequação da linguagem para essa área. O índice da linguagem irá ajudá-lo a
    localizar discussões relevantes no livro.

:Já sonhando em Python?: Pule os exemplos de Python e imerja-se no interessante material
    de análise linguística que inicia no chap-introduction_. Você logo estará pondo em prática
    seus conhecimentos neste fascinante domínio.

------
Ênfase
------

Este livro é uma introdução *prática* ao |NLP|. Você aprenderá por exemplos, escreverá programas
reais, e compreenderá o valor de ser capaz de testar uma idéia por meio da implementação.
Se você ainda não tiver ententido, este livro vai lhe ensinar a *programar*. Ao contrário de outros
livros sobre programação, nós fornecemos ilustrações extensa e exercícios no campo do |NLP|.
A abordagem que adotamos é também *TODO:principled*, no sentido que abordamos os fundamentos
teóricos e não nos coibimos de uma cuidadosa análise lingüística e computacional. Nós tentamos
ser *pragmáticos* em encontrar um equilíbrio entre teoria e aplicação, identificando conexões e tensões.
Finalmente, reconhecemos que você não vai passar por isso a menos que seja também *prazeroso*,
e por isso tentamos incluir muitas aplicações e exemplos que são interessantes e divertidos,
por vezes extravagantes.

Lembre-se que este livro não é uma obra de referência. Sua abordagem do Python e do |NLP|
é seletiva, e apresentada em estilo de tutorial. Para material de referência, consulte
a substancial quantidade de recursos disponível em |PYTHON-URL| e |NLTK-URL|.

Este livro não é um texto de ciência computacional avançada. Seu conteúdo varia de
introdutório a intermediári, e é dirigido a leitores que querem aprender a analisar
textos usando o Python e a Natural Language Toolkit. Para saber mais sobre algoritmos
avançados implementados na |NLTK|, você pode examinar seu código Python a partir de
|NLTK-URL|, e consultar os outros materiais citados neste livro.

-----------------------
O que você irá aprender
-----------------------

Ao explorar o material aqui apresentado, voce irá aprender:

* Como programas simples podem ajudá-lo a manipular e analisar
  dados linguísticos, e como escrever estes programas
* Como conceitos chaves do |NLP| e da linguísticas são utilizados para
  descrever e analisar a linguagem
* Como estruturas de dados e algoritmos são utilizados no |NLP|
* Como dados linguísticos são armazenaos em formatos padrão,
  e como estes podem ser utilizados para avalir o desempenho de técnicas
  de |NLP|

Dependendo de seu background, e de suas motivações para interessar-se pelo |NLP|,
você irá obter diferentes tipos de competências e conhecimentos a partir deste
livro, como ilustrado em tab-goals_.

.. table:: tab-goals

    ===================  ==================================  =====================================
    Objetivos            Background em artes e humanidades   Background em ciência e engenharia
    ===================  ==================================  =====================================
    Análise linguística  Manipulação de grandes corpora,     Utilizar tpecnicas em modelagem de
                         exploração de modelos               dados, data mining, e knowledge
                         linguísticos e teste de             discovery para analisar linguagens
                         afirmações empíricas.               naturais.
    -------------------  ----------------------------------  -------------------------------------
    Tecnologia de        Construçã de sistemas robustos      Utilizar algoritmos linguísticos e
    linguagem            para executar tarefas linguísticas  estruturas de dados em softwares
                         com aplicações tecnológicas..       robustos de processamento de
                                                             linguagem.
    ===================  ==================================  =====================================

    Competências e conhecimentos que podem ser obtidos a partir deste livro, dependendo dos objetos
    e do background dos leitores

-----------
Organização
-----------

Os capítulos iniciais estão organizados em ordem de dificuldade conceptual,
iniciando por uma introdução prática ao processamento linguístico que
ensina a investigar coleções de texto interessantes utilizando curtos
programas em Python (Capítulos 1-3). Em seguida apresentamos um
capítulo sobre programação estruturada (Capítulo 4) que consolida os
tópicos sobre programação esparsos nos capítulos anteriores.
Após isto, o ritmo se acelera, e passamos a uma série de capítulos
que abrangem tópicos fundamentais do processamento linguístico:
tagging, classificação e extração de informações (Capítulos 5-7).
Os três capítulos sucessivos exploram formas de se analisar sintaticamente
um período, reconhecer sua estrutura sintática e construir
representações de significado (Capítulos 8-10). O capítulo final
é centrado em dados linguísticos e em como estes podem ser
administrados eficientemente (Capítulo 11). O livro se encerra com
algumas considerações finais que discutem brevemente o passado e o
futuro dete campo.

Dentro de cada capítulo, alternamos entre diferentes estilos de apresentação.
Em um estilo, a linguagem natural é a guia. Analisamos a linguagem,
exploramos conceitos linguísticos e usamos exemplos de
programação em apoio à discussão. Geralmente empregamos construções
em Python que não foram introduzidas sistematicamente, de forma que
você possa ver suas finalidades antes de se imergir nos detalhes
da forma e dos motivos de seu funcionamento. É exatamente como
aprender expressões ideomáticas em uma língua estrangeira: você é
capaz de comprar um doce em uma padaria sem antes ter aprendido
os meandros da formação de frases interrogativas. No outro estilo
de apresentação, a linguagem de programação é a condutora.
Analisaremos programas, exploraremos algoritmos e os exemplos
linguísticos terão função de apoio.

Cada capítulo se encerra com uma série de exercícios classificados
de acordo com as competências, que são úteis para consolidar a
aprendizagem do material. Os exercícios são classificados de
acordo com o seguinte esquema: |easy| para exercicios fáceis
que requerem pequenas modificações aos códigos apresentados nos
exemplos ou outras tarefas simples; |soso| para exercícios
intermediários que exploram algum aspecto do material em maiores
detahes, exigindo uma análise e um projeto cuidadosos; |hard|
para as tarefas difíceis, sem uma única resposta que irão
desafiar sua compreensão do material e obrigar você a pensar
independentemente (leitores novatos em termos de programação
são aconselhados a saltar estes).

Cada capítulo tem uma seção de leituras adicionais e uma seção de
conteúdo complementar online em |NLTK-URL|, com referências para
materiais mais avançados e recursos disponíveis online. Versões
online de todos os códigos de exemplo também estão disponíveis.

-----------------
Por que o Python?
-----------------

O Python é uma linguagem de programação simples mas potente e
de excelente funcionalidade para o processamento de dados
linguísticos. O Python pode ser obtido gratuitamente em
``http://www.python.org/``. Há programas de instalação
disponíveis para todos os sistemas.

Abaixo apresentamos um programa de cinco linhas em Python que
lê o arquivo ``arquivo.txt`` e lista todas as palavras que
terminam em ``ando``:

.. doctest-ignore::
    >>> for line in open("arquivo.txt"):
    ...     for word in line.split():
    ...         if word.endswith('ando'):
    ...             print word

Este programa permite evidenciar algumas das principais características
do Python. Primeiro, espaços em branco são usados para *aninhar* linhas
de código, assim a linha que inicia por ``if`` está inserida no
âmbito da linha anterior que inicia por ``for``; isto garante que o
teste do final em ``ando`` seja exectado para todas as palavras.
Em segundo lugar, o Python é *orientado a objetos*; cada variável é
uma entidade que possui um número definido de atributos e métodos.
Por exemplo, o valor da variável ``line`` não é uma mera sequência de
caracteres. Trata-se de um objeto do tipo string que possui um
"método" (ou operação) chamado ``split()`` que podemos utilizar para
dividir uma linha nas palavras que a compõem. Para executar um método
de um objeto, escrevemos o nome do objeto, seguido por um ponto,
seguido pelo nome do método, por exemplo ``line.split()``. Em terceiro
lugar, os métodos possuem *argumentos* indicados dentro de parênteses.
Assim, neste exemplo, ``word.endswith('ando')`` possui o argumento
``'ando'`` para indicar que queremos as palavras que terminam em
`ando` :lx: e nada além disto. Por último |mdash| e o mais importante |mdash|
a leitura de código em Python é fácil, a tal ponto que é relativamente
fácil deduzir o que um programa faz mesmo se você nunca tenha escrito
um programa antes.

Escolhemos o Python porque ele tem uma curva de aprendizagem baixa,
sua sintaxe e sua semântica são transparentes e por ser dotado
de boa funcionalidade no tratamento de sequências de textos (as
ditas ``strings``). Por ser uma linguagem interpretada, o Python
facilita a exploração interativa. Por ser uma linguagem orientada
a objetos, o Python permite que dados e métodos sejam encapsulados
e reutilizados facilmente. Por ser uma linguagem dinâmica, o Python
permite que novas propriedades sejam acrescentadas aos objetos
durante a execução de um programa, e também permite que o tipo das
variáveis seja alterado dinâmicamente, facilitando um desenvolvimento
rápido. O Python inclui uma longa biblioteca padrão de funções,
com componentes para a programação gráfica, processamento numérico
e conectividade com a web.

O Python é usado intensivamente no meio industrial, na pesquisa
científica e na educação ao redor do mundo. O Python é frequentemente
elogiado pela sua forma de facilitar a produtividade, qualidade e
manutenção de software. Uma coleção de histórias de sucesso do
Python está disponível em ``http://www.python.org/about/success//``.

O |NLTK| estabelece uma infraestrutura que pode ser utilizada para
criar programas de |NLP| em Python. Ele fornece classes básicas para
representar dados relevantes ao processamento de linguagem
natural; interfaces padrão para executar tarefas como o
``part-of-speech tagging`` (classificação gramatical), análise
sintática e classificação textual; bem como implementações padrão
para cada tarefa, que podem ser combinadas para solucionar
problemas complexos.

O |NLTK| é dotado de uma vasta documentação. Além deste livro,
o site em |NLTK-URL| fornece documentação da API para todos
os módulos, classes e funções no toolkit, especificando os
parâmetros e apresentando exemplos de uso. O site também
disponibiliza vários HOWTOs com muitos exemplos e casos de teste,
destinados a usuários, programadores e professores.

----------------------
Exigências de software
----------------------

Para obter o máximo deste livro, você deve instalar uma série de programs gratuitos.
Links para as versões mais recentes e instruções estão disponíveis em |NLTK-URL|.

:Python:
    O material apresentado neste livro toma por base que você esteja utilizando o
    Python nas versões 2.4 ou 2.5. Assumimos o compromisso de atualizar o |NLTK|
    à versão 3.0 do Python uma vez que todas as bibliotecas das quais o |NLTK|
    depende tenham sido atualizadas.

:NLTK:
    Os exemplos de código deste livro usam a versão 2.0 do |NLTK|. Versões sucessivas
    do |NLTK| serão compátiveis com esta.

:NLTK-Data:
    Este pacote contém os corpora linguísticos que são analisados e processados neste livro.

:NumPy: (recomendado)
    Esta é uma biblioteca de computação científica que permite utilizar matrizes
    multidimencionais e algebra linear, exigida para algumas tarefas de probabilidade,
    tagging, clustering e classificação.

:Matplotlib: (recomendado)
    Esta é uma biblioteca para de gráficos em 2D utilizada para visualizar dados,
    e é utilizada em alguns dos exemplos de código deste livro para produzir gráficos
    em linha e de barras.

:NetworkX: (opcional)
    Este é uma biblioteca para armazenar e manipular estruturas de rede que consistem
    em nós e arestas. Para visualizar redes semânticas, instal também a biblioteca
    *Graphviz*.

:Prover9: (opcional)
    Este é um provador de teoremas automatizado para lógica de primeira ordem e
    equacional, utilizado para auxiliar a inferência em processamento linguístico.

-------------------------------
Natural Language Toolkit (NLTK)
-------------------------------

O |NLTK| foi originalmente criado em 2001 como parte de uma disciplina em
linguística computacional no Department of Computer and Information Science
da University of Pennsylvania. Desde então tem sido desenvolvido e acrescido
com a ajuda de dezenas de pessoas. É empregado em disciplinas ministradas em
dezenas de universidades e serve de base para vários projetos de pesquisa.
Veja tab-modules_ para uma lista dos módulos mais importantes do |NLTK|.

.. table:: tab-modules

   ===========================  ===========================  ============================================================
   Tarefa de processamento      Módulos NLTK                 Funcionalidades
   ===========================  ===========================  ============================================================
   Acessar corpora              nltk.corpus                  interfaces padrão para córpora e léxicos
   Processamento de strings     nltk.tokenize, nltk.stem     tokenizers, sentence tokenizers, stemmers
   Busca de colocações          nltk.collocations            t-test, chi-squared, point-wise mutual information 
   Part-of-speech tagging       nltk.tag                     n-gram, backoff, Brill, HMM, TnT
   Classificação                nltk.classify, nltk.cluster  árvores de decisão, máxima entropia, naive Bayes, EM, k-means  
   Chunking                     nltk.chunk                   expressões regulares, n-gram, named-entity
   Parsing                      nltk.parse                   chart, feature-based, unification, probabilistic, dependency
   Interpretação semântica      nltk.sem, nltk.inference     lambda calculus, lógica de primeira ordem, avaliação de modelos
   Métricas de avaliação        nltk.metrics                 precisão, recall, concordância de coeficientes
   Probabilidade e estimas      nltk.probability             distribuições de frequência, smoothed probability distributions
   Aplicações                   nltk.app, nltk.chat          graphical concordancer, parsers, WordNet browser, chatbots
   Trabalho de campo            nltk.toolbox                 manipulação de dados no formato SIL Toolbox
   ===========================  ===========================  ============================================================

   Tarefas de processamento linguistico e os múdulos NLTK correspondentes com exemplos de funcionalidades

O |NLTK| foi desenvolvido com quatro objetivos primários em mente:

:Simplicidade: Fornecer um framework intuitivo junto a substanciais blocos de
    construção, dotando os usuários de um conhecimento prático de
    |NLP| sem prender-se nas tediosas tarefas de "arrumação da
    casa" geralmente associadas com o processamento de dados
    linguísticos anotados.
:Consistência: Fornecer um framework unificado com 
    interfaces e estruturas de dados consistentes, e nomes de método
    facilmente conjecturáveis
:Extensibilidade: Fornecer uma estrutura na qual novos módulos de
    software possam ser acomodados facilmente, incluindo implementações
    alternativas a abordagens diversas para uma mesma tarefa
:Modularidade: Fornecer componentes que possam ser utilizados
    independentemente sem a necessidade de compreender o restante
    do toolkit

Em contraste com estes objetivos há três não exigências |mdash|
qualidades potencialmente úteis que deliberadamente evidamos. Primeiro,
apesar do toolkit disponibiliar uma ampla variedade de funções,
não é enciclopédico; trata-se de um toolkit, não de um sistema,
e continuará a evoluir junto ao campo de |NLP|. Segundo, apesar do
toolkit ser suficientemente eficiente para executar tarefas concretas,
não é otimizado para o desempenho durante a execução; otimizações
deste tipo geralente envolvem algoritmos mais complexos ou
implementações em linguagens de programação de menor nível como
C ou C++. Isto teria tornado o software menos legível e sua
instalação mais difícil. Terceiro, tentamos evitar truques de
programação, pois acreditamos que implementações claras são
preferíveis àquelas engenhosas mas indecifráveis.


----------------
Para professores
----------------

O Natural Language Processing é geralmente ensinadodentro dos limites
de uma disciplina semestre em níveis avançados de graduação ou de
pós-graduação. Muitos professores consideram difícil explorar
tanto os aspectos teóricos quanto os práticos deste tema em um
período de tempo tão curto. Algumas disciplinas se focam na teoria
em detrimento de exercícios práticos, privando os alunos do
desafio e da excitação de escrever programas que processem automaticamente
a linguagem. Outras são simplesmente orientadas ao ensino de
programação para linguistas, sem considerar qualquer conteúdo
significante de |NLP|. O |NLTK| foi originalmente desenvolvido
em resposta a este problema, fazendo com que fosse possível
ensinar uma quantidade substancial de teoria e prática durante uma
disciplina semestral, mesmo quando os estudantes não tivessem
nenhuma experiência anterior em programação.

Uma parcela significante de qualquer sílabo em |NLP| refere-se
a algoritmos e estruturas de dados. Isolamente, estes tópicos
podem ser bastante áridos, mas o |NLTK| os traz à vida com a
ajuda de interfaces de usuário gráficas e interativas que
tornam possível a visualização passo-a-passo dos algoritmos.
A maioria dos componentes do |NLTK| é dotada de uma demonstração
que executa alguma tarefa interessante sem a exigência de
alguma preparação especial por parte do usuário. Uma maneira
eficaz de ensinar este conteúdo é por meio de uma apresentação
interativa dos exemplos deste livro, utilizando-os em uma
sessão do Python, apontando o que fazem e modificando-os para
explorar certas implicações empíricas e teóricas.
    
Este livro contém centenas de exercícios que podem ser utilizados
como base para tarefas dos alunos. Os exercícios mais simples
envolvem a modificação de um fragmento de programa fornecido de
forma a responder uma questão concreta. Na outra ponta do espectro,
o |NLTK| fornece um framework flexível para projetos de pesquisa em
nível de graduação, com implementações padrão de todas as estruturas
de dados e algoritmos basilares, interfaces para dezenas de
conjuntos de dados amplamente utilizados (corpora) e uma arquitetura
flexível e extensível. Suporte adicional para o ensino utilizando
o |NLTK| está disponível no site do |NLTK|.

|nopar|  
Acreditamos que este livro seja único em oferecer um framework
completo para que estudantes aprendam sobre |NLP| no mesmo contexto
em que aprendem a programar. O que distingue este material é a
estreita ligação entre seus capítulos e exercícios com o |NLTK|,
representando para os estudantes |mdash| mesmo para aqueles sem experiência anterior
em programação |mdash| uma introdução prática ao |NLP|.
Após completar este material, os estudantes estarão prontos
para aventurar-se com um dos livros mais avançados, como o
*Speech and Language Processing*, de Jurafsky e Martin (Prentice Hall, 2008).

Este livro apresenta conceitos de programação em uma ordem não
costumeira, iniciando com um tipo de dados não trivial |mdash| uma
lista de strings |mdash| para então introduzir estruturas de controle
não triviais como ``comprehensions`` e ``conditionals``. Estas
expressões nos permitem fazer processamento linguístico útil desde
o início. Uma vez que esta motivação tenha sido atingida, retornamos
a uma apresentação sistemática de conceitos fundamentais como strings,
loops, arquivos e assim por diante. Desta forma, cobrimos o mesmo
terreno das abordagens mais convencionais, sem esperar que os leitores
estejam interessados na linguagem de programação por si própria.

Dois possíveis programas de disciplina estão elencados em tab-course-plans_.
O primeiro assume um público do campo das artes/humanidades, enquanto o
segundo assume um público de ciênca/engenharia. Outros programas possíveis
poderiam se referir aos cinco primeiros capítulos, e então empregar o tempo
estante a um único campo como a classificação textual (Capítulos 6-7),
a sintaxe (Capítulos 8-9), a semântica (Capítulo 10) ou o manuseio de
dados linguísticos (Capítulo 11).

.. table:: tab-course-plans

   ===============================================  ===================  =======================
   Capítulo                                         Artes e humanidades  Ciência e engenharia
   ===============================================  ===================  =======================
   1  Language Processing and Python                2-4                  2
   2  Accessing Text Corpora and Lexical Resources  2-4                  2
   3  Processing Raw Text                           2-4                  2
   4  Writing Structured Programs                   2-4                  1-2
   5  Categorizing and Tagging Words                2-4                  2-4
   6  Learning to Classify Text                     0-2                  2-4
   7  Extracting Information from Text              2                    2-4
   8  Analyzing Sentence Structure                  2-4                  2-4
   9  Building Feature Based Grammars               2-4                  1-4
   10 Analyzing the Meaning of Sentences            1-2                  1-4
   11 Managing Linguistic Data                      1-2                  1-4
   Total                                            18-36                18-36
   ===============================================  ===================  =======================

   Planos de disciplina sugeridos; número aproximados de lições por capítulo

---------------------------------
Convenções empregadas neste livro
---------------------------------

As seguintes convenções tipográficas foram utilizadas neste livro: 

`Negrito`:dt: -- Indica termos novos.

*Itálico* -- Usado dentro de parágrafos para se referir a exemplos linguísticos, o
nome de textos e URLs; também utilizado para nomes de arquivo e extensões de arquivo.

``Largura fixa`` -- Usado para listagem de programas, bem como dentro de parágrafos
para se referir a elementos de programas como nomes de variáveis ou de funções,
comandos e palavras-chave; também é utilizado para nomes de programas.
 
``Largura fixa em negrito`` -- Mostra comandos ou outro tipo de texto que deve
ser digitado literalmente pelo usuáro.
 
``Largura fixa em itálico`` -- Mostra textos que deveriam ser substituídos com
conteúdo fornecido pelo usuário ou por conteúdo determinado pelo contexto;
também é utilizado para metavariáveis dentro de exemplos de código de programas.

.. note:: Este símbolo denota uma dica, uma sugestão ou uma nota em geral.

.. caution:: Este símbolo denota um aviso.

-----------------------------
Utilizando exemplos de código
-----------------------------

Este livro foi escrito para ajudar você a concluir seus trabalhos. No geral, você
pode utilizar os códigos apresentados neste livro em seus programas e na sua
documentação. Você não precisa entrar em contato conoso para pedir permissão a menos
que você esteja reproduzindo uma quantidade significativa do código. Por exemplo,
escrever um programa que utilize vários trechos de código deste livro não requer
nossa permissão. Contudo, vender ou distribuir um CD-ROM com exemplos dos livros da
O'Reilly o requer. Responder a uma pergunta citando este livro e fornecendo um
exemplo de código não requer nossa permissão. Incorporar uma quantidade significativa
de código de exemplo deste livro na documentação de seus produtos requer uma
permissão.

Apreciamos, mas não exigimos, atribuição. Uma atribuição geralmente inclui o título,
o autor, o editor e o ISBN. Por exemplo: Natural Language Processing with Python,
by Steven Bird, Ewan Klein, and Edward Loper.  O'Reilly Media, 978-0-596-51649-9.
Se você considerar que eu emprego dos exemplos de código está além do fair use ou
da permissão explicitada acima, sinta-se livre para entrar em contato conosco
através do email *permissions@oreilly.com*.

----------------
Reconhecimentos
----------------

Os autores reconhecem sua dívidas com as seguintes pessoas pelos
pareceres dados durante os primeiros rascunhos deste livro:

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
Adam Przepiorkowski,
Brandon Rhodes,
Stuart Robinson,
Jussi Salmela,
Kyle Schlansker,
Rob Speer, and
Richard Sproat.
Agradecemos aos vários estudantes e colegas por seus comentários
no material didático que evoluiu nestes capítulos, incluindo
os participantes das escolas de verão em |NLP| e linguistica
no Brazil, na Índia e nos Estados Unidos. Este livro não existiria
sem os membros da comunidade de programadores ``nltk-dev``,
nomeada no site do |NLTK|, que cederam tanto de seus tempos livres
e experiências na construção e extensão do |NLTK|.

Somos agradecidos à U.S. National Science Foundation, ao Linguistic Data Consortium,
ao Edward Clarence Dyason Fellowship,
e às Universidades de Pennsylvania, Edinburgh, e Melbourne por apoiar nosso
trabalho neste livro.

Agradecemos Julie Steele, Abby Fox, Loranah Dimant, e os demais membros do grupo
O'Reilly por organizar revisões completas de nossos rascunhos a cargo das
comunidades de |NLP| e do Python, por adaptar de boa-vontade as ferramentas de produção
da O'Reilly às nossas exigências e pelo meticuloso trabalho de copy-editing.

Por fim, reconhecemos nossa enorme dívida de gratidão a nossas companheiras,
Kay, Mimo e Jee, por seu amor, paciência e apoio durante todos os anos em que
trabalhamos neste livro. Esperamos que nosss filhos |mdash| Andrew, Alison,
Kirsten, Leonie e Maaike |mdash| sejam contagiados por nosso entusiasmo
pelas línguas e pela computação a partir destas páginas.

.. LSA 325: Anna Asbury, Dustin Bowers

-----------------
Sobre os autores
-----------------

**Steven Bird** é um Associate Professor junto ao
Department of Computer Science and Software Engineering
da University of Melbourne, e Senior Research Associate junto ao
Linguistic Data Consortium da University of Pennsylvania.
Obteve um PhD em fonologia computacional junto à University of
Edinburgh em 1990, orientado por Ewan Klein.
Em seguida viajou a Camarões para executar trabalho de campo
linguístico nas linguagens Grassfields Bantu sob os auspícios
do Summer Institute of Linguistics. Recentemente foi durante
vários anos um Associate Director do Linguistic Data Consortium
onde coordenou um grupo de pesquisa e desenvolvimento para
criar modelos e ferramentas para grandes bancos de dados de
textos anotados. Junto à Melbourne University,
criou um grupo de pesquisa em tecnologia de linguagem e
ensinou em todos os níveis do currículo de graduação em
ciências da computação. Em 2009, Steven é o presidente da
Association for Computational Linguistics.

**Ewan Klein** é professor de Language Technology junto à School of
Informatics da University of Edinburgh. Completou seu PhD em
semântica formal junto à University of Cambridge em 1978. Após
alguns anos trabalhando junto à University of Sussex e University of Newcastle upon Tyne,
Ewan assumiu uma posição de professor em Edinburgh. Fez parte
da criação do Edinburgh's Language Technology Group em 1993, 
do qual tem sido um membro participativo desde então. Entre 2000\ |ndash|\ 2002,
está afastado da Universidade para servir de Research Manager junto ao
Natural Language Research Group, de Edinburgh, da Edify Corporation,
Santa Clara, e era o responsável por processamento de diálogos
falados. Ewan já foi presidente do capítulo europeu da Association for
Computational Linguistics e é um membro fundador e coordenador da
European Network of Excellence in Human Language Technologies
(ELSNET). 

**Edward Loper** completou recentemente seu PhD em
machine learing para processamento de linguagem natural
junto à University of Pennsylvania. Edward foi aluno do
curso de graduação de Steven em linguística computacional
no outono de 2000, e tornou-se um Teaching Assistant além
de participar no desenvolvimento do NLTK. Além do |NLTK|,
ele ajudou no desenvolvimento de dois pacotes para documentar
e testar software em Python, ``epydoc`` e ``doctest``.

---------
Royalties
---------

Royalties da venda deste livro estão sendo utilizadas para
ajudar no desenvolvimento do Natural Language Toolkit.

.. figure:: ../images/authors.png
   :scale: 250:100:330

   Edward Loper, Ewan Klein e Steven Bird, Stanford, julho de 2007 

--------------------------------------------------------------------------


.. include:: footer.rst

.. include:: footer-pt.rst

