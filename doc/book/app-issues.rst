.. -*- mode: rst -*-
.. include:: ../definitions.rst

.. _app-issue:

=====================================
Appendix: Known Issues with this Book
=====================================

--------------
General Issues
--------------

* Several topics could not be covered in time for the December deadline.  In some
  cases we decided that they could be dropped.  However, wherever we felt that the
  book should contain these topics, we left in a section (often with notes), so
  that readers could see our intentions and comment accordingly.

* A few the examples in the book depend on functionality which has only just been
  added to NLTK, and will be released as version 0.9.7 in late 2008, from the
  NLTK website at ``http://www.nltk.org/``.

* The further reading sections of each chapter are patchy; some are comprehensive while
  some are minimal.  We intend to make these consistent, providing a representative
  set of pointers to other materials.

* It is difficult for readers to know which exercises at the end of the chapter
  correspond to which sections of the chapter.

------------------------
Visual Formatting Issues
------------------------

* The phrase that appears as the book's subtitle is actually
  intended to appear as the by-line on the top of the front cover,
  following the pattern of other books in the Animal Series.

* Since the book is about language, we hope that the cover will feature an
  animal that is associated with communication, such as a primate or a whale.
  Primates have the advantage that they spend a lot of time in trees, and
  tree structures are a feature of language processing.  Whales have the
  advantage that they spend a lot of time far beneath the surface, and
  a goal of language analysis is to arrive at the so-called "deep structures"
  that represent meaning.

* The diagrams of the book need to be set in grayscale and high-resolution, for the
  hardcopy version.

* Definition lists
  are coming out with the definition term being treated as a variable
  term in Docbook, and therefore being rendered in fixed-width font.
  ``http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html#definition-lists``

-----------------------
Chapter-Specific Issues
-----------------------

* Chapter 1: This is the third complete re-write of the introduction chapter;
  the first attempt (2004-05) covered the history and motivations of NLP, but
  ended up being too scholarly;
  the second attempt (2006-07) was a rather conventional Python tutorial
  but with examples drawn from linguistics, but ended up being rather mundane
  because it was too focused on the syntax of the language;
  this new version is designed to appeal to as broad a range of readers
  as possible; it gives readers immediate access to language data (which
  most people find intrinsically interesting), and immediate access to
  Python idioms, and the cost of using concepts before introducing them
  systematically; does this work for you?

* Chapter 2: The learning curve of Chapter 1 was quite shallow, but it gets much
  steeper in this chapter; is there a way to make it easier for new programmers?
  
* Chapter 3: A short subsection on non-standard words still needs to be written,
  pending the addition of support for this to NLTK.  The idea is to map all
  tokens matching certain open patterns to some unique token (e.g. ``\d+``
  becomes ``NUM``).  

* Chapter 4: The final sections on the TnT Tagger hasn't been written yet; we are
  still getting this functionality working in NLTK.  Its important to have a
  reasonable quality, off-the-shelf, pure-Python tagger available to users.

* Chapter 5: Most of this chapter was written in late 2008 and has not been
  tested with readers like the rest of the book; it needs more exercises.

* Chapter 6: It has been difficult to find a good sequence for presenting the topics
  of this chapter; there are many topics to cover and its a trade-off between breadth
  and depth; suggestions for improving the structure and prioritizing the content welcomed;
  note that the final sections on program development and third-party libraries are
  only sketched.

* Chapter 7: We are hoping to get some English named-entity data so that we
  can illustrate how to train a named entity classifier.

* Chapter 8: The final section on scaling up grammars is incomplete; we are trying
  to get permission to redistribute the PE08 parser evaluation dataset.

* Chapter 9: The opening has not been updated to follow the model of the
  other chapters, identifying questions that are answered in this chapter. 

* Chapter 10: We don't have permission to use the photograph.

* Chapter 11: This chapter is quite uneven, with many small gaps. 

* Chapter 12: The last two sections planned for this chapter (NLTK Roadmap,
  NLP-Complete Problems) have not been written yet.

* Appendix B: Some images overlap the text (an issue we thought we had previously solved).

* References: we haven't worked out how to convert the references from BibTeX into Docbook.
  The HTML version is at ``http://nltk.googlecode.com/svn/trunk/doc/en/bibliography.html`` and
  the BibTeX source is at ``http://nltk.googlecode.com/svn/trunk/nltk/doc/refs.bib``

 