#!/usr/bin/env python
#
# Natural Language Toolkit: Documentation generation script
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
This is a customized driver for converting docutils reStructuredText
documents into HTML and LaTeX.  It customizes the standard writers in
the following ways:
    
    - Source code highlighting is added to all doctest blocks.  In
      the HTML output, highlighting is performed using css classes:
      'pysrc-prompt', 'pysrc-keyword', 'pysrc-string', 'pysrc-comment',
      and 'pysrc-output'.  In the LaTeX output, highlighting uses five
      new latex commands: '\pysrcprompt', '\pysrckeyword',
      '\pysrcstring', '\pysrccomment', and '\pyrcoutput'.

    - A new "example" directive is defined.

    - A new "doctest-ignore" directive is defined.

    - A new "tree" directive is defined.

    - New directives "def", "ifdef", and "ifndef", which can be used
      to conditionally control the inclusion of sections.  This is
      used, e.g., to make sure that the definitions in 'definitions.rst'
      are only performed once, even if 'definitions.rst' is included
      multiple times.
"""

import re, os.path, textwrap, sys, pickle
from optparse import OptionParser
from tree2image import tree_to_image

import docutils.core, docutils.nodes, docutils.io
from docutils.writers import Writer
from docutils.writers.html4css1 import HTMLTranslator, Writer as HTMLWriter
from docutils.writers.latex2e import LaTeXTranslator, Writer as LaTeXWriter
from docutils.parsers.rst import directives, roles
from docutils.readers.standalone import Reader as StandaloneReader
from docutils.transforms import Transform
import docutils.writers.html4css1
from doctest import DocTestParser
import docutils.statemachine

LATEX_VALIGN_IS_BROKEN = True
"""Set to true to compensate for a bug in the latex writer.  I've
   submitted a patch to docutils, so hopefully this wil be fixed
   soon."""

LATEX_DPI = 144
"""The scaling factor that should be used to display bitmapped images
   in latex/pdf output (specified in dots per inch).  E.g., if a
   bitmapped image is 100 pixels wide, it will be scaled to
   100/LATEX_DPI inches wide for the latex/pdf output.  (Larger
   values produce smaller images in the generated pdf.)"""

OUTPUT_FORMAT = None
"""A global variable, set by main(), indicating the output format for
   the current file.  Can be 'latex' or 'html' or 'ref'."""

OUTPUT_BASENAME = None
"""A global variable, set by main(), indicating the base filename
   of the current file (i.e., the filename with its extension
   stripped).  This is used to generate filenames for images."""

TREE_IMAGE_DIR = 'tree_images/'
"""The directory that tree images should be written to."""

EXTERN_REFERENCE_FILES = []
"""A list of .ref files, for crossrefering to external documents (used
   when building one chapter at a time)."""

BIBTEX_FILE = '../refs.bib'
"""The name of the bibtex file used to generate bibliographic entries."""

BIBLIOGRAPHY_HTML = "bibliography.html"
"""The name of the HTML file containing the bibliography (for
   hyperrefs from citations)."""

# needs to include "../doc" so it works in /doc_contrib
LATEX_STYLESHEET_PATH = '../../doc/definitions.sty'
"""The name of the LaTeX style file used for generating PDF output."""

LOCAL_BIBLIOGRAPHY = False
"""If true, assume that this document contains the bibliography, and
   link to it locally; if false, assume that bibliographic links
   should point to L{BIBLIOGRAPHY_HTML}."""

PYLISTING_DIR = 'pylisting/'
"""The directory where pylisting files should be written."""

PYLISTING_EXTENSION = ".py"
"""Extension for pylisting files."""

INCLUDE_DOCTESTS_IN_PYLISTING_FILES = False
"""If true, include code from doctests in the generated pylisting
   files. """

CALLOUT_IMG = '<img src="callouts/callout%s.gif" alt="[%s]" class="callout" />'
"""HTML code for callout images in pylisting blocks."""

REF_EXTENSION = '.ref'
"""File extension for reference files."""

# needs to include "../doc" so it works in /doc_contrib
CSS_STYLESHEET = '../../doc/nltkdoc.css'

######################################################################
#{ Reference files
######################################################################

def read_ref_file(basename=None):
    if basename is None: basename = OUTPUT_BASENAME
    if not os.path.exists(basename + REF_EXTENSION):
        warning('File %r does not exist!' %
                (basename + REF_EXTENSION))
        return dict(targets=(),terms={},reference_labes={})
    f = open(basename + REF_EXTENSION)
    ref_info = pickle.load(f)
    f.close()
    return ref_info

def write_ref_file(ref_info):
    f = open(OUTPUT_BASENAME + REF_EXTENSION, 'w')
    pickle.dump(ref_info, f)
    f.close()

def add_to_ref_file(**ref_info):
    if os.path.exists(OUTPUT_BASENAME + REF_EXTENSION):
        info = read_ref_file()
        info.update(ref_info)
        write_ref_file(info)
    else:
        write_ref_file(ref_info)

######################################################################
#{ Directives
######################################################################

class example(docutils.nodes.paragraph): pass

def example_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    """
    Basic use::

        .. example:: John went to the store.

    To refer to examples, use::

        .. _store:
        .. example:: John went to the store.

        In store_, John performed an action.
    """
    text = '\n'.join(content)
    node = example(text)
    state.nested_parse(content, content_offset, node)
    return [node]
example_directive.content = True
directives.register_directive('example', example_directive)
directives.register_directive('ex', example_directive)

def doctest_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    """
    Used to explicitly mark as doctest blocks things that otherwise
    wouldn't look like doctest blocks.
    """
    text = '\n'.join(content)
    if re.match(r'.*\n\s*\n', block_text):
        warning('doctest-ignore on line %d will not be ignored, '
             'because there is\na blank line between ".. doctest-ignore::"'
             ' and the doctest example.' % lineno)
    return [docutils.nodes.doctest_block(text, text, codeblock=True)]
doctest_directive.content = True
directives.register_directive('doctest-ignore', doctest_directive)

_treenum = 0
def tree_directive(name, arguments, options, content, lineno,
                   content_offset, block_text, state, state_machine):
    global _treenum
    text = '\n'.join(arguments) + '\n'.join(content)
    _treenum += 1
    # Note: the two filenames generated by these two cases should be
    # different, to prevent conflicts.
    if OUTPUT_FORMAT == 'latex':
        density, scale = 300, 150
        scale = scale * options.get('scale', 100) / 100
        filename = '%s-tree-%s.pdf' % (OUTPUT_BASENAME, _treenum)
        align = LATEX_VALIGN_IS_BROKEN and 'bottom' or 'top'
    elif OUTPUT_FORMAT == 'html':
        density, scale = 100, 100
        density = density * options.get('scale', 100) / 100
        filename = '%s-tree-%s.png' % (OUTPUT_BASENAME, _treenum)
        align = 'top'
    elif OUTPUT_FORMAT == 'ref':
        return []
    elif OUTPUT_FORMAT == 'docbook':
#        warning('TREE DIRECTIVE -- CHECK THIS')
        scale = options.get('scale', 60)
        density = 300 * scale / 100
        filename = '%s-tree-%s.png' % (OUTPUT_BASENAME, _treenum)
        align = 'top'
    else:
        assert 0, 'bad output format %r' % OUTPUT_FORMAT
    if not os.path.exists(TREE_IMAGE_DIR):
        os.mkdir(TREE_IMAGE_DIR)
    try:
        filename = os.path.join(TREE_IMAGE_DIR, filename)
        tree_to_image(text, filename, density)
    except Exception as e:
        raise
        warning('Error parsing tree: %s\n%s\n%s' % (e, text, filename))
        return [example(text, text)]

    imagenode = docutils.nodes.image(uri=filename, scale=scale, align=align)
    return [imagenode]

tree_directive.arguments = (1,0,1)
tree_directive.content = True
tree_directive.options = {'scale': directives.nonnegative_int}
directives.register_directive('tree', tree_directive)

def avm_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    text = '\n'.join(content)
    try:
        if OUTPUT_FORMAT == 'latex':
            latex_avm = parse_avm(textwrap.dedent(text)).as_latex()
            return [docutils.nodes.paragraph('','',
                       docutils.nodes.raw('', latex_avm, format='latex'))]
        elif OUTPUT_FORMAT == 'html':
            return [parse_avm(textwrap.dedent(text)).as_table()]
        elif OUTPUT_FORMAT == 'ref':
            return [docutils.nodes.paragraph()]
        # pass through for now
        elif OUTPUT_FORMAT == 'docbook':
            return [docutils.nodes.literal_block('', textwrap.dedent(text))]
    except ValueError as e:
        if isinstance(e.args[0], int):
            warning('Error parsing avm on line %s' % (lineno+e.args[0]))
        else:
            raise
            warning('Error parsing avm on line %s: %s' % (lineno, e))
        node = example(text, text)
        state.nested_parse(content, content_offset, node)
        return [node]
avm_directive.content = True
directives.register_directive('avm', avm_directive)

def def_directive(name, arguments, options, content, lineno,
                  content_offset, block_text, state, state_machine):
    state_machine.document.setdefault('__defs__', {})[arguments[0]] = 1
    return []
def_directive.arguments = (1, 0, 0)
directives.register_directive('def', def_directive)
    
def ifdef_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    if arguments[0] in state_machine.document.get('__defs__', ()):
        node = docutils.nodes.compound('')
        state.nested_parse(content, content_offset, node)
        return [node]
    else:
        return []
ifdef_directive.arguments = (1, 0, 0)
ifdef_directive.content = True
directives.register_directive('ifdef', ifdef_directive)
    
def ifndef_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    if arguments[0] not in state_machine.document.get('__defs__', ()):
        node = docutils.nodes.compound('')
        state.nested_parse(content, content_offset, node)
        return [node]
    else:
        return []
ifndef_directive.arguments = (1, 0, 0)
ifndef_directive.content = True
directives.register_directive('ifndef', ifndef_directive)

######################################################################
#{ Table Directive
######################################################################
_table_ids = set()
def table_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    # The identifier for this table.
    if arguments:
        table_id = arguments[0]
        if table_id in _table_ids:
            warning("Duplicate table id %r" % table_id)
        _table_ids.add(table_id)

        # Create a target element for the table
        target = docutils.nodes.target(names=[table_id])
        state_machine.document.note_explicit_target(target)

    # Parse the contents.
    node = docutils.nodes.compound('')
    state.nested_parse(content, content_offset, node)
    if len(node) == 0 or not isinstance(node[0], docutils.nodes.table):
        return [state_machine.reporter.error(
            'Error in "%s" directive: expected table as first child' %
            name)]

    # Move the caption into the table.
    table = node[0]
    caption = docutils.nodes.caption('','', *node[1:])
    table.append(caption)

    # Return the target and the table.
    if arguments:
        return [target, table]
    else:
        return [table]
    
    
table_directive.arguments = (0,1,0) # 1 optional arg, no whitespace
table_directive.content = True
table_directive.options = {'caption': directives.unchanged}
directives.register_directive('table', table_directive)
    
######################################################################
#{ Program Listings
######################################################################
# We define a new attribute for doctest blocks: 'is_codeblock'.  If
# this attribute is true, then the block contains python code only
# (i.e., don't expect to find prompts.)

class pylisting(docutils.nodes.General, docutils.nodes.Element):
    """
    Python source code listing.

    Children: doctest_block+ caption?
    """
class callout_marker(docutils.nodes.Inline, docutils.nodes.Element):
    """
    A callout marker for doctest block.  This element contains no
    children; and defines the attribute 'number'.
    """

DOCTEST_BLOCK_RE = re.compile('((?:[ ]*>>>.*\n?(?:.*[^ ].*\n?)+\s*)+)',
                              re.MULTILINE)
CALLOUT_RE = re.compile(r'#[ ]+\[_([\w-]+)\][ ]*', re.MULTILINE)

from docutils.nodes import fully_normalize_name as normalize_name

_listing_ids = set()
def pylisting_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    # The identifier for this listing.
    listing_id = arguments[0]
    if listing_id in _listing_ids:
        warning("Duplicate listing id %r" % listing_id)
    _listing_ids.add(listing_id)
    
    # Create the pylisting element itself.
    listing = pylisting('\n'.join(content), name=listing_id, callouts={})

    # Create a target element for the pylisting.
    target = docutils.nodes.target(names=[listing_id])
    state_machine.document.note_explicit_target(target)

    # Divide the text into doctest blocks.
    for i, v in enumerate(DOCTEST_BLOCK_RE.split('\n'.join(content))):
        pysrc = re.sub(r'\A( *\n)+', '', v.rstrip())
        if pysrc.strip():
            listing.append(docutils.nodes.doctest_block(pysrc, pysrc,
                                                        is_codeblock=(i%2==0)))

    # Add an optional caption.
    if options.get('caption'):
        cap = options['caption'].split('\n')
        caption = docutils.nodes.compound()
        state.nested_parse(docutils.statemachine.StringList(cap),
                           content_offset, caption)
        if (len(caption) == 1 and isinstance(caption[0],
                                             docutils.nodes.paragraph)):
            listing.append(docutils.nodes.caption('', '', *caption[0]))
        else:
            warning("Caption should be a single paragraph")
            listing.append(docutils.nodes.caption('', '', *caption))

    return [target, listing]

pylisting_directive.arguments = (1,0,0) # 1 required arg, no whitespace
pylisting_directive.content = True
pylisting_directive.options = {'caption': directives.unchanged}
directives.register_directive('pylisting', pylisting_directive)

def callout_directive(name, arguments, options, content, lineno,
                      content_offset, block_text, state, state_machine):
    if arguments:
        prefix = '%s-' % arguments[0]
    else:
        prefix = ''
    node = docutils.nodes.compound('')
    state.nested_parse(content, content_offset, node)
    if not (len(node.children) == 1 and
            isinstance(node[0], docutils.nodes.field_list)):
        return [state_machine.reporter.error(
            'Error in "%s" directive: may contain a single definition '
            'list only.' % (name), line=lineno)]

    node[0]['classes'] = ['callouts']
    for field in node[0]:
        if len(field[0]) != 1:
            return [state_machine.reporter.error(
                'Error in "%s" directive: bad field id' % (name), line=lineno)]
            
        field_name = prefix+('%s' % field[0][0])
        field[0].clear()
        field[0].append(docutils.nodes.reference(field_name, field_name,
                                                 refid=field_name))
        field[0]['classes'] = ['callout']

    return [node[0]]

callout_directive.arguments = (0,1,0) # 1 optional arg, no whitespace
callout_directive.content = True
directives.register_directive('callouts', callout_directive)

_OPTION_DIRECTIVE_RE = re.compile(
    r'(\n[ ]*\.\.\.[ ]*)?#\s*doctest:\s*([^\n\'"]*)$', re.MULTILINE)
def strip_doctest_directives(text):
    return _OPTION_DIRECTIVE_RE.sub('', text)

######################################################################
#{ RST In/Out table
######################################################################

def rst_example_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    raw = docutils.nodes.literal_block('', '\n'.join(content))
    out = docutils.nodes.compound('')
    state.nested_parse(content, content_offset, out)
    if OUTPUT_FORMAT == 'latex':
        return [
            docutils.nodes.definition_list('',
              docutils.nodes.definition_list_item('',
                docutils.nodes.term('','Input'),
                docutils.nodes.definition('', raw)),
              docutils.nodes.definition_list_item('',
                docutils.nodes.term('','Rendered'),
                docutils.nodes.definition('', out)))]
    else:
        return [
            docutils.nodes.table('',
              docutils.nodes.tgroup('',
                docutils.nodes.colspec(colwidth=5,classes=['rst-raw']),
                docutils.nodes.colspec(colwidth=5),
                docutils.nodes.thead('',
                  docutils.nodes.row('',
                    docutils.nodes.entry('',
                      docutils.nodes.paragraph('','Input')),
                    docutils.nodes.entry('',
                      docutils.nodes.paragraph('','Rendered')))),
                docutils.nodes.tbody('',
                  docutils.nodes.row('',
                    docutils.nodes.entry('',raw),
                    docutils.nodes.entry('',out)))),
              classes=["rst-example"])]

rst_example_directive.arguments = (0, 0, 0)
rst_example_directive.content = True
directives.register_directive('rst_example', rst_example_directive)

######################################################################
#{ Glosses
######################################################################

"""
.. gloss::
   This  | is | used | to | make | aligned | glosses.
    NN   | BE |  VB  | TO |  VB  |  JJ     |   NN
   *Foog blogg blarg.*
"""

class gloss(docutils.nodes.Element): "glossrow+"
class glossrow(docutils.nodes.Element): "paragraph+"

def gloss_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    # Transform into a table.
    lines = list(content)
    maxlen = max(len(line) for line in lines)
    lines = [('|%-'+repr(maxlen)+'s|') % line for line in lines]
    tablestr = ''
    prevline = ''
    for line in (lines+['']):
        div = ['-']*(maxlen+2)
        for m in re.finditer(r'\|', prevline):
            div[m.start()] = '+'
        for m in re.finditer(r'\|', line):
            div[m.start()] = '+'
        tablestr += ''.join(div) + '\n' + line + '\n'
        prevline = line
    table_lines = tablestr.strip().split('\n')
    new_content = docutils.statemachine.StringList(table_lines)
    # [XX] DEBUG GLOSSES:
    # print 'converted to:'
    # print tablestr

    # Parse the table.
    node = docutils.nodes.compound('')
    state.nested_parse(new_content, content_offset, node)
    if not (len(node.children) == 1 and
            isinstance(node[0], docutils.nodes.table)):
        error = state_machine.reporter.error(
            'Error in "%s" directive: may contain a single table '
            'only.' % (name), line=lineno)
        return [error]
    table = node[0]
    table['classes'] = ['gloss', 'nolines']
    
    colspecs = table[0]
    for colspec in colspecs:
        colspec['colwidth'] = colspec.get('colwidth',4)/2
    
    return [example('', '', table)]
gloss_directive.arguments = (0, 0, 0)
gloss_directive.content = True
directives.register_directive('gloss', gloss_directive)

######################################################################
#{ Bibliography
######################################################################

class Citations(Transform):
    default_priority = 500 # before footnotes.
    def apply(self):
        if not os.path.exists(BIBTEX_FILE):
            warning('Warning bibtex file %r not found.  '
                    'Not linking citations.' % BIBTEX_FILE)
            return
        bibliography = self.read_bibinfo(BIBTEX_FILE)
        for k, citation_refs in list(self.document.citation_refs.items()):
            for citation_ref in citation_refs[:]:
                cite = bibliography.get(citation_ref['refname'].lower())
                if cite:
                    new_cite = self.citeref(cite, citation_ref['refname'])
                    citation_ref.replace_self(new_cite)
                    self.document.citation_refs[k].remove(citation_ref)

    def citeref(self, cite, key):
        if LOCAL_BIBLIOGRAPHY:
            return docutils.nodes.raw('', '\cite{%s}' % key, format='latex')
        else:
            return docutils.nodes.reference('', '', docutils.nodes.Text(cite),
                                    refuri='%s#%s' % (BIBLIOGRAPHY_HTML, key))

    BIB_ENTRY = re.compile(r'@\w+{.*')
    def read_bibinfo(self, filename):
        bibliography = {} # key -> authors, year
        key = None
        for line in open(filename):
            line = line.strip()
            
            # @InProceedings{<key>,
            m = re.match(r'@\w+{([^,]+),$', line)
            if m:
                key = m.group(1).strip().lower()
                bibliography[key] = [None, None]
                
            #   author = <authors>,
            m = re.match(r'(?i)author\s*=\s*(.*)$', line)
            if m and key:
                bibliography[key][0] = self.bib_authors(m.group(1))
            else:
                m = re.match(r'(?i)editor\s*=\s*(.*)$', line)
                if m and key:
                    bibliography[key][0] = self.bib_authors(m.group(1))
                
            #   year = <year>,
            m = re.match(r'(?i)year\s*=\s*(.*)$', line)
            if m and key:
                bibliography[key][1] = self.bib_year(m.group(1))
        for key in bibliography:
            if bibliography[key][0] is None: warning('no author found:', key)
            if bibliography[key][1] is None: warning('no year found:', key)
            bibliography[key] = '(%s, %s)' % tuple(bibliography[key])
            #debug('%20s %s' % (key, `bibliography[key]`))
        return bibliography

    def bib_year(self, year):
        return re.sub(r'["\'{},]', "", year)

    def bib_authors(self, authors):
        # Strip trailing comma:
        if authors[-1:] == ',': authors=authors[:-1]
        # Strip quotes or braces:
        authors = re.sub(r'"(.*)"$', r'\1', authors)
        authors = re.sub(r'{(.*)}$', r'\1', authors)
        authors = re.sub(r"'(.*)'$", r'\1', authors)
        # Split on 'and':
        authors = re.split(r'\s+and\s+', authors)
        # Keep last name only:
        authors = [a.split()[-1] for a in authors]
        # Combine:
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return '%s & %s' % tuple(authors)
        elif len(authors) == 3:
            return '%s, %s, & %s' % tuple(authors)
        else:
            return '%s et al' % authors[0]
        return authors

        
        

######################################################################
#{ Indexing
######################################################################

#class termdef(docutils.nodes.Inline, docutils.nodes.TextElement): pass
class idxterm(docutils.nodes.Inline, docutils.nodes.TextElement): pass
class index(docutils.nodes.Element): pass

def idxterm_role(name, rawtext, text, lineno, inliner,
                 options={}, content=[]):
    if name == 'dt': options['classes'] = ['termdef']
    elif name == 'topic': options['classes'] = ['topic']
    else: options['classes'] = ['term']
    # Recursively parse the contents of the index term, in case it
    # contains a substitiution (like |alpha|).
    nodes, msgs = inliner.parse(text, lineno, memo=inliner,
                                parent=inliner.parent)
    return [idxterm(rawtext, '', *nodes, **options)], []

roles.register_canonical_role('dt', idxterm_role)
roles.register_canonical_role('idx', idxterm_role)
roles.register_canonical_role('topic', idxterm_role)

def index_directive(name, arguments, options, content, lineno,
                    content_offset, block_text, state, state_machine):
    pending = docutils.nodes.pending(ConstructIndex)
    pending.details.update(options)
    state_machine.document.note_pending(pending)
    return [index('', pending)]
index_directive.arguments = (0, 0, 0)
index_directive.content = False
index_directive.options = {'extern': directives.flag}
directives.register_directive('index', index_directive)


class SaveIndexTerms(Transform):
    default_priority = 810 # before NumberReferences transform
    def apply(self):
        v = FindTermVisitor(self.document)
        self.document.walkabout(v)
        
        if OUTPUT_FORMAT == 'ref':
            add_to_ref_file(terms=v.terms)

class ConstructIndex(Transform):
    default_priority = 820 # after NumberNodes, before NumberReferences.
    def apply(self):
        # Find any indexed terms in this document.
        v = FindTermVisitor(self.document)
        self.document.walkabout(v)
        terms = v.terms

        # Check the extern reference files for additional terms.
        if 'extern' in self.startnode.details:
            for filename in EXTERN_REFERENCE_FILES:
                basename = os.path.splitext(filename)[0]
                terms.update(read_ref_file(basename)['terms'])

        # Build the index & insert it into the document.
        index_node = self.build_index(terms)
        self.startnode.replace_self(index_node)

    def build_index(self, terms):
        if not terms: return []
        
        top = docutils.nodes.bullet_list('', classes=['index'])
        start_letter = None
        
        section = None
        for key in sorted(terms.keys()):
            if key[:1] != start_letter:
                top.append(docutils.nodes.list_item(
                    '', docutils.nodes.paragraph('', key[:1].upper()+'\n',
                                                 classes=['index-heading']),
                    docutils.nodes.bullet_list('', classes=['index-section']),
                    classes=['index']))
                section = top[-1][-1]
            section.append(self.entry(terms[key]))
            start_letter = key[:1]
        
        return top

    def entry(self, term_info):
        entrytext, name, sectnum = term_info
        if sectnum is not None:
            entrytext.append(docutils.nodes.emphasis('', ' (%s)' % sectnum))
        ref = docutils.nodes.reference('', '', refid=name,
                                       #resolved=True,
                                       *entrytext)
        para = docutils.nodes.paragraph('', '', ref)
        return docutils.nodes.list_item('', para, classes=['index'])

class FindTermVisitor(docutils.nodes.SparseNodeVisitor):
    def __init__(self, document):
        self.terms = {}
        docutils.nodes.NodeVisitor.__init__(self, document)
    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass

    def visit_idxterm(self, node):
        node['name'] = node['id'] = self.idxterm_key(node)
        node['names'] = node['ids'] = [node['id']]
        container = self.container_section(node)
        
        entrytext = node.deepcopy()
        if container: sectnum = container.get('sectnum')
        else: sectnum = '0'
        name = node['name']
        self.terms[node['name']] = (entrytext, name, sectnum)
            
    def idxterm_key(self, node):
        key = re.sub('\W', '_', node.astext().lower())+'_index_term'
        if key not in self.terms: return key
        n = 2
        while '%s_%d' % (key, n) in self.terms: n += 1
        return '%s_%d' % (key, n)

    def container_section(self, node):
        while not isinstance(node, docutils.nodes.section):
            if node.parent is None: return None
            else: node = node.parent
        return node

######################################################################
#{ Crossreferences
######################################################################

class ResolveExternalCrossrefs(Transform):
    """
    Using the information from EXTERN_REFERENCE_FILES, look for any
    links to external targets, and set their `refuid` appropriately.
    Also, if they are a figure, section, table, or example, then
    replace the link of the text with the appropriate counter.
    """
    default_priority = 849 # right before dangling refs

    def apply(self):
        ref_dict = self.build_ref_dict()
        v = ExternalCrossrefVisitor(self.document, ref_dict)
        self.document.walkabout(v)

    def build_ref_dict(self):
        """{target -> (uri, label)}"""
        ref_dict = {}
        for filename in EXTERN_REFERENCE_FILES:
            basename = os.path.splitext(filename)[0]
            if OUTPUT_FORMAT == 'html':
                uri = os.path.split(basename)[-1]+'.html'
            else:
                uri = os.path.split(basename)[-1]+'.pdf'
            if basename == OUTPUT_BASENAME:
                pass # don't read our own ref file.
            elif not os.path.exists(basename+REF_EXTENSION):
                warning('%s does not exist' % (basename+REF_EXTENSION))
            else:
                ref_info = read_ref_file(basename)
                for ref in ref_info['targets']:
                    label = ref_info['reference_labels'].get(ref)
                    ref_dict[ref] = (uri, label)

        return ref_dict
    
class ExternalCrossrefVisitor(docutils.nodes.NodeVisitor):
    def __init__(self, document, ref_dict):
        docutils.nodes.NodeVisitor.__init__(self, document)
        self.ref_dict = ref_dict
    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass

    # Don't mess with the table of contents.
    def visit_topic(self, node):
        if 'contents' in node.get('classes', ()):
            raise docutils.nodes.SkipNode

    def visit_reference(self, node):
        if node.resolved: return
        node_id = node.get('refid') or node.get('refname')
        if node_id in self.ref_dict:
            uri, label = self.ref_dict[node_id]
            #debug('xref: %20s -> %-30s (label=%s)' % (
            #    node_id, uri+'#'+node_id, label))
            node['refuri'] = '%s#%s' % (uri, node_id)
            node.resolved = True

            if label is not None:
                if node.get('expanded_ref'):
                    warning('Label %s is defined both locally (%s) and '
                            'externally (%s)' % (node_id, node[0], label))
                    # hmm...
                else:
                    node.clear()
                    node.append(docutils.nodes.Text(label))
                    process_reference_text(node, node_id)

######################################################################
#{ Figure & Example Numbering
######################################################################

# [xx] number examples, figures, etc, relative to chapter?  e.g.,
# figure 3.2?  maybe number examples within-chapter, but then restart
# the counter?

class section_context(docutils.nodes.Invisible, docutils.nodes.Element):
    def __init__(self, context):
        docutils.nodes.Element.__init__(self, '', context=context)
        assert self['context'] in ('body', 'preface', 'appendix')

def section_context_directive(name, arguments, options, content, lineno,
                       content_offset, block_text, state, state_machine):
    return [section_context(name)]
section_context_directive.arguments = (0,0,0)
directives.register_directive('preface', section_context_directive)
directives.register_directive('body', section_context_directive)
directives.register_directive('appendix', section_context_directive)
        
class NumberNodes(Transform):
    """
    This transform adds numbers to figures, tables, and examples; and
    converts references to the figures, tables, and examples to use
    these numbers.  For example, given the rst source::

        .. _my_example:
        .. ex:: John likes Mary.

        See example my_example_.

    This transform will assign a number to the example, '(1)', and
    will replace the following text with 'see example (1)', with an
    appropriate link.
    """
    # dangling = 850; contents = 720.
    default_priority = 800
    def apply(self):
        v = NumberingVisitor(self.document)
        self.document.walkabout(v)
        self.document.reference_labels = v.reference_labels
        self.document.callout_labels = v.callout_labels

class NumberReferences(Transform):
    default_priority = 830
    def apply(self):
        v = ReferenceVisitor(self.document, self.document.reference_labels,
                             self.document.callout_labels)
        self.document.walkabout(v)

        # Save reference info to a pickle file.
        if OUTPUT_FORMAT == 'ref':
            add_to_ref_file(reference_labels=self.document.reference_labels,
                            targets=v.targets)

class NumberingVisitor(docutils.nodes.NodeVisitor):
    """
    A transforming visitor that adds figure numbers to all figures,
    and converts any references to figures to use the text 'Figure #';
    and adds example numbers to all examples, and converts any
    references to examples to use the text 'Example #'.
    """
    LETTERS = 'abcdefghijklmnopqrstuvwxyz'
    ROMAN = 'i ii iii iv v vi vii viii ix x'.split()
    ROMAN += ['x%s' % r for r in ROMAN]
    
    def __init__(self, document):
        docutils.nodes.NodeVisitor.__init__(self, document)
        self.reference_labels = {}
        self.figure_num = 0
        self.table_num = 0
        self.example_num = [0]
        self.section_num = [0]
        self.listing_num = 0
        self.callout_labels = {} # name -> number
        self.set_section_context = None
        self.section_context = 'body' # preface, appendix, body
        
    #////////////////////////////////////////////////////////////
    # Figures
    #////////////////////////////////////////////////////////////

    def visit_figure(self, node):
        self.figure_num += 1
        num = '%s.%s' % (self.format_section_num(1), self.figure_num)
        for node_id in self.get_ids(node):
            self.reference_labels[node_id] = '%s' % num
        self.label_node(node, 'Figure %s' % num)
            
    #////////////////////////////////////////////////////////////
    # Tables
    #////////////////////////////////////////////////////////////

    def visit_table(self, node):
        if 'avm' in node['classes']: return
        if 'gloss' in node['classes']: return
        if 'rst-example' in node['classes']: return
        if 'doctest-list' in node['classes']: return
        self.table_num += 1
        num = '%s.%s' % (self.format_section_num(1), self.table_num)
        for node_id in self.get_ids(node):
            self.reference_labels[node_id] = '%s' % num
        self.label_node(node, 'Table %s' % num)

    #////////////////////////////////////////////////////////////
    # Listings
    #////////////////////////////////////////////////////////////

    def visit_pylisting(self, node):
        self.visit_figure(node)
        pyfile = re.sub('\W', '_', node['name']) + PYLISTING_EXTENSION
        num = '%s.%s' % (self.format_section_num(1), self.figure_num)
        self.label_node(node, 'Example %s (%s)' % (num, pyfile),
                      PYLISTING_DIR + pyfile)

        self.callout_labels.update(node['callouts'])
        
#        self.listing_num += 1
#        num = '%s.%s' % (self.format_section_num(1), self.listing_num)
#        for node_id in self.get_ids(node):
#            self.reference_labels[node_id] = '%s' % num
#        pyfile = re.sub('\W', '_', node['name']) + PYLISTING_EXTENSION
#        self.label_node(node, 'Listing %s (%s)' % (num, pyfile),
#                      PYLISTING_DIR + pyfile)
#        self.callout_labels.update(node['callouts'])

    def visit_doctest_block(self, node):
        if isinstance(node.parent, pylisting):
            callouts = node['callouts'] = node.parent['callouts']
        else:
            callouts = node['callouts'] = {}
        
        pysrc = ''.join(('%s' % c) for c in node)
        for callout_id in CALLOUT_RE.findall(pysrc):
            callouts[callout_id] = len(callouts)+1
        self.callout_labels.update(callouts)

    #////////////////////////////////////////////////////////////
    # Sections
    #////////////////////////////////////////////////////////////
    max_section_depth = 2
    no_section_numbers_in_preface = True
    TOP_SECTION = 'chapter'

    # [xx] I don't think this currently does anything..
    def visit_document(self, node):
        if (len(node)>0 and isinstance(node[0], docutils.nodes.title) and
            isinstance(node[0].children[0], docutils.nodes.Text) and
            re.match(r'(\d+(.\d+)*)\.?\s+', node[0].children[0].data)):
                node['sectnum'] = node[0].children[0].data.split()[0]
                for node_id in node.get('ids', []):
                    self.reference_labels[node_id] = '%s' % node['sectnum']

    def visit_section(self, node):
        title = node[0]
        
        # Check if we're entering a new context.
        if len(self.section_num) == 1 and self.set_section_context:
            self.start_new_context(node)

        # Record the section's context in its title.
        title['section_context'] = self.section_context

        # Increment the section counter.
        self.section_num[-1] += 1
        
        # If a section number is given explicitly as part of the
        # title, then it overrides our counter.
        if isinstance(title.children[0], docutils.nodes.Text):
            m = re.match(r'(\d+(.\d+)*)\.?\s+', title.children[0].data)
            if m:
                pieces = [int(n) for n in m.group(1).split('.')]
                if len(pieces) == len(self.section_num):
                    self.section_num = pieces
                    title.children[0].data = title.children[0].data[m.end():]
                else:
                    warning('Explicit section number (%s) does not match '
                         'current section depth' % m.group(1))
                self.prepend_raw_latex(node, r'\setcounter{%s}{%d}' %
                               (self.TOP_SECTION, self.section_num[0]-1))

        # Record the reference pointer for this section; and add the
        # section number to the section title.
        node['sectnum'] = self.format_section_num()
        for node_id in node.get('ids', []):
            self.reference_labels[node_id] = '%s' % node['sectnum']
        if (len(self.section_num) <= self.max_section_depth and
            (OUTPUT_FORMAT != 'latex') and
            not (self.section_context == 'preface' and
                 self.no_section_numbers_in_preface)):
            label = docutils.nodes.generated('', node['sectnum']+'\u00a0'*3,
                                             classes=['sectnum'])
            title.insert(0, label)
            title['auto'] = 1

        # Record the section number.
        self.section_num.append(0)

        # If this was a top-level section, then restart the figure,
        # table, and listing counters
        if len(self.section_num) == 2:
            self.figure_num = 0
            self.table_num = 0
            self.listing_num = 0

    def start_new_context(self,node):
        # Set the 'section_context' var.
        self.section_context = self.set_section_context
        self.set_section_context = None

        # Update our counter.
        self.section_num[0] = 0

        # Update latex's counter.
        if self.section_context == 'preface': style = 'Roman'
        elif self.section_context == 'body': style = 'arabic'
        elif self.section_context == 'appendix': style = 'Alph'
        raw_latex = (('\n'+r'\setcounter{%s}{0}' + '\n' + 
                      r'\renewcommand \the%s{\%s{%s}}'+'\n') %
               (self.TOP_SECTION, self.TOP_SECTION, style, self.TOP_SECTION))
        if self.section_context == 'appendix':
            raw_latex += '\\appendix\n'
        self.prepend_raw_latex(node, raw_latex)

    def prepend_raw_latex(self, node, raw_latex):
        if isinstance(node, docutils.nodes.document):
            node.insert(0, docutils.nodes.raw('', raw_latex, format='latex'))
        else:
            node_index = node.parent.children.index(node)
            node.parent.insert(node_index, docutils.nodes.raw('', raw_latex,
                                                              format='latex'))
        
    def depart_section(self, node):
        self.section_num.pop()

    def format_section_num(self, depth=None):
        pieces = [('%s' % p) for p in self.section_num]
        if self.section_context == 'body':
            pieces[0] = ('%s' % self.section_num[0])
        elif self.section_context == 'preface':
            pieces[0] = self.ROMAN[self.section_num[0]-1].upper()
        elif self.section_context == 'appendix':
            pieces[0] = self.LETTERS[self.section_num[0]-1].upper()
        else:
            assert 0, 'unexpected section context'
        if depth is None:
            return '.'.join(pieces)
        else:
            return '.'.join(pieces[:depth])
            
            
    def visit_section_context(self, node):
        assert node['context'] in ('body', 'preface', 'appendix')
        self.set_section_context = node['context']
        node.replace_self([])

    #////////////////////////////////////////////////////////////
    # Examples
    #////////////////////////////////////////////////////////////
    NESTED_EXAMPLES = True

    def visit_example(self, node):
        self.example_num[-1] += 1
        node['num'] = self.short_example_num()
        for node_id in self.get_ids(node):
            self.reference_labels[node_id] = self.format_example_num()
        self.example_num.append(0)

    def depart_example(self, node):
        if not self.NESTED_EXAMPLES:
            if self.example_num[-1] > 0:
                # If the example contains a list of subexamples, then
                # splice them in to our parent.
                node.replace_self(list(node))
        self.example_num.pop()

    def short_example_num(self):
        if len(self.example_num) == 1:
            return '(%s)' % self.example_num[0]
        if len(self.example_num) == 2:
            return '%s.' % self.LETTERS[self.example_num[1]-1]
        if len(self.example_num) == 3:
            return '%s.' % self.ROMAN[self.example_num[2]-1]
        else:
            return '%s.' % self.example_num[-1]

    def format_example_num(self):
        """ (1), (2); (1a), (1b); (1a.i), (1a.ii)"""
        ex_num = ('%s' % self.example_num[0])
        if len(self.example_num) > 1:
            ex_num += self.LETTERS[self.example_num[1]-1]
        if len(self.example_num) > 2:
            ex_num += '.%s' % self.ROMAN[self.example_num[2]-1]
        for n in self.example_num[3:]:
            ex_num += '.%s' % n
        return '(%s)' % ex_num

    #////////////////////////////////////////////////////////////
    # Helpers
    #////////////////////////////////////////////////////////////

    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass

    def get_ids(self, node):
        node_index = node.parent.children.index(node)
        if node_index>0 and isinstance(node.parent[node_index-1],
                                       docutils.nodes.target):
            target = node.parent[node_index-1]
            if 'refid' in target:
                refid = target['refid']
                target['ids'] = [refid]
                del target['refid']
                return [refid]
            elif 'ids' in target:
                return target['ids']
            else:
                warning('unable to find id for %s' % target)
                return []
        elif 'ids' in node.parent:
            # Sometimes a table is inside another node who's id is the
            # reference.
            return node.parent['ids']
        else:
            return []

    def label_node(self, node, label, refuri=None, cls='caption-label'):
        # OReilly Docbook do their own numbering.
        if OUTPUT_FORMAT == 'docbook':
            return

        if not isinstance(node[-1], docutils.nodes.caption):
            node.append(docutils.nodes.caption())
        caption = node[-1]

        if OUTPUT_FORMAT == 'html':
            cap = docutils.nodes.inline('', label, classes=[cls])
            if refuri:
                cap = docutils.nodes.reference('', '', cap, refuri=refuri,
                                               mimetype='text/x-python')
            caption.insert(0, cap)
            if len(caption) > 1:
                caption.insert(1, docutils.nodes.Text(': '))
        
class ReferenceVisitor(docutils.nodes.NodeVisitor):
    def __init__(self, document, reference_labels, callout_labels):
        self.reference_labels = reference_labels
        self.callout_labels = callout_labels
        self.targets = set()
        docutils.nodes.NodeVisitor.__init__(self, document)
    def unknown_visit(self, node):
        if isinstance(node, docutils.nodes.Element):
            self.targets.update(node.get('names', []))
            self.targets.update(node.get('ids', []))
    def unknown_departure(self, node): pass

    # Don't mess with the table of contents.
    def visit_topic(self, node):
        if 'contents' in node.get('classes', ()):
            raise docutils.nodes.SkipNode

    def visit_reference(self, node):
        node_id = (node.get('refid') or
                   self.document.nameids.get(node.get('refname')) or
                   node.get('refname'))
        if node_id in self.reference_labels:
            label = self.reference_labels[node_id]
            node.clear()
            # use xref label for docbook output
            if OUTPUT_FORMAT == 'docbook': # and not node_id.startswith('ex-'):
                node.append(callout_marker(number=label, name=node_id))
            else:
                node.append(docutils.nodes.Text(label))
                process_reference_text(node, node_id)
        elif node_id in self.callout_labels:
            label = self.callout_labels[node_id]
            node.clear()
            node.append(callout_marker(number=label, name='ref-%s' % node_id))
            # process_reference_text(node, node_id) -- don't process callout labels
            # There's no explicitly encoded target element, so manually
            # resolve the reference:
            node['refid'] = node_id
            node.resolved = True

# No longer required: this does the reverse of what we want
def expand_reference_text(node):
    """If the reference is immediately preceeded by the word 'figure'
    or the word 'table' or 'example', then include that word in the
    link (rather than just the number)."""
    if node.get('expanded_ref'):
        assert 0, ('Already expanded!!  %s' % node)
    node_index = node.parent.children.index(node)
    if node_index > 0:
        prev_node = node.parent.children[node_index-1]
        if (isinstance(prev_node, docutils.nodes.Text)):
            m = _EXPAND_REF_RE.match(prev_node.data)
            if m:
                prev_node.data = m.group(1)
                link = node.children[0]
                link.data = '%s %s' % (m.group(2), link.data)
                node['expanded_ref'] = True

# Handle the anchor text of references.

_EXPAND_REF_RE = re.compile(r'(?is)^(.*)(%s)\s+$' % '|'.join(
    ['figure', 'table', 'example', 'chapter', 'section', 'appendix']))

_EXPAND_REF_DICT = {'sec': 'Section',
                    'chap': 'Chapter',
                    'fig': 'Figure',
                    'ex': '',
                    'code': 'Example',
                    'tab': 'Table'
                    }

def process_reference_text(node, node_id):
    """Expand the reference text to include the right word,
    based on the prefix of the reference."""
    if node.get('expanded_ref'):
        assert 0, ('Already expanded!!  %s' % node)
    else:
        # Check that surrounding text does not contain the extra term
        node_index = node.parent.children.index(node)
        if node_index > 0:
            prev_node = node.parent.children[node_index-1]
            if (isinstance(prev_node, docutils.nodes.Text)):
                m = _EXPAND_REF_RE.match(prev_node.data)
                if m:
                    print(("Warning: '%s' citation has '%s' on its left" % (node_id, m.group(2))))

        # Add the extra term
        link = node.children[0]
        if '-' in node_id:
            reftype = node_id.split('-', 1)[0]
            if reftype in _EXPAND_REF_DICT:
                link.data = _EXPAND_REF_DICT[reftype] + ' ' + link.data
            else:
                print(("Warning: '%s' reference text not expanded" % node_id))
        else:
            print(("Warning: '%s' reference not hyphenated" % node_id))
        node['expanded_ref'] = True

######################################################################
#{ Feature Structures (AVMs)
######################################################################

class AVM:
    def __init__(self, ident):
        self.ident = ident
        self.keys = []
        self.vals = {}
    def assign(self, key, val):
        if key in self.keys: raise ValueError('duplicate key')
        self.keys.append(key)
        self.vals[key] = val
    def __str__(self):
        vals = []
        for key in self.keys:
            val = self.vals[key]
            if isinstance(val, AVMPointer):
                vals.append('%s -> %s' % (key, val.ident))
            else:
                vals.append('%s = %s' % (key, val))
        s = '{%s}' % ', '.join(vals)
        if self.ident: s += '[%s]' % self.ident
        return s

    def as_latex(self):
        return '\\begin{avm}\n%s\\end{avm}\n' % self._as_latex()

    def _as_latex(self, indent=0):
        if self.ident: ident = '\\@%s ' % self.ident
        else: ident = ''
        lines = ['%s %s & %s' % (indent*'    ', key,
                                 self.vals[key]._as_latex(indent+1))
                 for key in self.keys]
        return ident + '\\[\n' + ' \\\\\n'.join(lines) + '\\]\n'

    def _entry(self, val, cls):
        if isinstance(val, str):
            return docutils.nodes.entry('',
                docutils.nodes.paragraph('', val), classes=[cls])
        else:
            return docutils.nodes.entry('', val, classes=[cls])

    def _pointer(self, ident):
        return docutils.nodes.paragraph('', '', 
                    docutils.nodes.inline(ident, ident,
                                          classes=['avm-pointer']))
    def as_table(self):
        if not self.keys:
            return docutils.nodes.paragraph('', '[]',
                                            classes=['avm-empty'])
        
        rows = []
        for key in self.keys:
            val = self.vals[key]
            key_node = self._entry(key, 'avm-key')
            if isinstance(val, AVMPointer):
                eq_node = self._entry('\u2192', 'avm-eq') # right arrow
                val_node = self._entry(self._pointer(val.ident), 'avm-val')
            elif isinstance(val, AVM):
                eq_node = self._entry('=', 'avm-eq')
                val_node = self._entry(val.as_table(), 'avm-val')
            else:
                value = ('%s' % val.val).replace(' ', '\u00a0') # =nbsp
                eq_node = self._entry('=', 'avm-eq')
                val_node = self._entry(value, 'avm-val')
                
            rows.append(docutils.nodes.row('', key_node, eq_node, val_node))

            # Add left/right bracket nodes:
            if len(self.keys)==1: vpos = 'topbot'
            elif key == self.keys[0]: vpos = 'top'
            elif key == self.keys[-1]: vpos = 'bot'
            else: vpos = ''
            rows[-1].insert(0, self._entry('\u00a0', 'avm-%sleft' % vpos))
            rows[-1].append(self._entry('\u00a0', 'avm-%sright' % vpos))

            # Add id:
            if key == self.keys[0] and self.ident:
                rows[-1].append(self._entry(self._pointer(self.ident),
                                            'avm-ident'))
            else:
                rows[-1].append(self._entry('\u00a0', 'avm-ident'))

        colspecs = [docutils.nodes.colspec(colwidth=1) for i in range(6)]

        tbody = docutils.nodes.tbody('', *rows)
        tgroup = docutils.nodes.tgroup('', cols=3, *(colspecs+[tbody]))
        table = docutils.nodes.table('', tgroup, classes=['avm'])
        return table
    
class AVMValue:
    def __init__(self, ident, val):
        self.ident = ident
        self.val = val
    def __str__(self):
        if self.ident: return '%s[%s]' % (self.val, self.ident)
        else: return '%r' % self.val
    def _as_latex(self, indent=0):
        return '%s' % self.val

class AVMPointer:
    def __init__(self, ident):
        self.ident = ident
    def __str__(self):
        return '[%s]' % self.ident
    def _as_latex(self, indent=0):
        return '\\@{%s}' % self.ident

def parse_avm(s, ident=None):
    lines = [l.rstrip() for l in s.split('\n') if l.strip()]
    if not lines: raise ValueError(0)
    lines.append('[%s]' % (' '*(len(lines[0])-2)))

    # Create our new AVM.
    avm = AVM(ident)
    
    w = len(lines[0]) # Line width
    avmval_pos = None # (left, right, top) for nested AVMs
    key = None        # Key for nested AVMs
    ident = None      # Identifier for nested AVMs
    
    NESTED = re.compile(r'\[\s+(\[.*\])\s*\]$')
    ASSIGN = re.compile(r'\[\s*(?P<KEY>[^\[=>]+?)\s*'
                        r'(?P<EQ>=|->)\s*'
                        r'(\((?P<ID>\d+)\))?\s*'
                        r'((?P<VAL>.+?))\s*\]$')
    BLANK = re.compile(r'\[\s+\]$')

    for lineno, line in enumerate(lines):
        #debug('%s %s %s %r' % (lineno, key, avmval_pos, line))
        if line[0] != '[' or line[-1] != ']' or len(line) != w:
            raise ValueError(lineno)

        nested_m = NESTED.match(line)
        assign_m = ASSIGN.match(line)
        blank_m = BLANK.match(line)
        if not (nested_m or assign_m or blank_m):
            raise ValueError(lineno)
        
        if nested_m or (assign_m and assign_m.group('VAL').startswith('[')):
            left, right = line.index('[',1), line.rindex(']', 0, -1)+1
            if avmval_pos is None:
                avmval_pos = (left, right, lineno)
            elif avmval_pos[:2] != (left, right):
                raise ValueError(lineno)

        if assign_m:
            if assign_m.group('VAL').startswith('['):
                if key is not None: raise ValueError(lineno)
                if assign_m.group('EQ') != '=': raise ValueError(lineno)
                key = assign_m.group('KEY')
                ident = assign_m.group('ID')
            else:
                if assign_m.group('EQ') == '=':
                    avm.assign(assign_m.group('KEY'),
                               AVMValue(assign_m.group('ID'),
                                        assign_m.group('VAL')))
                else:
                    if assign_m.group('VAL').strip(): raise ValueError(lineno)
                    avm.assign(assign_m.group('KEY'),
                               AVMPointer(assign_m.group('ID')))

        if blank_m and avmval_pos is not None:
            left, right, top = avmval_pos
            valstr = '\n'.join(l[left:right] for l in lines[top:lineno])
            avm.assign(key, parse_avm(valstr, ident))
            key = avmval_pos = None
            
    return avm

######################################################################
#{ Doctest Indentation
######################################################################

class UnindentDoctests(Transform):
    """
    In our source text, we have indented most of the doctest blocks,
    for two reasons: it makes copy/pasting with the doctest script
    easier; and it's more readable.  But we don't *actually* want them
    to be included in block_quote environments when we output them.
    So this transform looks for any doctest_block's that are the only
    child of a block_quote, and eliminates the block_quote.
    """
    default_priority = 1000
    def apply(self):
        self.document.walkabout(UnindentDoctestVisitor(self.document))

class UnindentDoctestVisitor(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        docutils.nodes.NodeVisitor.__init__(self, document)
    def unknown_visit(self, node): pass
    def unknown_departure(self, node): pass
    def visit_block_quote(self, node):
        if (len(node) == sum([1 for c in node if
                              isinstance(c, docutils.nodes.doctest_block)])):
            node.replace_self(list(node))
        raise docutils.nodes.SkipNode()
        
######################################################################
#{ HTML Output
######################################################################
from epydoc.docwriter.html_colorize import PythonSourceColorizer
import epydoc.docwriter.html_colorize
epydoc.docwriter.html_colorize .PYSRC_EXPANDTO_JAVASCRIPT = ''

class CustomizedHTMLWriter(HTMLWriter):
    settings_defaults = HTMLWriter.settings_defaults.copy()
    settings_defaults.update({
        'stylesheet': CSS_STYLESHEET,
        'stylesheet_path': None,
        'output_encoding': 'ascii',
        'output_encoding_error_handler': 'xmlcharrefreplace',
        })
        
    def __init__(self):
        HTMLWriter.__init__(self)
        self.translator_class = CustomizedHTMLTranslator

    #def translate(self):
    #    postprocess(self.document)
    #    HTMLWriter.translate(self)

class CustomizedHTMLTranslator(HTMLTranslator):
    def __init__(self, document):
        HTMLTranslator.__init__(self, document)
        print((document.settings.__class__))
        self.head_prefix.append(COPY_CLIPBOARD_JS)

    def visit_pylisting(self, node):
        self._write_pylisting_file(node)
        self.body.append(self.CODEBOX_HEADER % ('pylisting', 'pylisting'))

    def depart_pylisting(self, node):
        self.body.append(self.CODEBOX_FOOTER)

    def visit_doctest_block(self, node):
        # Collect the text content of the doctest block.
        text = ''.join(('%s' % c) for c in node)
        text = textwrap.dedent(text)
        text = strip_doctest_directives(text)
        text = text.decode('latin1')

        # Colorize the contents of the doctest block.
        colorizer = HTMLDoctestColorizer(self.encode, node['callouts'])
        if node.get('is_codeblock'):
            pysrc = colorizer.colorize_codeblock(text)
        else:
            try:
                pysrc = colorizer.colorize_doctest(text)
            except:
                print(('='*70))
                print(text)
                print(('='*70))
                raise

        if node.get('is_codeblock'): typ = 'codeblock' 
        else: typ = 'doctest'
        pysrc = self.CODEBOX_ROW % (typ, typ, pysrc)

        if not isinstance(node.parent, pylisting):
            self.body.append(self.CODEBOX_HEADER % ('doctest', 'doctest'))
            self.body.append(pysrc)
            self.body.append(self.CODEBOX_FOOTER)
        else:
            self.body.append(pysrc)
            
        raise docutils.nodes.SkipNode() # Content already processed

    CODEBOX_HEADER = ('<div class="%s">\n'
                        '<table border="0" cellpadding="0" cellspacing="0" '
                        'class="%s" width="95%%">\n')
    CODEBOX_FOOTER = '</table></div>\n'
    CODEBOX_ROW = textwrap.dedent('''\
      <tr><td class="%s">
      <table border="0" cellpadding="0" cellspacing="0" width="100%%">
      <tr><td width="1" class="copybar"
              onclick="javascript:copy_%s_to_clipboard(this.nextSibling);"
              >&nbsp;</td>
      <td class="pysrc">%s</td>
      </tr></table></td></tr>\n''')

    # For generated pylisting files:
    _PYLISTING_FILE_HEADER = "# Natural Language Toolkit: %s\n\n"

    def _write_pylisting_file(self, node):
        if not os.path.exists(PYLISTING_DIR):
            os.mkdir(PYLISTING_DIR)
            
        name = re.sub('\W', '_', node['name'])
        filename = os.path.join(PYLISTING_DIR, name+PYLISTING_EXTENSION)
        out = open(filename, 'w')
        out.write(self._PYLISTING_FILE_HEADER % name)
        for child in node:
            if not isinstance(child, docutils.nodes.doctest_block):
                continue
            elif child['is_codeblock']:
                out.write(''.join(('%s' % c) for c in child)+'\n\n')
            elif INCLUDE_DOCTESTS_IN_PYLISTING_FILES:
                lines = ''.join(('%s' % c) for c in child).split('\n')
                in_doctest_block = False
                for line in lines:
                    if line.startswith('>>> '):
                        out.write(line[4:]+'\n')
                        in_doctest_block = True
                    elif line.startswith('... ') and in_doctest_block:
                        out.write(line[4:]+'\n')
                    elif line.strip():
                        if in_doctest_block:
                            out.write('# Expect:\n')
                        out.write('#     ' + line+'\n')
                        in_doctest_block = False
                    else:
                        out.write(line+'\n')
                        in_doctest_block = False
        out.close()

    def visit_literal(self, node):
        """Process text to prevent tokens from wrapping."""
        text = ''.join(('%s' % c) for c in node)
        text = text.decode('latin1')
        colorizer = HTMLDoctestColorizer(self.encode)
        pysrc = colorizer.colorize_inline(text)#.strip()
        #pysrc = colorize_doctestblock(text, self._markup_pysrc, True)
        self.body+= [self.starttag(node, 'tt', '', CLASS='doctest'),
                     '<span class="pre">%s</span></tt>' % pysrc]
        raise docutils.nodes.SkipNode() # Content already processed
                          
    def _markup_pysrc(self, s, tag):
        return '\n'.join('<span class="pysrc-%s">%s</span>' %
                         (tag, self.encode(line))
                         for line in s.split('\n'))

    def visit_example(self, node):
        self.body.append(
            '<p><table border="0" cellpadding="0" cellspacing="0" '
            'class="example">\n  '
            '<tr valign="top"><td width="30" align="right">'
            '%s</td><td width="15"></td><td>' % node['num'])

    def depart_example(self, node):
        self.body.append('</td></tr></table></p>\n')

    def visit_idxterm(self, node):
        self.body.append('<a name="%s" />' % node['name'])
        self.body.append('<span class="%s">' % ' '.join(node['classes']))
        if 'topic' in node['classes']: raise docutils.nodes.SkipChildren
        
    def depart_idxterm(self, node):
        self.body.append('</span>')

    def visit_index(self, node):
        self.body.append('<div class="index">\n<h1>Index</h1>\n')
        
    def depart_index(self, node):
        self.body.append('</div>\n')

    _seen_callout_markers = set()
    def visit_callout_marker(self, node):
        # Only add an id to a marker the first time we see it.
        add_id = (node['name'] not in self._seen_callout_markers)
        self._seen_callout_markers.add(node['name'])
        if add_id:
            self.body.append('<span id="%s">' % node['name'])
        self.body.append(CALLOUT_IMG % (node['number'], node['number']))
        if add_id:
            self.body.append('</span>')
        raise docutils.nodes.SkipNode() # Done with this node.

    def depart_field_name(self, node):
        # Don't add ":" in callout field lists.
        if 'callout' in node['classes']:
            self.body.append(self.context.pop())
        else:
            HTMLTranslator.depart_field_name(self, node)
    
    def _striphtml_len(self, s):
        return len(re.sub(r'&[^;]+;', 'x', re.sub(r'<[^<]+>', '', s)))

    def visit_caption(self, node):
        if isinstance(node.parent, pylisting):
            self.body.append('<tr><td class="caption">')
        HTMLTranslator.visit_caption(self, node)
        
    def depart_caption(self, node):
        if isinstance(node.parent, pylisting):
            self.body.append('</td></tr>')
        HTMLTranslator.depart_caption(self, node)

    def starttag(self, node, tagname, suffix='\n', empty=0, **attributes):
        if node.get('mimetype'):
            attributes['type'] = node.get('mimetype')
        return HTMLTranslator.starttag(self, node, tagname, suffix,
                                       empty, **attributes)
        
COPY_CLIPBOARD_JS = '''
<script language="javascript" type="text/javascript">

function astext(node)
{
    return node.innerHTML.replace(/(<([^>]+)>)/ig,"")
                         .replace(/&gt;/ig, ">")
                         .replace(/&lt;/ig, "<")
                         .replace(/&quot;/ig, \'"\')
                         .replace(/&amp;/ig, "&");
}

function copy_notify(node, bar_color, data)
{
    // The outer box: relative + inline positioning.
    var box1 = document.createElement("div");
    box1.style.position = "relative";
    box1.style.display = "inline";
    box1.style.top = "2em";
    box1.style.left = "1em";
  
    // A shadow for fun
    var shadow = document.createElement("div");
    shadow.style.position = "absolute";
    shadow.style.left = "-1.3em";
    shadow.style.top = "-1.3em";
    shadow.style.background = "#404040";
    
    // The inner box: absolute positioning.
    var box2 = document.createElement("div");
    box2.style.position = "relative";
    box2.style.border = "1px solid #a0a0a0";
    box2.style.left = "-.2em";
    box2.style.top = "-.2em";
    box2.style.background = "white";
    box2.style.padding = ".3em .4em .3em .4em";
    box2.style.fontStyle = "normal";
    box2.style.background = "#f0e0e0";

    node.insertBefore(box1, node.childNodes.item(0));
    box1.appendChild(shadow);
    shadow.appendChild(box2);
    box2.innerHTML="Copied&nbsp;to&nbsp;the&nbsp;clipboard: " +
                   "<pre class='copy-notify'>"+
                   data+"</pre>";
    setTimeout(function() { node.removeChild(box1); }, 1000);

    var elt = node.parentNode.firstChild;
    elt.style.background = "#ffc0c0";
    setTimeout(function() { elt.style.background = bar_color; }, 200);
}

function copy_codeblock_to_clipboard(node)
{
    var data = astext(node)+"\\n";
    if (copy_text_to_clipboard(data)) {
        copy_notify(node, "#40a060", data);
    }
}

function copy_doctest_to_clipboard(node)
{
    var s = astext(node)+"\\n   ";
    var data = "";

    var start = 0;
    var end = s.indexOf("\\n");
    while (end >= 0) {
        if (s.substring(start, start+4) == ">>> ") {
            data += s.substring(start+4, end+1);
        }
        else if (s.substring(start, start+4) == "... ") {
            data += s.substring(start+4, end+1);
        }
        /*
        else if (end-start > 1) {
            data += "# " + s.substring(start, end+1);
        }*/
        // Grab the next line.
        start = end+1;
        end = s.indexOf("\\n", start);
    }
    
    if (copy_text_to_clipboard(data)) {
        copy_notify(node, "#4060a0", data);
    }
}
    
function copy_text_to_clipboard(data)
{
    if (window.clipboardData) {
        window.clipboardData.setData("Text", data);
        return true;
     }
    else if (window.netscape) {
        // w/ default firefox settings, permission will be denied for this:
        netscape.security.PrivilegeManager
                      .enablePrivilege("UniversalXPConnect");
    
        var clip = Components.classes["@mozilla.org/widget/clipboard;1"]
                      .createInstance(Components.interfaces.nsIClipboard);
        if (!clip) return;
    
        var trans = Components.classes["@mozilla.org/widget/transferable;1"]
                       .createInstance(Components.interfaces.nsITransferable);
        if (!trans) return;
    
        trans.addDataFlavor("text/unicode");
    
        var str = new Object();
        var len = new Object();
    
        var str = Components.classes["@mozilla.org/supports-string;1"]
                     .createInstance(Components.interfaces.nsISupportsString);
        var datacopy=data;
        str.data=datacopy;
        trans.setTransferData("text/unicode",str,datacopy.length*2);
        var clipid=Components.interfaces.nsIClipboard;
    
        if (!clip) return false;
    
        clip.setData(trans,null,clipid.kGlobalClipboard);
        return true;
    }
    return false;
}
//-->
</script>
'''

######################################################################
#{ Docbook Output
######################################################################

from docbook import Writer as DocBookWriter, DocBookTranslator
import docbook

DOCBOOK_ROOT_NODE = "chapter"

APPENDIX_TITLE_RE = re.compile("^Appendix: (.*)$")

class CustomizedDocBookWriter(DocBookWriter):
    def translate(self):
        # what's the correct way to generate this??  why isn't it
        # getting generated for us??
        self.document.settings = docutils.frontend.Values(dict(
            strict_visitor=True, language_code='en',
            doctype=DOCBOOK_ROOT_NODE, output_encoding='utf-8',
            ))
        visitor = CustomizedDocBookTranslator(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()

class CustomizedDocBookTranslator(DocBookTranslator):
    def __init__(self, document):
        DocBookTranslator.__init__(self, document)

    def visit_compound(self, node):
        # Does compound need to be handled at all?
        warning('compound not handled yet')
    def depart_compound(self, node):
        pass

    # the standard writer doesn't like node['ids'] = []
    _next_id = 0
    def visit_target(self, node):
        if node.get('ids') == []:
            node['ids'] = ['target-id-%d' % self._next_id]
            self._next_id += 1
        DocBookTranslator.visit_target(self, node)

    # This is just a typo in the original (node.SkipNode should be
    # nodes.SkipNode)
    def visit_raw(self, node):
        if 'format' in node and node['format'] == 'docbook':
            self.body.append(node.astext())
        raise docutils.nodes.SkipNode

    def visit_inline(self, node):
        if 'category' in node.get('classes', ()):
            self.body.append('<emphasis role="smallcaps">')
        else:
            self.body.append("<emphasis>")
    def depart_inline(self, node):
        self.body.append("</emphasis>")

    def visit_caption(self, node):
        if isinstance(node.parent, pylisting):
            self.body.append("<title>")
        else:
            DocBookTranslator.visit_caption(self, node)

    def depart_caption(self, node): 
        if isinstance(node.parent, pylisting):
            self.body.append("</title>\n")
        else:
            DocBookTranslator.depart_caption(self, node)

    def visit_pylisting(self, node):
        self.visit_figure(node)

    def visit_pylisting(self, node):
        atts = {}
        if 'ids' in node.attributes and node.attributes['ids']:
            atts['id'] = node.attributes['ids'][0]
        try:
            last_child = node.children[-1]
            if isinstance(last_child, docutils.nodes.caption) and \
                    last_child.children != []:
                # Move the caption to the first element.
                node.children = [last_child] + node.children[0:-1]
        except IndexError:
            pass
                
        self.body.append(self.starttag(node, 'example', **atts))

    def depart_pylisting(self, node):
        self.body.append('</example>\n')

    # idxterm nodes have no special formatting.
    def visit_idxterm(self, node):
        self.body.append('<emphasis role="strong">')

    def depart_idxterm(self, node):
        self.body.append("</emphasis>")

    def visit_line(self, node):
        pass
    def depart_line(self, node):
        self.body.append('\n')
    
    def visit_example(self, node):

        title_child_idx, title_child = \
            docbook.child_of_instance(node, docbook.nodes.caption)

        atts = {}

#        No need to deliver these ids through to docbook
#        if 'ids' in node.attributes and node.attributes['ids']:
#            atts['id'] = node.attributes['ids'][-1]
            
        if "id" in node.attributes:
            atts["id"] = node.attributes["id"]

        # example with a title
        if title_child and title_child.children != []:
            self.stack_push(self.example_tag_stack, "example")
            self.body.append(self.starttag(node, "example", **atts))
            node.children = \
                docbook.item_to_front(node.children, title_child_idx)

        # linguistic examples (no title)
        else:
            if len(self.example_tag_stack) == 0:
                self.stack_push(self.example_tag_stack, "example")
                atts["role"] = "linguistic"
                self.body.append(self.starttag(node, "example", **atts))
                self.body.append("<title/>")
            else:
                self.stack_push(self.example_tag_stack, "orderedlist")
                if self.body[-1] != "</listitem>":
                    self.body.append('<orderedlist numeration="loweralpha">')
                self.body.append(self.starttag(node, "listitem", **atts))
            
    def depart_example(self, node):
        example_tag = self.stack_pop(self.example_tag_stack)
        if example_tag == "orderedlist":
            self.body.append("</listitem>")
        elif example_tag == "example":
            if self.body[-1] == "</listitem>":
                self.body.append("</orderedlist>")
            self.body.append("</%s>\n" % example_tag)

    def visit_image(self, node):
        if isinstance(node.parent, example):
            DocBookTranslator.visit_image(self, node, 'mediaobject')
        else:
            DocBookTranslator.visit_image(self, node)

    def visit_callout_marker(self, node):
        self.body.append('<xref linkend="%s"/>' % node['name'])

    def depart_callout_marker(self, node):
        pass

    def visit_title(self, node):
        # Remove the '^Appendix: ' string from titles within real
        # appendixes.  The name of the title seems to be the second
        # element in the node.
        match = APPENDIX_TITLE_RE.match(docbook.node_to_str(node[-1]))
        if match and DOCBOOK_ROOT_NODE == "appendix":
            del node[1]
            node.append(docutils.nodes.Text(match.group(1)))
        DocBookTranslator.visit_title(self, node)

    _not_handled = set()
    def unknown_visit(self, node):
        # print helpful warnings
        typ = node.__class__.__name__
        if typ not in self._not_handled:
            warning('not handled: %s' % typ)
            self._not_handled.add(typ)
        self.body.append('<!-- unknown visit: %s -->' % node)

        # display as literal
        #self.body.append('\n\n'+self.starttag(node, 'programlisting'))
        #self.body.append(
        # docbook.node_to_str(node).replace('&', '&amp;').replace('<', '&lt;'))
        #self.body.append('</programlisting>\n')
        #self.body.append('<!-- unknown visit: %s -->' % node)
        raise docutils.nodes.SkipNode
    def unknown_departure(self, node):
        self.body.append('<!-- unknown depart: %s -->' % node)
        pass

######################################################################
#{ LaTeX Output
######################################################################

class CustomizedLaTeXWriter(LaTeXWriter):
    settings_defaults = LaTeXWriter.settings_defaults.copy()
    settings_defaults.update({
        'output_encoding': 'utf-8',
        'output_encoding_error_handler': 'backslashreplace',
        #'use_latex_docinfo': True,
        'font_encoding': 'C10,T1',
        'stylesheet': LATEX_STYLESHEET_PATH,
        'documentoptions': '11pt,twoside',
        'use_latex_footnotes': True,
        'use_latex_toc': True,
        })
    
    def __init__(self):
        LaTeXWriter.__init__(self)
        self.translator_class = CustomizedLaTeXTranslator

    #def translate(self):
    #    postprocess(self.document)
    #    LaTeXWriter.translate(self)
        
class CustomizedLaTeXTranslator(LaTeXTranslator):
    
    # Not sure why we need this, but the old Makefile did it so I will too:
    encoding = '\\usepackage[%s,utf8x]{inputenc}\n'

    linking = ('\\usepackage[colorlinks=%s,linkcolor=%s,urlcolor=%s,'
               'citecolor=blue,'
               'bookmarks=true,bookmarksopenlevel=2]{hyperref}\n')
    
    foot_prefix = [] # (used to add bibliography, when requested)

    def __init__(self, document):
        LaTeXTranslator.__init__(self, document)
        # This needs to go before the \usepackage{inputenc}:
        self.head_prefix.insert(1, '\\usepackage[cjkgb,postscript]{ucs}\n')
        # Make sure we put these *before* the stylesheet include line.
        self.head_prefix.insert(-2, textwrap.dedent("""\
            % Unicode font:
            \usepackage{ttfucs}
            \DeclareTruetypeFont{cyberbit}{cyberbit}
            % Index:
            \\usepackage{makeidx}
            \\makeindex
            % Environment for source code listings:
            \\usepackage{float}
            \\floatstyle{ruled}
            \\newfloat{pylisting}{thp}{lop}[chapter]
            \\floatname{pylisting}{Listing}
            % For Python source code:
            \\usepackage{alltt}
            % Python source code: Prompt
            \\newcommand{\\pysrcprompt}[1]{\\textbf{#1}}
            \\newcommand{\\pysrcmore}[1]{\\textbf{#1}}
            % Python source code: Source code
            \\newcommand{\\pysrckeyword}[1]{\\textbf{#1}}
            \\newcommand{\\pysrcbuiltin}[1]{\\textbf{#1}}
            \\newcommand{\\pysrcstring}[1]{\\textit{#1}}
            \\newcommand{\\pysrcother}[1]{\\textbf{#1}}
            \\newcommand{\\pysrcdefname}[1]{\\textbf{#1}}
            % Python source code: Comments
            \\newcommand{\\pysrccomment}[1]{\\textrm{#1}}
            % Python interpreter: Traceback message
            \\newcommand{\\pysrcexcept}[1]{\\textbf{#1}}
            % Python interpreter: Output
            \\newcommand{\\pysrcoutput}[1]{#1}\n"""))
        # Tabularx conflicts with the avm package:
        self.head_prefix = [l for l in self.head_prefix
                            if ('{tabularx}' not in l and
                                '{\\extrarowheight}' not in l)]

    def bookmark(self, node):
        # this seems broken; just use the hyperref package's
        # "bookmarks" option instead.
        return

    def visit_title(self, node):
        LaTeXTranslator.visit_title(self, node)
        
        # hack: remove '*' in preface sections.
        if node.get('section_context') == 'preface':
            assert self.body[-1][-1] == '{'
            self.body[-1] = self.body[-1][:-1] + '*{'

    def visit_doctest_block(self, node):
        text = ''.join(('%s' % c) for c in node)
        text = textwrap.dedent(text)
        text = strip_doctest_directives(text)
        text = text.decode('latin1')
        colorizer = LaTeXDoctestColorizer(self.encode, wrap=False,
                                          callouts=node['callouts'])
        self.literal = True
        if node.get('is_codeblock'):
            pysrc = colorizer.colorize_codeblock(text)
        else:
            pysrc = colorizer.colorize_doctest(text)
        self.literal = False

        self.body.append(pysrc)
        raise docutils.nodes.SkipNode() # Content already processed
    

    def depart_document(self, node):
        self.body += self.foot_prefix
        LaTeXTranslator.depart_document(self, node)

    def depart_doctest_block(self, node):
        pass

    def visit_literal(self, node):
        self.literal = True
        wrap = (not self.node_is_inside_title(node))
        colorizer = LaTeXDoctestColorizer(self.encode, wrap)
        pysrc = colorizer.colorize_inline(('%s' % node[0]))
        #pysrc = colorize_doctestblock(('%s' % node[0]), markup_func, True)
        self.literal = False
        self.body.append('\\texttt{\\small %s}' % pysrc)
        raise docutils.nodes.SkipNode() # Content already processed

    def depart_literal(self, node):
        pass

    def node_is_inside_title(self, node):
        while node.parent is not None:
            if isinstance(node.parent, docutils.nodes.Titular):
                return True
            node = node.parent
        return False

    def visit_literal_block(self, node):
        LaTeXTranslator.visit_literal_block(self, node)
        self.body.append('\\small\n')

#     def _markup_pysrc(self, s, tag):
#         return '\n'.join('\\pysrc%s{%s}' % (tag, line)
#                          for line in self.encode(s).split('\n'))

#     def _markup_pysrc_wrap(self, s, tag):
#         """This version adds latex commands to allow for line wrapping
#         within literals."""
#         if '\255' in s:
#             warning('Literal contains char \\255')
#             return self._markup_pysrc(s, tag)
#         s = re.sub(r'(\W|\w\b)(?=.)', '\\1\255', s)
#         s = self.encode(s).replace('\255', '{\linebreak[0]}')
#         return '\n'.join('\\pysrc%s{%s}' % (tag, line)
#                          for line in s.split('\n'))

    def visit_image(self, node):
        """So image scaling manually"""
        # Images are rendered using \includegraphics from the graphicx
        # package.  By default, it assumes that bitmapped images
        # should be rendered at 72 DPI; but we'd rather use a
        # different scale.  So adjust the scale attribute & then
        # delegate to our parent class.
        node.attributes['scale'] = (node.attributes.get('scale', 100) *
                                    72.0/LATEX_DPI)
        return LaTeXTranslator.visit_image(self, node)
        
    def visit_example(self, node):
        self.body.append('\\begin{itemize}\n\item[%s] ' % node['num'])

    def depart_example(self, node):
        self.body.append('\\end{itemize}\n')

    def visit_idxterm(self, node):
        self.body.append('\\index{%s}' % node.astext())
        if 'topic' in node['classes']:
            raise docutils.nodes.SkipNode()
        elif 'termdef' in node['classes']:
            self.body.append('\\textbf{')
        else:
            self.body.append('\\textit{')
        
    def depart_idxterm(self, node):
        self.body.append('}')
    
    def visit_index(self, node):
        self.body.append('\\addcontentsline{toc}{chapter}{Subject Index}\n')
        self.body.append('\\printindex\n')
        raise docutils.nodes.SkipNode() # Content already processed

    def visit_docinfo(self, node):
        self.docinfo = []
        self.docinfo.append('\\begin{tabular}{ll}\n')

    def depart_docinfo(self, node):
        self.docinfo.append('\\end{tabular}\n')
        self.body = self.docinfo + self.body
        self.docinfo = None

    def visit_table(self, node):
        # For gloss tables, don't use 'longtable'.
        if 'gloss' in node['classes'] or 'avm' in node['classes']:
            self._orig_table_type = self.active_table._latex_type
            self.active_table._latex_type = 'tabular'
        LaTeXTranslator.visit_table(self, node)
        
    def depart_table(self, node):
        LaTeXTranslator.depart_table(self, node)
        if 'gloss' in node['classes'] or 'avm' in node['classes']:
            self.active_table._latex_type = self._orig_table_type

    def visit_callout_marker(self, node):
        self.body.append(self.encode(chr(0x2460+node['number']-1)))
        raise docutils.nodes.SkipNode()

    def visit_pylisting(self, node):
        self.visit_figure(node)
#        self.body.append('\n\\begin{pylisting}\n')
#        self.context.append('\n\\vspace{1ex}\n\\hrule\n\\end{pylisting}\n')

    def depart_pylisting(self, node):
        self.depart_figure(node)
#        self.body.append( self.context.pop() )

#     def visit_pysrc_block(self, node):
#         self.literal = True
#         colorizer = LaTeXDoctestColorizer(self.encode, wrap=False, 
#                                           callouts=node['callouts'])
#         text = ('%s' % node[0])
#         if node['is_doctest']:
#             text = strip_doctest_directives(text)
#             pysrc = colorizer.colorize_doctest(text)
#         else:
#             pysrc = colorizer.colorize_codeblock(text)
#         self.literal = False

#         # If we're the first child of a pylisting, then begin a
#         # boxedminipage environment.
#         if (node.parent[0] is node):
#             self.body.append('\n\n\\noindent\n'
#                              '\\begin{boxedminipage}{\\textwidth}\n')
            
#         self.body.append(pysrc)

#         # If we're the last non-caption child of a pylisting, then end
#         # the boxedminipage environment; otherwise, draw a horizontal
#         # rule to separate pysrc blocks in a listing.  The vspace
#         # arguments were picked via experimentation, to make the
#         # spacing look right.
#         if (node.parent[-1] is node or
#             (isinstance(node.parent[-1], docutils.nodes.caption) and
#              node.parent[-2] is node)):  # (the last child of a pylisting)
#             self.body.append('\\end{boxedminipage}\n')
#         else:                            # (not the last child)
#             self.body.append('\\vspace{-3.5ex}\\rule{\\textwidth}{1pt}'
#                              '\\vspace{-2.5ex}\n')
            
#         raise docutils.nodes.SkipNode() # Content already processed

    def circledigit(self, n):
        return docutils.nodes.Text(chr(0x2460+n-1))

    # Unfortunately, parbox doesn't interact well with alltt.  As a result,
    # any doctest or pysrc blocks inside an adominition get wrapped oddly.
    # To fix this, we replace the default code for visit_admonition, which
    # uses an fbox & parbox, with code that uses a boxedminipage instead.
    def visit_admonition(self, node, name=''):
        self.body.append('\n')
        self.body.append('\\begin{table}[h]\n')
        self.body.append('\\begin{minipage}[t]{8ex}\\includegraphics{../images/jigsaw.png}\\end{minipage}\n')
        self.body.append('\\begin{minipage}[t]{\\admonitionwidth}\\begin{sffamily}\\small\\vspace*{-5ex}\n')
        #self.body.append('\\fbox{\\parbox{\\admonitionwidth}{\n')
        if name and name.lower() != 'note':
            self.body.append('\\textbf{\\large '+ self.language.labels[name] + '}\n');


    def depart_admonition(self, node=None):
        #self.body.append('}}\n') # end parbox fbox
        self.body.append('\\end{sffamily}\\end{minipage}\\end{table}\n');
        
    #def depart_title(self, node):
    #    LaTeXTranslator.depart_title(self, node)
    #    if self.section_level == 1:
    #        title = self.encode(node.children[0].astext())
    #        sectnum = node.parent.get('sectnum')
    #        if sectnum:
    #            self.body.append('\\def\\chtitle{%s. %s}\n' %
    #                             (sectnum, title))
    #        else:
    #            self.body.append('\\def\\chtitle{}\n')

    #def visit_reference(self, node):
    #    """The visit_reference method in LaTeXTranslator escapes the
    #    '#' in URLs; but this seems to be the wrong thing to do, at
    #    least when using pdflatex.  So override that behavior."""
    #    if node.has_key('refuri'):
    #        self.body.append('\\href{%s}{' % node['refuri'])
    #    else:
    #        LaTeXTranslator.visit_reference(self, node)

######################################################################
#{ Source Code Highlighting
######################################################################

# [xx] Note: requires the very latest svn version of epydoc!
from epydoc.markup.doctest import DoctestColorizer

class HTMLDoctestColorizer(DoctestColorizer):
    PREFIX = '<pre class="doctest">\n'
    SUFFIX = '</pre>\n'
    def __init__(self, encode_func, callouts=None):
        self.encode = encode_func
        self.callouts = callouts
    def markup(self, s, tag):
        if tag == 'output':
            s = re.sub(r'(?m)^[ \t]*<BLANKLINE>[ \t]*$', '', s)
        if tag == 'other':
            return self.encode(s)
        elif (tag == 'comment' and self.callouts is not None and
              CALLOUT_RE.match(s)):
            callout_id = CALLOUT_RE.match(s).group(1)
            callout_num = self.callouts[callout_id]
            img = CALLOUT_IMG % (callout_num, callout_num)
            return ('<a name="%s" /><a href="#ref-%s">%s</a>' %
                    (callout_id, callout_id, img))
        else:
            return ('<span class="pysrc-%s">%s</span>' %
                    (tag, self.encode(s)))

class LaTeXDoctestColorizer(DoctestColorizer):
    PREFIX = '\\begin{alltt}\\setlength{\\parindent}{4ex}\\hspace{\\parindent}\\scriptsize\\textbf{'
    SUFFIX = '}\\end{alltt}\n'
    def __init__(self, encode_func, wrap=False, callouts=None):
        self.encode = encode_func
        self.wrap = wrap
        self.callouts = callouts
    def _callout(self, m):
        callout_id = m.group(1)
        callout_num = self.callouts[callout_id]
        return self.encode(chr(0x2460+int(callout_num)-1))
    def markup(self, s, tag):
        if tag == 'output':
            s = re.sub(r'(?m)^[ \t]*<BLANKLINE>[ \t]*$', '', s)
        if (tag == 'comment' and self.callouts is not None and
            CALLOUT_RE.match(s)):
            return self._callout(CALLOUT_RE.match(s))

        if tag == 'output':
            s = CALLOUT_RE.sub(self._callout, s)
            
        if self.wrap and '\255' not in s:
            s = re.sub(r'(\W|\w\b)(?=.)', '\\1\255', s)
            s = self.encode(s).replace('\255', '{\linebreak[0]}')
        else:
            if self.wrap: warning('Literal contains char \\255')
            s = self.encode(s)
            
        if tag == 'other':
            return s
        else:
            return '\\pysrc%s{%s}' % (tag, s)


# # Regular expressions for colorize_doctestblock
# # set of keywords as listed in the Python Language Reference 2.4.1
# # added 'as' as well since IDLE already colorizes it as a keyword.
# # The documentation states that 'None' will become a keyword
# # eventually, but IDLE currently handles that as a builtin.
# _KEYWORDS = """
# and       del       for       is        raise    
# assert    elif      from      lambda    return   
# break     else      global    not       try      
# class     except    if        or        while    
# continue  exec      import    pass      yield    
# def       finally   in        print
# as
# """.split()
# _KEYWORD = '|'.join([r'\b%s\b' % _KW for _KW in _KEYWORDS])

# _BUILTINS = [_BI for _BI in dir(__builtins__) if not _BI.startswith('__')]
# _BUILTIN = (r'(?<!\.)(?:%s)' %
#             '|'.join([r'\b%s\b' % _BI for _BI in _BUILTINS]))

# _STRING = '|'.join([r'("""("""|.*?((?!").)"""))', r'("("|.*?((?!").)"))',
#                     r"('''('''|.*?[^\\']'''))", r"('('|.*?[^\\']'))"])
# _COMMENT = '(#.*?$)'
# _PROMPT1 = r'^\s*>>>(?:\s|$)'
# _PROMPT2 = r'^\s*\.\.\.(?:\s|$)'

# _DEFNAME = r'(?<=def )\w+|(?<=def  )\w+'

# PROMPT_RE = re.compile('(%s|%s)' % (_PROMPT1, _PROMPT2),
#                      re.MULTILINE | re.DOTALL)
# PROMPT2_RE = re.compile('(%s)' % _PROMPT2, re.MULTILINE | re.DOTALL)
# '''The regular expression used to find Python prompts (">>>" and
# "...") in doctest blocks.'''

# EXCEPT_RE = re.compile(r'(.*)(^Traceback \(most recent call last\):.*)',
#                        re.DOTALL | re.MULTILINE)

# DOCTEST_DIRECTIVE_RE = re.compile(r'#\s*doctest:.*')

# DOCTEST_RE = re.compile(r"""(?P<STRING>%s)|(?P<COMMENT>%s)|"""
#                         r"""(?P<KEYWORD>(%s))|(?P<BUILTIN>(%s))|"""
#                         r"""(?P<DEFNAME>%s)|"""
#                         r"""(?P<PROMPT1>%s)|(?P<PROMPT2>%s)|"""
#                         r"""(?P<OTHER_WHITESPACE>\s)|(?P<OTHER>.)""" %
#   (_STRING, _COMMENT, _KEYWORD, _BUILTIN, _DEFNAME, _PROMPT1, _PROMPT2),
#   re.MULTILINE | re.DOTALL)
# '''The regular expression used by L{_doctest_sub} to colorize doctest
# blocks.'''

# def colorize_doctestblock(s, markup_func, inline=False, strip_directives=True):
#     """
#     Colorize the given doctest string C{s} using C{markup_func()}.
#     C{markup_func()} should be a function that takes a substring and a
#     tag, and returns a colorized version of the substring.  E.g.:

#         >>> def html_markup_func(s, tag):
#         ...     return '<span class="%s">%s</span>' % (tag, s)

#     The tags that will be passed to the markup function are: 
#         - C{prompt} -- the Python PS1 prompt (>>>)
#       - C{more} -- the Python PS2 prompt (...)
#         - C{keyword} -- a Python keyword (for, if, etc.)
#         - C{builtin} -- a Python builtin name (abs, dir, etc.)
#         - C{string} -- a string literal
#         - C{comment} -- a comment
#       - C{except} -- an exception traceback (up to the next >>>)
#         - C{output} -- the output from a doctest block.
#         - C{other} -- anything else (does *not* include output.)
#     """
#     pysrc = [] # the source code part of a docstest block (lines)
#     pyout = [] # the output part of a doctest block (lines)
#     result = []
#     out = result.append

#     if strip_directives:
#         s = DOCTEST_DIRECTIVE_RE.sub('', s)

#     # Use this var to aggregate 'other' regions, since the regexp just
#     # gives it to us one character at a time:
#     other = [] 
    
#     def subfunc(match):
#         if match.group('OTHER'):
#             other.extend(match.group())
#             return ''
#         elif other:
#             v = markup_func(''.join(other), 'other')
#             del other[:]
#         else:
#             v = ''

#         if match.group('OTHER_WHITESPACE'):
#             return v+match.group() # No coloring for other-whitespace.
#         if match.group('PROMPT1'):
#             return v+markup_func(match.group(), 'prompt')
#       if match.group('PROMPT2'):
#           return v+markup_func(match.group(), 'more')
#         if match.group('KEYWORD'):
#             return v+markup_func(match.group(), 'keyword')
#         if match.group('BUILTIN'):
#             return v+markup_func(match.group(), 'builtin')
#         if match.group('DEFNAME'):
#             return v+markup_func(match.group(), 'defname')
#         if match.group('COMMENT'):
#             return v+markup_func(match.group(), 'comment')
#         if match.group('STRING') and '\n' not in match.group():
#             return v+markup_func(match.group(), 'string')
#         elif match.group('STRING'):
#             # It's a multiline string; colorize the string & prompt
#             # portion of each line.
#             pieces = [markup_func(s, ['string','more'][i%2])
#                       for i, s in enumerate(PROMPT2_RE.split(match.group()))]
#             return v+''.join(pieces)
#         else:
#             assert 0, 'unexpected match'

#     if inline:
#       pysrc = DOCTEST_RE.sub(subfunc, s)
#         if other: pysrc += markup_func(''.join(other), 'other')
#       return pysrc.strip()

#     # need to add a third state here for correctly formatting exceptions

#     for line in s.split('\n')+['\n']:
#         if PROMPT_RE.match(line):
#             pysrc.append(line)
#             if pyout:
#                 pyout = '\n'.join(pyout)
#                 m = EXCEPT_RE.match(pyout)
#                 if m:
#                     pyout, pyexc = m.group(1).strip(), m.group(2).strip()
#                     if pyout:
#                         warning('doctest does not allow for mixed '
#                              'output and exceptions!')
#                         result.append(markup_func(pyout, 'output'))
#                     result.append(markup_func(pyexc, 'except'))
#                 else:
#                     result.append(markup_func(pyout, 'output'))
#                 pyout = []
#         else:
#             pyout.append(line)
#             if pysrc:
#                 pysrc = DOCTEST_RE.sub(subfunc, '\n'.join(pysrc))
#                 if other:
#                     pysrc += markup_func(''.join(other), 'other')
#                     del other[:]
#                 result.append(pysrc.strip())
#                 #result.append(markup_func(pysrc.strip(), 'python'))
#                 pysrc = []

#     remainder = '\n'.join(pyout).rstrip()
#     if remainder:
#         result.append(markup_func(remainder, 'output'))
        
#     return '\n'.join(result)

######################################################################
#{ Old Code
######################################################################
# This was added so that chapter numbers could be propagated 
# to subsections properly; this is now done as part of the generation
# of the section numbering, rather than as a post-processing step.

# # Add chapter numbers; docutils doesn't handle (multi-file) books
# def chapter_numbers(out_file):
#     f = open(out_file).read()
#     # LaTeX
#     c = re.search(r'pdftitle={(\d+)\. ([^}]+)}', f)
#     if c:
#         chnum = c.group(1)
#         chtitle = c.group(2)
#         f = re.sub(r'(pdfbookmark\[\d+\]{)', r'\g<1>'+chnum+'.', f)
#         f = re.sub(r'(section\*{)', r'\g<1>'+chnum+'.', f)
#         f = re.sub(r'(\\begin{document})',
#                    r'\def\chnum{'+chnum+r'}\n' +
#                    r'\def\chtitle{'+chtitle+r'}\n' +
#                    r'\g<1>', f)
#         open(out_file, 'w').write(f)
#     # HTML
#     c = re.search(r'<h1 class="title">(\d+)\.', f)
#     if c:
#         chapter = c.group(1)
#         f = re.sub(r'(<h\d><a[^>]*>)', r'\g<1>'+chapter+'.', f)
#         open(out_file, 'w').write(f)

######################################################################
#{ Customized Reader (register new transforms)
######################################################################

class CustomizedReader(StandaloneReader):
    _TRANSFORMS = [
        Citations,                  #  500
        NumberNodes,                #  800
        SaveIndexTerms,             #  810
        NumberReferences,           #  830
        ResolveExternalCrossrefs,   #  849
        UnindentDoctests,           # 1000
        ]
    def get_transforms(self):
        return StandaloneReader.get_transforms(self) + self._TRANSFORMS

######################################################################
#{ Logging
######################################################################

try:
    from epydoc.cli import ConsoleLogger
    from epydoc.log import DEBUG, ERROR, WARNING
    logger = ConsoleLogger(0)
    #def log(msg): logger.progress(0, msg)
except Exception as e:
    DEBUG = ERROR = WARNING = 0
    class FakeLogger:
        def __getattr__(self, a):
            return (lambda *args: None)
    logger = FakeLogger()

# monkey-patch RSTState to give us progress info.
from docutils.parsers.rst.states import RSTState
_old_RSTState_section = RSTState.section
_section = 'Parsing'
def _new_RSTState_section(self, title, source, style, lineno, messages):
    lineno = self.state_machine.abs_line_number()
    numlines = (len(self.state_machine.input_lines) +
                self.state_machine.input_offset)
    progress = 0.5 * lineno / numlines
    global _section
    if style == ('=','='): _section = title
    _section = _section.encode('ascii', 'replace')
    logger.progress(progress, '%s -- line %d/%d' % (_section,lineno,numlines))
    _old_RSTState_section(self, title, source, style, lineno, messages)
RSTState.section = _new_RSTState_section

# monkey-patch Publisher to give us progress info.
from docutils.core import Publisher
_old_Publisher_apply_transforms = Publisher.apply_transforms
def _new_Publisher_apply_transforms(self):
    logger.progress(.6, 'Processing Document Tree')
    _old_Publisher_apply_transforms(self)
    logger.progress(.9, 'Writing Output')
Publisher.apply_transforms = _new_Publisher_apply_transforms

supress_warnings = False
def debug(s):
    s = ('%s' % s)
    if s.strip(): logger.log(DEBUG, s.strip())
def warning(s):
    if supress_warnings: return
    s = ('%s' % s)
    if s.strip(): logger.log(WARNING, s.strip())
def error(s):
    s = ('%s' % s)
    if s.strip(): logger.log(ERROR, s.strip())

class WarningStream:
    isatty = False
    closed = False
    def write(self, s): warning(s)
    def writelines(self, seq): warning(''.join(seq))
    def flush(self): pass
    def close(self): pass

######################################################################
#{ Main Script
######################################################################
__version__ = 0.2

def parse_args():
    optparser = OptionParser()

    optparser.add_option("--html", 
        action="store_const", dest="action", const="html",
        help="Write HTML output.")
    optparser.add_option("--latex", "--tex",
        action="store_const", dest="action", const="latex",
        help="Write LaTeX output.")
    optparser.add_option("--docbook", 
        action="store_const", dest="action", const="docbook",
        help="Write docbook output.")
    optparser.add_option("--ref",
        action="store_const", dest="action", const="ref",
        help="Generate references linking file.")
    optparser.add_option("--documentclass",
        action="store", dest="documentclass", 
        help="Document class for latex output (article, book).")
    optparser.add_option("--a4",
        action="store_const", dest="papersize", const="a4paper",
        help="Use a4 paper size.")
    optparser.add_option("--letter",
        action="store_const", dest="papersize", const="letterpaper",
        help="Use letter paper size.")
    optparser.add_option("--css",
        action="store", dest="css", help="CSS stylesheet")
    optparser.add_option("--bibliography",
        action="store_const", dest="bibliography", const=True,
        help="Include a bibliography (LaTeX only).")
    optparser.add_option("-o",
        action="store", dest="outputfile", help="Output File")
    optparser.add_option("--bibtex_file", action="store", dest="bibtex_file",
        help="BibTeX .bib file to use.")
    optparser.add_option("--latex_stylesheet_path", action="store",
        dest="latex_stylesheet", help="LaTeX definitions.sty file to use.")
    optparser.set_defaults(action='html', documentclass='report',
                           papersize='letterpaper',
                           bibliography=False,
                           outputfile=None,
                           bibtex_file=BIBTEX_FILE,
                           css=CSS_STYLESHEET,
                           latex_stylesheet=LATEX_STYLESHEET_PATH)

    options, filenames = optparser.parse_args()
    if options.outputfile is not None and len(filenames)>1:
        optparser.error('-o can only be used with one filename')

    return options, filenames

def main():
    global OUTPUT_FORMAT, OUTPUT_BASENAME, EXTERN_REFERENCE_FILES
    global LOCAL_BIBLIOGRAPHY
    options, filenames = parse_args()

    if not os.path.exists(TREE_IMAGE_DIR):
        os.mkdir(TREE_IMAGE_DIR)

    if docutils.writers.html4css1.Image is None:
        warning('Cannot scale images in HTML unless Python '
             'Imaging\n         Library (PIL) is installed!')

    if options.css:
        CustomizedHTMLWriter.settings_defaults.update({
            'stylesheet': options.css})

    EXTERN_REFERENCE_FILES = [f for f in filenames if
                              f.endswith(REF_EXTENSION)]
    filenames = [f for f in filenames if not f.endswith(REF_EXTENSION)]

    CustomizedLaTeXWriter.settings_defaults.update(dict(
        documentclass = options.documentclass,
        stylesheet=options.latex_stylesheet,
        use_latex_docinfo = (options.documentclass=='book')))
    CustomizedLaTeXWriter.settings_defaults['documentoptions'] += (
        ','+options.papersize)

    if options.documentclass == 'article':
        NumberingVisitor.TOP_SECTION = 'section'
    else:
        NumberingVisitor.TOP_SECTION = 'chapter'

    if options.bibliography:
        LOCAL_BIBLIOGRAPHY = True
        CustomizedLaTeXTranslator.foot_prefix += [
            '\\bibliographystyle{apalike}\n',
            '\\addcontentsline{toc}{chapter}{Bibliography}\n',
            '\\bibliography{%s}\n' %
            os.path.splitext(options.bibtex_file)[0]]

    OUTPUT_FORMAT = options.action
    if options.action == 'html':
        writer = CustomizedHTMLWriter()
        output_ext = '.html'
    elif options.action == 'latex':
        writer = CustomizedLaTeXWriter()
        output_ext = '.tex'
    elif options.action == 'docbook':
        writer = CustomizedDocBookWriter()
        output_ext = '.xml'
    elif options.action == 'ref':
        writer = None
        global supress_warnings
        supress_warnings = True
        output_ext = REF_EXTENSION
    else:
        assert 0, 'bad action'

    settings = { 'warning_stream': WarningStream(), }

    for in_file in filenames:
        OUTPUT_BASENAME = os.path.splitext(in_file)[0]
        if options.outputfile != None:
            out_file = options.outputfile
        else:
            out_file = os.path.splitext(in_file)[0] + output_ext
        logger.start_progress()#'%s -> %s' % (in_file, out_file))
        if in_file == out_file: out_file += output_ext

        # For .ref files:
        if writer is None:
            if os.path.exists(out_file): os.remove(out_file)
            docutils.core.publish_doctree(source=None, source_path=in_file,
                                          source_class=docutils.io.FileInput,
                                          reader=CustomizedReader(),
                                          settings_overrides=settings)

        # For .tex and .html files:
        else:
            global DOCBOOK_ROOT_NODE
            if in_file == "ch00.rst" or in_file == "ch12.rst":
                DOCBOOK_ROOT_NODE="preface"
            if in_file.startswith("app"):
                DOCBOOK_ROOT_NODE="appendix"
            docutils.core.publish_file(source_path=in_file, writer=writer,
                                       destination_path=out_file,
                                       reader=CustomizedReader(),
                                       settings_overrides=settings)
        logger.end_progress()

if __name__ == '__main__':
    try:
        main()
    except docutils.utils.SystemMessage as e:
        print(('Fatal error encountered!', e))
        raise
        sys.exit(-1)
