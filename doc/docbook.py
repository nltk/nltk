#!/usr/bin/env python

# Misc hacks by Steven Bird for NLTK book

"""
:Author: Ollie Rutherfurd
:Contact: oliver@rutherfurd.net
:Revision: $Revision: 4701 $
:Date: $Date: 2006-08-25 14:10:05 -0400 (Fri, 25 Aug 2006) $
:Copyright: This module has been placed in the public domain.

DocBook XML document tree Writer.

This Writer converts a reST document tree to a subset
of DocBook.

**This is an unfinished work in progress.**
"""

__docformat__ = 'reStructuredText'

import re
import string
import textwrap
from docutils import writers, nodes, languages
from types import ListType
import Image

# XML entity definitions are similar to HTML ones. we use them to
# escape special charicters.
import html.entities

class Writer(writers.Writer):

    settings_spec = (
        'DocBook-Specific Options',
        None,
        (('Set DocBook document type. '
            'Choices are "article", "book", and "chapter". '
            'Default is "article".',
            ['--doctype'],
            {'default': 'article', 
             'metavar': '<name>',
             'type': 'choice', 
             'choices': ('article', 'book', 'chapter', 'preface', 'appendix')
            }
         ),
        )
    )


    """DocBook does it's own section numbering"""
    settings_default_overrides = {'enable_section_numbering': 0}

    output = None
    """Final translated form of `document`."""

    def translate(self):
        visitor = DocBookTranslator(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


class DocBookTranslator(nodes.NodeVisitor):

    XML_DECL = '<?xml version="1.0" encoding="%s"?>\n'

    DOCTYPE_DECL = """<!DOCTYPE %s 
        PUBLIC "-//OASIS//DTD DocBook XML V4.4//EN"
        "http://www.oasis-open.org/docbook/xml/4.4/docbookx.dtd">\n"""

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.language = languages.get_language(
            document.settings.language_code)
        self.doctype = document.settings.doctype
        self.doc_header = [
            self.XML_DECL % (document.settings.output_encoding,),
            self.DOCTYPE_DECL % (self.doctype,),
            '<%s>\n' % (self.doctype,),
        ]
        self.doc_footer = [
            '</%s>\n' % (self.doctype,)
        ]
        self.body = []
        self.section = 0
        self.context = []
        self.colnames = []
        self.footnotes = {}
        self.footnote_map = {}
        self.docinfo = []
        self.title = ''
        self.subtitle = ''
        self.table_tag_stack = []
        self.figure_tag_stack = []
        self.example_tag_stack = []
        self.section_stack = []
        self._OPTION_DIRECTIVE_RE = re.compile(
            r'(\n[ ]*\.\.\.[ ]*)?#\s*doctest:\s*([^\n\'"]*)$', re.MULTILINE)

    def stack_push(self, stack, item):
        "Push an item onto the given stack"
        stack += [item]

    def stack_pop(self, stack):
        "Pop an item off the given stack and return it"
        item = self.stack_peek(stack)
        if item:
            del stack[-1]
            return item
        else:
            return None

    def stack_peek(self, stack):
        "Peek at the item on the top of the stack"
        try:
            return stack[-1]
        except IndexError:
            return None

    def astext(self):
        return ''.join(self.doc_header
                    + self.docinfo
                    + self.body
                    + self.doc_footer)

    def encode(self, text):
        """Encode special characters in `text` & return."""
        # @@@ A codec to do these and all other 
        # HTML entities would be nice.
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace('"', "&quot;")
        text = text.replace(">", "&gt;")
        return text

    def encodeattr(self, text):
        """Encode attributes characters > 128 as &#XXX;"""
        buff = []
        for c in text:
            if ord(c) >= 128:
                buff.append('&#%d;' % ord(c))
            else:
                buff.append(c)
        return ''.join(buff)

    def rearrange_footnotes(self):
        """
        Replaces ``foonote_reference`` placeholders with
        ``footnote`` element content as DocBook and reST
        handle footnotes differently.

        DocBook defines footnotes inline, whereas they
        may be anywere in reST.  This function replaces the 
        first instance of a ``footnote_reference`` with 
        the ``footnote`` element itself, and later 
        references of the same a  footnote with 
        ``footnoteref`` elements.
        """
        for (footnote_id,refs) in list(self.footnote_map.items()):
            ref_id, context, pos = refs[0]
            context[pos] = ''.join(self.footnotes[footnote_id])
            for ref_id, context, pos in refs[1:]:
                context[pos] = '<footnoteref linkend="%s"/>' \
                    % (footnote_id,)

    def attval(self, text,
               transtable=string.maketrans('\n\r\t\v\f', '     ')):
        """Cleanse, encode, and return attribute value text."""
        return self.encode(text.translate(transtable))

    def starttag(self, node, tagname, suffix='\n', infix='', **attributes):
        """
        Construct and return a start tag given a node 
        (id & class attributes are extracted), tag name, 
        and optional attributes.
        """
        atts = {}
        for (name, value) in list(attributes.items()):
            atts[name.lower()] = value

        for att in ('xml:id',):             # node attribute overrides
            if att in node:
                atts[att] = node[att]

        attlist = list(atts.items())
        attlist.sort()
        parts = [tagname.lower()]
        for name, value in attlist:
            if value is None:           # boolean attribute
                # this came from the html writer, but shouldn't
                # apply here, as an element with no attribute
                # isn't well-formed XML.
                parts.append(name.lower())
            elif isinstance(value, ListType):
                values = [str(v) for v in value]
                parts.append('%s="%s"' % (name.lower(),
                                          self.attval(' '.join(values))))
            else:
                name = self.encodeattr(name.lower())
                value = str(self.encodeattr(str(value)))
                value = self.attval(value)
                parts.append('%s="%s"' % (name,value))

        return '<%s%s>%s' % (' '.join(parts), infix, suffix)

    def emptytag(self, node, tagname, suffix='\n', **attributes):
        """Construct and return an XML-compatible empty tag."""
        return self.starttag(node, tagname, suffix, infix=' /', **attributes)

    def visit_Text(self, node):
        self.body.append(self.encode(node.astext()))

    def depart_Text(self, node):
        pass

    def visit_address(self, node):
        # handled by visit_docinfo
        pass

    def depart_address(self, node):
        # handled by visit_docinfo
        pass

    def visit_admonition(self, node, name=''):
        # This shouldn't be placed in chapters.
        if self.doctype == "chapter" or \
                self.doctype == "preface" or \
                self.doctype == "appendix":
            raise nodes.SkipNode

        self.body.append(self.starttag(node, 'note'))

    def depart_admonition(self, node=None):
        self.body.append('</note>\n')

    def visit_attention(self, node):
        self.body.append(self.starttag(node, 'note'))
        self.body.append('\n<title>%s</title>\n' 
            % (self.language.labels[node.tagname],))

    def depart_attention(self, node):
        self.body.append('</note>\n')

    def visit_attribution(self, node):
        # attribution must precede blockquote content
        if isinstance(node.parent, nodes.block_quote):
            raise nodes.SkipNode
        self.body.append(self.starttag(node, 'attribution', ''))

    def depart_attribution(self, node):
        # attribution must precede blockquote content
        if not isinstance(node.parent, nodes.block_quote):
            self.body.append('</attribution>\n')

    # author is handled in ``visit_docinfo()``
    def visit_author(self, node):
        raise nodes.SkipNode

    # authors is handled in ``visit_docinfo()``
    def visit_authors(self, node):
        raise nodes.SkipNode

    def visit_block_quote(self, node):
        self.body.append(self.starttag(node, 'blockquote'))
        if isinstance(node[-1], nodes.attribution):
            self.body.append('<attribution>%s</attribution>\n' % node[-1].astext())

    def depart_block_quote(self, node):
        self.body.append('</blockquote>\n')

    def visit_bullet_list(self, node):
        self.body.append(self.starttag(node, 'itemizedlist'))

    def depart_bullet_list(self, node):
        self.body.append('</itemizedlist>\n')

    def visit_caption(self, node):
        if node.children == []:
            node_is_empty = True
        else:
            node_is_empty = False

        if isinstance(node.parent, nodes.table):
            if node_is_empty:
                raise nodes.SkipNode
            else:
                tag = "title"

        elif isinstance(node.parent, nodes.figure):
            if node_is_empty:
                raise nodes.SkipNode
            else:
                tag = "title"

        else:
            tag = "para"
        
        self.context.append(tag)
        self.body.append(self.starttag(node, self.context[-1]))

    def depart_caption(self, node):
        self.body.append('</%s>' % self.context.pop())

    def visit_caution(self, node):
        self.body.append(self.starttag(node, 'caution'))
        self.body.append('\n<title>%s</title>\n' 
            % (self.language.labels[node.tagname],))

    def depart_caution(self, node):
        self.body.append('</caution>\n')

    # reST & DocBook ciations are somewhat 
    # different creatures.
    #
    # reST seems to handle citations as a labled
    # footnotes, whereas DocBook doesn't from what
    # I can tell.  In DocBook, it looks like they're
    # an abbreviation for a published work, which 
    # might be in the bibliography.
    #
    # Quote:
    #
    #   The content of a Citation is assumed to be a reference 
    #   string, perhaps identical to an abbreviation in an entry 
    #   in a Bibliography. 
    #
    # I hoped to have citations behave look footnotes,
    # using the citation label as the footnote label,
    # which would seem functionally equivlent, however
    # the DocBook stylesheets for generating HTML & FO 
    # output don't seem to be using the label for foonotes
    # so this doesn't work very well.
    #
    # Any ideas or suggestions would be welcome.

    def visit_citation(self, node):
        self.visit_footnote(node)

    def depart_citation(self, node):
        self.depart_footnote(node)

    def visit_citation_reference(self, node):
        self.visit_footnote_reference(node)

    def depart_citation_reference(self, node):
        # there isn't a a depart_footnote_reference
        pass

    def visit_classifier(self, node):
        self.body.append(self.starttag(node, 'type'))

    def depart_classifier(self, node):
        self.body.append('</type>\n')

    def visit_colspec(self, node):
        self.colnames.append('col_%d' % (len(self.colnames) + 1,))
        atts = {'colname': self.colnames[-1]}
        self.body.append(self.emptytag(node, 'colspec', **atts))

    def depart_colspec(self, node):
        pass

    def visit_comment(self, node, sub=re.compile('-(?=-)').sub):
        """Escape double-dashes in comment text."""
        #self.body.append('<!-- %s -->\n' % sub('- ', node.astext()))
        raise nodes.SkipNode

    # contact is handled in ``visit_docinfo()``
    def visit_contact(self, node):
        raise nodes.SkipNode

    # copyright is handled in ``visit_docinfo()``
    def visit_copyright(self, node):
        raise nodes.SkipNode

    def visit_danger(self, node):
        self.body.append(self.starttag(node, 'caution'))
        self.body.append('\n<title>%s</title>\n' 
            % (self.language.labels[node.tagname],))

    def depart_danger(self, node):
        self.body.append('</caution>\n')

    # date is handled in ``visit_docinfo()``
    def visit_date(self, node):
        raise nodes.SkipNode

    def visit_decoration(self, node):
        pass
    def depart_decoration(self, node):
        pass

    def visit_definition(self, node):
        # "term" is not closed in depart_term
        self.body.append('</term>\n')
        self.body.append(self.starttag(node, 'listitem'))

    def depart_definition(self, node):
        self.body.append('</listitem>\n')

    def visit_definition_list(self, node):
        self.body.append(self.starttag(node, 'variablelist'))

    def depart_definition_list(self, node):
        self.body.append('</variablelist>\n')

    def visit_definition_list_item(self, node):
        self.body.append(self.starttag(node, 'varlistentry'))

    def depart_definition_list_item(self, node):
        self.body.append('</varlistentry>\n')

    def visit_description(self, node):
        self.body.append(self.starttag(node, 'entry'))

    def depart_description(self, node):
        self.body.append('</entry>\n')

    def visit_docinfo(self, node):
        """
        Collects all docinfo elements for the document.

        Since reST's bibliography elements don't map very
        cleanly to DocBook, rather than maintain state and
        check dependencies within the different visitor
        fuctions all processing of bibliography elements
        is dont within this function.

        .. NOTE:: Skips processing of all child nodes as
                  everything should be collected here.
        """

        # XXX There are a number of fields in docinfo elements
        #     which don't map nicely to docbook elements and 
        #     reST allows one to insert arbitrary fields into
        #     the header, We need to be able to handle fields
        #     which either don't map or nicely or are unexpected.
        #     I'm thinking of just using DocBook to display these
        #     elements in some sort of tabular format -- but
        #     to collecting them is not straight-forward.  
        #     Paragraphs, links, lists, etc... can all live within
        #     the values so we either need a separate visitor
        #     to translate these elements, or to maintain state
        #     in any possible child elements (not something I
        #     want to do).

        docinfo = ['<%sinfo>\n' % self.doctype]

        address = ''
        authors = []
        author = ''
        contact = ''
        date = ''
        legalnotice = ''
        orgname = ''
        releaseinfo = ''
        revision,version = '',''
 
        docinfo.append('<title>%s</title>\n' % self.title)
        if self.subtitle:
            docinfo.append('<subtitle>%s</subtitle>\n' % self.subtitle)

        for n in node:
            if isinstance(n, nodes.address):
                address = n.astext()
            elif isinstance(n, nodes.author):
                author = n.astext()
            elif isinstance(n, nodes.authors):
                for a in n:
                    authors.append(a.astext())
            elif isinstance(n, nodes.contact):
                contact = n.astext()
            elif isinstance(n, nodes.copyright):
                legalnotice = n.astext()
            elif isinstance(n, nodes.date):
                date = n.astext()
            elif isinstance(n, nodes.organization):
                orgname = n.astext()
            elif isinstance(n, nodes.revision):
                # XXX yuck
                revision = 'Revision ' + n.astext()
            elif isinstance(n, nodes.status):
                releaseinfo = n.astext()
            elif isinstance(n, nodes.version):
                # XXX yuck
                version = 'Version ' + n.astext()
            elif isinstance(n, nodes.field):
                # XXX
                import sys
                print("I don't do 'field' yet", file=sys.stderr)
                print(n.astext())
            # since all child nodes are handled here raise an exception
            # if node is not handled, so it doesn't silently slip through.
            else:
                print(dir(n))
                print(n.astext())
                raise self.unimplemented_visit(n)

        # can only add author if name is present
        # since contact is associate with author, the contact
        # can also only be added if an author name is given.
        if author:
            docinfo.append('<author>\n')
            docinfo.append('<othername>%s</othername>\n' % author)
            if contact:
                docinfo.append('<email>%s</email>\n' % contact)
            docinfo.append('</author>\n')

        if authors:
            docinfo.append('<authorgroup>\n')
            for name in authors:
                docinfo.append(
                    '<author><othername>%s</othername></author>\n' % name)
            docinfo.append('</authorgroup>\n')

        if revision or version:
            edition = version
            if edition and revision:
                edition += ', ' + revision
            elif revision:
                edition = revision
            docinfo.append('<edition>%s</edition>\n' % edition)

        if date:
            docinfo.append('<date>%s</date>\n' % date)

        if orgname:
            docinfo.append('<orgname>%s</orgname>\n' % orgname)

        if releaseinfo:
            docinfo.append('<releaseinfo>%s</releaseinfo>\n' % releaseinfo)

        if legalnotice:
            docinfo.append('<legalnotice>\n')
            docinfo.append('<para>%s</para>\n' % legalnotice)
            docinfo.append('</legalnotice>\n')

        if address:
            docinfo.append('<address xml:space="preserve">' + 
                address + '</address>\n')

        if len(docinfo) > 1:
            docinfo.append('</%sinfo>\n' % self.doctype)

        self.docinfo = docinfo

        raise nodes.SkipChildren

    def depart_docinfo(self, node):
        pass

    def visit_doctest_block(self, node):
        def strip_doctest_directives(text):
            return self._OPTION_DIRECTIVE_RE.sub('', text)

        def replace_html_entity(c):
            try:
                return str("&%s;" % html.entities.codepoint2name[ord(c)])
            except KeyError:
                return c

        def create_anchors(text, callouts):
            for name, line in list(callouts.items()):
                text = re.sub("# *\[_%s\]" % name, 
                              "<co id=\"ref-%s\"/>" % name, 
                              text)
            return text

        self.body.append('\n<programlisting>')

        text = ''.join(str(c).encode('utf8') for c in node)
        text = textwrap.dedent(text)
        text = strip_doctest_directives(text)
        text = text.decode('utf8')
        text = ''.join(map(replace_html_entity, text))
        text = create_anchors(text, node['callouts'])
        
        self.body.append(text)
        self.body.append('</programlisting>\n')
        raise nodes.SkipNode # This node processes it's children.

    def depart_doctest_block(self, node):
        pass

    def visit_document(self, node):
        pass

    def depart_document(self, node):
        self.rearrange_footnotes()

    def visit_emphasis(self, node):
        self.body.append('<emphasis>')

    def depart_emphasis(self, node):
        self.body.append('</emphasis>')

    def visit_entry(self, node):
        tagname = 'entry'
        atts = {}
        if 'morerows' in node:
            atts['morerows'] = node['morerows']
        if 'morecols' in node:
            atts['namest'] = self.colnames[self.entry_level]
            atts['nameend'] = self.colnames[self.entry_level \
                + node['morecols']]
        self.entry_level += 1   # for tracking what namest and nameend are
        self.body.append(self.starttag(node, tagname, '', **atts))

    def depart_entry(self, node):
        self.body.append('</entry>\n')

    def visit_enumerated_list(self, node):
        # TODO: need to specify "mark" type used for list items
        self.body.append(self.starttag(node, 'orderedlist'))

    def depart_enumerated_list(self, node):
        self.body.append('</orderedlist>\n')

    def visit_error(self, node):
        self.body.append(self.starttag(node, 'caution'))
        self.body.append('\n<title>%s</title>\n' 
            % (self.language.labels[node.tagname],))

    def depart_error(self, node):
        self.body.append('</caution>\n')

    # TODO: wrap with some element (filename used in DocBook example)
    def visit_field(self, node):
        self.body.append(self.starttag(node, 'varlistentry'))

    def depart_field(self, node):
        self.body.append('</varlistentry>\n')

    # TODO: see if this should be wrapped with some element
    def visit_field_argument(self, node):
        self.body.append(' ')

    def depart_field_argument(self, node):
        pass

    def visit_field_body(self, node):
        # NOTE: this requires that a field body always
        #   be present, which looks like the case
        #   (from docutils.dtd)
        self.body.append(self.context.pop())
        self.body.append(self.starttag(node, 'listitem'))

    def depart_field_body(self, node):
        self.body.append('</listitem>\n')

    def visit_field_list(self, node):
        self.body.append(self.starttag(node, 'variablelist'))

    def depart_field_list(self, node):
        self.body.append('</variablelist>\n')

    def visit_field_name(self, node):
        self.body.append(self.starttag(node, 'term'))
        # popped by visit_field_body, so "field_argument" is
        # content within "term"
        self.context.append('</term>\n')

    def depart_field_name(self, node):
        pass

    def visit_figure(self, node):
        atts = {}
        if 'ids' in node.attributes and node.attributes['ids']:
            atts['id'] = node.attributes['ids'][0]
        try:
            last_child = node.children[-1]
            if isinstance(last_child, nodes.caption) and \
                    last_child.children != []:
                figure_tag = "figure"
                # Move the caption to the first element.
                node.children = [last_child] + node.children[0:-1]
            else:
                figure_tag = "informalfigure"
        except IndexError:
            figure_tag = "informalfigure"
                
        self.body.append(self.starttag(node, figure_tag, **atts))
        self.stack_push(self.figure_tag_stack, figure_tag)

    def depart_figure(self, node):
        figure_tag = self.stack_pop(self.figure_tag_stack)
        self.body.append('</%s>\n' % figure_tag)

    # TODO: footer (this is where 'generated by docutils' arrives)
    # if that's all that will be there, it could map to "colophon"
    def visit_footer(self, node):
        raise nodes.SkipChildren

    def depart_footer(self, node):
        pass

    def visit_footnote(self, node):
        self.footnotes[node['ids'][0]] = []
        atts = {'xml:id': node['ids'][0]}
        if isinstance(node[0], nodes.label):
            atts['label'] = node[0].astext()
        self.footnotes[node['ids'][0]].append(
            self.starttag(node, 'footnote', **atts))

        # replace body with this with a footnote collector list
        # which will hold all the contents for this footnote.
        # This needs to be kept separate so it can be used to replace
        # the first ``footnote_reference`` as DocBook defines 
        # ``footnote`` elements inline. 
        self._body = self.body
        self.body = self.footnotes[node['ids'][0]]

    def depart_footnote(self, node):
        # finish footnote and then replace footnote collector
        # with real body list.
        self.footnotes[node['ids'][0]].append('</footnote>')
        self.body = self._body
        self._body = None

    def visit_footnote_reference(self, node):
        if 'refid' in node:
            refid = node['refid']
        else:
            refid = self.document.nameids[node['refname']]

        # going to replace this footnote reference with the actual
        # footnote later on, so store the footnote id to replace
        # this reference with and the list and position to replace it
        # in. Both list and position are stored in case a footnote
        # reference is within a footnote, in which case ``self.body``
        # won't really be ``self.body`` but a footnote collector
        # list.
        refs = self.footnote_map.get(refid, [])
        refs.append((node['ids'][0], self.body, len(self.body),))
        self.footnote_map[refid] = refs

        # add place holder list item which should later be 
        # replaced with the contents of the footnote element
        # and it's child elements
        self.body.append('<!-- REPLACE WITH FOOTNOTE -->')

        raise nodes.SkipNode

    def visit_header(self, node):
        pass
    def depart_header(self, node):
        pass

    # ??? does anything need to be done for generated?
    def visit_generated(self, node):
        raise nodes.SkipNode # Docbook generates it's own stuff chapter numbers
                             # and such.
    def depart_generated(self, node):
        pass

    def visit_hint(self, node):
        self.body.append(self.starttag(node, 'note'))
        self.body.append('\n<title>%s</title>\n' 
            % (self.language.labels[node.tagname],))

    def depart_hint(self, node):
        self.body.append('</note>\n')

    def visit_image(self, node, element=None):

        def docbook_scale_image(dimension, scale):
            # 1/64 is 12/768 which fits the description of scaling below.
            # Divide by 100.0 also since the scaling factor is expressed in a
            # percentage.
            return float(dimension) * scale / 100.0 / 64.0

        if not element:
            if isinstance(node.parent, nodes.paragraph):
                element = 'inlinemediaobject'
            elif isinstance(node.parent, nodes.reference):
                element = 'inlinemediaobject'
            else:
                element = 'mediaobject'

        atts = {}
        atts['fileref'] = node.attributes['uri']
        # NLTK specific:
        if atts['fileref'][:10] == '../images/':
            atts['fileref'] = 'figs/incoming/' + atts['fileref'][10:]
        if atts['fileref'][:12] == 'tree_images/':
            atts['fileref'] = 'figs/incoming/' + atts['fileref'][12:]

        # Scale images by specifying their width.  The sizes of the image files
        # and the scale values given in the RST source describe how much of the
        # page they should take up, 768 = Width * Scale is the whole width of
        # the page, just under 13cm in the O'Reilly rendered docbook output, (we
        # round this down to 12cm).
        if 'scale' in node.attributes:
            if ('height' in node.attributes) and ('width' in node.attributes):
                raise ValueError(
                    "docbook.py doesn't handle specifying image width in ReST")
            scale = node.attributes['scale']
            im = Image.open(node.attributes['uri'])
            atts['width'] = atts['contentwidth'] = "%fcm" % docbook_scale_image(im.size[0], scale)
            atts['depth'] = atts['contentdepth'] = "%fcm" % docbook_scale_image(im.size[1], scale)

        # Don't wrap the image in a para, this breaks when the image
        # is in a figure tag.  I don't know if it breaks anywhere
        # else. - boney.

        # self.body.append('<para>')

        # ensure image is contained in a figure so that it is allocated page space
        if element == 'mediaobject' and not self.figure_tag_stack and not self.table_tag_stack:
            self.body.append('<informalfigure>')

        self.body.append('<%s>' % element)
        self.body.append('<imageobject>')
        self.body.append(self.emptytag(node, 'imagedata', **atts))
        self.body.append('</imageobject>')
        if 'alt' in node.attributes:
            self.body.append('<textobject><phrase>%s</phrase></textobject>\n' % node.attributes['alt'])
        self.body.append('</%s>' % element)
        # self.body.append('</para>')

        if element == 'mediaobject' and not self.figure_tag_stack and not self.table_tag_stack:
            self.body.append('</informalfigure>')

    def depart_image(self, node):
        pass

    def visit_important(self, node):
        self.body.append(self.starttag(node, 'important'))

    def depart_important(self, node):
        self.body.append('</important>')

    # @@@ Incomplete, pending a proper implementation on the
    # Parser/Reader end.
    # XXX see if the default for interpreted should be ``citetitle``
    def visit_interpreted(self, node):
        self.body.append('<constant>\n')

    def depart_interpreted(self, node):
        self.body.append('</constant>\n')

    def visit_label(self, node):
        # getting label for "footnote" in ``visit_footnote``
        # because label is an attribute for the ``footnote``
        # element.
        if isinstance(node.parent, nodes.footnote):
            raise nodes.SkipNode
        # citations are currently treated as footnotes
        elif isinstance(node.parent, nodes.citation):
            raise nodes.SkipNode

    def depart_label(self, node):
        pass

    def visit_legend(self, node):
        # legend is placed inside the figure's ``blockquote``
        # so there's nothing special to be done for it
        pass

    def depart_legend(self, node):
        pass

    def visit_line_block(self, node):
        if node.parent.tagname == 'line_block':
            raise nodes.SkipNode
        self.body.append(self.starttag(node, 'literallayout'))

    def depart_line_block(self, node):
        if node.parent.tagname == 'line_block':
            raise nodes.SkipNode
        self.body.append('</literallayout>\n')

    def visit_list_item(self, node):
        self.body.append(self.starttag(node, 'listitem'))

    def depart_list_item(self, node):
        self.body.append('</listitem>\n')

    def visit_literal(self, node):
         self.body.append('<literal>')

    def depart_literal(self, node):
        self.body.append('</literal>')

    def visit_literal_block(self, node):
        self.body.append(self.starttag(node, 'programlisting'))

    def depart_literal_block(self, node):
        self.body.append('</programlisting>\n')

    def visit_note(self, node):
        self.body.append(self.starttag(node, 'note'))

    def depart_note(self, node):
        self.body.append('</note>\n')

    def visit_option(self, node):
        self.body.append(self.starttag(node, 'command'))
        if self.context[-1]:
            self.body.append(', ')

    def depart_option(self, node):
        self.context[-1] += 1
        self.body.append('</command>')

    def visit_option_argument(self, node):
        self.body.append(node.get('delimiter', ' '))
        self.body.append(self.starttag(node, 'replaceable', ''))

    def depart_option_argument(self, node):
        self.body.append('</replaceable>')

    def visit_option_group(self, node):
        self.body.append(self.starttag(node, 'entry'))
        self.context.append(0)

    def depart_option_group(self, node):
        self.context.pop()
        self.body.append('</entry>\n')

    def visit_option_list(self, node):
        self.body.append(self.starttag(node, 'informaltable', frame='all'))
        self.body.append('<tgroup cols="2">\n')
        self.body.append('<colspec colname="option_col"/>\n')
        self.body.append('<colspec colname="description_col"/>\n')
        self.body.append('<tbody>\n')

    def depart_option_list(self, node):
        self.body.append('</tbody>')
        self.body.append('</tgroup>\n')
        self.body.append('</informaltable>\n')

    def visit_option_list_item(self, node):
        self.body.append(self.starttag(node, 'row'))

    def depart_option_list_item(self, node):
        self.body.append('</row>\n')

    def visit_option_string(self, node):
        pass

    def depart_option_string(self, node):
        pass

    # organization is handled in ``visit_docinfo()``
    def visit_organization(self, node):
        raise nodes.SkipNode

    def visit_paragraph(self, node):
        if not isinstance(node.parent, nodes.caption):
            self.body.append(self.starttag(node, 'para', ''))
        
    def depart_paragraph(self, node):
        if not isinstance(node.parent, nodes.caption):
            self.body.append('</para>')

    # TODO: problematic
    visit_problematic = depart_problematic = lambda self, node: None

    def visit_raw(self, node):
        if 'format' in node and node['format'] == 'docbook':
            self.body.append(node.astext())
        raise node.SkipNode

    def visit_reference(self, node):
        pass
        # if parent is a section, 
        # wrap link in a para
#        if isinstance(node.parent, nodes.section):
#            self.body.append('<para>')
#
#        atts = {}
#        if node.has_key('refuri'):
#            self.context.append('ulink')
#            self.body.append(self.starttag(node, 'ulink', '', url=node['refuri']))
#        elif node.has_key('refid'):
#            self.context.append('xref')
#            self.body.append(self.starttag(node, 'xref', '', linkend=node['refid']))
#        elif node.has_key('refname'):
#            self.context.append('link')
#            self.body.append(self.starttag(node, 'link', '',
#                    linkend=self.document.nameids[node['refname']]))
#             self.body.append(node.astext())
#        else:
#            raise ValueError('Unidentified reference type:' + node.__str__())
            
    def depart_reference(self, node):
        pass
#       self.body.append('</%s>' % (self.context.pop(),))

        # if parent is a section, 
        # wrap link in a para
#        if isinstance(node.parent, nodes.section):
#            self.body.append('</para>')

    # revision is handled in ``visit_docinfo()``
    def visit_revision(self, node):
        raise nodes.SkipNode

    def visit_row(self, node):
        self.entry_level = 0
        self.body.append(self.starttag(node, 'row'))

    def depart_row(self, node):
        self.body.append('</row>\n')

    def visit_rubric(self, node):
        self.body.append(self.starttag(node, 'bridgehead'))

    def depart_rubric(self, node):
        self.body.append('</bridgehead>')

    def visit_section(self, node):
        if self.section:
            atts = {}
            # ignore the automatically-generated id (based on section title)
            # and only keep the user-supplied id
            if 'ids' in node.attributes and len(node.attributes['ids']) > 1:
                atts['id'] = node.attributes['ids'][1]
            section_tag = 'sect' + repr(self.section)
            if self.section > 1:  # don't number subsections
                section_tag = 'simplesect'
                if 'id' in atts:
                    raise ValueError("Identifier given to un-numbered section: " + atts['id'])
            self.body.append(self.starttag(node, section_tag, **atts))
            self.stack_push(self.section_stack, section_tag)

        self.section += 1
    
    def depart_section(self, node):
        self.section -= 1
        if self.section:
            section_tag = self.stack_pop(self.section_stack)
            self.body.append('</%s>\n' % section_tag)

    def visit_sidebar(self, node):
        self.body.append(self.starttag(node, 'sidebar'))
        if isinstance(node[0], nodes.title):
            self.body.append('<sidebarinfo>\n')
            self.body.append('<title>%s</title>\n' % node[0].astext())
            if isinstance(node[1], nodes.subtitle):
                self.body.append('<subtitle>%s</subtitle>\n' % node[1].astext())
            self.body.append('</sidebarinfo>\n')

    def depart_sidebar(self, node):
        self.body.append('</sidebar>\n')

    # author is handled in ``visit_docinfo()``
    def visit_status(self, node):
        raise nodes.SkipNode

    def visit_strong(self, node):
        self.body.append('<emphasis role="strong">')

    def depart_strong(self, node):
        self.body.append('</emphasis>')

    def visit_subscript(self, node):
        self.body.append(self.starttag(node, 'subscript', ''))

    def depart_subscript(self, node):
        self.body.append('</subscript>')

    def visit_substitution_definition(self, node):
        raise nodes.SkipNode

    def visit_substitution_reference(self, node):
        self.unimplemented_visit(node)

    def visit_subtitle(self, node):
        # document title needs to go into
        # <type>info/subtitle, so save it for
        # when we do visit_docinfo
        if isinstance(node.parent, nodes.document):
            self.subtitle = node.astext()
            raise nodes.SkipNode
        else:
            # sidebar subtitle needs to go into a sidebarinfo element
            #if isinstance(node.parent, nodes.sidebar):
            #    self.body.append('<sidebarinfo>')
            if isinstance(node.parent, nodes.sidebar):
                raise nodes.SkipNode
            self.body.append(self.starttag(node, 'subtitle', ''))

    def depart_subtitle(self, node):
        if not isinstance(node.parent, nodes.document):
            self.body.append('</subtitle>\n')
        #if isinstance(node.parent, nodes.sidebar):
        #    self.body.append('</sidebarinfo>\n')

    def visit_superscript(self, node):
        self.body.append(self.starttag(node, 'superscript', ''))

    def depart_superscript(self, node):
        self.body.append('</superscript>')

    # TODO: system_message
    visit_system_message = depart_system_message = lambda self, node: None

    def visit_table(self, node):
        atts = dict()
        if 'ids' in node.attributes and node.attributes['ids']:
            atts['id'] = node.attributes['ids'][0]
        elif node.parent and \
                not isinstance(node.parent, nodes.section) and \
                'ids' in node.parent.attributes and \
                node.parent.attributes['ids']:
            # Sometimes the parent carries the id for the table.
            atts['id'] = node.parent.attributes['ids'][0]

        # If a child is a non-empty title then make this a table,
        # otherwise an informal table.  Multiple 'title' children are
        # not handled.
        title_child_idx, title_child = child_of_instance(node, nodes.caption)

        if title_child and title_child.children != []:
            table_tag = "table"
            # This is probably naughty but let's mutate the children
            # so that the title comes first.
            node.children = item_to_front(node.children, title_child_idx)
        else:
            table_tag = "informaltable"
            if "id" in atts: # informal tables don't have identifiers
                del atts["id"]
            if 'gloss' in node['classes']:
                 atts['tabstyle'] = "orm:glossed-text-padding"

        self.body.append(self.starttag(node, table_tag, **atts))
        self.stack_push(self.table_tag_stack, table_tag)

    def depart_table(self, node):
        table_tag = self.stack_pop(self.table_tag_stack)
        self.body.append('</%s>\n' % table_tag)

    # don't think anything is needed for targets
    def visit_target(self, node):
        # XXX this would like to be a transform!
        # XXX comment this mess!
        handled = 0
        siblings = node.parent.children
        for i in range(len(siblings)):
            if siblings[i] is node:
                if i+1 < len(siblings):
                    next = siblings[i+1]
                    if isinstance(next,nodes.Text):
                        pass
                    elif 'id' not in next.attributes:
                        next['id'] = node['ids'][0]
                        handled = 1
        if not handled:
            if 'id' not in node.parent.attributes:
                # TODO node["ids"] 
                node.parent.attributes['id'] = node['ids'][0]
                handled = 1
        # might need to do more...
        # (if not handled, update the referrer to refer to the parent's id)

    def depart_target(self, node):
        pass

    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody'))

    def depart_tbody(self, node):
        self.body.append('</tbody>\n')

    def visit_term(self, node):
        self.body.append(self.starttag(node, 'term'))
        self.body.append('<varname>')

    def depart_term(self, node):
        # Leave the end tag "term" to ``visit_definition()``,
        # in case there's a classifier.
        self.body.append('</varname>')

    def visit_tgroup(self, node):
        self.colnames = []
        atts = {'cols': node['cols']}
        self.body.append(self.starttag(node, 'tgroup', **atts))

    def depart_tgroup(self, node):
        self.body.append('</tgroup>\n')

    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead'))

    def depart_thead(self, node):
        self.body.append('</thead>\n')

    def visit_tip(self, node):
        self.body.append(self.starttag(node, 'tip'))

    def depart_tip(self, node):
        self.body.append('</tip>\n')

    def visit_title(self, node):
        # document title needs to go inside
        # <type>info/title
        if isinstance(node.parent, nodes.document):
            self.title = node.astext()
            raise nodes.SkipNode
        elif isinstance(node.parent, nodes.sidebar):
            # sidebar title and subtitle are collected in visit_sidebar
            raise nodes.SkipNode
        
        self.body.append(self.starttag(node, 'title', ''))

    def depart_title(self, node):
        if not isinstance(node.parent, nodes.document):
            self.body.append('</title>\n')

    def visit_title_reference(self, node):
        self.body.append('<citetitle>')

    def depart_title_reference(self, node):
        self.body.append('</citetitle>')

    def visit_topic(self, node):
        # let DocBook handle Table of Contents generation
        if node.get('class') == 'contents':
            raise nodes.SkipChildren
        elif node.get('class') == 'abstract':
            self.body.append(self.starttag(node, 'abstract'))
            self.context.append('abstract')
        elif node.get('class') == 'dedication':
            # docbook only supports dedication in a book,
            # so we're faking it for article & chapter
            if self.doctype == 'book':
                self.body.append(self.starttag(node, 'dedication'))
                self.context.append('dedication')
            else:
                self.body.append(self.starttag(node, 'section'))
                self.context.append('section')

        # generic "topic" element treated as a section
        elif node.get('class','') == '':
            self.body.append(self.starttag(node, 'section'))
            self.context.append('section')
        else:
            # XXX DEBUG CODE
            print('class:', node.get('class'))
            print(node.__class__.__name__)
            print(node)
            print(repr(node))
            print(dir(node))
            self.unimplemented_visit(node)

    def depart_topic(self, node):
        if len(self.context):
            self.body.append('</%s>\n' % (self.context.pop(),))

    def visit_transition(self, node):
        pass
    def depart_transition(self, node):
        pass

    # author is handled in ``visit_docinfo()``
    def visit_version(self, node):
        raise nodes.SkipNode

    def visit_warning(self, node):
        self.body.append(self.starttag(node, 'warning'))

    def depart_warning(self, node):
        self.body.append('</warning>\n')

    def unimplemented_visit(self, node):
        raise NotImplementedError('visiting unimplemented node type: %s'
                % node.__class__.__name__)

# Utilitiy functions.

def child_of_instance(node, object):
    """
    If the node has a child of the given class return it's index
    within the children attribute and it its self.
    """
    for child_idx, child in enumerate(node.children): 
        if isinstance(child, object): 
            return child_idx, child 
    return None, None

def item_to_front(list, index):
    """
    Move the item at index of the list to the front of the list.  This
    is not done in-place, a new list is returned.
    """
    return [list[index]] + list[0 : index] + list[index + 1 : -1]


def node_to_str(node):
    """
    Return a unicode string representation of this node.  Docutils doesn't
    implement __str__ or __unicode__ properely, hence the need for this.
    """

    if node.children:
        return '%s%s%s' % (node.starttag(),
                            ''.join([node_to_str(c) for c in node.children]),
                            node.endtag())
    else:
        str = ""
        try:
            str += node.starttag()
        except:
            pass
        str += node.astext()
        try:
            str += node.endtag()
        except:
            pass
        return str

# :collapseFolds=0:folding=indent:indentSize=4:
# :lineSeparator=\n:noTabs=true:tabSize=4:
