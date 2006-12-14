
# YAML can be parsed by an LL(1) parser!
#
# We use the following production rules:
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END?
# implicit_document ::= block_node DOCUMENT-END?
# block_node    ::= ALIAS | properties? block_content
# flow_node     ::= ALIAS | properties? flow_content
# properties    ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# block_mapping     ::= BLOCK-MAPPING_START ((KEY block_node_or_indentless_sequence?)? (VALUE block_node_or_indentless_sequence?)?)* BLOCK-END
# block_node_or_indentless_sequence ::= ALIAS | properties? (block_content | indentless_block_sequence)
# indentless_block_sequence         ::= (BLOCK-ENTRY block_node?)+
# flow_collection   ::= flow_sequence | flow_mapping
# flow_sequence     ::= FLOW-SEQUENCE-START (flow_sequence_entry FLOW-ENTRY)* flow_sequence_entry? FLOW-SEQUENCE-END
# flow_mapping      ::= FLOW-MAPPING-START (flow_mapping_entry FLOW-ENTRY)* flow_mapping_entry? FLOW-MAPPING-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

# TODO: support for BOM within a stream.
# stream ::= (BOM? implicit_document)? (BOM? explicit_document)* STREAM-END

# FIRST sets:
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from error import MarkedYAMLError
from tokens import *
from events import *
from scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser:
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.
    # Note that we use Python generators. If you rewrite the parser in another
    # language, you may replace all 'yield'-s with event handler calls.

    DEFAULT_TAGS = {
        u'!':   u'!',
        u'!!':  u'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.event_generator = self.parse_stream()

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            try:
                self.current_event = self.event_generator.next()
            except StopIteration:
                pass
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            try:
                self.current_event = self.event_generator.next()
            except StopIteration:
                pass
        return self.current_event

    def get_event(self):
        # Get the next event.
        if self.current_event is None:
            try:
                self.current_event = self.event_generator.next()
            except StopIteration:
                pass
        value = self.current_event
        self.current_event = None
        return value

    def __iter__(self):
        # Iterator protocol.
        return self.event_generator

    def parse_stream(self):
        # STREAM-START implicit_document? explicit_document* STREAM-END

        # Parse start of stream.
        token = self.get_token()
        yield StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Parse implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            yield DocumentStartEvent(start_mark, end_mark,
                    explicit=False)
            for event in self.parse_block_node():
                yield event
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            explicit = False
            while self.check_token(DocumentEndToken):
                token = self.get_token()
                end_mark = token.end_mark
                explicit = True
            yield DocumentEndEvent(start_mark, end_mark,
                    explicit=explicit)

        # Parse explicit documents.
        while not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            yield DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            if self.check_token(DirectiveToken,
                    DocumentStartToken, DocumentEndToken, StreamEndToken):
                yield self.process_empty_scalar(token.end_mark)
            else:
                for event in self.parse_block_node():
                    yield event
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            explicit = False
            while self.check_token(DocumentEndToken):
                token = self.get_token()
                end_mark = token.end_mark
                explicit=True
            yield DocumentEndEvent(start_mark, end_mark,
                    explicit=explicit)

        # Parse end of stream.
        token = self.get_token()
        yield StreamEndEvent(token.start_mark, token.end_mark)

    def process_directives(self):
        # DIRECTIVE*
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == u'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == u'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle.encode('utf-8'),
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        # block_node    ::= ALIAS | properties? block_content
        # flow_node     ::= ALIAS | properties? flow_content
        # properties    ::= TAG ANCHOR? | ANCHOR TAG?
        # block_content     ::= block_collection | flow_collection | SCALAR
        # flow_content      ::= flow_collection | SCALAR
        # block_collection  ::= block_sequence | block_mapping
        # block_node_or_indentless_sequence ::= ALIAS | properties?
        #                                       (block_content | indentless_block_sequence)
        if self.check_token(AliasToken):
            token = self.get_token()
            yield AliasEvent(token.value, token.start_mark, token.end_mark)
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None and tag != u'!':
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle.encode('utf-8'),
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == u'!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            collection_events = None
            implicit = (tag is None or tag == u'!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                collection_events = self.parse_indentless_sequence()
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == u'!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    collection_events = self.parse_flow_sequence()
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    collection_events = self.parse_flow_mapping()
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    collection_events = self.parse_block_sequence()
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    collection_events = self.parse_block_mapping()
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), u'',
                            start_mark, end_mark)
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while scanning a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
            yield event
            if collection_events is not None:
                for event in collection_events:
                    yield event

    def parse_block_sequence(self):
        # BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
        token = self.get_token()
        start_mark = token.start_mark
        while self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                for event in self.parse_block_node():
                    yield event
            else:
                yield self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while scanning a block collection", start_mark,
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        yield SequenceEndEvent(token.start_mark, token.end_mark)

    def parse_indentless_sequence(self):
        # (BLOCK-ENTRY block_node?)+
        while self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                for event in self.parse_block_node():
                    yield event
            else:
                yield self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        yield SequenceEndEvent(token.start_mark, token.start_mark)

    def parse_block_mapping(self):
        # BLOCK-MAPPING_START
        #   ((KEY block_node_or_indentless_sequence?)?
        #   (VALUE block_node_or_indentless_sequence?)?)*
        # BLOCK-END
        token = self.get_token()
        start_mark = token.start_mark
        while self.check_token(KeyToken, ValueToken):
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                    for event in self.parse_block_node_or_indentless_sequence():
                        yield event
                else:
                    yield self.process_empty_scalar(token.end_mark)
            if self.check_token(ValueToken):
                token = self.get_token()
                if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                    for event in self.parse_block_node_or_indentless_sequence():
                        yield event
                else:
                    yield self.process_empty_scalar(token.end_mark)
            else:
                token = self.peek_token()
                yield self.process_empty_scalar(token.start_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while scanning a block mapping", start_mark,
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        yield MappingEndEvent(token.start_mark, token.end_mark)

    def parse_flow_sequence(self):
        # flow_sequence     ::= FLOW-SEQUENCE-START
        #                       (flow_sequence_entry FLOW-ENTRY)*
        #                       flow_sequence_entry?
        #                       FLOW-SEQUENCE-END
        # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
        #
        # Note that while production rules for both flow_sequence_entry and
        # flow_mapping_entry are equal, their interpretations are different.
        # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
        # generate an inline mapping (set syntax).
        token = self.get_token()
        start_mark = token.start_mark
        while not self.check_token(FlowSequenceEndToken):
            if self.check_token(KeyToken):
                token = self.get_token()
                yield MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowSequenceEndToken):
                    for event in self.parse_flow_node():
                        yield event
                else:
                    yield self.process_empty_scalar(token.end_mark)
                if self.check_token(ValueToken):
                    token = self.get_token()
                    if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                        for event in self.parse_flow_node():
                            yield event
                    else:
                        yield self.process_empty_scalar(token.end_mark)
                else:
                    token = self.peek_token()
                    yield self.process_empty_scalar(token.start_mark)
                token = self.peek_token()
                yield MappingEndEvent(token.start_mark, token.start_mark)
            else:
                for event in self.parse_flow_node():
                    yield event
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                token = self.peek_token()
                raise ParserError("while scanning a flow sequence", start_mark,
                        "expected ',' or ']', but got %r" % token.id, token.start_mark)
            if self.check_token(FlowEntryToken):
                self.get_token()
        token = self.get_token()
        yield SequenceEndEvent(token.start_mark, token.end_mark)

    def parse_flow_mapping(self):
        # flow_mapping      ::= FLOW-MAPPING-START
        #                       (flow_mapping_entry FLOW-ENTRY)*
        #                       flow_mapping_entry?
        #                       FLOW-MAPPING-END
        # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
        token = self.get_token()
        start_mark = token.start_mark
        while not self.check_token(FlowMappingEndToken):
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    for event in self.parse_flow_node():
                        yield event
                else:
                    yield self.process_empty_scalar(token.end_mark)
                if self.check_token(ValueToken):
                    token = self.get_token()
                    if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                        for event in self.parse_flow_node():
                            yield event
                    else:
                        yield self.process_empty_scalar(token.end_mark)
                else:
                    token = self.peek_token()
                    yield self.process_empty_scalar(token.start_mark)
            else:
                for event in self.parse_flow_node():
                    yield event
                yield self.process_empty_scalar(self.peek_token().start_mark)
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                token = self.peek_token()
                raise ParserError("while scanning a flow mapping", start_mark,
                        "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(FlowEntryToken):
                self.get_token()
        if not self.check_token(FlowMappingEndToken):
            token = self.peek_token()
            raise ParserError("while scanning a flow mapping", start_mark,
                    "expected '}', but found %r" % token.id, token.start_mark)
        token = self.get_token()
        yield MappingEndEvent(token.start_mark, token.end_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), u'', mark, mark)

