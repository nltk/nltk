~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
PyWordNet - A Python Interface to WordNet
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Overview
========

PyWordNet is a Python_ interface to the WordNet_ database of word
meanings and lexical relationships.&nbsp; (A lexical relationship is a
relationship between words, such as **synonym**, **antonym**,
**hypernym** (``"poodle"`` -> ``"dog"``), and **hyponym**
(``"poodle"`` -> ``"dog"``).

PyWordNet presents a concise interface to WordNet, that allows the
user to type expressions such as ``N['dog']``,
``hyponyms(N['dog'][0])``, and ``closure(ADJ['red'], SYNONYM)`` to
query the database.

If Python is already installed at your site, download PyWordNet from
the project home page, at
http://sourceforge.net/projects/pywordnet. For more information, read
the documentation at the top of the source file, or skip to the
example session `Example Session`_ below.

PyWordNet is hosted on SourceForge_ <IMG
src="http://sourceforge.net/sflogo.php?group_id=27422" width="88"
height="31" border="0" alt="SourceForge Logo"></A>

Copyright (c) 1998-2001 by Oliver Steele. Use is permitted under the
`Artistic License`_.

Requirements
============

Python 1.5 or later, available from http://www.python.org/download/.
(For the MacOS, you can use MacPython, at http://www.python.org/download/download_mac.html.)

WordNet 1.6 or 1.7, available from
http://www.cogsci.princeton.edu/~wn/. (PyWordNet only uses the data
files.)

Other Links
===========
- `Change History`_
- `Installation Instructions`_

.. _`Change History`: changes.html
.. _`Installation Instructions`: install.html

Example Session
===============
``wordnet.py`` contains the core database access functions.
``wntools.py`` contains the utility functions such as ``hyponyms``,
``meet``, ``morphy``, ``closure``, etc.  Importing ``wntools`` imports
all the public functions from both modules:

	>>> from wntools import *

Retrieve a Word from the Noun database:

	>>> N['dog']
	dog(n.)

"Dog" has six senses:

	>>> N['dog'].getSenses()
	('dog' in {noun: dog, domestic dog, Canis familiaris},
	 'dog' in {noun: frump, dog}, 'dog' in {noun: dog},
	 'dog' in {noun: cad, bounder, blackguard, dog, hound, heel},
	 'dog' in {noun: pawl, detent, click, dog},
	 'dog' in {noun: andiron, firedog, dog, dogiron})

Bind the first-listed sense to a variable, for easier access.
(``word[0]`` is shorthand for ``word.getSenses()[0]``.)

	>>> dog = N['dog'][0]
	>>> dog
	'dog' in {noun: dog, domestic dog, Canis familiaris}

Retrieve all the relations, of any kind, that have this sense of "dog"
as the source.  (``dog.getPointers(HYPONYM)`` would retrieve the
hyponyms, or names of subcategories of this sense of "dog".)

	>>> dog.getPointers()
	(hypernym -> {noun: canine, canid},
	 member meronym -> {noun: Canis, genus Canis},
	 member meronym -> {noun: pack},
	 hyponym -> {noun: pooch, doggie, doggy, bow-wow},
	 hyponym -> {noun: cur, mongrel, mutt},
	 hyponym -> {noun: lapdog},
	 hyponym -> {noun: toy dog, toy},
	 hyponym -> {noun: hunting dog},
	 hyponym -> {noun: working dog},
	 hyponym -> {noun: dalmatian, coach dog, carriage dog},
	 hyponym -> {noun: basenji},
	 hyponym -> {noun: pug, pug-dog},
	 hyponym -> {noun: Newfoundland},
	 hyponym -> {noun: Great Pyrenees},
	 hyponym -> {noun: spitz},
	 hyponym -> {noun: griffon, Brussels griffon, Belgian griffon},
	 hyponym -> {noun: corgi, Welsh corgi},
	 hyponym -> {noun: poodle, poodle dog},
	 hyponym -> {noun: Mexican hairless},
	 part holonym -> {noun: flag})

	>>> dog.pointerTargets(MEMBER_MERONYM)
	[{noun: Canis, genus Canis}, {noun: pack}]

Hypernyms of "dog", and their hypernyms, and so on until the links
peter out.  (``hypernyms(dog)`` is a shortcut for the closure of this
particular relationship.)

	>>> closure(dog, HYPERNYM)
	['dog' in {noun: dog, domestic dog, Canis familiaris}, {noun: canine, canid},
	 {noun: carnivore}, {noun: placental, placental mammal, eutherian, eutherian
	  mammal}, {noun: mammal}, {noun: vertebrate, craniate}, {noun: chordate},
	 {noun: animal, animate being, beast, brute, creature, fauna}, {noun: life form,
	  organism, being, living thing}, {noun: entity, something}]
	>>> cat = N['cat']

The ``meet`` of two items is their most subordinate common concept:

	>>> meet(dog, cat[0])
	{noun: carnivore}
	>>> meet(dog, N['person'][0])
	{noun: life form, organism, being, living thing}
	>>> meet(N['thought'][0], N['belief'][0])
	{noun: content, cognitive content, mental object}

Hyponyms of "dog" (n.) that are homophonous with verbs:

	>>> filter(lambda sense:V.get(sense.form),
			   flatten1(map(lambda e:e.senses(), hyponyms(N['dog'][0]))))
	['dog' in {noun: dog, domestic dog, Canis familiaris}, 'pooch' in {noun: pooch,
	  doggie, doggy, bow-wow}, 'toy' in {noun: toy dog, toy}, 'hound' in
	 {noun: hound, hound dog}, 'basset' in {noun: basset, basset hound}, 'cocker' in
	 {noun: cocker spaniel, English cocker spaniel, cocker}, 'bulldog' in {noun:
	  bulldog, English bulldog}]

The first five adjectives that are transitively SIMILAR to red (there
are 71 in all):

	>>> closure(ADJ['red'][0], SIMILAR)
	['red' in {adjective: red, reddish, ruddy, blood-red, carmine, cerise, cherry, cherry-red, crimson, ruby, ruby-red, scarlet}, {adjective: chromatic}, {adjective: amber, brownish-yellow, yellow-brown}, {adjective: amethyst}, {adjective: aureate, gilded, gilt, gold, golden}]

Trace the senses of dog to the top concepts, and display the results
in a readable form:

	>>> from pprint import pprint
	>>> pprint(tree(N['dog'], HYPERNYM))
	[['dog' in {noun: dog, domestic dog, Canis familiaris},
	  [{noun: canine, canid},
	   [{noun: carnivore},
		[{noun: placental, placental mammal, eutherian, eutherian mammal},
		 [{noun: mammal},
		  [{noun: vertebrate, craniate},
		   [{noun: chordate},
			[{noun: animal, animate being, beast, brute, creature, fauna},
			 [{noun: life form, organism, being, living thing},
			  [{noun: entity, something}]]]]]]]]]],
	 ['dog' in {noun: frump, dog},
	  [{noun: unpleasant woman, disagreeable woman},
	   [{noun: unpleasant person, disagreeable person},
		[{noun: unwelcome person, persona non grata},
		 [{noun: person, individual, someone, somebody, mortal, human, soul},
		  [{noun: life form, organism, being, living thing},
		   [{noun: entity, something}]],
		  [{noun: causal agent, cause, causal agency},
		   [{noun: entity, something}]]]]]]],
	 ['dog' in {noun: dog},
	  [{noun: chap, fellow, lad, gent, fella, blighter, cuss},
	   [{noun: male, male person},
		[{noun: person, individual, someone, somebody, mortal, human, soul},
		 [{noun: life form, organism, being, living thing},
		  [{noun: entity, something}]],
		 [{noun: causal agent, cause, causal agency},
		  [{noun: entity, something}]]]]]],
	 ['dog' in {noun: cad, bounder, blackguard, dog, hound, heel},
	  [{noun: villain, scoundrel},
	   [{noun: unwelcome person, persona non grata},
		[{noun: person, individual, someone, somebody, mortal, human, soul},
		 [{noun: life form, organism, being, living thing},
		  [{noun: entity, something}]],
		 [{noun: causal agent, cause, causal agency},
		  [{noun: entity, something}]]]]]],
	 ['dog' in {noun: pawl, detent, click, dog},
	  [{noun: catch, stop},
	   [{noun: restraint, constraint},
		[{noun: device},
		 [{noun: instrumentality, instrumentation},
		  [{noun: artifact, artefact},
		   [{noun: object, physical object}, [{noun: entity, something}]]]]]]]],
	 ['dog' in {noun: andiron, firedog, dog, dogiron},
	  [{noun: support},
	   [{noun: device},
		[{noun: instrumentality, instrumentation},
		 [{noun: artifact, artefact},
		  [{noun: object, physical object}, [{noun: entity, something}]]]]]]]]

<hr>
<address>
<a href="http://www.cs.brandeis.edu/~steele/">Oliver Steele</a><br>
Modified 9/21/2001
</address>

.. _Python: http://www.python.org/
.. _WordNet: http://www.cogsci.princeton.edu/~wn/
.. _SourceForge: http://sourceforge.net
.. _`Artistic License`: http://www.opensource.org/licenses/artistic-license.html
