# Natural Language Toolkit: WordNet Browser Application
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Jussi Salmela <jtsalmela@users.sourceforge.net>
#         Paul Bone <pbone@students.csse.unimelb.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A WordNet Browser application which launches the default browser
(if it is not already running) and opens a new tab with a connection
to http://localhost:port/ .  It also starts an HTTP server on the
specified port and begins serving browser requests.  The default
port is 8000.  (For command-line help, run "python wordnet -h")
This application requires that the user's web browser supports
Javascript.

BrowServer is a server for browsing the NLTK Wordnet database It first
launches a browser client to be used for browsing and then starts
serving the requests of that and maybe other clients

Usage::

    browserver.py -h
    browserver.py [-s] [-p <port>]

Options::

    -h or --help
        Display this help message.

    -l <file> or --log-file <file>
        Logs messages to the given file, If this option is not specified
        messages are silently dropped.

    -p <port> or --port <port>
        Run the web server on this TCP port, defaults to 8000.

    -s or --server-mode
        Do not start a web browser, and do not allow a user to
        shutdown the server through the web interface.
"""
# TODO: throughout this package variable names and docstrings need
# modifying to be compliant with NLTK's coding standards.  Tests also
# need to be develop to ensure this continues to work in the face of
# changes to other NLTK packages.

import base64
import copy
import getopt
import html
import io
import logging
import os
import pickle
import secrets
import sys
import threading
import time
import webbrowser
from collections import defaultdict
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import unquote_plus

# Allow this program to run inside the NLTK source tree.
from sys import argv

from nltk.corpus import wordnet as wn
from nltk.corpus.reader.wordnet import Lemma, Synset
from nltk.picklesec import RestrictedUnpickler

# ============================================================================
# Logging Configuration
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('nltk.wordnet_browser')

# Global variables
firstClient = True
server_mode = None
logfile = None

# Security constants
MAX_REQUEST_SIZE = 1024 * 1024  # 1MB max request size
ALLOWED_PATHS = {'index.html', 'index_2.html', 'upper.html', 'upper_2.html', 
                 'web_help.html', 'wx_help.html', 'NLTK Wordnet Browser Database Info.html'}
SESSION_TIMEOUT = 3600  # 1 hour
MAX_WORD_LENGTH = 100
MAX_WORDS_IN_SEARCH = 10


class SecurityHeaders:
    """HTTP security headers for responses"""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'none'; script-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Cache-Control': 'no-store, max-age=0',
        }


class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def sanitize_word(word: str) -> str:
        """Sanitize and validate a word input"""
        if not word or not isinstance(word, str):
            return ""
        
        # Remove any control characters
        word = ''.join(char for char in word if ord(char) >= 32)
        
        # Limit length
        word = word[:MAX_WORD_LENGTH]
        
        # HTML escape for safety
        return html.escape(word.strip())
    
    @staticmethod
    def sanitize_words(words: List[str]) -> List[str]:
        """Sanitize a list of words"""
        sanitized = []
        for word in words[:MAX_WORDS_IN_SEARCH]:  # Limit number of words
            cleaned = InputValidator.sanitize_word(word)
            if cleaned:
                sanitized.append(cleaned)
        return sanitized
    
    @staticmethod
    def validate_path(path: str) -> bool:
        """Validate if a path is allowed"""
        return path in ALLOWED_PATHS
    
    @staticmethod
    def validate_port(port: int) -> bool:
        """Validate port number"""
        return 1024 <= port <= 65535


class RateLimiter:
    """Simple rate limiter for requests"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.RLock()
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request from client IP is allowed"""
        with self._lock:
            now = time.time()
            # Clean old requests
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if now - req_time < self.window_seconds
            ]
            
            # Check if under limit
            if len(self.requests[client_ip]) < self.max_requests:
                self.requests[client_ip].append(now)
                return True
            
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False


class SessionManager:
    """Simple session management"""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def create_session(self) -> str:
        """Create a new session"""
        with self._lock:
            session_id = secrets.token_urlsafe(32)
            self.sessions[session_id] = {
                'created_at': time.time(),
                'last_access': time.time(),
                'data': {}
            }
            return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                # Check timeout
                if time.time() - session['last_access'] < SESSION_TIMEOUT:
                    session['last_access'] = time.time()
                    return session['data']
                else:
                    # Session expired
                    del self.sessions[session_id]
            return None
    
    def cleanup_expired(self):
        """Clean up expired sessions"""
        with self._lock:
            now = time.time()
            expired = [
                sid for sid, session in self.sessions.items()
                if now - session['last_access'] >= SESSION_TIMEOUT
            ]
            for sid in expired:
                del self.sessions[sid]


# Initialize security components
rate_limiter = RateLimiter()
session_manager = SessionManager()


class MyServerHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP request handler with security features"""
    
    # Class variable for server instance
    server_instance = None
    
    def __init__(self, *args, **kwargs):
        self.validator = InputValidator()
        super().__init__(*args, **kwargs)
    
    def log_message(self, format: str, *args):
        """Enhanced logging with security context"""
        global logfile
        
        client_ip = self.client_address[0]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"{client_ip} - - [{timestamp}] {format % args}"
        
        if logfile:
            logfile.write(message + "\n")
            logfile.flush()
        
        logger.info(message)
    
    def send_error_response(self, code: int, message: str, content_type: str = "text/plain"):
        """Send an error response with proper headers"""
        self.send_response(code)
        self.send_header("Content-type", content_type)
        
        # Add security headers
        for header, value in SecurityHeaders.get_headers().items():
            self.send_header(header, value)
        
        self.end_headers()
        
        safe_message = html.escape(message)
        self.wfile.write(safe_message.encode("utf-8"))
    
    def send_success_response(self, content: str, content_type: str = "text/html"):
        """Send a success response with proper headers"""
        self.send_response(200)
        self.send_header("Content-type", content_type)
        
        # Add security headers
        for header, value in SecurityHeaders.get_headers().items():
            self.send_header(header, value)
        
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))
    
    def do_HEAD(self):
        """Handle HEAD requests"""
        self.send_success_response("", "text/html")
    
    def do_GET(self):
        """Handle GET requests with security enhancements"""
        global firstClient
        
        # Rate limiting
        client_ip = self.client_address[0]
        if not rate_limiter.is_allowed(client_ip):
            self.send_error_response(429, "Too many requests")
            return
        
        # Parse and validate path
        raw_path = self.path[1:]
        sp = unquote_plus(raw_path)
        
        # Security: Validate path length
        if len(sp) > MAX_REQUEST_SIZE:
            self.send_error_response(414, "Request URI too long")
            return
        
        try:
            # Handle shutdown request
            if sp == "SHUTDOWN THE SERVER":
                if server_mode:
                    self.send_success_response(
                        "Server must be killed with SIGTERM.", 
                        "text/plain"
                    )
                else:
                    logger.info("Server shutting down via web interface")
                    self.send_success_response("Server shutting down...", "text/plain")
                    # Schedule shutdown after response is sent
                    threading.Thread(target=self._shutdown_server).start()
                return
            
            # Handle empty path (first request)
            elif sp == "":
                if not server_mode and firstClient:
                    firstClient = False
                    page = get_static_index_page(True)
                else:
                    page = get_static_index_page(False)
                self.send_success_response(page)
                return
            
            # Handle HTML file requests with validation
            elif sp.endswith(".html"):
                usp = unquote_plus(sp)
                
                # Validate path
                if not self.validator.validate_path(usp):
                    self.send_error_response(404, "File not found")
                    return
                
                if usp == "NLTK Wordnet Browser Database Info.html":
                    word = "* Database Info *"
                    if os.path.isfile(usp) and os.path.getsize(usp) < MAX_REQUEST_SIZE:
                        try:
                            with open(usp, 'r', encoding='utf-8') as infile:
                                page = infile.read()
                        except (IOError, OSError) as e:
                            logger.error(f"Error reading file {usp}: {e}")
                            page = (
                                f"<p>Error reading database info file: {html.escape(str(e))}</p>"
                                "<p>Run this: <b>python dbinfo_html.py</b> to regenerate it.</p>"
                            )
                    else:
                        page = (
                            "<p>The database info file was not found or is too large.</p>"
                            "<p>Run this: <b>python dbinfo_html.py</b> to produce it.</p>"
                        )
                    
                    full_page = (html_header % html.escape(word)) + page + html_trailer
                    self.send_success_response(full_page)
                else:
                    try:
                        page = get_static_page_by_path(usp)
                        self.send_success_response(page)
                    except FileNotFoundError:
                        self.send_error_response(404, f"Page not found: {html.escape(usp)}")
                return
            
            # Handle search requests
            elif sp.startswith("search"):
                parts = sp.split("?")
                if len(parts) < 2:
                    self.send_error_response(400, "Invalid search request")
                    return
                
                query_params = parts[1].split("&")
                words = []
                for p in query_params:
                    if p.startswith("nextWord"):
                        try:
                            # Get and validate word
                            raw_word = p.split("=")[1].replace("+", " ")
                            sanitized_word = self.validator.sanitize_word(raw_word)
                            if sanitized_word:
                                words.append(sanitized_word)
                        except (IndexError, ValueError):
                            continue
                
                if not words:
                    self.send_error_response(400, "No valid search terms provided")
                    return
                
                # Use first word for display (security: already sanitized)
                word = words[0]
                page, result_word = page_from_word(word)
                self.send_success_response(page)
                return
            
            # Handle lookup requests (fixed XSS vulnerability)
            elif sp.startswith("lookup_"):
                encoded_data = sp[len("lookup_"):]
                try:
                    page, word = page_from_href(encoded_data)
                    self.send_success_response(page)
                except (ValueError, pickle.UnpicklingError, KeyError) as e:
                    logger.error(f"Invalid lookup data: {e}")
                    self.send_error_response(400, "Invalid lookup data")
                return
            
            # Handle start page
            elif sp == "start_page":
                page, word = page_from_word("wordnet")
                self.send_success_response(page)
                return
            
            # Unknown request
            else:
                self.send_error_response(404, f"Unknown request: {html.escape(sp[:100])}")
                
        except Exception as e:
            logger.error(f"Unhandled exception in GET handler: {e}", exc_info=True)
            self.send_error_response(500, "Internal server error")
    
    def _shutdown_server(self):
        """Shutdown the server gracefully"""
        time.sleep(1)  # Give time for response to be sent
        if self.server_instance:
            self.server_instance.shutdown()
    
    def version_string(self):
        """Override server version string for security"""
        return "NLTK-Wordnet-Server"


def get_unique_counter_from_url(sp: str) -> Optional[int]:
    """
    Extract the unique counter from the URL if it has one.  Otherwise return
    null.
    """
    pos = sp.rfind("%23")
    if pos != -1:
        try:
            return int(sp[(pos + 3):])
        except ValueError:
            return None
    return None


def wnb(port: int = 8000, runBrowser: bool = True, logfilename: Optional[str] = None):
    """
    Run NLTK Wordnet Browser Server.

    :param port: The port number for the server to listen on, defaults to 8000
    :type  port: int
    :param runBrowser: True to start a web browser and point it at the web server
    :type  runBrowser: bool
    :param logfilename: File to write logs to
    :type  logfilename: Optional[str]
    """
    global server_mode, logfile
    
    # Validate port
    validator = InputValidator()
    if not validator.validate_port(port):
        logger.error(f"Invalid port number: {port}")
        sys.exit(1)
    
    server_mode = not runBrowser

    # Setup logging
    if logfilename:
        try:
            logfile = open(logfilename, "a", 1)  # 1 means 'line buffering'
        except OSError as e:
            logger.error(f"Couldn't open {logfilename} for writing: {e}")
            sys.exit(1)
    else:
        logfile = None

    # Compute URL and start web browser
    url = f"http://localhost:{port}"

    server_ready = None
    browser_thread = None

    if runBrowser:
        server_ready = threading.Event()
        browser_thread = startBrowser(url, server_ready)

    # Start the server with security enhancements
    # Bind to localhost only to prevent remote access
    try:
        server = HTTPServer(("127.0.0.1", port), MyServerHandler)
        MyServerHandler.server_instance = server
        
        # Set socket timeout for security
        server.socket.settimeout(30)
        
        logger.info(f"NLTK Wordnet browser server running serving: {url}")
        
        if runBrowser:
            server_ready.set()

        # Start session cleanup thread
        def cleanup_sessions():
            while True:
                time.sleep(300)  # Clean every 5 minutes
                session_manager.cleanup_expired()
        
        cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
        cleanup_thread.start()

        server.serve_forever()
        
    except OSError as e:
        logger.error(f"Failed to start server on port {port}: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    finally:
        if runBrowser and browser_thread:
            browser_thread.join()
        if logfile:
            logfile.close()


def startBrowser(url: str, server_ready: threading.Event) -> threading.Thread:
    """Start a browser thread"""
    def run():
        server_ready.wait()
        time.sleep(1)  # Wait a little bit more to avoid race condition
        try:
            webbrowser.open(url, new=2, autoraise=1)
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
    
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


#####################################################################
# Utilities
#####################################################################

"""
WordNet Browser Utilities.

This provides a backend to both wxbrowse and browserver.py.
"""

################################################################################
#
# Main logic for wordnet browser.
#


# This is wrapped inside a function since wn is only available if the
# WordNet corpus is installed.
def _pos_tuples():
    return [
        (wn.NOUN, "N", "noun"),
        (wn.VERB, "V", "verb"),
        (wn.ADJ, "J", "adj"),
        (wn.ADV, "R", "adv"),
    ]


def _pos_match(pos_tuple):
    """
    This function returns the complete pos tuple for the partial pos
    tuple given to it.  It attempts to match it against the first
    non-null component of the given pos tuple.
    """
    if pos_tuple[0] == "s":
        pos_tuple = ("a", pos_tuple[1], pos_tuple[2])
    for n, x in enumerate(pos_tuple):
        if x is not None:
            break
    for pt in _pos_tuples():
        if pt[n] == pos_tuple[n]:
            return pt
    return None


# Relation type constants
HYPONYM = 0
HYPERNYM = 1
CLASS_REGIONAL = 2
PART_HOLONYM = 3
PART_MERONYM = 4
ATTRIBUTE = 5
SUBSTANCE_HOLONYM = 6
SUBSTANCE_MERONYM = 7
MEMBER_HOLONYM = 8
MEMBER_MERONYM = 9
VERB_GROUP = 10
INSTANCE_HYPONYM = 12
INSTANCE_HYPERNYM = 13
CAUSE = 14
ALSO_SEE = 15
SIMILAR = 16
ENTAILMENT = 17
ANTONYM = 18
FRAMES = 19
PERTAINYM = 20
CLASS_CATEGORY = 21
CLASS_USAGE = 22
CLASS_REGIONAL = 23
DERIVATIONALLY_RELATED_FORM = 25
INDIRECT_HYPERNYMS = 26


def lemma_property(word: str, synset: Synset, func):
    def flatten(l):
        if l == []:
            return []
        else:
            return l[0] + flatten(l[1:])

    return flatten([func(l) for l in synset.lemmas() if l.name() == word])


def rebuild_tree(orig_tree):
    node = orig_tree[0]
    children = orig_tree[1:]
    return (node, [rebuild_tree(t) for t in children])


def get_relations_data(word: str, synset: Synset):
    """
    Get synset relations data for a synset.  Note that this doesn't
    yet support things such as full hyponym vs direct hyponym.
    """
    if synset.pos() == wn.NOUN:
        return (
            (HYPONYM, "Hyponyms", synset.hyponyms()),
            (INSTANCE_HYPONYM, "Instance hyponyms", synset.instance_hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            (INSTANCE_HYPERNYM, "Instance hypernyms", synset.instance_hypernyms()),
            (PART_HOLONYM, "Part holonyms", synset.part_holonyms()),
            (PART_MERONYM, "Part meronyms", synset.part_meronyms()),
            (SUBSTANCE_HOLONYM, "Substance holonyms", synset.substance_holonyms()),
            (SUBSTANCE_MERONYM, "Substance meronyms", synset.substance_meronyms()),
            (MEMBER_HOLONYM, "Member holonyms", synset.member_holonyms()),
            (MEMBER_MERONYM, "Member meronyms", synset.member_meronyms()),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ANTONYM, "Antonyms", lemma_property(word, synset, lambda l: l.antonyms())),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.VERB:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (HYPONYM, "Hyponym", synset.hyponyms()),
            (HYPERNYM, "Direct hypernyms", synset.hypernyms()),
            (
                INDIRECT_HYPERNYMS,
                "Indirect hypernyms",
                rebuild_tree(synset.tree(lambda x: x.hypernyms()))[1],
            ),
            (ENTAILMENT, "Entailments", synset.entailments()),
            (CAUSE, "Causes", synset.causes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
            (VERB_GROUP, "Verb Groups", synset.verb_groups()),
            (
                DERIVATIONALLY_RELATED_FORM,
                "Derivationally related form",
                lemma_property(
                    word, synset, lambda l: l.derivationally_related_forms()
                ),
            ),
        )
    elif synset.pos() == wn.ADJ or synset.pos() == wn.ADJ_SAT:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
            (SIMILAR, "Similar to", synset.similar_tos()),
            (
                PERTAINYM,
                "Pertainyms",
                lemma_property(word, synset, lambda l: l.pertainyms()),
            ),
            (ATTRIBUTE, "Attributes", synset.attributes()),
            (ALSO_SEE, "Also see", synset.also_sees()),
        )
    elif synset.pos() == wn.ADV:
        return (
            (ANTONYM, "Antonym", lemma_property(word, synset, lambda l: l.antonyms())),
        )
    else:
        raise TypeError(f"Unhandled synset POS type: {synset.pos()}")


# HTML templates with improved security
html_header = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; connect-src 'self'; img-src 'self'; style-src 'self';">
    <title>NLTK Wordnet Browser - {}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        ul {{ list-style-type: none; padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        .warning {{ color: #cc0000; font-weight: bold; }}
        .info {{ color: #006600; }}
    </style>
</head>
<body>
"""

html_trailer = """
</body>
</html>
"""

explanation = """
<h3>Search Help</h3>
<ul>
    <li>The display below the line is an example of the output the browser shows you when you enter a search word. The search word was <b>green</b>.</li>
    <li>The search result shows for different parts of speech the <b>synsets</b> i.e. different meanings for the word.</li>
    <li>All underlined texts are hypertext links. There are two types of links: word links and others. Clicking a word link carries out a search for the word in the Wordnet database.</li>
    <li>Clicking a link of the other type opens a display section of data attached to that link. Clicking that link a second time closes the section again.</li>
    <li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
    <li>Clicking on a relation name opens a section that displays the associated synsets.</li>
    <li>Type a search word in the <b>Word</b> field and start the search by the <b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
<hr>
"""

# HTML helper functions
def _bold(txt: str) -> str:
    return f"<b>{txt}</b>"


def _center(txt: str) -> str:
    return f"<center>{txt}</center>"


def _hlev(n: int, txt: str) -> str:
    return f"<h{n}>{txt}</h{n}>"


def _italic(txt: str) -> str:
    return f"<i>{txt}</i>"


def _li(txt: str) -> str:
    return f"<li>{txt}</li>"


def pg(word: str, body: str) -> str:
    """
    Return a HTML page of NLTK Browser format constructed from the
    word and body

    :param word: The word that the body corresponds to
    :type word: str
    :param body: The HTML body corresponding to the word
    :type body: str
    :return: a HTML page for the word-body combination
    :rtype: str
    """
    return html_header.format(html.escape(word)) + body + html_trailer


def _ul(txt: str) -> str:
    return f"<ul>{txt}</ul>"


def _abbc(txt: str) -> str:
    """
    abbc = asterisks, breaks, bold, center
    """
    return _center(_bold("<br>" * 10 + "*" * 10 + " " + txt + " " + "*" * 10))


full_hyponym_cont_text = _ul(_li(_italic("(has full hyponym continuation)"))) + "\n"


def _get_synset(synset_key: str) -> Synset:
    """
    The synset key is the unique name of the synset, this can be
    retrieved via synset.name()
    """
    return wn.synset(synset_key)


def _collect_one_synset(
    word: str, 
    synset: Union[Synset, Tuple], 
    synset_relations: Dict[str, Set[int]]
) -> str:
    """
    Returns the HTML string for one synset or word

    :param word: the current word
    :type word: str
    :param synset: a synset
    :type synset: Synset
    :param synset_relations: information about which synset relations to display
    :type synset_relations: dict(synset_key, set(relation_id))
    :return: The HTML string built for this synset
    :rtype: str
    """
    if isinstance(synset, tuple):  # It's a word
        raise NotImplementedError("word not supported by _collect_one_synset")

    typ = "S"
    pos_tuple = _pos_match((synset.pos(), None, None))
    if pos_tuple is None:
        raise ValueError(f"Invalid POS: {synset.pos()}")
    
    descr = pos_tuple[2]
    ref = copy.deepcopy(Reference(word, synset_relations))
    ref.toggle_synset(synset)
    synset_label = typ + ";"
    
    if synset.name() in synset_relations:
        synset_label = _bold(synset_label)
    
    s = f"<li>{make_lookup_link(ref, synset_label)} ({descr}) "

    def format_lemma(w: str) -> str:
        w = w.replace("_", " ")
        if w.lower() == word:
            return _bold(w)
        else:
            ref = Reference(w)
            return make_lookup_link(ref, w)

    s += ", ".join(format_lemma(l.name()) for l in synset.lemmas())

    gl = " ({}) <i>{}</i> ".format(
        html.escape(synset.definition()),
        html.escape("; ".join(f'"{e}"' for e in synset.examples())),
    )
    return s + gl + _synset_relations(word, synset, synset_relations) + "</li>\n"


def _collect_all_synsets(
    word: str, 
    pos: str, 
    synset_relations: Dict[str, Set[int]] = None
) -> str:
    """Return a HTML unordered list of synsets for the given word and part of speech."""
    if synset_relations is None:
        synset_relations = {}
    
    return "<ul>%s\n</ul>\n" % "".join(
        _collect_one_synset(word, synset, synset_relations)
        for synset in wn.synsets(word, pos)
    )


def _synset_relations(
    word: str, 
    synset: Synset, 
    synset_relations: Dict[str, Set[int]]
) -> str:
    """
    Builds the HTML string for the relations of a synset

    :param word: The current word
    :type word: str
    :param synset: The synset for which we're building the relations.
    :type synset: Synset
    :param synset_relations: synset keys and relation types for which to display relations.
    :type synset_relations: dict(synset_key, set(relation_type))
    :return: The HTML for a synset's relations
    :rtype: str
    """
    if synset.name() not in synset_relations:
        return ""
    
    ref = Reference(word, synset_relations)

    def relation_html(r):
        if isinstance(r, Synset):
            safe_word = html.escape(r.lemma_names()[0])
            return make_lookup_link(Reference(safe_word), safe_word)
        elif isinstance(r, Lemma):
            return relation_html(r.synset())
        elif isinstance(r, tuple):
            # It's probably a tuple containing a Synset and a list of similar tuples
            return "{}\n<ul>{}</ul>\n".format(
                relation_html(r[0]),
                "".join(f"<li>{relation_html(sr)}</li>\n" for sr in r[1]),
            )
        else:
            raise TypeError(
                f"r must be a synset, lemma or list, it was: type(r) = {type(r)}"
            )

    def make_synset_html(db_name: int, disp_name: str, rels: List) -> str:
        synset_html = "<i>%s</i>\n" % make_lookup_link(
            copy.deepcopy(ref).toggle_synset_relation(synset, db_name),
            html.escape(disp_name),
        )

        if db_name in ref.synset_relations[synset.name()]:
            synset_html += "<ul>%s</ul>\n" % "".join(
                f"<li>{relation_html(r)}</li>\n" for r in rels
            )

        return synset_html

    html = (
        "<ul>"
        + "\n".join(
            f"<li>{make_synset_html(*rel_data)}</li>"
            for rel_data in get_relations_data(word, synset)
            if rel_data[2]
        )
        + "</ul>"
    )

    return html


class Reference:
    """
    A reference to a page that may be generated by page_word
    """

    def __init__(self, word: str, synset_relations: Optional[Dict[str, Set[int]]] = None):
        """
        Build a reference to a new page.

        word is the word or words (separated by commas) for which to
        search for synsets of

        synset_relations is a dictionary of synset keys to sets of
        synset relation identifiers to unfold a list of synset
        relations for.
        """
        self.word = word
        self.synset_relations = synset_relations or {}

    def encode(self) -> str:
        """
        Encode this reference into a string to be used in a URL.
        """
        # This uses a tuple rather than an object since the python
        # pickle representation is much smaller and there is no need
        # to represent the complete object.
        string = pickle.dumps((self.word, self.synset_relations), -1)
        return base64.urlsafe_b64encode(string).decode()

    @staticmethod
    def decode(string: str) -> 'Reference':
        """
        Decode a reference encoded with Reference.encode
        
        :raises ValueError: If decoding fails
        """
        try:
            decoded = base64.urlsafe_b64decode(string.encode())
            word, synset_relations = RestrictedUnpickler(io.BytesIO(decoded)).load()
            return Reference(word, synset_relations)
        except (pickle.UnpicklingError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid reference data: {e}")

    def toggle_synset_relation(self, synset: Synset, relation: int) -> 'Reference':
        """
        Toggle the display of the relations for the given synset and
        relation type.

        This function will throw a KeyError if the synset is currently
        not being displayed.
        """
        if synset.name() in self.synset_relations:
            if relation in self.synset_relations[synset.name()]:
                self.synset_relations[synset.name()].remove(relation)
            else:
                self.synset_relations[synset.name()].add(relation)

        return self

    def toggle_synset(self, synset: Synset) -> 'Reference':
        """
        Toggle displaying of the relation types for the given synset
        """
        if synset.name() in self.synset_relations:
            del self.synset_relations[synset.name()]
        else:
            self.synset_relations[synset.name()] = set()

        return self


def make_lookup_link(ref: Reference, label: str) -> str:
    """Create a secure lookup link"""
    safe_label = html.escape(label)
    return f'<a href="lookup_{ref.encode()}">{safe_label}</a>'


def page_from_word(word: str) -> Tuple[str, str]:
    """
    Return a HTML page for the given word.

    :type word: str
    :param word: The currently active word
    :return: A tuple (page,word), where page is the new current HTML page
        to be sent to the browser and
        word is the new current word
    :rtype: A tuple (str,str)
    """
    validator = InputValidator()
    safe_word = validator.sanitize_word(word)
    return page_from_reference(Reference(safe_word))


def page_from_href(href: str) -> Tuple[str, str]:
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: str
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    
    :raises ValueError: If href is invalid
    """
    ref = Reference.decode(href)
    return page_from_reference(ref)


def page_from_reference(href: Reference) -> Tuple[str, str]:
    """
    Returns a tuple of the HTML page built and the new current word

    :param href: The hypertext reference to be solved
    :type href: Reference
    :return: A tuple (page,word), where page is the new current HTML page
             to be sent to the browser and
             word is the new current word
    :rtype: A tuple (str,str)
    """
    validator = InputValidator()
    raw_word = href.word
    safe_word = validator.sanitize_word(raw_word)
    
    pos_forms = defaultdict(list)
    
    # Split and sanitize words
    words = [w.strip().lower().replace(" ", "_") for w in safe_word.split(",")]
    words = validator.sanitize_words(words)
    
    if not words:
        # No valid words were found
        return "", "Please specify a valid word to search for."

    # Look up morphological forms
    for w in words:
        for pos in [wn.NOUN, wn.VERB, wn.ADJ, wn.ADV]:
            form = wn.morphy(w, pos)
            if form and form not in pos_forms[pos]:
                pos_forms[pos].append(form)
    
    body = ""
    for pos, pos_str, name in _pos_tuples():
        if pos in pos_forms:
            body += _hlev(3, html.escape(name)) + "\n"
            for w in pos_forms[pos]:
                # Not all words of exc files are in the database, skip
                # to the next word if a KeyError is raised.
                try:
                    safe_w = html.escape(w)
                    body += _collect_all_synsets(safe_w, pos, href.synset_relations)
                except KeyError:
                    logger.debug(f"Word not found in database: {w}")
                    continue
    
    if not body:
        # FIXED: XSS vulnerability - word is properly escaped now
        safe_word_display = html.escape(raw_word)
        body = f"The word or words '{safe_word_display}' were not found in the dictionary."
    
    return body, safe_word


#####################################################################
# Static pages
#####################################################################


def get_static_page_by_path(path: str) -> str:
    """
    Return a static HTML page from the path given.
    
    :raises FileNotFoundError: If path is invalid
    """
    validator = InputValidator()
    if not validator.validate_path(path):
        raise FileNotFoundError(f"Invalid path: {path}")
    
    if path == "index_2.html":
        return get_static_index_page(False)
    elif path == "index.html":
        return get_static_index_page(True)
    elif path == "NLTK Wordnet Browser Database Info.html":
        return "Display of Wordnet Database Statistics is not supported"
    elif path == "upper_2.html":
        return get_static_upper_page(False)
    elif path == "upper.html":
        return get_static_upper_page(True)
    elif path == "web_help.html":
        return get_static_web_help_page()
    elif path == "wx_help.html":
        return get_static_wx_help_page()
    
    raise FileNotFoundError(f"Unknown path: {path}")


def get_static_web_help_page() -> str:
    """
    Return the static web help page.
    """
    return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NLTK Wordnet Browser Help</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
        h1, h2, h3 { color: #333; }
        a { color: #0066cc; text-decoration: none; }
        a:hover { text-decoration: underline; }
        ul { margin-left: 20px; }
        li { margin: 5px 0; }
    </style>
</head>
<body>
<h1>NLTK Wordnet Browser Help</h1>

<p>The NLTK Wordnet Browser is a tool to use in browsing the Wordnet database. It tries to behave like the Wordnet project's web browser but the difference is that the NLTK Wordnet Browser uses a local Wordnet database.</p>

<p><b>You are using the Javascript client part of the NLTK Wordnet BrowseServer.</b> We assume your browser is in tab sheets enabled mode.</p>

<p>For background information on Wordnet, see the Wordnet project home page: <a href="https://wordnet.princeton.edu/" target="_blank" rel="noopener noreferrer"><b>WordNet Princeton</b></a>. For more information on the NLTK project, see the project home: <a href="https://www.nltk.org/" target="_blank" rel="noopener noreferrer"><b>NLTK Project</b></a>. To get an idea of what the Wordnet version used by this browser includes choose <b>Show Database Info</b> from the <b>View</b> submenu.</p>

<h2>Word Search</h2>
<p>The word to be searched is typed into the <b>New Word</b> field and the search started with Enter or by clicking the <b>Search</b> button. There is no uppercase/lowercase distinction: the search word is transformed to lowercase before the search.</p>

<p>In addition, the word does not have to be in base form. The browser tries to find the possible base form(s) by making certain morphological substitutions.</p>

<p>The result of a search is a display of one or more <b>synsets</b> for every part of speech in which a form of the search word was found to occur. A synset is a set of words having the same sense or meaning. Each word in a synset that is underlined is a hyperlink which can be clicked to trigger an automatic search for that word.</p>

<p>Every synset has a hyperlink <b>S:</b> at the start of its display line. Clicking that symbol shows you the name of every <b>relation</b> that this synset is part of. Every relation name is a hyperlink that opens up a display for that relation. Clicking it another time closes the display again.</p>

<p>It is also possible to give two or more words or collocations to be searched at the same time separating them with a comma.</p>

<h2>The Buttons</h2>
<p>The <b>Search</b> and <b>Help</b> buttons need no more explanation.</p>
<p>The <b>Show Database Info</b> button shows a collection of Wordnet database statistics.</p>
<p>The <b>Shutdown the Server</b> button is shown for the first client of the BrowServer program.</p>

</body>
</html>
"""


def get_static_wx_help_page() -> str:
    """
    Return the static wx help page.
    """
    return get_static_web_help_page()  # Same content for now


def get_static_welcome_message() -> str:
    """
    Get the static welcome page.
    """
    return """
<h3>Search Help</h3>
<ul>
    <li>The display below the line is an example of the output the browser shows you when you enter a search word. The search word was <b>green</b>.</li>
    <li>The search result shows for different parts of speech the <b>synsets</b> i.e. different meanings for the word.</li>
    <li>All underlined texts are hypertext links. Clicking a word link carries out a search for the word in the Wordnet database.</li>
    <li>Clicking <u>S:</u> opens a section showing the relations for that synset.</li>
    <li>Type a search word in the <b>Next Word</b> field and start the search by the <b>Enter/Return</b> key or click the <b>Search</b> button.</li>
</ul>
"""


def get_static_index_page(with_shutdown: bool) -> str:
    """
    Get the static index page.
    """
    template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NLTK Wordnet Browser</title>
    <style>
        body { margin: 0; padding: 0; }
        frameset { border: none; }
    </style>
</head>
<frameset rows="80px, *">
    <frame src="%s" name="header" noresize>
    <frame src="start_page" name="body" noresize>
</frameset>
</html>
"""
    upper_link = "upper.html" if with_shutdown else "upper_2.html"
    return template % upper_link


def get_static_upper_page(with_shutdown: bool) -> str:
    """
    Return the upper frame page.

    If with_shutdown is True then a 'shutdown' button is also provided
    to shutdown the server.
    """
    template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>NLTK Wordnet Browser - Controls</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 10px; 
            padding: 0;
            background-color: #f5f5f5;
        }
        .container { 
            display: flex; 
            align-items: center; 
            gap: 15px;
            flex-wrap: wrap;
        }
        input[type="text"] { 
            padding: 5px; 
            font-size: 14px;
            border: 1px solid #ccc;
            border-radius: 3px;
        }
        input[type="submit"] { 
            padding: 5px 15px;
            background-color: #0066cc;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #0052a3;
        }
        a { 
            color: #0066cc; 
            text-decoration: none;
            padding: 5px 10px;
        }
        a:hover {
            text-decoration: underline;
        }
        .shutdown { 
            color: #cc0000;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <form method="GET" action="search" target="body">
            <label for="nextWord">Word:</label>
            <input type="text" id="nextWord" name="nextWord" size="20" 
                   maxlength="100" placeholder="Enter word to search">
            <input type="submit" value="Search">
        </form>
        <a href="web_help.html" target="body">Help</a>
        %s
    </div>
</body>
</html>
"""
    shutdown_link = '<a href="SHUTDOWN THE SERVER" class="shutdown">Shutdown Server</a>' if with_shutdown else ""
    return template % shutdown_link


def usage():
    """Display the command line help message."""
    print(__doc__)


def app():
    """Main application entry point"""
    # Parse and interpret options
    try:
        opts, _ = getopt.getopt(
            argv[1:], "l:p:sh", ["logfile=", "port=", "server-mode", "help"]
        )
    except getopt.GetoptError as e:
        print(f"Error parsing options: {e}")
        usage()
        sys.exit(1)
    
    port = 8000
    server_mode = False
    help_mode = False
    logfilename = None
    
    for opt, value in opts:
        if opt in ("-l", "--logfile"):
            logfilename = str(value)
        elif opt in ("-p", "--port"):
            try:
                port = int(value)
            except ValueError:
                print(f"Invalid port number: {value}")
                sys.exit(1)
        elif opt in ("-s", "--server-mode"):
            server_mode = True
        elif opt in ("-h", "--help"):
            help_mode = True

    if help_mode:
        usage()
    else:
        try:
            wnb(port, not server_mode, logfilename)
        except KeyboardInterrupt:
            print("\nServer stopped by user")
        except Exception as e:
            print(f"Error running server: {e}")
            logger.error(f"Server error: {e}", exc_info=True)
            sys.exit(1)


if __name__ == "__main__":
    app()

__all__ = ["app"]
